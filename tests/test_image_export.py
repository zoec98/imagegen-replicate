"""Clean image export tests.

Behaviors protected:
- Clean image exports strip embedded metadata without mutating stored gallery files.
- Clean exports are written outside the gallery and stay hidden from gallery listings.
"""

from PIL import Image

from imagegen.image_export import clean_image_export
from imagegen.metadata_embed import (
    PNG_METADATA_KEY,
    read_embedded_metadata,
    write_embedded_metadata,
)


def sample_metadata():
    return {
        "created_at": "2026-05-30T12:00:00+00:00",
        "model_alias": "seedream45",
        "model": "bytedance/seedream-4.5",
        "prompt": "a small red house",
        "parameters": {"size": "2K"},
        "author": "Zoé Cordelier",
        "copyright": "© 2026 Zoé Cordelier",
        "software": "imagegen",
    }


def write_sample(path, image_format):
    Image.new("RGB", (8, 8), (255, 0, 0)).save(path, image_format)


def test_clean_png_export_strips_text_and_app_metadata(tmp_path):
    source_path = tmp_path / "sample.png"
    write_sample(source_path, "PNG")
    write_embedded_metadata(source_path, sample_metadata())

    export_path = clean_image_export(source_path, tmp_dir=tmp_path / "tmp")

    assert export_path.parent == tmp_path / "tmp"
    assert export_path.name.startswith("sample-clean-")
    assert source_path.exists()
    assert read_embedded_metadata(source_path) == sample_metadata()
    assert read_embedded_metadata(export_path) is None
    with Image.open(export_path) as exported:
        assert exported.format == "PNG"
        assert PNG_METADATA_KEY not in exported.info
        assert "Author" not in exported.info
        assert "Copyright" not in exported.info
        assert exported.getpixel((0, 0)) == (255, 0, 0)


def test_clean_jpeg_export_strips_exif_and_app_metadata(tmp_path):
    source_path = tmp_path / "sample.jpg"
    write_sample(source_path, "JPEG")
    write_embedded_metadata(source_path, sample_metadata())

    export_path = clean_image_export(source_path, tmp_dir=tmp_path / "tmp")

    assert source_path.exists()
    assert read_embedded_metadata(source_path) == sample_metadata()
    assert read_embedded_metadata(export_path) is None
    with Image.open(export_path) as exported:
        assert exported.format == "JPEG"
        assert not exported.getexif()


def test_clean_webp_export_strips_exif_and_app_metadata(tmp_path):
    source_path = tmp_path / "sample.webp"
    write_sample(source_path, "WEBP")
    write_embedded_metadata(source_path, sample_metadata())

    export_path = clean_image_export(source_path, tmp_dir=tmp_path / "tmp")

    assert source_path.exists()
    assert read_embedded_metadata(source_path) == sample_metadata()
    assert read_embedded_metadata(export_path) is None
    with Image.open(export_path) as exported:
        assert exported.format == "WEBP"
        assert not exported.getexif()


def test_clean_exports_do_not_appear_in_gallery(app_config, app_factory):
    source_path = app_config.output_dir / "sample.png"
    source_path.parent.mkdir(parents=True)
    write_sample(source_path, "PNG")
    export_path = clean_image_export(source_path, tmp_dir=app_config.tmp_dir)
    client = app_factory().test_client()

    response = client.get("/api/images")

    assert response.status_code == 200
    assert [image["filename"] for image in response.json["images"]] == ["sample.png"]
    assert export_path.name not in response.get_data(as_text=True)
