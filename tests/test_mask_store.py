"""Mask payload validation and storage tests."""

from base64 import b64encode
from io import BytesIO

import pytest
from PIL import Image

from imagegen.mask_store import MaskPayloadError, save_mask_payload


def test_save_mask_payload_writes_grayscale_mask(tmp_path):
    output_dir = tmp_path / "images"
    output_dir.mkdir()
    source_path = output_dir / "sample.png"
    Image.new("RGB", (2, 1), (255, 255, 255)).save(source_path, "PNG")

    saved_name = save_mask_payload(
        {"mask_png": _png_payload(mode="L", pixels=[0, 255], size=(2, 1))},
        source_filename="sample.png",
        source_path=source_path,
        output_dir=output_dir,
        content_length=None,
    )

    assert saved_name == "sample-mask.png"
    with Image.open(output_dir / saved_name) as image:
        assert image.mode == "L"
        assert image.size == (2, 1)
        assert image.tobytes() == bytes([0, 255])


def test_save_mask_payload_rejects_non_png_payload(tmp_path):
    source_path = tmp_path / "sample.png"
    Image.new("RGB", (1, 1), (255, 255, 255)).save(source_path, "PNG")

    with pytest.raises(MaskPayloadError, match="Mask PNG is invalid."):
        save_mask_payload(
            {"mask_png": b64encode(b"not a png").decode("ascii")},
            source_filename="sample.png",
            source_path=source_path,
            output_dir=tmp_path,
            content_length=None,
        )


def test_save_mask_payload_rejects_dimension_mismatch(tmp_path):
    source_path = tmp_path / "sample.png"
    Image.new("RGB", (2, 2), (255, 255, 255)).save(source_path, "PNG")

    with pytest.raises(
        MaskPayloadError,
        match="Mask dimensions must match the source image.",
    ):
        save_mask_payload(
            {"mask_png": _png_payload(size=(1, 1))},
            source_filename="sample.png",
            source_path=source_path,
            output_dir=tmp_path,
            content_length=None,
        )


def test_save_mask_payload_rejects_invalid_source_image(tmp_path):
    source_path = tmp_path / "sample.png"
    source_path.write_bytes(b"not an image")

    with pytest.raises(MaskPayloadError, match="Source image is invalid."):
        save_mask_payload(
            {"mask_png": _png_payload(size=(1, 1))},
            source_filename="sample.png",
            source_path=source_path,
            output_dir=tmp_path,
            content_length=None,
        )


def _png_payload(
    *,
    mode: str = "RGB",
    pixels: list[int] | None = None,
    size: tuple[int, int] = (1, 1),
) -> str:
    buffer = BytesIO()
    image = Image.new(mode, size)
    if pixels is not None:
        image.putdata(pixels)
    image.save(buffer, "PNG")
    encoded = b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"
