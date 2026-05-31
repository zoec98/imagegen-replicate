"""Image export helpers for downloadable gallery variants."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from PIL import Image, UnidentifiedImageError


EXPORT_FORMATS = {"JPEG", "PNG", "WEBP"}
EXPORT_SUFFIXES = {".jpeg", ".jpg", ".png", ".webp"}


class ImageExportError(RuntimeError):
    pass


def clean_image_export(source_path: Path, *, tmp_dir: Path) -> Path:
    """Create a metadata-stripped temporary copy of a supported image."""

    tmp_dir.mkdir(parents=True, exist_ok=True)
    try:
        with Image.open(source_path) as image:
            image_format = image.format
            if image_format not in EXPORT_FORMATS:
                msg = f"Clean export is not supported for {source_path.name}."
                raise ImageExportError(msg)
            export_path = _export_path(source_path, tmp_dir=tmp_dir)
            export_image = _export_image(image)
            export_image.save(export_path, format=image_format)
            return export_path
    except ImageExportError:
        raise
    except (OSError, UnidentifiedImageError) as error:
        msg = f"Could not create clean export for {source_path.name}."
        raise ImageExportError(msg) from error


def clean_tmp_exports(tmp_dir: Path) -> None:
    """Remove app-created clean export files from the temporary directory."""

    if not tmp_dir.exists():
        return
    for path in tmp_dir.iterdir():
        if path.is_file() and path.suffix.lower() in EXPORT_SUFFIXES:
            path.unlink()


def _export_path(source_path: Path, *, tmp_dir: Path) -> Path:
    suffix = source_path.suffix.lower()
    while True:
        candidate = tmp_dir / f"{source_path.stem}-clean-{uuid4().hex}{suffix}"
        if not candidate.exists():
            return candidate


def _export_image(image: Image.Image) -> Image.Image:
    image.load()
    if image.format == "JPEG" and image.mode not in {"L", "RGB", "CMYK"}:
        return image.convert("RGB")
    return image.copy()
