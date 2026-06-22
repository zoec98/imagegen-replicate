"""Image route and gallery API tests.

Behaviors protected:
- Stored images can be viewed, downloaded normally, downloaded cleanly, and read for metadata.
- Gallery JSON lists safe local images and embedded metadata newest first.
- Image deletion moves files to trash safely and rejects missing, unsafe, or unsupported names.
- Mask saving rejects unsafe names, invalid payloads, dimension mismatches, missing CSRF,
  and oversized payloads before storing a provider-ready mask.
"""

import os
from base64 import b64encode
from dataclasses import replace
from io import BytesIO

import httpx
import pytest
from PIL import Image

from imagegen.app import create_app
from imagegen.mask_store import (
    MASK_PNG_ABSOLUTE_DECODED_LIMIT_BYTES,
    MASK_DATA_URL_PREFIX,
    MASK_JSON_FIXED_OVERHEAD_BYTES,
    MASK_PNG_BYTES_PER_PIXEL_LIMIT,
    MASK_PNG_FIXED_OVERHEAD_BYTES,
    mask_payload_limits,
)
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


def route_image_bytes(image_format):
    buffer = BytesIO()
    Image.new("RGB", (8, 8), (255, 0, 0)).save(buffer, image_format)
    return buffer.getvalue()


def import_response_client(response):
    return httpx.Client(transport=httpx.MockTransport(lambda request: response))


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
    os.utime(older, (2_000_000_000, 2_000_000_000))
    os.utime(newer, (2_000_000_100, 2_000_000_100))
    os.utime(gif, (300, 300))
    client = app_factory().test_client()

    response = client.get("/api/images")

    assert response.status_code == 200
    assert response.json == {
        "images": [
            {
                "clean_download_url": "/images/newer.jpg/download-clean",
                "blur_save_url": "/api/images/newer.jpg/blur",
                "crop_save_url": "/api/images/newer.jpg/crop",
                "delete_url": "/api/images/newer.jpg/delete",
                "download_url": "/images/newer.jpg/download",
                "filename": "newer.jpg",
                "mask_save_url": "/api/images/newer.jpg/mask",
                "mask_url": "/images/newer-mask.png",
                "url": "/images/newer.jpg",
                "metadata_url": None,
                "content_type": None,
                "created_at": None,
            },
            {
                "clean_download_url": "/images/older.png/download-clean",
                "blur_save_url": "/api/images/older.png/blur",
                "crop_save_url": "/api/images/older.png/crop",
                "delete_url": "/api/images/older.png/delete",
                "download_url": "/images/older.png/download",
                "filename": "older.png",
                "mask_save_url": "/api/images/older.png/mask",
                "mask_url": "/images/older-mask.png",
                "url": "/images/older.png",
                "metadata_url": None,
                "content_type": None,
                "created_at": None,
            },
        ],
        "trash_count": 0,
    }


def test_api_images_returns_empty_gallery(app_factory):
    client = app_factory().test_client()

    response = client.get("/api/images")

    assert response.status_code == 200
    assert response.json == {"images": [], "trash_count": 0}


def test_api_images_purges_old_trash_and_returns_updated_count(
    app_config,
    app_factory,
):
    app_config.output_dir.mkdir(parents=True)
    app_config.trash_dir.mkdir(parents=True)
    active_image = app_config.output_dir / "active.png"
    old_trash = app_config.trash_dir / "old.png"
    fresh_trash = app_config.trash_dir / "fresh.png"
    active_image.write_bytes(b"active")
    old_trash.write_bytes(b"old")
    fresh_trash.write_bytes(b"fresh")
    old_timestamp = 100
    fresh_timestamp = 2_000_000_000
    os.utime(old_trash, (old_timestamp, old_timestamp))
    os.utime(fresh_trash, (fresh_timestamp, fresh_timestamp))
    client = app_factory().test_client()

    response = client.get("/api/images")

    assert response.status_code == 200
    assert response.json["trash_count"] == 1
    assert not old_trash.exists()
    assert fresh_trash.is_file()
    assert active_image.is_file()


def test_api_images_skips_trash_purge_when_retention_disabled(
    app_config,
    app_factory,
):
    app_config.trash_dir.mkdir(parents=True)
    old_trash = app_config.trash_dir / "old.png"
    old_trash.write_bytes(b"old")
    os.utime(old_trash, (100, 100))
    disabled_config = replace(app_config, trashcan_hold_limit_days=None)
    client = app_factory(IMAGEGEN_APP_CONFIG=disabled_config).test_client()

    response = client.get("/api/images")

    assert response.status_code == 200
    assert response.json == {"images": [], "trash_count": 1}
    assert old_trash.is_file()


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
                "blur_save_url": "/api/images/sample.png/blur",
                "crop_save_url": "/api/images/sample.png/crop",
                "delete_url": "/api/images/sample.png/delete",
                "download_url": "/images/sample.png/download",
                "filename": "sample.png",
                "mask_save_url": "/api/images/sample.png/mask",
                "mask_url": "/images/sample-mask.png",
                "url": "/images/sample.png",
                "metadata_url": "/images/sample.png/metadata",
                "content_type": "image/png",
                "created_at": "2026-05-29T12:00:00+00:00",
            }
        ],
        "trash_count": 0,
    }


