"""Gallery discovery helpers for locally stored images.

This module contains filesystem-facing read helpers used by routes and tests to
list generated image files. It does not serve files or know about Flask request
handling beyond receiving a URL builder callable.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path


IMAGE_EXTENSIONS = {".gif", ".jpeg", ".jpg", ".png", ".webp"}


@dataclass(frozen=True)
class GalleryImage:
    filename: str
    url: str


def list_gallery_images(
    output_dir: Path,
    *,
    image_url: Callable[[str], str],
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
        GalleryImage(
            filename=path.name,
            url=image_url(path.name),
        )
        for path in files
    ]
