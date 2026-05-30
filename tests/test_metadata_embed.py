from io import BytesIO

import pytest
from PIL import Image

from imagegen.metadata_embed import (
    EmbeddedMetadataError,
    IMAGE_DESCRIPTION_TAG,
    PNG_METADATA_KEY,
    human_description,
    read_embedded_metadata,
    write_embedded_metadata,
)


def write_sample_image(path, image_format):
    Image.new("RGB", (8, 8), (255, 0, 0)).save(path, image_format)


def sample_metadata():
    return {
        "created_at": "2026-05-30T12:00:00+00:00",
        "model_alias": "seedream45",
        "model": "bytedance/seedream-4.5",
        "prediction_id": "abc123",
        "sequence": 1,
        "prompt": "a small red house",
        "parameters": {
            "prompt": "a small red house",
            "size": "2K",
            "disable_safety_checker": True,
        },
        "source_url": "https://example.com/out.png",
        "content_type": "image/png",
        "size_bytes": 123,
        "filename": "sample.png",
    }


@pytest.mark.parametrize(
    ("image_format", "suffix"),
    [
        ("JPEG", ".jpg"),
        ("PNG", ".png"),
        ("WEBP", ".webp"),
    ],
)
def test_embedded_metadata_round_trips_parameters(tmp_path, image_format, suffix):
    image_path = tmp_path / f"sample{suffix}"
    metadata = sample_metadata()
    write_sample_image(image_path, image_format)

    write_embedded_metadata(image_path, metadata)

    assert read_embedded_metadata(image_path) == metadata


def test_embedded_metadata_preserves_existing_png_text(tmp_path):
    image_path = tmp_path / "sample.png"
    image = Image.new("RGB", (8, 8), (255, 0, 0))
    image.save(image_path, "PNG")
    metadata = sample_metadata()

    write_embedded_metadata(image_path, metadata)

    with Image.open(image_path) as reloaded:
        assert reloaded.info[PNG_METADATA_KEY]
        assert "Generated image" in reloaded.info["Description"]
        assert "a small red house" in reloaded.info["ImageDescription"]


def test_embedded_metadata_writes_human_exif_description(tmp_path):
    image_path = tmp_path / "sample.jpg"
    metadata = sample_metadata()
    write_sample_image(image_path, "JPEG")

    write_embedded_metadata(image_path, metadata)

    with Image.open(image_path) as reloaded:
        description = reloaded.getexif()[IMAGE_DESCRIPTION_TAG]
    assert "Generated image" in description
    assert "2026-05-30T12:00:00+00:00" in description
    assert "bytedance/seedream-4.5" in description
    assert "Prompt: a small red house" in description


def test_human_description_handles_missing_optional_fields():
    assert human_description({}) == "Generated image."


def test_write_embedded_metadata_rejects_unsupported_file(tmp_path):
    image_path = tmp_path / "sample.txt"
    image_path.write_text("not an image", encoding="utf-8")

    with pytest.raises(EmbeddedMetadataError):
        write_embedded_metadata(image_path, sample_metadata())


def test_read_embedded_metadata_returns_none_for_missing_payload(tmp_path):
    image_path = tmp_path / "sample.jpg"
    buffer = BytesIO()
    Image.new("RGB", (8, 8), (255, 0, 0)).save(buffer, "JPEG")
    image_path.write_bytes(buffer.getvalue())

    assert read_embedded_metadata(image_path) is None
