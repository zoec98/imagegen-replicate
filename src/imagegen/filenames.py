"""Shared filename validation for locally managed image files."""

from __future__ import annotations

from pathlib import Path

from werkzeug.utils import secure_filename


IMAGE_EXTENSIONS = {".jpeg", ".jpg", ".png", ".webp"}


def safe_image_filename(filename: str) -> str | None:
    safe_name = secure_filename(filename)
    if safe_name != filename or Path(filename).suffix.lower() not in IMAGE_EXTENSIONS:
        return None
    return safe_name
