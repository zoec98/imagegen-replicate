"""Immich upload client boundary."""

from __future__ import annotations

import mimetypes
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx


IMMICH_GALLERY_PAGE_SIZE = 20


@dataclass(frozen=True)
class ImmichUploadResult:
    status: str
    asset_id: str | None = None


@dataclass(frozen=True)
class ImmichGalleryAsset:
    asset_id: str
    thumbnail_url: str
    label: str | None
    created_at: str | None
    width: int | None
    height: int | None
    import_eligible: bool


@dataclass(frozen=True)
class ImmichGalleryPage:
    assets: list[ImmichGalleryAsset]
    page: int
    page_size: int
    next_page: int | None
    previous_page: int | None


class ImmichUploadError(RuntimeError):
    pass


class ImmichGalleryError(RuntimeError):
    pass


@dataclass(frozen=True)
class ImmichClient:
    base_url: str
    api_key: str
    album_id: str
    timeout: float = 60.0

    def upload_image(
        self,
        image_path: Path,
        *,
        client: httpx.Client | None = None,
    ) -> ImmichUploadResult:
        close_client = client is None
        http_client = client or httpx.Client(timeout=self.timeout)
        try:
            result = self._upload_asset(image_path, http_client)
            if not result.asset_id:
                raise ImmichUploadError("Immich upload did not return an asset id.")
            self._add_asset_to_album(result.asset_id, http_client)
            return result
        finally:
            if close_client:
                http_client.close()

    def list_main_gallery_assets(
        self,
        *,
        page: int = 1,
        page_size: int = IMMICH_GALLERY_PAGE_SIZE,
        client: httpx.Client | None = None,
    ) -> ImmichGalleryPage:
        if page < 1:
            raise ImmichGalleryError("Immich gallery page must be 1 or greater.")
        if page_size != IMMICH_GALLERY_PAGE_SIZE:
            raise ImmichGalleryError(
                f"Immich gallery page size must be {IMMICH_GALLERY_PAGE_SIZE}."
            )

        close_client = client is None
        http_client = client or httpx.Client(timeout=self.timeout)
        try:
            response = http_client.post(
                self._api_url("/api/search/metadata"),
                headers=self._headers(),
                json={
                    "page": page,
                    "size": page_size,
                    "type": "IMAGE",
                    "withExif": True,
                },
            )
            if response.status_code != 200:
                raise ImmichGalleryError(
                    _response_error_message(
                        response,
                        (
                            "Immich gallery request failed with status "
                            f"{response.status_code}."
                        ),
                        secret=self.api_key,
                    )
                )
            payload = _json_response(response)
            assets, total = self._gallery_assets(payload)
            next_page = page + 1 if _has_next_page(page, page_size, len(assets), total) else None
            previous_page = page - 1 if page > 1 else None
            return ImmichGalleryPage(
                assets=assets,
                page=page,
                page_size=page_size,
                next_page=next_page,
                previous_page=previous_page,
            )
        finally:
            if close_client:
                http_client.close()

    def download_asset(
        self,
        asset_id: str,
        *,
        client: httpx.Client | None = None,
    ) -> bytes:
        if not asset_id.strip():
            raise ImmichGalleryError("Immich asset id is required.")

        close_client = client is None
        http_client = client or httpx.Client(timeout=self.timeout)
        try:
            response = http_client.get(
                self._api_url(f"/api/assets/{quote(asset_id)}/original"),
                headers=self._headers(),
            )
            if response.status_code != 200:
                raise ImmichGalleryError(
                    _response_error_message(
                        response,
                        (
                            "Immich asset download failed with status "
                            f"{response.status_code}."
                        ),
                        secret=self.api_key,
                    )
                )
            return response.content
        finally:
            if close_client:
                http_client.close()

    def download_thumbnail(
        self,
        asset_id: str,
        *,
        client: httpx.Client | None = None,
    ) -> tuple[bytes, str]:
        if not asset_id.strip():
            raise ImmichGalleryError("Immich asset id is required.")

        close_client = client is None
        http_client = client or httpx.Client(timeout=self.timeout)
        try:
            response = http_client.get(
                self._api_url(
                    f"/api/assets/{quote(asset_id)}/thumbnail?size=thumbnail"
                ),
                headers=self._headers(),
            )
            if response.status_code != 200:
                raise ImmichGalleryError(
                    _response_error_message(
                        response,
                        (
                            "Immich asset thumbnail failed with status "
                            f"{response.status_code}."
                        ),
                        secret=self.api_key,
                    )
                )
            return response.content, _content_type(response)
        finally:
            if close_client:
                http_client.close()

    def _upload_asset(
        self,
        image_path: Path,
        client: httpx.Client,
    ) -> ImmichUploadResult:
        stat = image_path.stat()
        timestamp = _timestamp(stat.st_mtime)
        content_type = (
            mimetypes.guess_type(image_path.name)[0] or "application/octet-stream"
        )
        with image_path.open("rb") as image_file:
            response = client.post(
                self._api_url("/api/assets"),
                headers=self._headers(),
                data={
                    "deviceAssetId": _device_asset_id(image_path, stat),
                    "deviceId": "imagegen",
                    "fileCreatedAt": timestamp,
                    "fileModifiedAt": timestamp,
                    "isFavorite": "false",
                },
                files={
                    "assetData": (image_path.name, image_file, content_type),
                },
            )
        if response.status_code not in {200, 201}:
            raise ImmichUploadError(
                _response_error_message(
                    response,
                    f"Immich upload failed with status {response.status_code}.",
                    secret=self.api_key,
                )
            )
        payload = _json_response(response)
        upload_status = str(payload.get("status", "")).lower()
        asset_id = _asset_id(payload)
        if upload_status == "duplicate":
            return ImmichUploadResult(status="already_present", asset_id=asset_id)
        return ImmichUploadResult(status="uploaded", asset_id=asset_id)

    def _add_asset_to_album(self, asset_id: str, client: httpx.Client) -> None:
        response = client.put(
            self._api_url(f"/api/albums/{self.album_id}/assets"),
            headers=self._headers(),
            json={"ids": [asset_id]},
        )
        if response.status_code not in {200, 201}:
            raise ImmichUploadError(
                _response_error_message(
                    response,
                    f"Immich album attach failed with status {response.status_code}.",
                    secret=self.api_key,
                )
            )

        payload = _json_response(response)
        if isinstance(payload, list):
            failures = [
                item
                for item in payload
                if isinstance(item, dict) and item.get("success") is False
            ]
            if failures and not all(_is_album_duplicate(item) for item in failures):
                raise ImmichUploadError("Immich album attach failed.")

    def _headers(self) -> dict[str, str]:
        return {
            "Accept": "application/json",
            "x-api-key": self.api_key,
        }

    def _api_url(self, path: str) -> str:
        return f"{self.base_url.rstrip('/')}{path}"

    def _gallery_assets(self, payload: Any) -> tuple[list[ImmichGalleryAsset], int | None]:
        items, total = _search_items(payload)
        if items is None:
            raise ImmichGalleryError("Immich gallery response was malformed.")
        assets: list[ImmichGalleryAsset] = []
        for item in items:
            if not isinstance(item, dict):
                raise ImmichGalleryError("Immich gallery response was malformed.")
            asset = self._gallery_asset(item)
            if asset is not None:
                assets.append(asset)
        return assets, total

    def _gallery_asset(self, item: dict[str, Any]) -> ImmichGalleryAsset | None:
        asset_id = item.get("id")
        if not isinstance(asset_id, str) or not asset_id:
            raise ImmichGalleryError("Immich gallery response was malformed.")

        asset_type = item.get("type")
        import_eligible = not isinstance(asset_type, str) or asset_type.upper() == "IMAGE"
        if not import_eligible:
            return None

        return ImmichGalleryAsset(
            asset_id=asset_id,
            thumbnail_url=self._api_url(
                f"/api/assets/{quote(asset_id)}/thumbnail?size=thumbnail"
            ),
            label=_asset_label(item),
            created_at=_asset_date(item),
            width=_int_value(item.get("exifInfo"), "exifImageWidth")
            or _int_value(item, "exifImageWidth"),
            height=_int_value(item.get("exifInfo"), "exifImageHeight")
            or _int_value(item, "exifImageHeight"),
            import_eligible=True,
        )


