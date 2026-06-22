"""Local image edit operation tests.

Behaviors protected:
- Crop writes a new image without mutating the source.
- Crop validation rejects unsafe rectangles before writing output.
- Crop preserves existing embedded application metadata exactly.
"""

import pytest
from PIL import Image

from imagegen.image_edits import ImageEditError, crop_image
from imagegen.metadata_embed import read_embedded_metadata, write_embedded_metadata


def test_crop_image_writes_new_cropped_image(tmp_path):
    source_path = tmp_path / "sample.png"
    Image.new("RGB", (20, 20), (255, 0, 0)).save(source_path, "PNG")
    original_bytes = source_path.read_bytes()

    edited = crop_image(
        {"rectangle": {"x": 2, "y": 3, "width": 10, "height": 11}},
        source_filename="sample.png",
        output_dir=tmp_path,
    )

    assert edited.path.name.startswith("sample-crop-")
    assert edited.path.suffix == ".png"
    assert source_path.read_bytes() == original_bytes
    with Image.open(edited.path) as image:
        assert image.size == (10, 11)
        assert image.getpixel((0, 0)) == (255, 0, 0)


def test_crop_image_rejects_too_small_rectangle_without_writing_output(tmp_path):
    source_path = tmp_path / "sample.png"
    Image.new("RGB", (20, 20), (255, 0, 0)).save(source_path, "PNG")

    with pytest.raises(ImageEditError, match="at least 10 by 10 pixels"):
        crop_image(
            {"rectangle": {"x": 0, "y": 0, "width": 9, "height": 10}},
            source_filename="sample.png",
            output_dir=tmp_path,
        )

    assert list(tmp_path.glob("sample-crop-*.png")) == []


def test_crop_image_preserves_embedded_metadata(tmp_path):
    source_path = tmp_path / "sample.png"
    Image.new("RGB", (20, 20), (255, 0, 0)).save(source_path, "PNG")
    metadata = {
        "created_at": "2026-06-22T12:00:00+00:00",
        "provider": "manual",
        "prompt": "existing metadata",
    }
    write_embedded_metadata(source_path, metadata)

    edited = crop_image(
        {"rectangle": {"x": 0, "y": 0, "width": 10, "height": 10}},
        source_filename="sample.png",
        output_dir=tmp_path,
    )

    assert read_embedded_metadata(edited.path) == metadata
