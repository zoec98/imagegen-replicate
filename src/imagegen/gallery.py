"""Gallery discovery helpers for locally stored images.

This module contains filesystem-facing read helpers used by routes and tests to
list generated image files. It does not serve files or know about Flask request
handling beyond receiving a URL builder callable.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from imagegen.metadata import EmbeddedImageMetadataProvider, ImageMetadataProvider


IMAGE_EXTENSIONS = {".jpeg", ".jpg", ".png", ".webp"}


@dataclass(frozen=True)
class GalleryImage:
    filename: str
    url: str
    metadata_url: str | None
    content_type: str | None
    created_at: str | None


def list_gallery_images(
    output_dir: Path,
    *,
    image_url: Callable[[str], str],
    metadata_url: Callable[[str], str] | None = None,
    metadata_provider: ImageMetadataProvider | None = None,
) -> list[GalleryImage]:
    if not output_dir.exists():
        return []

    files = [
        path
        for path in output_dir.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    ]
    files.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    return [
        _gallery_image(
            path,
            image_url=image_url,
            metadata_url=metadata_url,
            metadata_provider=metadata_provider or EmbeddedImageMetadataProvider(),
        )
        for path in files
    ]


def move_gallery_image_to_trash(
    filename: str,
    *,
    output_dir: Path,
    trash_dir: Path,
) -> Path:
    image_path = output_dir / filename
    if image_path.parent != output_dir or not image_path.is_file():
        raise FileNotFoundError(filename)

    trash_dir.mkdir(parents=True, exist_ok=True)
    trash_path = _trash_path(filename, trash_dir=trash_dir)
    return image_path.replace(trash_path)


def _gallery_image(
    path: Path,
    *,
    image_url: Callable[[str], str],
    metadata_url: Callable[[str], str] | None,
    metadata_provider: ImageMetadataProvider,
) -> GalleryImage:
    metadata = metadata_provider.get(path)
    return GalleryImage(
        filename=path.name,
        url=image_url(path.name),
        metadata_url=metadata_url(path.name)
        if metadata_url and metadata.exists
        else None,
        content_type=metadata.content_type,
        created_at=metadata.created_at,
    )


def _trash_path(filename: str, *, trash_dir: Path) -> Path:
    candidate = trash_dir / filename
    if not candidate.exists():
        return candidate

    source = Path(filename)
    while True:
        candidate = trash_dir / f"{source.stem}-{uuid4().hex}{source.suffix}"
        if not candidate.exists():
            return candidate