def test_api_import_image_url_stores_http_image(app_config, app_factory):
    http_client = import_response_client(
        httpx.Response(
            200,
            content=route_image_bytes("PNG"),
            request=httpx.Request("GET", "http://example.test/image.png"),
        )
    )
    app = app_factory(IMAGEGEN_IMAGE_IMPORT_HTTP_CLIENT=http_client)
    client = app.test_client()
    token = extract_csrf_token(client.get("/"))

    response = client.post(
        "/api/images/import-url",
        json={"url": "http://example.test/image.png"},
        headers={"X-CSRF-Token": token},
    )

    assert response.status_code == 201
    image = response.json["image"]
    assert image == {
        "clean_download_url": f"/images/{image['filename']}/download-clean",
        "blur_save_url": f"/api/images/{image['filename']}/blur",
        "crop_save_url": f"/api/images/{image['filename']}/crop",
        "delete_url": f"/api/images/{image['filename']}/delete",
        "download_url": f"/images/{image['filename']}/download",
        "filename": image["filename"],
        "mask_save_url": f"/api/images/{image['filename']}/mask",
        "mask_url": f"/images/{image['filename'].removesuffix('.png')}-mask.png",
        "url": f"/images/{image['filename']}",
        "metadata_url": None,
        "content_type": None,
        "created_at": None,
    }
    assert image["filename"].startswith("import-")
    assert image["filename"].endswith(".png")
    with Image.open(app_config.output_dir / image["filename"]) as stored:
        assert stored.format == "PNG"


def test_api_import_image_url_stores_https_image(app_config, app_factory):
    http_client = import_response_client(
        httpx.Response(
            200,
            content=route_image_bytes("JPEG"),
            request=httpx.Request("GET", "https://example.test/image.jpg"),
        )
    )
    client = app_factory(IMAGEGEN_IMAGE_IMPORT_HTTP_CLIENT=http_client).test_client()
    token = extract_csrf_token(client.get("/"))

    response = client.post(
        "/api/images/import-url",
        json={"url": "https://example.test/image.jpg"},
        headers={"X-CSRF-Token": token},
    )

    assert response.status_code == 201
    assert response.json["image"]["filename"].startswith("import-")
    assert response.json["image"]["filename"].endswith(".jpg")


def test_api_import_image_url_rejects_non_http_scheme(app_factory):
    client = app_factory().test_client()
    token = extract_csrf_token(client.get("/"))

    response = client.post(
        "/api/images/import-url",
        json={"url": "file:///tmp/image.png"},
        headers={"X-CSRF-Token": token},
    )

    assert response.status_code == 400
    assert response.json == {"error": "Image URL must use http or https."}


def test_api_import_image_url_rejects_missing_or_invalid_payload(app_factory):
    client = app_factory().test_client()
    token = extract_csrf_token(client.get("/"))

    response = client.post(
        "/api/images/import-url",
        json={},
        headers={"X-CSRF-Token": token},
    )

    assert response.status_code == 400
    assert response.json == {"error": "Image URL is required."}


def test_api_import_image_url_rejects_malformed_url(app_factory):
    client = app_factory().test_client()
    token = extract_csrf_token(client.get("/"))

    response = client.post(
        "/api/images/import-url",
        json={"url": "https://"},
        headers={"X-CSRF-Token": token},
    )

    assert response.status_code == 400
    assert response.json == {"error": "Image URL must include a host."}


def test_api_import_image_url_reports_fetch_failures(app_factory):
    def handler(request):
        raise httpx.ConnectError("connection failed", request=request)

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = app_factory(IMAGEGEN_IMAGE_IMPORT_HTTP_CLIENT=http_client).test_client()
    token = extract_csrf_token(client.get("/"))

    response = client.post(
        "/api/images/import-url",
        json={"url": "https://example.test/image.png"},
        headers={"X-CSRF-Token": token},
    )

    assert response.status_code == 400
    assert response.json == {"error": "Image URL request failed."}


def test_api_import_image_url_rejects_oversized_response(app_factory):
    http_client = import_response_client(
        httpx.Response(
            200,
            headers={"content-length": "9"},
            content=b"too large",
            request=httpx.Request("GET", "https://example.test/image.png"),
        )
    )
    client = app_factory(
        IMAGEGEN_IMAGE_IMPORT_HTTP_CLIENT=http_client,
        IMAGEGEN_IMAGE_IMPORT_MAX_BYTES=8,
    ).test_client()
    token = extract_csrf_token(client.get("/"))

    response = client.post(
        "/api/images/import-url",
        json={"url": "https://example.test/image.png"},
        headers={"X-CSRF-Token": token},
    )

    assert response.status_code == 400
    assert response.json == {"error": "Image download is too large."}


def test_api_import_image_url_rejects_non_image_response(app_factory):
    http_client = import_response_client(
        httpx.Response(
            200,
            content=b"not an image",
            request=httpx.Request("GET", "https://example.test/image.txt"),
        )
    )
    client = app_factory(IMAGEGEN_IMAGE_IMPORT_HTTP_CLIENT=http_client).test_client()
    token = extract_csrf_token(client.get("/"))

    response = client.post(
        "/api/images/import-url",
        json={"url": "https://example.test/image.txt"},
        headers={"X-CSRF-Token": token},
    )

    assert response.status_code == 400
    assert response.json == {"error": "Uploaded file is not a valid image."}


def test_api_import_image_url_rejects_unsupported_image_format(app_factory):
    http_client = import_response_client(
        httpx.Response(
            200,
            content=route_image_bytes("GIF"),
            request=httpx.Request("GET", "https://example.test/image.gif"),
        )
    )
    client = app_factory(IMAGEGEN_IMAGE_IMPORT_HTTP_CLIENT=http_client).test_client()
    token = extract_csrf_token(client.get("/"))

    response = client.post(
        "/api/images/import-url",
        json={"url": "https://example.test/image.gif"},
        headers={"X-CSRF-Token": token},
    )

    assert response.status_code == 400
    assert response.json == {"error": "Unsupported image format: GIF."}


def test_api_import_image_url_requires_csrf(app_factory):
    http_client = import_response_client(
        httpx.Response(
            200,
            content=route_image_bytes("PNG"),
            request=httpx.Request("GET", "https://example.test/image.png"),
        )
    )
    client = app_factory(IMAGEGEN_IMAGE_IMPORT_HTTP_CLIENT=http_client).test_client()
    client.get("/")

    response = client.post(
        "/api/images/import-url",
        json={"url": "https://example.test/image.png"},
    )

    assert response.status_code == 403
    assert response.json == {"error": "Invalid CSRF token."}


