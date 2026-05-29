import json

from imagegen.metadata import ImageMetadata, SidecarImageMetadataProvider


def test_image_metadata_exists_when_known_fields_are_present():
    assert ImageMetadata().exists is False
    assert ImageMetadata(content_type="image/png").exists is True
    assert ImageMetadata(created_at="2026-05-29T12:00:00+00:00").exists is True


def test_sidecar_metadata_provider_reads_known_fields(tmp_path):
    image_path = tmp_path / "sample.png"
    image_path.write_bytes(b"image-bytes")
    image_path.with_name("sample.png.json").write_text(
        json.dumps(
            {
                "content_type": "image/png",
                "created_at": "2026-05-29T12:00:00+00:00",
                "ignored": "not part of provider contract",
            }
        ),
        encoding="utf-8",
    )

    metadata = SidecarImageMetadataProvider().get(image_path)

    assert metadata == ImageMetadata(
        content_type="image/png",
        created_at="2026-05-29T12:00:00+00:00",
    )
    assert metadata.to_json() == {
        "content_type": "image/png",
        "created_at": "2026-05-29T12:00:00+00:00",
    }


def test_sidecar_metadata_provider_returns_empty_metadata_for_bad_sidecar(tmp_path):
    image_path = tmp_path / "sample.png"
    image_path.write_bytes(b"image-bytes")
    image_path.with_name("sample.png.json").write_text("not json", encoding="utf-8")

    metadata = SidecarImageMetadataProvider().get(image_path)

    assert metadata == ImageMetadata()
