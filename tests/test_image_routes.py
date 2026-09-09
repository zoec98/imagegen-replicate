"""Stored image serving, download, and metadata route tests."""

from image_route_helpers import write_sample_png

from imagegen.app import create_app
from imagegen.metadata_embed import read_embedded_metadata, write_embedded_metadata


def test_image_route_serves_stored_file(app_config, app_factory):
    app_config.output_dir.mkdir(parents=True)
    (app_config.output_dir / "sample.png").write_bytes(b"image-bytes")
    client = app_factory().test_client()

    response = client.get("/images/sample.png")

    assert response.status_code == 200
    assert response.data == b"image-bytes"


def test_image_route_uses_env_relative_data_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("IMAGEGEN_DATA_DIR", raising=False)
    monkeypatch.delenv("IMAGEGEN_MODEL", raising=False)
    monkeypatch.delenv("IMAGEGEN_FLASK_SECRET_KEY", raising=False)
    output_dir = tmp_path / "data" / "images"
    output_dir.mkdir(parents=True)
    (output_dir / "sample.png").write_bytes(b"image-bytes")
    (tmp_path / ".env").write_text(
        "IMAGEGEN_DATA_DIR=data\n"
        "IMAGEGEN_MODEL=seedream45\n"
        "IMAGEGEN_FLASK_SECRET_KEY=test-secret\n",
        encoding="utf-8",
    )
    app = create_app({"TESTING": True, "IMAGEGEN_ENV_PATH": tmp_path / ".env"})

    response = app.test_client().get("/images/sample.png")

    assert response.status_code == 200
    assert response.data == b"image-bytes"


def test_image_route_blocks_unsafe_paths(app_factory):
    client = app_factory().test_client()

    response = client.get("/images/../pyproject.toml")

    assert response.status_code == 404


def test_image_route_blocks_gif_files(app_config, app_factory):
    app_config.output_dir.mkdir(parents=True)
    (app_config.output_dir / "animated.gif").write_bytes(b"gif")
    client = app_factory().test_client()

    response = client.get("/images/animated.gif")

    assert response.status_code == 404


def test_image_view_renders_full_image_page(app_config, app_factory):
    app_config.output_dir.mkdir(parents=True)
    (app_config.output_dir / "sample.png").write_bytes(b"image-bytes")
    client = app_factory().test_client()

    response = client.get("/images/sample.png/view")

    assert response.status_code == 302
    assert response.headers["Location"] == "/images/sample.png"


def test_image_download_forces_stored_file_attachment(app_config, app_factory):
    app_config.output_dir.mkdir(parents=True)
    (app_config.output_dir / "sample.png").write_bytes(b"image-bytes")
    client = app_factory().test_client()

    response = client.get("/images/sample.png/download")

    assert response.status_code == 200
    assert response.data == b"image-bytes"
    assert response.headers["Content-Disposition"].startswith(
        "attachment; filename=sample.png"
    )


def test_image_download_rejects_unsafe_paths(app_factory):
    client = app_factory().test_client()

    response = client.get("/images/../sample.png/download")

    assert response.status_code == 404


def test_image_download_clean_returns_stripped_attachment(app_config, app_factory):
    image_path = app_config.output_dir / "sample.png"
    write_sample_png(image_path)
    metadata = {
        "content_type": "image/png",
        "created_at": "2026-05-29T12:00:00+00:00",
        "model_alias": "seedream45",
        "model": "bytedance/seedream-4.5",
        "prompt": "a red house",
        "parameters": {"size": "2K"},
        "author": "Zoé Cordelier",
        "copyright": "© 2026 Zoé Cordelier",
        "software": "imagegen",
    }
    write_embedded_metadata(image_path, metadata)
    client = app_factory().test_client()

    response = client.get("/images/sample.png/download-clean")

    assert response.status_code == 200
    assert response.headers["Content-Disposition"].startswith(
        "attachment; filename=sample-clean.png"
    )
    assert read_embedded_metadata(image_path) == metadata
    clean_path = app_config.tmp_dir / "downloaded-clean.png"
    clean_path.write_bytes(response.data)
    assert read_embedded_metadata(clean_path) is None


def test_image_download_clean_rejects_missing_file(app_factory):
    client = app_factory().test_client()

    response = client.get("/images/missing.png/download-clean")

    assert response.status_code == 404


def test_image_metadata_route_serves_embedded_metadata(app_config, app_factory):
    image_path = app_config.output_dir / "sample.png"
    write_sample_png(image_path)
    metadata = {
        "content_type": "image/png",
        "created_at": "2026-05-29T12:00:00+00:00",
        "model_alias": "seedream45",
        "model": "bytedance/seedream-4.5",
        "prompt": "a red house",
        "parameters": {"size": "2K"},
    }
    write_embedded_metadata(image_path, metadata)
    client = app_factory().test_client()

    response = client.get("/images/sample.png/metadata")

    assert response.status_code == 200
    assert response.json == {**metadata, "provider": "replicate", "edit_mode": False}


def test_image_metadata_route_exposes_edit_source_images(app_config, app_factory):
    image_path = app_config.output_dir / "sample.png"
    source_a = app_config.output_dir / "source-a.jpg"
    source_b = app_config.output_dir / "source-b.jpg"
    write_sample_png(image_path)
    write_sample_png(source_a)
    write_sample_png(source_b)
    write_embedded_metadata(
        image_path,
        {
            "content_type": "image/png",
            "provider": "replicate",
            "model_alias": "seedream45",
            "model": "bytedance/seedream-4.5",
            "prompt": "edit this",
            "parameters": {
                "prompt": "edit this",
                "image_input": ["source-a.jpg", "source-b.jpg"],
                "size": "4K",
            },
        },
    )
    client = app_factory().test_client()

    response = client.get("/images/sample.png/metadata")

    assert response.status_code == 200
    assert response.json["edit_mode"] is True
    assert response.json["source_images"] == ["source-a.jpg", "source-b.jpg"]


def test_image_metadata_route_warns_for_unavailable_edit_source_images(
    app_config,
    app_factory,
):
    image_path = app_config.output_dir / "sample.png"
    write_sample_png(image_path)
    write_embedded_metadata(
        image_path,
        {
            "content_type": "image/png",
            "provider": "replicate",
            "model_alias": "seedream45",
            "model": "bytedance/seedream-4.5",
            "prompt": "edit this",
            "parameters": {
                "prompt": "edit this",
                "image_input": ["../secret.jpg", ".hidden.jpg", "missing.jpg"],
                "size": "4K",
            },
        },
    )
    client = app_factory().test_client()

    response = client.get("/images/sample.png/metadata")

    assert response.status_code == 200
    assert response.json["edit_mode"] is True
    assert response.json["source_images"] == []
    assert response.json["warnings"] == [
        "Some saved source image references were ignored because they are unsafe.",
        "Some saved source images are no longer available.",
    ]


def test_image_metadata_route_404s_for_missing_embedded_metadata(
    app_config,
    app_factory,
):
    write_sample_png(app_config.output_dir / "sample.png")
    client = app_factory().test_client()

    response = client.get("/images/sample.png/metadata")

    assert response.status_code == 404
