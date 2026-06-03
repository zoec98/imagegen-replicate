"""Generated image metadata provider tests.

Behaviors protected:
- Metadata objects report existence only when generated-image fields are present.
- The metadata provider reads embedded metadata and ignores JSON sidecars.
"""

from PIL import Image

from imagegen.metadata import EmbeddedImageMetadataProvider, ImageMetadata
from imagegen.metadata_embed import write_embedded_metadata


def test_image_metadata_exists_when_known_fields_are_present():
    assert ImageMetadata().exists is False
    assert ImageMetadata(content_type="image/png").exists is True
    assert ImageMetadata(created_at="2026-05-29T12:00:00+00:00").exists is True
    assert ImageMetadata(provider="replicate").exists is True
    assert ImageMetadata(model_alias="seedream45").exists is True
    assert ImageMetadata(model="bytedance/seedream-4.5").exists is True
    assert ImageMetadata(prompt="a red house").exists is True
    assert ImageMetadata(parameters={"size": "2K"}).exists is True


def test_embedded_metadata_provider_reads_embedded_metadata(tmp_path):
    image_path = tmp_path / "sample.png"
    Image.new("RGB", (8, 8), (255, 0, 0)).save(image_path, "PNG")
    write_embedded_metadata(
        image_path,
        {
            "content_type": "image/png",
            "created_at": "2026-05-29T12:00:00+00:00",
            "provider": "falai",
            "model_alias": "seedream45",
            "model": "fal-ai/bytedance/seedream/v4.5/edit",
            "prompt": "a red house",
            "parameters": {"size": "2K"},
        },
    )

    metadata = EmbeddedImageMetadataProvider().get(image_path)

    assert metadata == ImageMetadata(
        content_type="image/png",
        created_at="2026-05-29T12:00:00+00:00",
        provider="falai",
        model_alias="seedream45",
        model="fal-ai/bytedance/seedream/v4.5/edit",
        prompt="a red house",
        parameters={"size": "2K"},
    )
    assert metadata.to_json() == {
        "content_type": "image/png",
        "created_at": "2026-05-29T12:00:00+00:00",
        "provider": "falai",
        "model_alias": "seedream45",
        "model": "fal-ai/bytedance/seedream/v4.5/edit",
        "prompt": "a red house",
        "parameters": {"size": "2K"},
    }


def test_embedded_metadata_provider_ignores_json_sidecar_metadata(tmp_path):
    image_path = tmp_path / "sample.png"
    image_path.write_bytes(b"image-bytes")
    image_path.with_name("sample.png.json").write_text(
        '{"content_type": "image/png", "created_at": "2026-05-29T12:00:00+00:00"}',
        encoding="utf-8",
    )

    metadata = EmbeddedImageMetadataProvider().get(image_path)

    assert metadata == ImageMetadata()
