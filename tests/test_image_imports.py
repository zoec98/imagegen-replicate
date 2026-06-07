"""Imported image storage tests.

Behaviors protected:
- Imported images are validated with Pillow before storage.
- Imported image filenames are generated safely and never preserve caller names.
- Existing embedded metadata bytes are preserved by storing original image bytes.
"""

from io import BytesIO

import pytest
from PIL import Image

from imagegen.image_imports import ImageImportError, store_imported_image
from imagegen.metadata_embed import read_embedded_metadata, write_embedded_metadata


def image_bytes(image_format: str) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (8, 8), (255, 0, 0)).save(buffer, image_format)
    return buffer.getvalue()


@pytest.mark.parametrize(
    ("image_format", "extension", "content_type"),
    [
        ("PNG", ".png", "image/png"),
        ("JPEG", ".jpg", "image/jpeg"),
        ("WEBP", ".webp", "image/webp"),
    ],
)
def test_store_imported_image_accepts_supported_formats(
    tmp_path,
    image_format,
    extension,
    content_type,
):
    stored = store_imported_image(image_bytes(image_format), output_dir=tmp_path)

    assert stored.path.parent == tmp_path
    assert stored.path.name.startswith("import-")
    assert stored.path.suffix == extension
    assert stored.content_type == content_type
    assert stored.size_bytes == stored.path.stat().st_size
    with Image.open(stored.path) as image:
        assert image.format == image_format


def test_store_imported_image_creates_output_directory(tmp_path):
    output_dir = tmp_path / "missing" / "images"

    stored = store_imported_image(image_bytes("PNG"), output_dir=output_dir)

    assert stored.path.parent == output_dir
    assert stored.path.is_file()


def test_store_imported_image_rejects_empty_payload(tmp_path):
    with pytest.raises(ImageImportError, match="Image upload is empty."):
        store_imported_image(b"", output_dir=tmp_path)


def test_store_imported_image_rejects_invalid_image_bytes(tmp_path):
    with pytest.raises(ImageImportError, match="not a valid image"):
        store_imported_image(b"not an image", output_dir=tmp_path)


def test_store_imported_image_rejects_unsupported_formats(tmp_path):
    with pytest.raises(ImageImportError, match="Unsupported image format: GIF."):
        store_imported_image(image_bytes("GIF"), output_dir=tmp_path)


def test_store_imported_image_rejects_oversized_payload(tmp_path):
    with pytest.raises(ImageImportError, match="exceeding limit 8"):
        store_imported_image(b"not checked", output_dir=tmp_path, max_bytes=8)


def test_store_imported_image_uses_collision_safe_generated_name(
    tmp_path,
    monkeypatch,
):
    class Token:
        def __init__(self, value: str) -> None:
            self.hex = value

    tokens = iter([Token("collision"), Token("unique")])
    monkeypatch.setattr("imagegen.image_imports.uuid4", lambda: next(tokens))
    existing = tmp_path / "import-collision.png"
    existing.write_bytes(b"existing")

    stored = store_imported_image(image_bytes("PNG"), output_dir=tmp_path)

    assert stored.path == tmp_path / "import-unique.png"
    assert existing.read_bytes() == b"existing"


def test_store_imported_image_does_not_use_caller_filename_or_paths(tmp_path):
    stored = store_imported_image(image_bytes("PNG"), output_dir=tmp_path)

    assert stored.path.parent == tmp_path
    assert "/" not in stored.path.name
    assert "\\" not in stored.path.name
    assert ".." not in stored.path.name


def test_store_imported_image_preserves_existing_embedded_metadata(tmp_path):
    source_path = tmp_path / "source.png"
    Image.new("RGB", (8, 8), (255, 0, 0)).save(source_path, "PNG")
    metadata = {
        "created_at": "2026-06-07T12:00:00+00:00",
        "provider": "manual",
        "prompt": "existing metadata",
    }
    write_embedded_metadata(source_path, metadata)

    stored = store_imported_image(
        source_path.read_bytes(),
        output_dir=tmp_path / "imports",
    )

    assert read_embedded_metadata(stored.path) == metadata
