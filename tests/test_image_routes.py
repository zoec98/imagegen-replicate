"""Image route and gallery API tests.

Behaviors protected:
- Stored images can be viewed, downloaded normally, downloaded cleanly, and read for metadata.
- Gallery JSON lists safe local images and embedded metadata newest first.
- Image deletion moves files to trash safely and rejects missing, unsafe, or unsupported names.
"""

import os

from PIL import Image

from imagegen.app import create_app
from imagegen.metadata_embed import read_embedded_metadata, write_embedded_metadata
from route_helpers import extract_csrf_token

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


def write_sample_png(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (8, 8), (255, 0, 0)).save(path, "PNG")

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
    assert response.json == metadata

def test_image_metadata_route_404s_for_missing_embedded_metadata(
    app_config,
    app_factory,
):
    write_sample_png(app_config.output_dir / "sample.png")
    client = app_factory().test_client()

    response = client.get("/images/sample.png/metadata")

    assert response.status_code == 404

def test_api_images_returns_gallery_json_newest_first(app_config, app_factory):
    output_dir = app_config.output_dir
    output_dir.mkdir(parents=True)
    older = output_dir / "older.png"
    newer = output_dir / "newer.jpg"
    gif = output_dir / "animated.gif"
    ignored = output_dir / "ignored.txt"
    older.write_bytes(b"older")
    newer.write_bytes(b"newer")
    gif.write_bytes(b"gif")
    ignored.write_text("ignored", encoding="utf-8")
    os.utime(older, (100, 100))
    os.utime(newer, (200, 200))
    os.utime(gif, (300, 300))
    client = app_factory().test_client()

    response = client.get("/api/images")

    assert response.status_code == 200
    assert response.json == {
        "images": [
            {
                "clean_download_url": "/images/newer.jpg/download-clean",
                "delete_url": "/api/images/newer.jpg/delete",
                "download_url": "/images/newer.jpg/download",
                "filename": "newer.jpg",
                "url": "/images/newer.jpg",
                "metadata_url": None,
                "content_type": None,
                "created_at": None,
            },
            {
                "clean_download_url": "/images/older.png/download-clean",
                "delete_url": "/api/images/older.png/delete",
                "download_url": "/images/older.png/download",
                "filename": "older.png",
                "url": "/images/older.png",
                "metadata_url": None,
                "content_type": None,
                "created_at": None,
            },
        ]
    }

def test_api_images_returns_empty_gallery(app_factory):
    client = app_factory().test_client()

    response = client.get("/api/images")

    assert response.status_code == 200
    assert response.json == {"images": []}

def test_api_images_includes_embedded_metadata(app_config, app_factory):
    image_path = app_config.output_dir / "sample.png"
    write_sample_png(image_path)
    write_embedded_metadata(
        image_path,
        {
            "content_type": "image/png",
            "created_at": "2026-05-29T12:00:00+00:00",
            "model_alias": "seedream45",
            "model": "bytedance/seedream-4.5",
            "prompt": "a red house",
            "parameters": {"size": "2K"},
        },
    )
    client = app_factory().test_client()

    response = client.get("/api/images")

    assert response.status_code == 200
    assert response.json == {
        "images": [
            {
                "clean_download_url": "/images/sample.png/download-clean",
                "delete_url": "/api/images/sample.png/delete",
                "download_url": "/images/sample.png/download",
                "filename": "sample.png",
                "url": "/images/sample.png",
                "metadata_url": "/images/sample.png/metadata",
                "content_type": "image/png",
                "created_at": "2026-05-29T12:00:00+00:00",
            }
        ]
    }

def test_api_delete_image_moves_valid_image_to_trash(app_config, app_factory):
    image_path = app_config.output_dir / "sample.png"
    image_path.parent.mkdir(parents=True)
    image_path.write_bytes(b"image")
    client = app_factory().test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    response = client.post(
        "/api/images/sample.png/delete",
        json={},
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 200
    assert response.json == {"deleted": "sample.png"}
    assert not image_path.exists()
    assert (app_config.trash_dir / "sample.png").read_bytes() == b"image"

def test_api_delete_image_creates_missing_trash_dir(app_config, app_factory):
    app = app_factory()
    app_config.trash_dir.rmdir()
    image_path = app_config.output_dir / "sample.png"
    image_path.write_bytes(b"image")
    client = app.test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    response = client.post(
        "/api/images/sample.png/delete",
        json={},
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 200
    assert not image_path.exists()
    assert (app_config.trash_dir / "sample.png").read_bytes() == b"image"

def test_api_delete_image_does_not_overwrite_trash_collision(
    app_config,
    app_factory,
):
    app = app_factory()
    image_path = app_config.output_dir / "sample.png"
    image_path.write_bytes(b"new image")
    trash_path = app_config.trash_dir / "sample.png"
    trash_path.write_bytes(b"old image")
    client = app.test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    response = client.post(
        "/api/images/sample.png/delete",
        json={},
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 200
    assert response.json == {"deleted": "sample.png"}
    assert trash_path.read_bytes() == b"old image"
    collision_files = sorted(app_config.trash_dir.glob("sample-*.png"))
    assert len(collision_files) == 1
    assert collision_files[0].read_bytes() == b"new image"

def test_api_delete_image_rejects_path_traversal(app_config, app_factory):
    image_path = app_config.output_dir / "sample.png"
    image_path.parent.mkdir(parents=True)
    image_path.write_bytes(b"image")
    client = app_factory().test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    response = client.post(
        "/api/images/../sample.png/delete",
        json={},
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 404
    assert response.json == {"error": "Image not found."}
    assert image_path.exists()

def test_api_delete_image_rejects_missing_image(app_factory):
    client = app_factory().test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    response = client.post(
        "/api/images/missing.png/delete",
        json={},
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 404
    assert response.json == {"error": "Image not found."}

def test_api_delete_image_rejects_gif(app_config, app_factory):
    image_path = app_config.output_dir / "sample.gif"
    image_path.parent.mkdir(parents=True)
    image_path.write_bytes(b"gif")
    client = app_factory().test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    response = client.post(
        "/api/images/sample.gif/delete",
        json={},
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 404
    assert response.json == {"error": "Image not found."}
    assert image_path.exists()

def test_api_delete_image_requires_csrf(app_config, app_factory):
    image_path = app_config.output_dir / "sample.png"
    image_path.parent.mkdir(parents=True)
    image_path.write_bytes(b"image")
    client = app_factory().test_client()
    client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})

    response = client.post(
        "/api/images/sample.png/delete",
        json={},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 403
    assert response.json == {"error": "Invalid CSRF token."}
    assert image_path.exists()
