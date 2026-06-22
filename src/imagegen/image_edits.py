"""Local image edit operations for gallery images."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from PIL import Image, ImageFilter, UnidentifiedImageError

from imagegen.mask_store import MaskPayloadError, decode_mask_payload
from imagegen.metadata_embed import read_embedded_metadata, write_embedded_metadata
from imagegen.source_images import validate_source_image_filename


MIN_CROP_SIZE = 10
MAX_BLUR_RADIUS = 50


class ImageEditError(ValueError):
    pass


@dataclass(frozen=True)
class EditedImage:
    path: Path


@dataclass(frozen=True)
class CropRectangle:
    x: int
    y: int
    width: int
    height: int


def crop_image(
    payload: object,
    *,
    source_filename: str,
    output_dir: Path,
) -> EditedImage:
    safe_name = validate_source_image_filename(source_filename, output_dir=output_dir)
    source_path = output_dir / safe_name

    try:
        with Image.open(source_path) as source:
            source.load()
            rectangle = _crop_rectangle(payload, source_size=source.size)
            cropped = source.crop(
                (
                    rectangle.x,
                    rectangle.y,
                    rectangle.x + rectangle.width,
                    rectangle.y + rectangle.height,
                )
            )
            output_path = _edited_output_path(
                safe_name,
                operation="crop",
                output_dir=output_dir,
            )
            _save_image(cropped, output_path=output_path, image_format=source.format)
    except ImageEditError:
        raise
    except (OSError, UnidentifiedImageError) as error:
        raise ImageEditError("Source image is invalid.") from error

    _copy_embedded_metadata(source_path, output_path)
    return EditedImage(path=output_path)


def blur_image(
    payload: object,
    *,
    source_filename: str,
    output_dir: Path,
    content_length: int | None = None,
) -> EditedImage:
    safe_name = validate_source_image_filename(source_filename, output_dir=output_dir)
    source_path = output_dir / safe_name
    blur_radius = _blur_radius(payload)

    try:
        with Image.open(source_path) as source:
            source.load()
            mask_image = decode_mask_payload(
                payload,
                source_size=source.size,
                content_length=content_length,
            )
            _validate_non_empty_mask(mask_image)
            blurred = source.filter(ImageFilter.GaussianBlur(radius=blur_radius))
            edited_image = Image.composite(blurred, source, mask_image)
            output_path = _edited_output_path(
                safe_name,
                operation="blur",
                output_dir=output_dir,
            )
            _save_image(
                edited_image, output_path=output_path, image_format=source.format
            )
    except ImageEditError:
        raise
    except MaskPayloadError as error:
        raise ImageEditError(str(error)) from error
    except (OSError, UnidentifiedImageError) as error:
        raise ImageEditError("Source image is invalid.") from error

    _copy_embedded_metadata(source_path, output_path)
    return EditedImage(path=output_path)


def _crop_rectangle(payload: object, *, source_size: tuple[int, int]) -> CropRectangle:
    if not isinstance(payload, dict):
        raise ImageEditError("Crop rectangle is required.")
    raw_rectangle = payload.get("rectangle")
    if not isinstance(raw_rectangle, dict):
        raise ImageEditError("Crop rectangle is required.")

    try:
        rectangle = CropRectangle(
            x=_integer_coordinate(raw_rectangle.get("x"), name="x"),
            y=_integer_coordinate(raw_rectangle.get("y"), name="y"),
            width=_integer_coordinate(raw_rectangle.get("width"), name="width"),
            height=_integer_coordinate(raw_rectangle.get("height"), name="height"),
        )
    except TypeError as error:
        raise ImageEditError(str(error)) from error

    _validate_crop_rectangle(rectangle, source_size=source_size)
    return rectangle


def _blur_radius(payload: object) -> float:
    if not isinstance(payload, dict):
        raise ImageEditError("Blur radius is required.")
    if "brush_size" in payload:
        raise ImageEditError("brush_size is not accepted for blur operations.")
    value = payload.get("blur_radius")
    if value is None:
        raise ImageEditError("Blur radius is required.")
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ImageEditError("Blur radius must be a number.")
    radius = float(value)
    if radius < 0 or radius > MAX_BLUR_RADIUS:
        raise ImageEditError(
            f"Blur radius must be between 0 and {MAX_BLUR_RADIUS} pixels."
        )
    return radius


def _validate_non_empty_mask(mask_image: Image.Image) -> None:
    if mask_image.getbbox() is None:
        raise ImageEditError("Mask must mark at least one pixel.")


def _integer_coordinate(value: object, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"Crop rectangle {name} must be an integer.")
    return value


def _validate_crop_rectangle(
    rectangle: CropRectangle,
    *,
    source_size: tuple[int, int],
) -> None:
    if rectangle.x < 0 or rectangle.y < 0:
        raise ImageEditError("Crop rectangle must be inside the source image.")
    if rectangle.width < MIN_CROP_SIZE or rectangle.height < MIN_CROP_SIZE:
        raise ImageEditError(
            f"Crop rectangle must be at least {MIN_CROP_SIZE} by {MIN_CROP_SIZE} pixels."
        )
    source_width, source_height = source_size
    if (
        rectangle.x + rectangle.width > source_width
        or rectangle.y + rectangle.height > source_height
    ):
        raise ImageEditError("Crop rectangle must be inside the source image.")


def _edited_output_path(filename: str, *, operation: str, output_dir: Path) -> Path:
    source = Path(filename)
    output_dir.mkdir(parents=True, exist_ok=True)
    while True:
        path = output_dir / f"{source.stem}-{operation}-{uuid4().hex}{source.suffix}"
        if not path.exists():
            return path


def _save_image(
    image: Image.Image, *, output_path: Path, image_format: str | None
) -> None:
    if image_format == "JPEG" and image.mode not in {"L", "RGB", "CMYK"}:
        image = image.convert("RGB")
    image.save(output_path, format=image_format)


def _copy_embedded_metadata(source_path: Path, output_path: Path) -> None:
    metadata = read_embedded_metadata(source_path)
    if metadata is not None:
        write_embedded_metadata(output_path, metadata)
