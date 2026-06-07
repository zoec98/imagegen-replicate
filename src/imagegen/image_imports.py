"""Validation and storage for user-imported image bytes."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

import httpx
from PIL import Image, UnidentifiedImageError


MAX_UPLOAD_BYTES = 100 * 1024 * 1024

FORMAT_EXTENSIONS = {
    "JPEG": ".jpg",
    "PNG": ".png",
    "WEBP": ".webp",
}

FORMAT_CONTENT_TYPES = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
}


class ImageImportError(ValueError):
    pass


class ImageImportFetchError(ValueError):
    pass


@dataclass(frozen=True)
class ImportedImage:
    path: Path
    content_type: str
    size_bytes: int


def import_image_from_url(
    url: object,
    *,
    output_dir: Path,
    client: httpx.Client,
    max_bytes: int = MAX_UPLOAD_BYTES,
) -> ImportedImage:
    validated_url = validate_import_url(url)
    image_bytes = fetch_import_url(
        validated_url,
        client=client,
        max_bytes=max_bytes,
    )
    return store_imported_image(
        image_bytes,
        output_dir=output_dir,
        max_bytes=max_bytes,
    )


def validate_import_url(url: object) -> str:
    if not isinstance(url, str) or not url.strip():
        raise ImageImportFetchError("Image URL is required.")
    value = url.strip()
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"}:
        raise ImageImportFetchError("Image URL must use http or https.")
    if not parsed.hostname:
        raise ImageImportFetchError("Image URL must include a host.")
    return value


def fetch_import_url(
    url: str,
    *,
    client: httpx.Client,
    max_bytes: int = MAX_UPLOAD_BYTES,
) -> bytes:
    try:
        with client.stream("GET", url, follow_redirects=True) as response:
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as error:
                msg = f"Image URL returned HTTP {response.status_code}."
                raise ImageImportFetchError(msg) from error
            content_length = _content_length(response)
            if content_length is not None and content_length > max_bytes:
                raise ImageImportFetchError("Image download is too large.")
            return _read_bounded_response(response, max_bytes=max_bytes)
    except ImageImportFetchError:
        raise
    except httpx.HTTPError as error:
        raise ImageImportFetchError("Image URL request failed.") from error


def store_imported_image(
    image_bytes: bytes,
    *,
    output_dir: Path,
    max_bytes: int = MAX_UPLOAD_BYTES,
) -> ImportedImage:
    if not image_bytes:
        raise ImageImportError("Image upload is empty.")
    if len(image_bytes) > max_bytes:
        raise ImageImportError(
            f"Image upload is {len(image_bytes)} bytes, exceeding limit {max_bytes}."
        )

    image_format = _validated_image_format(image_bytes)
    extension = FORMAT_EXTENSIONS.get(image_format)
    if extension is None:
        raise ImageImportError(f"Unsupported image format: {image_format}.")

    output_dir.mkdir(parents=True, exist_ok=True)
    path = _write_collision_safe(image_bytes, output_dir=output_dir, extension=extension)
    return ImportedImage(
        path=path,
        content_type=FORMAT_CONTENT_TYPES[image_format],
        size_bytes=len(image_bytes),
    )


def _validated_image_format(image_bytes: bytes) -> str:
    try:
        with Image.open(BytesIO(image_bytes)) as image:
            image.load()
            image_format = image.format
    except (OSError, UnidentifiedImageError) as error:
        raise ImageImportError("Uploaded file is not a valid image.") from error
    if image_format not in FORMAT_EXTENSIONS:
        raise ImageImportError(f"Unsupported image format: {image_format or 'unknown'}.")
    return image_format


def _write_collision_safe(
    image_bytes: bytes,
    *,
    output_dir: Path,
    extension: str,
) -> Path:
    while True:
        path = output_dir / f"import-{uuid4().hex}{extension}"
        try:
            with path.open("xb") as output:
                output.write(image_bytes)
        except FileExistsError:
            continue
        return path


def _content_length(response: httpx.Response) -> int | None:
    raw_value = response.headers.get("content-length")
    if raw_value is None:
        return None
    try:
        return int(raw_value)
    except ValueError:
        return None


def _read_bounded_response(response: httpx.Response, *, max_bytes: int) -> bytes:
    chunks: list[bytes] = []
    total = 0
    for chunk in response.iter_bytes():
        total += len(chunk)
        if total > max_bytes:
            raise ImageImportFetchError("Image download is too large.")
        chunks.append(chunk)
    return b"".join(chunks)
