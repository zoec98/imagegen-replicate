"""Local image edit operation tests.

Behaviors protected:
- Crop writes a new image without mutating the source.
- Crop validation rejects unsafe rectangles before writing output.
- Crop preserves existing embedded application metadata exactly.
"""

import pytest
from base64 import b64encode
from io import BytesIO
from PIL import Image

from imagegen.image_edits import ImageEditError, blur_image, crop_image
from imagegen.metadata_embed import read_embedded_metadata, write_embedded_metadata


def mask_payload(pixels, size):
    buffer = BytesIO()
    image = Image.new("L", size)
    image.putdata(pixels)
    image.save(buffer, "PNG")
    encoded = b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


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


def test_blur_image_blurs_only_masked_pixels(tmp_path):
    source_path = tmp_path / "sample.png"
    source = Image.new("RGB", (8, 8), (255, 0, 0))
    for x in range(4, 8):
        for y in range(8):
            source.putpixel((x, y), (0, 0, 255))
    source.save(source_path, "PNG")
    original_bytes = source_path.read_bytes()

    edited = blur_image(
        {
            "blur_radius": 4,
            "mask_png": mask_payload(
                [255 if x >= 4 else 0 for _y in range(8) for x in range(8)],
                (8, 8),
            ),
        },
        source_filename="sample.png",
        output_dir=tmp_path,
    )

    assert edited.path.name.startswith("sample-blur-")
    assert edited.path.suffix == ".png"
    assert source_path.read_bytes() == original_bytes
    with Image.open(edited.path) as image:
        assert image.size == (8, 8)
        assert image.getpixel((0, 0)) == (255, 0, 0)
        assert image.getpixel((7, 0)) != (0, 0, 255)


def test_blur_image_preserves_embedded_metadata(tmp_path):
    source_path = tmp_path / "sample.png"
    Image.new("RGB", (8, 8), (255, 0, 0)).save(source_path, "PNG")
    metadata = {
        "created_at": "2026-06-22T12:00:00+00:00",
        "provider": "manual",
        "prompt": "existing metadata",
    }
    write_embedded_metadata(source_path, metadata)

    edited = blur_image(
        {
            "blur_radius": 2.5,
            "mask_png": mask_payload([255] + [0] * 63, (8, 8)),
        },
        source_filename="sample.png",
        output_dir=tmp_path,
    )

    assert read_embedded_metadata(edited.path) == metadata


def test_blur_image_does_not_add_metadata_when_source_has_none(tmp_path):
    source_path = tmp_path / "sample.png"
    Image.new("RGB", (8, 8), (255, 0, 0)).save(source_path, "PNG")

    edited = blur_image(
        {
            "blur_radius": 2,
            "mask_png": mask_payload([255] + [0] * 63, (8, 8)),
        },
        source_filename="sample.png",
        output_dir=tmp_path,
    )

    assert read_embedded_metadata(edited.path) is None


def test_blur_image_accepts_maximum_radius(tmp_path):
    source_path = tmp_path / "sample.png"
    Image.new("RGB", (1, 1), (255, 0, 0)).save(source_path, "PNG")

    edited = blur_image(
        {"blur_radius": 50, "mask_png": mask_payload([255], (1, 1))},
        source_filename="sample.png",
        output_dir=tmp_path,
    )

    assert edited.path.is_file()


@pytest.mark.parametrize(
    ("payload", "error"),
    [
        ({"mask_png": mask_payload([255], (1, 1))}, "Blur radius is required."),
        (
            {"blur_radius": "2", "mask_png": mask_payload([255], (1, 1))},
            "Blur radius must be a number.",
        ),
        (
            {"blur_radius": -0.1, "mask_png": mask_payload([255], (1, 1))},
            "Blur radius must be between 0 and 50 pixels.",
        ),
        (
            {"blur_radius": 50.1, "mask_png": mask_payload([255], (1, 1))},
            "Blur radius must be between 0 and 50 pixels.",
        ),
    ],
)
def test_blur_image_rejects_invalid_radius(tmp_path, payload, error):
    source_path = tmp_path / "sample.png"
    Image.new("RGB", (1, 1), (255, 0, 0)).save(source_path, "PNG")

    with pytest.raises(ImageEditError, match=error):
        blur_image(payload, source_filename="sample.png", output_dir=tmp_path)

    assert list(tmp_path.glob("sample-blur-*.png")) == []


@pytest.mark.parametrize(
    ("payload", "error"),
    [
        (
            {"blur_radius": 2},
            "Mask PNG is required.",
        ),
        (
            {"blur_radius": 2, "mask_png": mask_payload([0] * 64, (8, 8))},
            "Mask must mark at least one pixel.",
        ),
        (
            {"blur_radius": 2, "mask_png": mask_payload([255], (1, 1))},
            "Mask dimensions must match the source image.",
        ),
    ],
)
def test_blur_image_rejects_invalid_mask(tmp_path, payload, error):
    source_path = tmp_path / "sample.png"
    Image.new("RGB", (8, 8), (255, 0, 0)).save(source_path, "PNG")

    with pytest.raises(ImageEditError, match=error):
        blur_image(payload, source_filename="sample.png", output_dir=tmp_path)

    assert list(tmp_path.glob("sample-blur-*.png")) == []
