"""Immich upload client boundary."""

from __future__ import annotations

import mimetypes
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx


@dataclass(frozen=True)
class ImmichUploadResult:
    status: str
    asset_id: str | None = None


class ImmichUploadError(RuntimeError):
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
                f"{self.base_url}/api/assets",
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
                f"Immich upload failed with status {response.status_code}."
            )
        payload = _json_response(response)
        upload_status = str(payload.get("status", "")).lower()
        asset_id = _asset_id(payload)
        if upload_status == "duplicate":
            return ImmichUploadResult(status="already_present", asset_id=asset_id)
        return ImmichUploadResult(status="uploaded", asset_id=asset_id)

    def _add_asset_to_album(self, asset_id: str, client: httpx.Client) -> None:
        response = client.put(
            f"{self.base_url}/api/albums/{self.album_id}/assets",
            headers=self._headers(),
            json={"ids": [asset_id]},
        )
        if response.status_code not in {200, 201}:
            raise ImmichUploadError(
                f"Immich album attach failed with status {response.status_code}."
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


def _json_response(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return {}


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
