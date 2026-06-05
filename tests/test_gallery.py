"""Gallery filesystem helper tests.

Behaviors protected:
- Trash helpers list and count only supported image files.
- Trash restore rejects unsafe filenames and never overwrites active images.
- Empty and purge operations stay confined to eligible files in the trash directory.
"""

from datetime import datetime, timedelta, timezone
import os

import pytest

from imagegen.trash import (
    count_trash_images,
    empty_trash,
    list_trash_images,
    purge_old_trash,
    restore_trash_image,
)


def test_trash_listing_and_count_ignore_unsupported_files(tmp_path):
    trash_dir = tmp_path / "trash"
    trash_dir.mkdir()
    (trash_dir / "older.png").write_bytes(b"older")
    (trash_dir / "newer.jpg").write_bytes(b"newer")
    (trash_dir / "animated.gif").write_bytes(b"gif")
    (trash_dir / "notes.txt").write_text("ignored", encoding="utf-8")
    os.utime(trash_dir / "older.png", (100, 100))
    os.utime(trash_dir / "newer.jpg", (200, 200))

    images = list_trash_images(trash_dir)

    assert [image.name for image in images] == ["newer.jpg", "older.png"]
    assert count_trash_images(trash_dir) == 2


def test_restore_trash_image_moves_file_back_to_output_dir(tmp_path):
    trash_dir = tmp_path / "trash"
    output_dir = tmp_path / "images"
    trash_dir.mkdir()
    output_dir.mkdir()
    (trash_dir / "sample.png").write_bytes(b"image")

    restored = restore_trash_image(
        "sample.png",
        trash_dir=trash_dir,
        output_dir=output_dir,
    )

    assert restored == output_dir / "sample.png"
    assert restored.read_bytes() == b"image"
    assert not (trash_dir / "sample.png").exists()


@pytest.mark.parametrize("filename", ["../sample.png", ".hidden.png", "sample.gif"])
def test_restore_trash_image_rejects_unsafe_names(tmp_path, filename):
    trash_dir = tmp_path / "trash"
    output_dir = tmp_path / "images"
    trash_dir.mkdir()
    output_dir.mkdir()

    with pytest.raises(FileNotFoundError):
        restore_trash_image(filename, trash_dir=trash_dir, output_dir=output_dir)


def test_restore_trash_image_does_not_overwrite_existing_output(tmp_path):
    trash_dir = tmp_path / "trash"
    output_dir = tmp_path / "images"
    trash_dir.mkdir()
    output_dir.mkdir()
    (trash_dir / "sample.png").write_bytes(b"trashed")
    (output_dir / "sample.png").write_bytes(b"active")

    restored = restore_trash_image(
        "sample.png",
        trash_dir=trash_dir,
        output_dir=output_dir,
    )

    assert restored.name.startswith("sample-")
    assert restored.suffix == ".png"
    assert restored.read_bytes() == b"trashed"
    assert (output_dir / "sample.png").read_bytes() == b"active"


def test_empty_trash_deletes_only_supported_trash_files(tmp_path):
    trash_dir = tmp_path / "trash"
    image_dir = tmp_path / "images"
    trash_dir.mkdir()
    image_dir.mkdir()
    (trash_dir / "sample.png").write_bytes(b"image")
    (trash_dir / "notes.txt").write_text("keep", encoding="utf-8")
    (image_dir / "active.png").write_bytes(b"active")

    deleted = empty_trash(trash_dir)

    assert [path.name for path in deleted] == ["sample.png"]
    assert not (trash_dir / "sample.png").exists()
    assert (trash_dir / "notes.txt").exists()
    assert (image_dir / "active.png").exists()


def test_purge_old_trash_deletes_only_old_supported_files(tmp_path):
    trash_dir = tmp_path / "trash"
    trash_dir.mkdir()
    old_image = trash_dir / "old.png"
    fresh_image = trash_dir / "fresh.png"
    old_text = trash_dir / "old.txt"
    old_image.write_bytes(b"old")
    fresh_image.write_bytes(b"fresh")
    old_text.write_text("keep", encoding="utf-8")
    os.utime(old_image, (100, 100))
    os.utime(fresh_image, (300, 300))
    os.utime(old_text, (100, 100))
    cutoff = datetime.fromtimestamp(200, tz=timezone.utc)

    deleted = purge_old_trash(trash_dir, cutoff=cutoff)

    assert [path.name for path in deleted] == ["old.png"]
    assert not old_image.exists()
    assert fresh_image.exists()
    assert old_text.exists()


def test_purge_old_trash_accepts_timezone_aware_cutoff(tmp_path):
    trash_dir = tmp_path / "trash"
    trash_dir.mkdir()
    old_image = trash_dir / "old.png"
    old_image.write_bytes(b"old")
    os.utime(old_image, (100, 100))

    deleted = purge_old_trash(
        trash_dir,
        cutoff=datetime.fromtimestamp(100, tz=timezone.utc) + timedelta(seconds=1),
    )

    assert [path.name for path in deleted] == ["old.png"]