def _json_response(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return {}


def _content_type(response: httpx.Response) -> str:
    content_type = response.headers.get("Content-Type", "").split(";", 1)[0].strip()
    return content_type or "image/jpeg"


def _response_error_message(
    response: httpx.Response,
    fallback: str,
    *,
    secret: str,
) -> str:
    payload = _json_response(response)
    message = payload.get("message") if isinstance(payload, dict) else None
    if isinstance(message, list):
        message = " ".join(str(item) for item in message if str(item).strip())
    if not isinstance(message, str) or not message.strip():
        return fallback
    return _redact_secret(message.strip(), secret=secret)


def _redact_secret(message: str, *, secret: str) -> str:
    if not secret:
        return message
    return message.replace(secret, "[redacted]")


def _search_items(payload: Any) -> tuple[list[Any] | None, int | None]:
    if isinstance(payload, dict):
        assets = payload.get("assets")
        if isinstance(assets, dict):
            items = assets.get("items")
            total = _optional_int(assets.get("total"))
            if isinstance(items, list):
                return items, total
        items = payload.get("items")
        total = _optional_int(payload.get("total"))
        if isinstance(items, list):
            return items, total
    return None, None


def _has_next_page(
    page: int,
    page_size: int,
    item_count: int,
    total: int | None,
) -> bool:
    if total is not None:
        return page * page_size < total
    return item_count == page_size


def _asset_label(item: dict[str, Any]) -> str | None:
    for key in ("originalFileName", "originalPath"):
        value = item.get(key)
        if isinstance(value, str) and value:
            return Path(value).name
    return None


def _asset_date(item: dict[str, Any]) -> str | None:
    for key in ("fileCreatedAt", "localDateTime", "fileModifiedAt"):
        value = item.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _int_value(payload: Any, key: str) -> int | None:
    if not isinstance(payload, dict):
        return None
    return _optional_int(payload.get(key))


def _optional_int(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def _asset_id(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    for key in ("id", "assetId"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _is_album_duplicate(item: dict[str, object]) -> bool:
    error = str(item.get("error", "")).lower()
    return "duplicate" in error or "already" in error


def _timestamp(seconds: float) -> str:
    return datetime.fromtimestamp(seconds, UTC).isoformat()


def _device_asset_id(image_path: Path, stat: object) -> str:
    return (
        f"imagegen:{image_path.name}:"
        f"{getattr(stat, 'st_size')}:{getattr(stat, 'st_mtime_ns')}"
    )
