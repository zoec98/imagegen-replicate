"""Local storage for generated image files and embedded metadata.

This module downloads Replicate image outputs, validates basic response safety,
writes files under the configured output directory, and embeds metadata.
"""

from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol
from urllib.parse import urljoin, urlparse, urlunparse
from uuid import uuid4

import httpx

from imagegen.metadata_embed import write_embedded_metadata
from imagegen.metadata_policy import synthesize_copyright
from imagegen.model_registry import ProviderId
from imagegen.security import MAX_GENERATED_IMAGE_BYTES, MAX_GENERATED_IMAGES

SOFTWARE_NAME = "https://github.com/zoec98/imagegen-replicate"


CONTENT_TYPE_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
MAX_REDIRECTS = 5


class StoredImageModel(Protocol):
    alias: str


@dataclass(frozen=True)
class StoredImage:
    path: Path
    source_url: str
    content_type: str
    size_bytes: int
    created_at: str


class ImageDownloadError(RuntimeError):
    pass


class HostResolver(Protocol):
    def __call__(
        self, hostname: str
    ) -> list[ipaddress.IPv4Address | ipaddress.IPv6Address]: ...


def persist_generated_images(
    urls: list[str],
    *,
    output_dir: Path,
    model: StoredImageModel,
    provider: ProviderId = "replicate",
    model_alias: str | None = None,
    provider_model: str | None = None,
    prompt: str,
    prediction_id: str,
    local_request_id: str | None = None,
    prediction_input: dict[str, object],
    author: str,
    client: httpx.Client | None = None,
    resolver: HostResolver | None = None,
) -> list[StoredImage]:
    if len(urls) > MAX_GENERATED_IMAGES:
        raise ImageDownloadError(
            f"Provider returned {len(urls)} images; maximum is {MAX_GENERATED_IMAGES}."
        )
    output_dir.mkdir(parents=True, exist_ok=True)
    close_client = client is None
    http_client = client or httpx.Client(timeout=30.0, follow_redirects=False)
    request_id = local_request_id or uuid4().hex
    try:
        stored: list[StoredImage] = []
        try:
            for sequence, url in enumerate(urls, start=1):
                stored.append(
                    download_image(
                        url,
                        output_dir=output_dir,
                        model=model,
                        provider=provider,
                        model_alias=model_alias,
                        provider_model=provider_model,
                        prompt=prompt,
                        prediction_id=prediction_id,
                        local_request_id=request_id,
                        sequence=sequence,
                        prediction_input=prediction_input,
                        author=author,
                        client=http_client,
                        resolver=resolver,
                    )
                )
        except Exception:
            for image in stored:
                image.path.unlink(missing_ok=True)
            raise
        return stored
    finally:
        if close_client:
            http_client.close()


def download_image(
    url: str,
    *,
    output_dir: Path,
    model: StoredImageModel,
    provider: ProviderId = "replicate",
    model_alias: str | None = None,
    provider_model: str | None = None,
    prompt: str,
    prediction_id: str,
    local_request_id: str | None = None,
    sequence: int,
    prediction_input: dict[str, object],
    author: str,
    client: httpx.Client,
    resolver: HostResolver | None = None,
) -> StoredImage:
    content, content_type, final_url = _fetch_validated_image(
        url,
        provider=provider,
        client=client,
        resolver=resolver or resolve_host_ips,
        max_bytes=max_download_bytes(model),
    )

    if content_type == "image/gif":
        msg = f"GIF image outputs are not supported from {_display_url(final_url)}."
        raise ImageDownloadError(msg)
    if not content_type.startswith("image/"):
        msg = (
            f"Expected image content from {_display_url(final_url)}, "
            f"got {content_type or 'unknown'}."
        )
        raise ImageDownloadError(msg)

    extension = _extension_for(content_type, final_url)
    request_id = local_request_id or uuid4().hex
    filename = f"{model.alias}-{request_id}-{sequence:02d}{extension}"
    path = output_dir / filename
    try:
        with path.open("xb") as output:
            output.write(content)
    except FileExistsError as error:
        raise ImageDownloadError(
            f"Image output path already exists: {filename}."
        ) from error
    try:
        created_at = datetime.now(UTC).isoformat()
        metadata = {
            "created_at": created_at,
            "provider": provider,
            "model_alias": model_alias or model.alias,
            "model": provider_model or getattr(model, "replicate_model", model.alias),
            "prediction_id": prediction_id,
            "sequence": sequence,
            "prompt": prompt,
            "parameters": prediction_input,
            "source_url": url,
            "content_type": content_type,
            "size_bytes": len(content),
            "filename": filename,
            "author": author,
            "copyright": synthesize_copyright(author, created_at),
            "software": SOFTWARE_NAME,
        }
        write_embedded_metadata(path, metadata)
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return StoredImage(
        path=path,
        source_url=url,
        content_type=content_type,
        size_bytes=len(content),
        created_at=created_at,
    )


def max_download_bytes(model: StoredImageModel) -> int:
    return MAX_GENERATED_IMAGE_BYTES


