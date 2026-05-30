"""Embedded image metadata read/write helpers.

The metadata contract stores one JSON document under an application-specific
key. PNG uses a text chunk. JPEG and WebP use EXIF UserComment because Pillow
can round-trip it for both formats without native Exiv2 dependencies.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PIL import Image, PngImagePlugin, UnidentifiedImageError


IMAGE_DESCRIPTION_TAG = 270
USER_COMMENT_TAG = 37510
PNG_DESCRIPTION_KEYS = ("Description", "ImageDescription")
PNG_METADATA_KEY = "imagegen:metadata"
USER_COMMENT_PREFIX = b"UNICODE\0"


class EmbeddedMetadataError(RuntimeError):
    pass


def write_embedded_metadata(image_path: Path, metadata: dict[str, Any]) -> None:
    payload = json.dumps(metadata, ensure_ascii=False, sort_keys=True)
    description = human_description(metadata)
    try:
        with Image.open(image_path) as image:
            image_format = image.format
            if image_format == "PNG":
                _write_png_metadata(image_path, image, payload, description)
                return
            if image_format in {"JPEG", "WEBP"}:
                _write_exif_metadata(image_path, image, payload, description)
                return
    except (OSError, UnidentifiedImageError) as error:
        msg = f"Could not write embedded metadata for {image_path.name}."
        raise EmbeddedMetadataError(msg) from error

    msg = f"Embedded metadata is not supported for {image_path.suffix or image_path.name}."
    raise EmbeddedMetadataError(msg)


def read_embedded_metadata(image_path: Path) -> dict[str, Any] | None:
    try:
        with Image.open(image_path) as image:
            if image.format == "PNG":
                return _decode_metadata_payload(image.info.get(PNG_METADATA_KEY))
            if image.format in {"JPEG", "WEBP"}:
                return _read_exif_metadata(image)
    except OSError, UnidentifiedImageError, ValueError:
        return None
    return None


def human_description(metadata: dict[str, Any]) -> str:
    parts = ["Generated image"]
    created_at = metadata.get("created_at")
    model = metadata.get("model")
    prompt = metadata.get("prompt")
    if isinstance(created_at, str) and created_at:
        parts.append(f"generated at {created_at}")
    if isinstance(model, str) and model:
        parts.append(f"with {model}")
    if isinstance(prompt, str) and prompt:
        parts.append(f"Prompt: {prompt}")
    return ". ".join(parts) + "."


def _write_png_metadata(
    image_path: Path,
    image: Image.Image,
    payload: str,
    description: str,
) -> None:
    pnginfo = PngImagePlugin.PngInfo()
    for key, value in image.info.items():
        if (
            isinstance(value, str)
            and key != PNG_METADATA_KEY
            and key not in PNG_DESCRIPTION_KEYS
        ):
            pnginfo.add_text(key, value)
    for key in PNG_DESCRIPTION_KEYS:
        pnginfo.add_text(key, description)
    pnginfo.add_text(PNG_METADATA_KEY, payload)
    image.save(image_path, format="PNG", pnginfo=pnginfo)


def _write_exif_metadata(
    image_path: Path,
    image: Image.Image,
    payload: str,
    description: str,
) -> None:
    exif = image.getexif()
    exif[IMAGE_DESCRIPTION_TAG] = description[:1024]
    exif[USER_COMMENT_TAG] = USER_COMMENT_PREFIX + payload.encode("utf-16-be")
    image.save(image_path, format=image.format, exif=exif)


def _read_exif_metadata(image: Image.Image) -> dict[str, Any] | None:
    value = image.getexif().get(USER_COMMENT_TAG)
    if isinstance(value, str):
        return _decode_metadata_payload(value)
    if isinstance(value, bytes):
        if value.startswith(USER_COMMENT_PREFIX):
            return _decode_metadata_payload(
                value[len(USER_COMMENT_PREFIX) :].decode("utf-16-be")
            )
        return _decode_metadata_payload(value.decode("utf-8"))
    return None


def _decode_metadata_payload(value: object) -> dict[str, Any] | None:
    if not isinstance(value, str) or not value:
        return None
    decoded = json.loads(value)
    return decoded if isinstance(decoded, dict) else None
