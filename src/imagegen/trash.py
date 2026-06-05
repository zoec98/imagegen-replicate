"""Filesystem-facing helpers for the local image trashcan."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from imagegen.filenames import IMAGE_EXTENSIONS, safe_image_filename


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


def list_trash_images(trash_dir: Path) -> list[Path]:
    if not trash_dir.exists():
        return []
    files = [
        path
        for path in trash_dir.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    ]
    files.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    return files


def count_trash_images(trash_dir: Path) -> int:
    return len(list_trash_images(trash_dir))


def restore_trash_image(filename: str, *, trash_dir: Path, output_dir: Path) -> Path:
    safe_name = safe_image_filename(filename)
    if safe_name is None:
        raise FileNotFoundError(filename)
    trash_path = trash_dir / safe_name
    if trash_path.parent != trash_dir or not trash_path.is_file():
        raise FileNotFoundError(filename)

    output_dir.mkdir(parents=True, exist_ok=True)
    restored_path = _collision_safe_path(safe_name, output_dir=output_dir)
    return trash_path.replace(restored_path)


def empty_trash(trash_dir: Path) -> list[Path]:
    deleted: list[Path] = []
    for path in list_trash_images(trash_dir):
        path.unlink()
        deleted.append(path)
    return deleted


def purge_old_trash(trash_dir: Path, *, cutoff: datetime) -> list[Path]:
    cutoff_timestamp = cutoff.timestamp()
    deleted: list[Path] = []
    for path in list_trash_images(trash_dir):
        if path.stat().st_mtime >= cutoff_timestamp:
            continue
        path.unlink()
        deleted.append(path)
    return deleted


def refresh_trash_count(
    trash_dir: Path,
    *,
    retention_days: int | None,
) -> int:
    if retention_days is not None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
        purge_old_trash(trash_dir, cutoff=cutoff)
    return count_trash_images(trash_dir)


def _trash_path(filename: str, *, trash_dir: Path) -> Path:
    return _collision_safe_path(filename, output_dir=trash_dir)


def _collision_safe_path(filename: str, *, output_dir: Path) -> Path:
    source = Path(filename)
    candidate = output_dir / filename
    if not candidate.exists():
        return candidate

    while True:
        candidate = output_dir / f"{source.stem}-{uuid4().hex}{source.suffix}"
        if not candidate.exists():
            return candidate