def test_api_import_uploaded_image_stores_single_file(app_config, app_factory):
    client = app_factory().test_client()
    token = extract_csrf_token(client.get("/"))

    response = client.post(
        "/api/images/import-upload",
        data={
            "image": (
                BytesIO(route_image_bytes("PNG")),
                "ignored-client-name.png",
                "image/png",
            )
        },
        headers={"X-CSRF-Token": token},
        content_type="multipart/form-data",
    )

    assert response.status_code == 201
    image = response.json["image"]
    assert image["filename"].startswith("import-")
    assert image["filename"].endswith(".png")
    assert image["filename"] != "ignored-client-name.png"
    assert image["url"] == f"/images/{image['filename']}"
    assert image["delete_url"] == f"/api/images/{image['filename']}/delete"
    with Image.open(app_config.output_dir / image["filename"]) as stored:
        assert stored.format == "PNG"


def test_api_import_uploaded_image_rejects_missing_file(app_factory):
    client = app_factory().test_client()
    token = extract_csrf_token(client.get("/"))

    response = client.post(
        "/api/images/import-upload",
        data={},
        headers={"X-CSRF-Token": token},
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert response.json == {"error": "Image file is required."}


def test_api_import_uploaded_image_rejects_empty_upload(app_factory):
    client = app_factory().test_client()
    token = extract_csrf_token(client.get("/"))

    response = client.post(
        "/api/images/import-upload",
        data={"image": (BytesIO(b""), "empty.png", "image/png")},
        headers={"X-CSRF-Token": token},
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert response.json == {"error": "Image upload is empty."}


def test_api_import_uploaded_image_rejects_multiple_files(app_factory):
    client = app_factory().test_client()
    token = extract_csrf_token(client.get("/"))

    response = client.post(
        "/api/images/import-upload",
        data={
            "first": (BytesIO(route_image_bytes("PNG")), "one.png", "image/png"),
            "second": (BytesIO(route_image_bytes("PNG")), "two.png", "image/png"),
        },
        headers={"X-CSRF-Token": token},
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert response.json == {"error": "Only one image file can be uploaded at a time."}


def test_api_import_uploaded_image_rejects_invalid_image_data(app_factory):
    client = app_factory().test_client()
    token = extract_csrf_token(client.get("/"))

    response = client.post(
        "/api/images/import-upload",
        data={"image": (BytesIO(b"not an image"), "sample.png", "image/png")},
        headers={"X-CSRF-Token": token},
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert response.json == {"error": "Uploaded file is not a valid image."}


def test_api_import_uploaded_image_rejects_unsupported_image_format(app_factory):
    client = app_factory().test_client()
    token = extract_csrf_token(client.get("/"))

    response = client.post(
        "/api/images/import-upload",
        data={"image": (BytesIO(route_image_bytes("GIF")), "sample.gif", "image/gif")},
        headers={"X-CSRF-Token": token},
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert response.json == {"error": "Unsupported image format: GIF."}


def test_api_import_uploaded_image_ignores_misleading_mime_type(
    app_config, app_factory
):
    client = app_factory().test_client()
    token = extract_csrf_token(client.get("/"))

    response = client.post(
        "/api/images/import-upload",
        data={"image": (BytesIO(route_image_bytes("PNG")), "sample.txt", "text/plain")},
        headers={"X-CSRF-Token": token},
        content_type="multipart/form-data",
    )

    assert response.status_code == 201
    filename = response.json["image"]["filename"]
    assert filename.endswith(".png")
    with Image.open(app_config.output_dir / filename) as stored:
        assert stored.format == "PNG"


def test_api_import_uploaded_image_does_not_overwrite_collision(
    app_config,
    app_factory,
    monkeypatch,
):
    class Token:
        def __init__(self, value):
            self.hex = value

    tokens = iter([Token("collision"), Token("unique")])
    monkeypatch.setattr("imagegen.image_imports.uuid4", lambda: next(tokens))
    existing = app_config.output_dir / "import-collision.png"
    existing.parent.mkdir(parents=True, exist_ok=True)
    existing.write_bytes(b"existing")
    client = app_factory().test_client()
    token = extract_csrf_token(client.get("/"))

    response = client.post(
        "/api/images/import-upload",
        data={"image": (BytesIO(route_image_bytes("PNG")), "sample.png", "image/png")},
        headers={"X-CSRF-Token": token},
        content_type="multipart/form-data",
    )

    assert response.status_code == 201
    assert response.json["image"]["filename"] == "import-unique.png"
    assert existing.read_bytes() == b"existing"


def test_api_import_uploaded_image_requires_csrf(app_factory):
    client = app_factory().test_client()
    client.get("/")

    response = client.post(
        "/api/images/import-upload",
        data={"image": (BytesIO(route_image_bytes("PNG")), "sample.png", "image/png")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 403
    assert response.json == {"error": "Invalid CSRF token."}


def test_trash_route_serves_trashed_file(app_config, app_factory):
    app_config.trash_dir.mkdir(parents=True)
    (app_config.trash_dir / "sample.png").write_bytes(b"trash-image")
    client = app_factory().test_client()

    response = client.get("/trash/sample.png")

    assert response.status_code == 200
    assert response.data == b"trash-image"


def test_trash_route_blocks_unsafe_paths(app_factory):
    client = app_factory().test_client()

    response = client.get("/trash/../sample.png")

    assert response.status_code == 404


def test_api_trash_lists_eligible_images_newest_first(app_config, app_factory):
    app_config.trash_dir.mkdir(parents=True)
    older = app_config.trash_dir / "older.png"
    newer = app_config.trash_dir / "newer.webp"
    ignored = app_config.trash_dir / "ignored.txt"
    older.write_bytes(b"older")
    newer.write_bytes(b"newer")
    ignored.write_text("ignored", encoding="utf-8")
    os.utime(older, (2_000_000_000, 2_000_000_000))
    os.utime(newer, (2_000_000_100, 2_000_000_100))
    client = app_factory().test_client()

    response = client.get("/api/trash")

    assert response.status_code == 200
    assert response.json == {
        "images": [
            {
                "filename": "newer.webp",
                "restore_url": "/api/trash/newer.webp/restore",
                "url": "/trash/newer.webp",
            },
            {
                "filename": "older.png",
                "restore_url": "/api/trash/older.png/restore",
                "url": "/trash/older.png",
            },
        ],
        "trash_count": 2,
    }


def test_api_restore_trash_image_moves_file_back_to_gallery(
    app_config,
    app_factory,
):
    app_config.trash_dir.mkdir(parents=True)
    trash_path = app_config.trash_dir / "sample.png"
    trash_path.write_bytes(b"image")
    client = app_factory().test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    response = client.post(
        "/api/trash/sample.png/restore",
        json={},
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 200
    assert response.json == {
        "filename": "sample.png",
        "image_count": 1,
        "trash_count": 0,
    }
    assert not trash_path.exists()
    assert (app_config.output_dir / "sample.png").read_bytes() == b"image"


def test_api_restore_trash_image_uses_collision_safe_gallery_name(
    app_config,
    app_factory,
):
    app_config.output_dir.mkdir(parents=True)
    app_config.trash_dir.mkdir(parents=True)
    (app_config.output_dir / "sample.png").write_bytes(b"active")
    (app_config.trash_dir / "sample.png").write_bytes(b"trashed")
    client = app_factory().test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    response = client.post(
        "/api/trash/sample.png/restore",
        json={},
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 200
    restored_name = response.json["filename"]
    assert restored_name.startswith("sample-")
    assert restored_name.endswith(".png")
    assert response.json["image_count"] == 2
    assert response.json["trash_count"] == 0
    assert (app_config.output_dir / "sample.png").read_bytes() == b"active"
    assert (app_config.output_dir / restored_name).read_bytes() == b"trashed"


def test_api_restore_trash_image_rejects_unsafe_or_missing_name(
    app_config,
    app_factory,
):
    app_config.trash_dir.mkdir(parents=True)
    (app_config.trash_dir / "sample.png").write_bytes(b"image")
    client = app_factory().test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    unsafe_response = client.post(
        "/api/trash/../sample.png/restore",
        json={},
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )
    missing_response = client.post(
        "/api/trash/missing.png/restore",
        json={},
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert unsafe_response.status_code == 404
    assert unsafe_response.json == {"error": "Trash image not found."}
    assert missing_response.status_code == 404
    assert missing_response.json == {"error": "Trash image not found."}
    assert (app_config.trash_dir / "sample.png").is_file()


def test_api_restore_trash_image_requires_csrf(app_config, app_factory):
    app_config.trash_dir.mkdir(parents=True)
    (app_config.trash_dir / "sample.png").write_bytes(b"image")
    client = app_factory().test_client()

    response = client.post("/api/trash/sample.png/restore", json={})

    assert response.status_code == 403
    assert response.json == {"error": "Invalid CSRF token."}
    assert (app_config.trash_dir / "sample.png").is_file()


def test_api_empty_trash_deletes_only_eligible_trash_images(
    app_config,
    app_factory,
):
    app_config.output_dir.mkdir(parents=True)
    app_config.trash_dir.mkdir(parents=True)
    (app_config.output_dir / "active.png").write_bytes(b"active")
    (app_config.trash_dir / "one.png").write_bytes(b"one")
    (app_config.trash_dir / "two.jpg").write_bytes(b"two")
    ignored = app_config.trash_dir / "ignored.txt"
    ignored.write_text("ignored", encoding="utf-8")
    client = app_factory().test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    response = client.post(
        "/api/trash/empty",
        json={},
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 200
    assert sorted(response.json["deleted"]) == ["one.png", "two.jpg"]
    assert response.json["image_count"] == 1
    assert response.json["trash_count"] == 0
    assert (app_config.output_dir / "active.png").is_file()
    assert ignored.is_file()


def test_api_empty_trash_requires_csrf(app_config, app_factory):
    app_config.trash_dir.mkdir(parents=True)
    (app_config.trash_dir / "sample.png").write_bytes(b"image")
    client = app_factory().test_client()

    response = client.post("/api/trash/empty", json={})

    assert response.status_code == 403
    assert response.json == {"error": "Invalid CSRF token."}
    assert (app_config.trash_dir / "sample.png").is_file()


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


def png_payload(size=(8, 8), color=(255, 255, 255)):
    buffer = BytesIO()
    Image.new("RGB", size, color).save(buffer, "PNG")
    encoded = b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def grayscale_png_payload(pixels, size):
    buffer = BytesIO()
    image = Image.new("L", size)
    image.putdata(pixels)
    image.save(buffer, "PNG")
    encoded = b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def crop_image_via_api(client, token, filename="sample.png"):
    return client.post(
        f"/api/images/{filename}/crop",
        json={"rectangle": {"x": 0, "y": 0, "width": 10, "height": 10}},
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )


def blur_image_via_api(client, token, filename="sample.png"):
    return client.post(
        f"/api/images/{filename}/blur",
        json={
            "blur_radius": 2,
            "mask_png": grayscale_png_payload([255] + [0] * 63, (8, 8)),
        },
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )


def mask_limit_values(size):
    width, height = size
    decoded = (
        width * height * MASK_PNG_BYTES_PER_PIXEL_LIMIT + MASK_PNG_FIXED_OVERHEAD_BYTES
    )
    base64_chars = ((decoded + 2) // 3) * 4 + len(MASK_DATA_URL_PREFIX)
    return {
        "decoded": decoded,
        "base64": base64_chars,
        "request": base64_chars + MASK_JSON_FIXED_OVERHEAD_BYTES,
    }


def test_api_save_mask_writes_mask_png_next_to_source(app_config, app_factory):
    source_path = app_config.output_dir / "sample.jpg"
    write_sample_png(source_path)
    original_bytes = source_path.read_bytes()
    client = app_factory().test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    response = client.post(
        "/api/images/sample.jpg/mask",
        json={"mask_png": png_payload()},
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    mask_path = app_config.output_dir / "sample-mask.png"
    assert response.status_code == 201
    assert response.json == {
        "filename": "sample-mask.png",
        "url": "/images/sample-mask.png",
    }
    assert source_path.read_bytes() == original_bytes
    with Image.open(mask_path) as image:
        assert image.format == "PNG"
        assert image.size == (8, 8)
        assert image.mode == "L"


def test_api_crop_image_writes_new_gallery_image(app_config, app_factory):
    source_path = app_config.output_dir / "sample.png"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (20, 20), (255, 0, 0)).save(source_path, "PNG")
    original_bytes = source_path.read_bytes()
    client = app_factory().test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    response = client.post(
        "/api/images/sample.png/crop",
        json={"rectangle": {"x": 2, "y": 3, "width": 10, "height": 11}},
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 201
    image = response.json["image"]
    assert image == {
        "clean_download_url": f"/images/{image['filename']}/download-clean",
        "blur_save_url": f"/api/images/{image['filename']}/blur",
        "crop_save_url": f"/api/images/{image['filename']}/crop",
        "delete_url": f"/api/images/{image['filename']}/delete",
        "download_url": f"/images/{image['filename']}/download",
        "filename": image["filename"],
        "mask_save_url": f"/api/images/{image['filename']}/mask",
        "mask_url": f"/images/{image['filename'].removesuffix('.png')}-mask.png",
        "url": f"/images/{image['filename']}",
        "metadata_url": None,
        "content_type": None,
        "created_at": None,
    }
    assert image["filename"].startswith("sample-crop-")
    assert image["filename"].endswith(".png")
    assert source_path.read_bytes() == original_bytes
    with Image.open(app_config.output_dir / image["filename"]) as cropped:
        assert cropped.size == (10, 11)
        assert cropped.getpixel((0, 0)) == (255, 0, 0)


def test_api_crop_image_preserves_embedded_metadata(app_config, app_factory):
    source_path = app_config.output_dir / "sample.png"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (20, 20), (255, 0, 0)).save(source_path, "PNG")
    metadata = {
        "content_type": "image/png",
        "created_at": "2026-06-22T12:00:00+00:00",
        "provider": "manual",
        "prompt": "existing metadata",
    }
    write_embedded_metadata(source_path, metadata)
    client = app_factory().test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    response = client.post(
        "/api/images/sample.png/crop",
        json={"rectangle": {"x": 0, "y": 0, "width": 10, "height": 10}},
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 201
    cropped_path = app_config.output_dir / response.json["image"]["filename"]
    assert read_embedded_metadata(cropped_path) == metadata
    assert read_embedded_metadata(source_path) == metadata


def test_api_crop_image_does_not_add_metadata_when_source_has_none(
    app_config,
    app_factory,
):
    source_path = app_config.output_dir / "sample.png"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (20, 20), (255, 0, 0)).save(source_path, "PNG")
    client = app_factory().test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    response = client.post(
        "/api/images/sample.png/crop",
        json={"rectangle": {"x": 0, "y": 0, "width": 10, "height": 10}},
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 201
    cropped_path = app_config.output_dir / response.json["image"]["filename"]
    assert read_embedded_metadata(cropped_path) is None


def test_api_crop_image_does_not_overwrite_collision(
    app_config,
    app_factory,
    monkeypatch,
):
    class Token:
        def __init__(self, value):
            self.hex = value

    source_path = app_config.output_dir / "sample.png"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (20, 20), (255, 0, 0)).save(source_path, "PNG")
    existing = app_config.output_dir / "sample-crop-collision.png"
    existing.write_bytes(b"existing")
    tokens = iter([Token("collision"), Token("unique")])
    monkeypatch.setattr("imagegen.image_edits.uuid4", lambda: next(tokens))
    client = app_factory().test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    response = client.post(
        "/api/images/sample.png/crop",
        json={"rectangle": {"x": 0, "y": 0, "width": 10, "height": 10}},
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 201
    assert response.json["image"]["filename"] == "sample-crop-unique.png"
    assert existing.read_bytes() == b"existing"


def test_api_crop_image_rejects_unsafe_source_filename(app_config, app_factory):
    source_path = app_config.output_dir / "sample.png"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (20, 20), (255, 0, 0)).save(source_path, "PNG")
    client = app_factory().test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    response = client.post(
        "/api/images/../sample.png/crop",
        json={"rectangle": {"x": 0, "y": 0, "width": 10, "height": 10}},
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 404
    assert response.json == {"error": "Image not found."}
    assert len(list(app_config.output_dir.glob("sample-crop-*.png"))) == 0


def test_api_crop_image_rejects_missing_source_image(app_factory):
    client = app_factory().test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    response = client.post(
        "/api/images/missing.png/crop",
        json={"rectangle": {"x": 0, "y": 0, "width": 10, "height": 10}},
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 404
    assert response.json == {"error": "Image not found."}


@pytest.mark.parametrize(
    ("payload", "error"),
    [
        ({}, "Crop rectangle is required."),
        (
            {"rectangle": {"x": "0", "y": 0, "width": 10, "height": 10}},
            "Crop rectangle x must be an integer.",
        ),
        (
            {"rectangle": {"x": -1, "y": 0, "width": 10, "height": 10}},
            "Crop rectangle must be inside the source image.",
        ),
        (
            {"rectangle": {"x": 0, "y": 0, "width": 9, "height": 10}},
            "Crop rectangle must be at least 10 by 10 pixels.",
        ),
        (
            {"rectangle": {"x": 15, "y": 0, "width": 10, "height": 10}},
            "Crop rectangle must be inside the source image.",
        ),
    ],
)
def test_api_crop_image_rejects_invalid_rectangle(
    app_config,
    app_factory,
    payload,
    error,
):
    source_path = app_config.output_dir / "sample.png"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (20, 20), (255, 0, 0)).save(source_path, "PNG")
    client = app_factory().test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    response = client.post(
        "/api/images/sample.png/crop",
        json=payload,
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 400
    assert response.json == {"error": error}
    assert len(list(app_config.output_dir.glob("sample-crop-*.png"))) == 0


def test_api_crop_image_requires_csrf(app_config, app_factory):
    source_path = app_config.output_dir / "sample.png"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (20, 20), (255, 0, 0)).save(source_path, "PNG")
    client = app_factory().test_client()
    client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})

    response = client.post(
        "/api/images/sample.png/crop",
        json={"rectangle": {"x": 0, "y": 0, "width": 10, "height": 10}},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 403
    assert response.json == {"error": "Invalid CSRF token."}
    assert len(list(app_config.output_dir.glob("sample-crop-*.png"))) == 0


def test_api_blur_image_writes_new_gallery_image(app_config, app_factory):
    source_path = app_config.output_dir / "sample.png"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source = Image.new("RGB", (8, 8), (255, 0, 0))
    for x in range(4, 8):
        for y in range(8):
            source.putpixel((x, y), (0, 0, 255))
    source.save(source_path, "PNG")
    original_bytes = source_path.read_bytes()
    client = app_factory().test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    response = client.post(
        "/api/images/sample.png/blur",
        json={
            "blur_radius": 4.5,
            "mask_png": grayscale_png_payload(
                [255 if x >= 4 else 0 for _y in range(8) for x in range(8)],
                (8, 8),
            ),
        },
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 201
    image = response.json["image"]
    assert image == {
        "clean_download_url": f"/images/{image['filename']}/download-clean",
        "blur_save_url": f"/api/images/{image['filename']}/blur",
        "crop_save_url": f"/api/images/{image['filename']}/crop",
        "delete_url": f"/api/images/{image['filename']}/delete",
        "download_url": f"/images/{image['filename']}/download",
        "filename": image["filename"],
        "mask_save_url": f"/api/images/{image['filename']}/mask",
        "mask_url": f"/images/{image['filename'].removesuffix('.png')}-mask.png",
        "url": f"/images/{image['filename']}",
        "metadata_url": None,
        "content_type": None,
        "created_at": None,
    }
    assert image["filename"].startswith("sample-blur-")
    assert image["filename"].endswith(".png")
    assert source_path.read_bytes() == original_bytes
    with Image.open(app_config.output_dir / image["filename"]) as blurred:
        assert blurred.getpixel((0, 0)) == (255, 0, 0)
        assert blurred.getpixel((7, 0)) != (0, 0, 255)


def test_api_blur_image_preserves_embedded_metadata(app_config, app_factory):
    source_path = app_config.output_dir / "sample.png"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (8, 8), (255, 0, 0)).save(source_path, "PNG")
    metadata = {
        "content_type": "image/png",
        "created_at": "2026-06-22T12:00:00+00:00",
        "provider": "manual",
        "prompt": "existing metadata",
    }
    write_embedded_metadata(source_path, metadata)
    client = app_factory().test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    response = client.post(
        "/api/images/sample.png/blur",
        json={
            "blur_radius": 2,
            "mask_png": grayscale_png_payload([255] + [0] * 63, (8, 8)),
        },
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 201
    blurred_path = app_config.output_dir / response.json["image"]["filename"]
    assert read_embedded_metadata(blurred_path) == metadata
    assert read_embedded_metadata(source_path) == metadata


def test_api_blur_image_does_not_add_metadata_when_source_has_none(
    app_config,
    app_factory,
):
    source_path = app_config.output_dir / "sample.png"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (8, 8), (255, 0, 0)).save(source_path, "PNG")
    client = app_factory().test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    response = client.post(
        "/api/images/sample.png/blur",
        json={
            "blur_radius": 2,
            "mask_png": grayscale_png_payload([255] + [0] * 63, (8, 8)),
        },
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 201
    blurred_path = app_config.output_dir / response.json["image"]["filename"]
    assert read_embedded_metadata(blurred_path) is None


def test_cropped_image_uses_normal_gallery_metadata_download_and_trash_workflows(
    app_config,
    app_factory,
):
    source_path = app_config.output_dir / "sample.png"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (20, 20), (255, 0, 0)).save(source_path, "PNG")
    metadata = {
        "content_type": "image/png",
        "created_at": "2026-06-22T12:00:00+00:00",
        "model_alias": "seedream45",
        "model": "bytedance/seedream-4.5",
        "prompt": "existing metadata",
        "parameters": {"size": "2K"},
    }
    write_embedded_metadata(source_path, metadata)
    client = app_factory().test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    crop_response = crop_image_via_api(client, token)

    assert crop_response.status_code == 201
    filename = crop_response.json["image"]["filename"]
    image_path = app_config.output_dir / filename
    assert image_path.is_file()
    gallery_response = client.get("/api/images")
    gallery_image = next(
        image
        for image in gallery_response.json["images"]
        if image["filename"] == filename
    )
    assert gallery_image["metadata_url"] == f"/images/{filename}/metadata"
    assert gallery_image["clean_download_url"] == f"/images/{filename}/download-clean"
    assert gallery_image["delete_url"] == f"/api/images/{filename}/delete"
    assert gallery_image["content_type"] == "image/png"
    assert gallery_image["created_at"] == "2026-06-22T12:00:00+00:00"

    metadata_response = client.get(f"/images/{filename}/metadata")
    clean_response = client.get(f"/images/{filename}/download-clean")
    clean_path = app_config.tmp_dir / "cropped-clean.png"
    clean_path.write_bytes(clean_response.data)

    assert metadata_response.status_code == 200
    assert metadata_response.json == {
        **metadata,
        "provider": "replicate",
        "edit_mode": False,
    }
    assert clean_response.status_code == 200
    assert read_embedded_metadata(clean_path) is None
    assert read_embedded_metadata(image_path) == metadata

    delete_response = client.post(
        f"/api/images/{filename}/delete",
        json={},
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )
    restore_response = client.post(
        f"/api/trash/{filename}/restore",
        json={},
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert delete_response.status_code == 200
    assert delete_response.json == {"deleted": filename}
    assert restore_response.status_code == 200
    assert restore_response.json["filename"] == filename
    assert (app_config.output_dir / filename).is_file()
    assert not (app_config.trash_dir / filename).exists()


def test_blurred_image_appears_in_gallery_and_can_be_reused_as_source_image(
    app_config,
    app_factory,
):
    source_path = app_config.output_dir / "sample.png"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (8, 8), (255, 0, 0)).save(source_path, "PNG")
    client = app_factory().test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    blur_response = blur_image_via_api(client, token)

    assert blur_response.status_code == 201
    filename = blur_response.json["image"]["filename"]
    gallery_response = client.get("/api/images")
    assert any(
        image["filename"] == filename for image in gallery_response.json["images"]
    )

    generate_response = client.post(
        "/api/generate",
        json={
            "prompt": "edit this",
            "edit_mode": True,
            "source_images": [filename],
        },
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert generate_response.status_code == 202
    assert generate_response.json["source_images"] == [filename]
    request_log = client.application.config[
        "IMAGEGEN_GENERATION_LOG"
    ].get_logged_request(generate_response.json["request_id"])
    assert request_log is not None
    assert request_log.source_images == [filename]
    assert request_log.request_sent["image_input"] == [filename]


@pytest.mark.parametrize(
    ("endpoint", "payload", "prefix"),
    [
        (
            "crop",
            {
                "filename": "client-chosen.png",
                "rectangle": {"x": 0, "y": 0, "width": 10, "height": 10},
            },
            "sample-crop-",
        ),
        (
            "blur",
            {
                "filename": "client-chosen.png",
                "blur_radius": 2,
                "mask_png": grayscale_png_payload([255] + [0] * 63, (8, 8)),
            },
            "sample-blur-",
        ),
    ],
)
def test_edited_image_outputs_ignore_browser_submitted_filenames(
    app_config,
    app_factory,
    endpoint,
    payload,
    prefix,
):
    source_path = app_config.output_dir / "sample.png"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    if endpoint == "crop":
        Image.new("RGB", (20, 20), (255, 0, 0)).save(source_path, "PNG")
    else:
        Image.new("RGB", (8, 8), (255, 0, 0)).save(source_path, "PNG")
    client = app_factory().test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    response = client.post(
        f"/api/images/sample.png/{endpoint}",
        json=payload,
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 201
    filename = response.json["image"]["filename"]
    assert filename.startswith(prefix)
    assert filename.endswith(".png")
    assert filename != "client-chosen.png"
    assert not (app_config.output_dir / "client-chosen.png").exists()
    assert (app_config.output_dir / filename).is_file()


def test_api_blur_image_rejects_unsafe_source_filename(app_config, app_factory):
    source_path = app_config.output_dir / "sample.png"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (8, 8), (255, 0, 0)).save(source_path, "PNG")
    client = app_factory().test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    response = client.post(
        "/api/images/../sample.png/blur",
        json={
            "blur_radius": 2,
            "mask_png": grayscale_png_payload([255] + [0] * 63, (8, 8)),
        },
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 404
    assert response.json == {"error": "Image not found."}
    assert len(list(app_config.output_dir.glob("sample-blur-*.png"))) == 0


def test_api_blur_image_rejects_missing_source_image(app_factory):
    client = app_factory().test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    response = client.post(
        "/api/images/missing.png/blur",
        json={
            "blur_radius": 2,
            "mask_png": grayscale_png_payload([255] + [0] * 63, (8, 8)),
        },
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 404
    assert response.json == {"error": "Image not found."}


@pytest.mark.parametrize(
    ("payload", "error"),
    [
        (
            {"mask_png": grayscale_png_payload([255] + [0] * 63, (8, 8))},
            "Blur radius is required.",
        ),
        (
            {
                "blur_radius": "2",
                "mask_png": grayscale_png_payload([255] + [0] * 63, (8, 8)),
            },
            "Blur radius must be a number.",
        ),
        (
            {
                "blur_radius": 20.1,
                "mask_png": grayscale_png_payload([255] + [0] * 63, (8, 8)),
            },
            "Blur radius must be between 0 and 20 pixels.",
        ),
        ({"blur_radius": 2}, "Mask PNG is required."),
        (
            {"blur_radius": 2, "mask_png": grayscale_png_payload([0] * 64, (8, 8))},
            "Mask must mark at least one pixel.",
        ),
        (
            {"blur_radius": 2, "mask_png": grayscale_png_payload([255], (1, 1))},
            "Mask dimensions must match the source image.",
        ),
        (
            {
                "blur_radius": 2,
                "brush_size": 48,
                "mask_png": grayscale_png_payload([255] + [0] * 63, (8, 8)),
            },
            "brush_size is not accepted for blur operations.",
        ),
    ],
)
def test_api_blur_image_rejects_invalid_payload(
    app_config,
    app_factory,
    payload,
    error,
):
    source_path = app_config.output_dir / "sample.png"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (8, 8), (255, 0, 0)).save(source_path, "PNG")
    client = app_factory().test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    response = client.post(
        "/api/images/sample.png/blur",
        json=payload,
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 400
    assert response.json == {"error": error}
    assert len(list(app_config.output_dir.glob("sample-blur-*.png"))) == 0


def test_api_blur_image_requires_csrf(app_config, app_factory):
    source_path = app_config.output_dir / "sample.png"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (8, 8), (255, 0, 0)).save(source_path, "PNG")
    client = app_factory().test_client()
    client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})

    response = client.post(
        "/api/images/sample.png/blur",
        json={
            "blur_radius": 2,
            "mask_png": grayscale_png_payload([255] + [0] * 63, (8, 8)),
        },
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 403
    assert response.json == {"error": "Invalid CSRF token."}
    assert len(list(app_config.output_dir.glob("sample-blur-*.png"))) == 0


def test_api_save_mask_preserves_black_white_and_gray_pixels(
    app_config,
    app_factory,
):
    source_path = app_config.output_dir / "sample.png"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (3, 1), (255, 0, 0)).save(source_path, "PNG")
    client = app_factory().test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    response = client.post(
        "/api/images/sample.png/mask",
        json={"mask_png": grayscale_png_payload([0, 128, 255], (3, 1))},
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 201
    with Image.open(app_config.output_dir / "sample-mask.png") as image:
        assert image.mode == "L"
        assert image.size == (3, 1)
        assert image.tobytes() == bytes([0, 128, 255])


def test_api_save_mask_rejects_unsafe_source_filename(app_config, app_factory):
    source_path = app_config.output_dir / "sample.png"
    write_sample_png(source_path)
    client = app_factory().test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    response = client.post(
        "/api/images/../sample.png/mask",
        json={"mask_png": png_payload()},
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 404
    assert response.json == {"error": "Image not found."}
    assert not (app_config.output_dir / "sample-mask.png").exists()


def test_api_save_mask_rejects_missing_source_image(app_factory):
    client = app_factory().test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    response = client.post(
        "/api/images/missing.png/mask",
        json={"mask_png": png_payload()},
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 404
    assert response.json == {"error": "Image not found."}


def test_api_save_mask_rejects_invalid_payload(app_config, app_factory):
    source_path = app_config.output_dir / "sample.png"
    write_sample_png(source_path)
    client = app_factory().test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    response = client.post(
        "/api/images/sample.png/mask",
        json={"mask_png": "not a png"},
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 400
    assert response.json == {"error": "Mask PNG is invalid."}
    assert not (app_config.output_dir / "sample-mask.png").exists()


def test_mask_payload_limit_scales_with_source_dimensions():
    limits = mask_payload_limits((8, 8))

    assert limits.max_decoded_bytes == mask_limit_values((8, 8))["decoded"]


def test_mask_payload_limit_is_capped_at_256_mib():
    limits = mask_payload_limits((100_000, 100_000))

    assert limits.max_decoded_bytes == MASK_PNG_ABSOLUTE_DECODED_LIMIT_BYTES


def test_api_save_mask_rejects_oversized_request_body(app_config, app_factory):
    source_path = app_config.output_dir / "sample.png"
    write_sample_png(source_path)
    limits = mask_limit_values((8, 8))
    client = app_factory().test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    response = client.post(
        "/api/images/sample.png/mask",
        data='{"mask_png":"' + ("A" * limits["request"]) + '"}',
        content_type="application/json",
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 400
    assert response.json == {"error": "Mask PNG is too large."}
    assert not (app_config.output_dir / "sample-mask.png").exists()


def test_api_save_mask_rejects_oversized_mask_string(app_config, app_factory):
    source_path = app_config.output_dir / "sample.png"
    write_sample_png(source_path)
    limits = mask_limit_values((8, 8))
    oversized_payload = "A" * (limits["base64"] + 1)
    client = app_factory().test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    response = client.post(
        "/api/images/sample.png/mask",
        json={"mask_png": oversized_payload},
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 400
    assert response.json == {"error": "Mask PNG is too large."}
    assert not (app_config.output_dir / "sample-mask.png").exists()


def test_api_save_mask_rejects_oversized_decoded_mask(app_config, app_factory):
    source_path = app_config.output_dir / "sample.png"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (1, 1), (255, 0, 0)).save(source_path, "PNG")
    limits = mask_limit_values((1, 1))
    oversized_decoded = b"\0" * (limits["decoded"] + 1)
    client = app_factory().test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    response = client.post(
        "/api/images/sample.png/mask",
        json={"mask_png": b64encode(oversized_decoded).decode("ascii")},
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 400
    assert response.json == {"error": "Mask PNG is too large."}
    assert not (app_config.output_dir / "sample-mask.png").exists()


def test_api_save_mask_rejects_mismatched_dimensions(app_config, app_factory):
    source_path = app_config.output_dir / "sample.png"
    write_sample_png(source_path)
    client = app_factory().test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    response = client.post(
        "/api/images/sample.png/mask",
        json={"mask_png": png_payload(size=(4, 4))},
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 400
    assert response.json == {"error": "Mask dimensions must match the source image."}
    assert not (app_config.output_dir / "sample-mask.png").exists()


def test_api_save_mask_requires_csrf(app_config, app_factory):
    source_path = app_config.output_dir / "sample.png"
    write_sample_png(source_path)
    client = app_factory().test_client()
    client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})

    response = client.post(
        "/api/images/sample.png/mask",
        json={"mask_png": png_payload()},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 403
    assert response.json == {"error": "Invalid CSRF token."}
    assert not (app_config.output_dir / "sample-mask.png").exists()
