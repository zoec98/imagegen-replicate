"""Source image validation and local path resolution.

This module owns the shared local storage boundary for image-edit inputs. Source
images live in the same application-controlled image directory as generated
outputs because re-editing generated images is expected to be common.
"""

from __future__ import annotations

from pathlib import Path

from werkzeug.utils import secure_filename

from imagegen.gallery import IMAGE_EXTENSIONS


class SourceImageError(ValueError):
    pass


def validate_source_images(
    value: object,
    *,
    max_count: int,
    output_dir: Path,
) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise SourceImageError("source_images must be an array.")
    if not value:
        return []
    if len(value) > max_count:
        raise SourceImageError(
            f"source_images cannot contain more than {max_count} files."
        )

    return [
        validate_source_image_filename(filename, output_dir=output_dir)
        for filename in value
    ]


def validate_source_image_filename(filename: object, *, output_dir: Path) -> str:
    if not isinstance(filename, str) or not filename.strip():
        raise SourceImageError("source_images entries must be filenames.")

    filename = filename.strip()
    safe_name = secure_filename(filename)
    if safe_name != filename or Path(filename).suffix.lower() not in IMAGE_EXTENSIONS:
        raise SourceImageError(f"Invalid source image filename: {filename}.")

    path = source_image_path(safe_name, output_dir=output_dir)
    if not path.is_file():
        raise SourceImageError(f"Source image not found: {safe_name}.")
    return safe_name


def source_image_paths(filenames: list[str], *, output_dir: Path) -> list[Path]:
    return [
        source_image_path(filename, output_dir=output_dir) for filename in filenames
    ]


def source_image_path(filename: str, *, output_dir: Path) -> Path:
    return output_dir / filename