def resolve_host_ips(
    hostname: str,
) -> list[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    try:
        infos = socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
    except socket.gaierror as error:
        msg = f"Could not resolve image download host: {hostname}."
        raise ImageDownloadError(msg) from error
    addresses: list[ipaddress.IPv4Address | ipaddress.IPv6Address] = []
    for info in infos:
        raw_address = info[4][0]
        address = ipaddress.ip_address(raw_address)
        if address not in addresses:
            addresses.append(address)
    if not addresses:
        msg = f"Could not resolve image download host: {hostname}."
        raise ImageDownloadError(msg)
    return addresses


def validate_download_url(
    url: str,
    *,
    provider: ProviderId = "replicate",
    resolver: HostResolver = resolve_host_ips,
) -> str:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise ImageDownloadError("Image download URLs must use https.")
    if not parsed.hostname:
        raise ImageDownloadError("Image download URL must include a host.")
    if parsed.hostname.lower().rstrip(".") in {"localhost"}:
        raise ImageDownloadError("Image download host is unsafe: localhost.")
    for address in resolver(parsed.hostname):
        if is_unsafe_download_address(address):
            msg = f"Image download host resolves to unsafe address: {parsed.hostname}."
            raise ImageDownloadError(msg)
    if not _provider_host_allowed(provider, parsed.hostname):
        raise ImageDownloadError(
            f"Image download host is not allowed for provider {provider}."
        )
    return url


def _fetch_validated_image(
    url: str,
    *,
    provider: ProviderId,
    client: httpx.Client,
    resolver: HostResolver,
    max_bytes: int,
) -> tuple[bytes, str, str]:
    current_url = validate_download_url(url, provider=provider, resolver=resolver)
    for _ in range(MAX_REDIRECTS + 1):
        try:
            response_context = client.stream(
                "GET",
                current_url,
                follow_redirects=False,
            )
            with response_context as response:
                if response.is_redirect:
                    location = response.headers.get("location")
                    if not location:
                        raise ImageDownloadError(
                            "Image download redirect did not include a location."
                        )
                    current_url = validate_download_url(
                        urljoin(str(response.url), location),
                        provider=provider,
                        resolver=resolver,
                    )
                    continue
                try:
                    response.raise_for_status()
                except httpx.HTTPStatusError as error:
                    msg = (
                        f"Image download failed with status {response.status_code} "
                        f"from {_display_url(current_url)}."
                    )
                    raise ImageDownloadError(msg) from error
                content_length = response.headers.get("content-length")
                if content_length is not None:
                    try:
                        if int(content_length) > max_bytes:
                            raise ImageDownloadError(
                                f"Image from {_display_url(current_url)} is too large, "
                                f"exceeding limit {max_bytes} bytes."
                            )
                    except ValueError:
                        pass
                content = _read_bounded_download(response, max_bytes=max_bytes)
                content_type = (
                    response.headers.get("content-type", "")
                    .split(";", 1)[0]
                    .lower()
                )
                return content, content_type, str(response.url)
        except httpx.HTTPError as error:
            msg = f"Image download request failed for {_display_url(current_url)}."
            raise ImageDownloadError(msg) from error
    raise ImageDownloadError("Image download followed too many redirects.")


def _read_bounded_download(response: httpx.Response, *, max_bytes: int) -> bytes:
    chunks: list[bytes] = []
    total = 0
    for chunk in response.iter_bytes():
        total += len(chunk)
        if total > max_bytes:
            raise ImageDownloadError(
                f"Image download is too large, exceeding limit {max_bytes} bytes."
            )
        chunks.append(chunk)
    return b"".join(chunks)


def is_unsafe_download_address(
    address: ipaddress.IPv4Address | ipaddress.IPv6Address,
) -> bool:
    return any(
        (
            address.is_loopback,
            address.is_private,
            address.is_link_local,
            address.is_multicast,
            address.is_unspecified,
            address.is_reserved,
        )
    )


def _provider_host_allowed(provider: ProviderId, hostname: str) -> bool:
    host = hostname.lower().rstrip(".")
    if provider == "replicate":
        return host == "replicate.delivery" or host.endswith(".replicate.delivery")
    if provider == "falai":
        return host.endswith(".fal.media")
    if provider == "wiro":
        return host.endswith(".wiro.ai")
    return False


def _display_url(url: str) -> str:
    parsed = urlparse(url)
    netloc = parsed.hostname or ""
    try:
        port = parsed.port
    except ValueError:
        port = None
    if port is not None:
        netloc = f"{netloc}:{port}"
    return urlunparse((parsed.scheme, netloc, parsed.path, "", "", ""))


def _extension_for(content_type: str, url: str) -> str:
    if content_type in CONTENT_TYPE_EXTENSIONS:
        return CONTENT_TYPE_EXTENSIONS[content_type]
    suffix = Path(urlparse(url).path).suffix.lower()
    if suffix in {".jpeg", ".jpg", ".png", ".webp"}:
        return suffix
    return ".img"
