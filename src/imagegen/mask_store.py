"""Mask PNG validation and storage helpers."""

from __future__ import annotations

from base64 import b64decode
from binascii import Error as Base64Error
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from imagegen.gallery import mask_filename


MASK_PNG_BYTES_PER_PIXEL_LIMIT = 4
MASK_PNG_FIXED_OVERHEAD_BYTES = 1024 * 1024
MASK_PNG_ABSOLUTE_DECODED_LIMIT_BYTES = 256 * 1024 * 1024
MASK_JSON_FIXED_OVERHEAD_BYTES = 4096
MASK_DATA_URL_PREFIX = "data:image/png;base64,"


class MaskPayloadError(ValueError):
    pass


@dataclass(frozen=True)
class MaskPayloadLimits:
    max_decoded_bytes: int
    max_base64_chars: int
    max_request_bytes: int


def save_mask_payload(
    payload: object,
    *,
    source_filename: str,
    source_path: Path,
    output_dir: Path,
    content_length: int | None,
) -> str:
    try:
        source_size = _image_size(source_path)
    except OSError as error:
        raise MaskPayloadError("Source image is invalid.") from error

    mask_image = decode_mask_payload(
        payload,
        source_size=source_size,
        content_length=content_length,
    )

    saved_name = mask_filename(source_filename)
    mask_image.save(output_dir / saved_name, "PNG")
    return saved_name


def decode_mask_payload(
    payload: object,
    *,
    source_size: tuple[int, int],
    content_length: int | None,
) -> Image.Image:
    limits = mask_payload_limits(source_size)
    _validate_mask_request_size(content_length, limits)
    mask_image = _decode_mask_png(_mask_png_payload(payload, limits))
    if mask_image.size != source_size:
        raise MaskPayloadError("Mask dimensions must match the source image.")
    return mask_image.convert("L")


def mask_payload_limits(source_size: tuple[int, int]) -> MaskPayloadLimits:
    width, height = source_size
    pixel_count = width * height
    max_decoded_bytes = (
        pixel_count * MASK_PNG_BYTES_PER_PIXEL_LIMIT + MASK_PNG_FIXED_OVERHEAD_BYTES
    )
    max_decoded_bytes = min(
        max_decoded_bytes,
        MASK_PNG_ABSOLUTE_DECODED_LIMIT_BYTES,
    )
    max_base64_chars = ((max_decoded_bytes + 2) // 3) * 4 + len(MASK_DATA_URL_PREFIX)
    return MaskPayloadLimits(
        max_decoded_bytes=max_decoded_bytes,
        max_base64_chars=max_base64_chars,
        max_request_bytes=max_base64_chars + MASK_JSON_FIXED_OVERHEAD_BYTES,
    )


def _validate_mask_request_size(
    content_length: int | None,
    limits: MaskPayloadLimits,
) -> None:
    if content_length is not None and content_length > limits.max_request_bytes:
        raise MaskPayloadError("Mask PNG is too large.")


def _mask_png_payload(payload: object, limits: MaskPayloadLimits) -> bytes:
    if not isinstance(payload, dict):
        raise MaskPayloadError("Mask PNG is required.")
    value = payload.get("mask_png")
    if not isinstance(value, str) or not value:
        raise MaskPayloadError("Mask PNG is required.")
    if len(value) > limits.max_base64_chars:
        raise MaskPayloadError("Mask PNG is too large.")
    if value.startswith("data:"):
        if not value.startswith(MASK_DATA_URL_PREFIX):
            raise MaskPayloadError("Mask PNG is invalid.")
        value = value[len(MASK_DATA_URL_PREFIX) :]
    try:
        decoded = b64decode(value, validate=True)
    except (Base64Error, ValueError) as error:
        raise MaskPayloadError("Mask PNG is invalid.") from error
    if len(decoded) > limits.max_decoded_bytes:
        raise MaskPayloadError("Mask PNG is too large.")
    return decoded


def _decode_mask_png(mask_bytes: bytes) -> Image.Image:
    try:
        with Image.open(BytesIO(mask_bytes)) as image:
            image.load()
            if image.format != "PNG":
                raise MaskPayloadError("Mask PNG is invalid.")
            return image.copy()
    except (OSError, UnidentifiedImageError) as error:
        raise MaskPayloadError("Mask PNG is invalid.") from error


def _image_size(path: Path) -> tuple[int, int]:
    with Image.open(path) as image:
        return image.size
