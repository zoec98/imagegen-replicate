"""Image export helpers for downloadable gallery variants."""

from __future__ import annotations

import os
import stat
import tempfile
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from imagegen.security import ImageDecodeLimitError, validate_decoded_image_size

EXPORT_FORMATS = {"JPEG", "PNG", "WEBP"}
EXPORT_SUFFIXES = {".jpeg", ".jpg", ".png", ".webp"}


class ImageExportError(RuntimeError):
    pass


def clean_image_export(source_path: Path, *, tmp_dir: Path) -> Path:
    """Create a metadata-stripped temporary copy of a supported image."""

    tmp_dir.mkdir(parents=True, exist_ok=True)
    try:
        with Image.open(source_path) as image:
            validate_decoded_image_size(image.size)
            image_format = image.format
            if image_format not in EXPORT_FORMATS:
                msg = f"Clean export is not supported for {source_path.name}."
                raise ImageExportError(msg)
            export_path = _export_path(source_path, tmp_dir=tmp_dir)
            _reject_unsafe_destination(export_path)
            export_image = _export_image(image)
            temporary_path = _temporary_export_path(tmp_dir)
            try:
                export_image.save(temporary_path, format=image_format)
                os.replace(temporary_path, export_path)
            finally:
                temporary_path.unlink(missing_ok=True)
            return export_path
    except ImageExportError:
        raise
    except ImageDecodeLimitError as error:
        raise ImageExportError(str(error)) from error
    except (OSError, UnidentifiedImageError) as error:
        msg = f"Could not create clean export for {source_path.name}."
        raise ImageExportError(msg) from error


def clean_tmp_exports(tmp_dir: Path) -> None:
    """Remove app-created clean export files from the temporary directory."""

    if not tmp_dir.exists():
        return
    for path in tmp_dir.iterdir():
        if path.is_file() and (
            path.suffix.lower() in EXPORT_SUFFIXES
            or path.name.startswith(".imagegen-clean-")
        ):
            path.unlink()


def _export_path(source_path: Path, *, tmp_dir: Path) -> Path:
    suffix = source_path.suffix.lower()
    return tmp_dir / f"{source_path.stem}-clean{suffix}"


def _temporary_export_path(tmp_dir: Path) -> Path:
    with tempfile.NamedTemporaryFile(
        dir=tmp_dir,
        prefix=".imagegen-clean-",
        suffix=".tmp",
        delete=False,
    ) as handle:
        return Path(handle.name)


def _reject_unsafe_destination(path: Path) -> None:
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError:
        return
    if stat.S_ISDIR(mode):
        raise ImageExportError(f"Clean export destination is a directory: {path.name}.")
    if stat.S_ISLNK(mode):
        raise ImageExportError(f"Clean export destination is a symlink: {path.name}.")


def _export_image(image: Image.Image) -> Image.Image:
    image.load()
    if image.format == "JPEG" and image.mode not in {"L", "RGB", "CMYK"}:
        return image.convert("RGB")
    return image.copy()
