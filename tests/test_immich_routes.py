"""Immich API route tests.

Behaviors protected:
- Gallery JSON exposes Immich upload actions only when configured.
- Immich upload routes require configuration, CSRF, and safe image filenames.
- Immich upload errors are returned as sanitized API responses.
"""

from dataclasses import replace
from io import BytesIO

from PIL import Image

from imagegen.immich_client import (
    IMMICH_GALLERY_PAGE_SIZE,
    ImmichGalleryAsset,
    ImmichGalleryError,
    ImmichGalleryPage,
    ImmichUploadError,
    ImmichUploadResult,
)
from imagegen.metadata_embed import read_embedded_metadata, write_embedded_metadata
from route_helpers import extract_csrf_token


def test_api_images_exposes_immich_upload_url_only_when_configured(
    app_config,
    app_factory,
):
    app_config.output_dir.mkdir(parents=True)
    (app_config.output_dir / "sample.png").write_bytes(b"image")
    disabled = app_factory().test_client().get("/api/images")
    import_only_config = replace(
        app_config,
        immich_url="https://immich.example.test",
        immich_upload_album_id="",
        immich_api_key="immich-key",
    )
    import_only = (
        app_factory(IMAGEGEN_APP_CONFIG=import_only_config)
        .test_client()
        .get("/api/images")
    )
    immich_config = replace(
        app_config,
        immich_url="https://immich.example.test",
        immich_upload_album_id="album-123",
        immich_api_key="immich-key",
    )
    enabled = (
        app_factory(IMAGEGEN_APP_CONFIG=immich_config).test_client().get("/api/images")
    )

    assert disabled.status_code == 200
    assert "immich_upload_url" not in disabled.json["images"][0]
    assert import_only.status_code == 200
    assert "immich_upload_url" not in import_only.json["images"][0]
    assert enabled.status_code == 200
    assert enabled.json["images"][0]["immich_upload_url"] == (
        "/api/images/sample.png/immich-upload"
    )


def test_api_immich_upload_requires_configuration(app_config, app_factory):
    app_config.output_dir.mkdir(parents=True)
    (app_config.output_dir / "sample.png").write_bytes(b"image")
    client = app_factory().test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    response = client.post(
        "/api/images/sample.png/immich-upload",
        json={},
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 404
    assert response.json == {"error": "Immich upload is not configured."}


def test_api_immich_upload_requires_upload_album(app_config, app_factory):
    app_config.output_dir.mkdir(parents=True)
    (app_config.output_dir / "sample.png").write_bytes(b"image")
    immich_config = replace(
        app_config,
        immich_url="https://immich.example.test",
        immich_upload_album_id="",
        immich_api_key="immich-key",
    )
    client = app_factory(IMAGEGEN_APP_CONFIG=immich_config).test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    response = client.post(
        "/api/images/sample.png/immich-upload",
        json={},
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 404
    assert response.json == {"error": "Immich upload is not configured."}


def test_api_immich_upload_requires_csrf(app_config, app_factory):
    app_config.output_dir.mkdir(parents=True)
    (app_config.output_dir / "sample.png").write_bytes(b"image")
    immich_config = replace(
        app_config,
        immich_url="https://immich.example.test",
        immich_upload_album_id="album-123",
        immich_api_key="immich-key",
    )
    client = app_factory(IMAGEGEN_APP_CONFIG=immich_config).test_client()

    response = client.post("/api/images/sample.png/immich-upload", json={})

    assert response.status_code == 403


def test_api_immich_upload_rejects_missing_or_unsafe_filename(
    app_config,
    app_factory,
):
    immich_config = replace(
        app_config,
        immich_url="https://immich.example.test",
        immich_upload_album_id="album-123",
        immich_api_key="immich-key",
    )
    client = app_factory(IMAGEGEN_APP_CONFIG=immich_config).test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    missing = client.post(
        "/api/images/missing.png/immich-upload",
        json={},
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )
    unsafe = client.post(
        "/api/images/../pyproject.toml/immich-upload",
        json={},
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert missing.status_code == 404
    assert missing.json == {"error": "Image not found."}
    assert unsafe.status_code == 404
    assert unsafe.json == {"error": "Image not found."}


def test_api_immich_upload_calls_configured_backend_client(
    app_config,
    app_factory,
):
    class RecordingImmichClient:
        def __init__(self):
            self.paths = []

        def upload_image(self, image_path):
            self.paths.append(image_path)
            return ImmichUploadResult(status="uploaded", asset_id="asset-123")

    app_config.output_dir.mkdir(parents=True)
    (app_config.output_dir / "sample.png").write_bytes(b"image")
    immich_config = replace(
        app_config,
        immich_url="https://immich.example.test",
        immich_upload_album_id="album-123",
        immich_api_key="immich-key",
    )
    immich_client = RecordingImmichClient()
    client = app_factory(
        IMAGEGEN_APP_CONFIG=immich_config,
        IMAGEGEN_IMMICH_CLIENT=immich_client,
    ).test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    response = client.post(
        "/api/images/sample.png/immich-upload",
        json={},
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 200
    assert response.json == {"filename": "sample.png", "status": "uploaded"}
    assert immich_client.paths == [app_config.output_dir / "sample.png"]


def test_api_immich_upload_treats_already_present_as_success(
    app_config,
    app_factory,
):
    class AlreadyPresentImmichClient:
        def upload_image(self, image_path):
            return ImmichUploadResult(status="already_present", asset_id="asset-123")

    app_config.output_dir.mkdir(parents=True)
    (app_config.output_dir / "sample.png").write_bytes(b"image")
    immich_config = replace(
        app_config,
        immich_url="https://immich.example.test",
        immich_upload_album_id="album-123",
        immich_api_key="immich-key",
    )
    client = app_factory(
        IMAGEGEN_APP_CONFIG=immich_config,
        IMAGEGEN_IMMICH_CLIENT=AlreadyPresentImmichClient(),
    ).test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    response = client.post(
        "/api/images/sample.png/immich-upload",
        json={},
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 200
    assert response.json == {"filename": "sample.png", "status": "already_present"}


def test_api_immich_upload_returns_sanitized_error(
    app_config,
    app_factory,
):
    class FailingImmichClient:
        def upload_image(self, image_path):
            raise ImmichUploadError("Immich upload failed with status 403.")

    app_config.output_dir.mkdir(parents=True)
    (app_config.output_dir / "sample.png").write_bytes(b"image")
    immich_config = replace(
        app_config,
        immich_url="https://immich.example.test",
        immich_upload_album_id="album-123",
        immich_api_key="immich-secret-key",
    )
    client = app_factory(
        IMAGEGEN_APP_CONFIG=immich_config,
        IMAGEGEN_IMMICH_CLIENT=FailingImmichClient(),
    ).test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    response = client.post(
        "/api/images/sample.png/immich-upload",
        json={},
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 502
    assert response.json == {"error": "Immich upload failed with status 403."}
    assert "immich-secret-key" not in response.get_data(as_text=True)


def test_api_immich_assets_requires_configuration(app_factory):
    client = app_factory().test_client()

    response = client.get("/api/immich/assets")

    assert response.status_code == 404
    assert response.json == {"error": "Immich import is not configured."}


def test_api_immich_assets_returns_first_page(app_config, app_factory):
    class GalleryImmichClient:
        def __init__(self):
            self.calls = []

        def list_main_gallery_assets(self, *, page, page_size):
            self.calls.append((page, page_size))
            return ImmichGalleryPage(
                assets=[
                    ImmichGalleryAsset(
                        asset_id="asset-1",
                        thumbnail_url="https://immich.example.test/thumb",
                        label="sample.jpg",
                        created_at="2026-06-07T12:00:00Z",
                        width=1200,
                        height=800,
                        import_eligible=True,
                    )
                ],
                page=1,
                page_size=IMMICH_GALLERY_PAGE_SIZE,
                next_page=2,
                previous_page=None,
            )

    immich_client = GalleryImmichClient()
    client = app_factory(
        IMAGEGEN_APP_CONFIG=immich_enabled_config(app_config),
        IMAGEGEN_IMMICH_CLIENT=immich_client,
    ).test_client()

    response = client.get("/api/immich/assets")

    assert response.status_code == 200
    assert response.json == {
        "assets": [
            {
                "asset_id": "asset-1",
                "thumbnail_url": "/api/immich/assets/asset-1/thumbnail",
                "label": "sample.jpg",
                "created_at": "2026-06-07T12:00:00Z",
                "width": 1200,
                "height": 800,
                "import_eligible": True,
            }
        ],
        "page": 1,
        "page_size": 20,
        "next_page": 2,
        "previous_page": None,
    }
    assert immich_client.calls == [(1, 20)]


def test_api_immich_asset_thumbnail_proxies_authenticated_request(
    app_config,
    app_factory,
):
    class ThumbnailImmichClient:
        def __init__(self):
            self.asset_ids = []

        def download_thumbnail(self, asset_id):
            self.asset_ids.append(asset_id)
            return b"thumbnail", "image/webp"

    immich_client = ThumbnailImmichClient()
    client = app_factory(
        IMAGEGEN_APP_CONFIG=immich_enabled_config(app_config),
        IMAGEGEN_IMMICH_CLIENT=immich_client,
    ).test_client()

    response = client.get("/api/immich/assets/asset-1/thumbnail")

    assert response.status_code == 200
    assert response.data == b"thumbnail"
    assert response.content_type == "image/webp"
    assert immich_client.asset_ids == ["asset-1"]


def test_api_immich_asset_thumbnail_returns_api_errors(app_config, app_factory):
    class FailingThumbnailImmichClient:
        def download_thumbnail(self, asset_id):
            raise ImmichGalleryError("Missing required permission: asset.view")

    client = app_factory(
        IMAGEGEN_APP_CONFIG=immich_enabled_config(app_config, api_key="secret-key"),
        IMAGEGEN_IMMICH_CLIENT=FailingThumbnailImmichClient(),
    ).test_client()

    response = client.get("/api/immich/assets/asset-1/thumbnail")

    assert response.status_code == 502
    assert response.json == {"error": "Missing required permission: asset.view"}
    assert "secret-key" not in response.get_data(as_text=True)


def test_api_immich_assets_returns_next_page(app_config, app_factory):
    class GalleryImmichClient:
        def __init__(self):
            self.calls = []

        def list_main_gallery_assets(self, *, page, page_size):
            self.calls.append((page, page_size))
            return ImmichGalleryPage(
                assets=[],
                page=page,
                page_size=page_size,
                next_page=3,
                previous_page=1,
            )

    immich_client = GalleryImmichClient()
    client = app_factory(
        IMAGEGEN_APP_CONFIG=immich_enabled_config(app_config),
        IMAGEGEN_IMMICH_CLIENT=immich_client,
    ).test_client()

    response = client.get("/api/immich/assets?page=2")

    assert response.status_code == 200
    assert response.json["page"] == 2
    assert response.json["previous_page"] == 1
    assert response.json["next_page"] == 3
    assert immich_client.calls == [(2, 20)]


def test_api_immich_assets_rejects_invalid_page(app_config, app_factory):
    client = app_factory(
        IMAGEGEN_APP_CONFIG=immich_enabled_config(app_config),
        IMAGEGEN_IMMICH_CLIENT=object(),
    ).test_client()

    response = client.get("/api/immich/assets?page=0")

    assert response.status_code == 400
    assert response.json == {"error": "Immich page must be a positive integer."}


def test_api_immich_assets_returns_empty_result(app_config, app_factory):
    class EmptyImmichClient:
        def list_main_gallery_assets(self, *, page, page_size):
            return ImmichGalleryPage(
                assets=[],
                page=page,
                page_size=page_size,
                next_page=None,
                previous_page=None,
            )

    client = app_factory(
        IMAGEGEN_APP_CONFIG=immich_enabled_config(app_config),
        IMAGEGEN_IMMICH_CLIENT=EmptyImmichClient(),
    ).test_client()

    response = client.get("/api/immich/assets")

    assert response.status_code == 200
    assert response.json == {
        "assets": [],
        "page": 1,
        "page_size": 20,
        "next_page": None,
        "previous_page": None,
    }


def test_api_immich_assets_returns_sanitized_api_failure(app_config, app_factory):
    class FailingImmichClient:
        def list_main_gallery_assets(self, *, page, page_size):
            raise ImmichGalleryError("Missing required permission: asset.read")

    client = app_factory(
        IMAGEGEN_APP_CONFIG=immich_enabled_config(app_config, api_key="secret-key"),
        IMAGEGEN_IMMICH_CLIENT=FailingImmichClient(),
    ).test_client()

    response = client.get("/api/immich/assets")

    assert response.status_code == 502
    assert response.json == {"error": "Missing required permission: asset.read"}
    assert "secret-key" not in response.get_data(as_text=True)


def test_api_import_immich_asset_requires_configuration(app_factory):
    client = app_factory().test_client()
    token = extract_csrf_token(client.get("/"))

    response = client.post(
        "/api/immich/assets/import",
        json={"asset_id": "asset-1"},
        headers={"X-CSRF-Token": token},
    )

    assert response.status_code == 404
    assert response.json == {"error": "Immich import is not configured."}


def test_api_import_immich_asset_stores_downloaded_image_and_metadata(
    app_config,
    app_factory,
    tmp_path,
):
    source_path = tmp_path / "source.png"
    Image.new("RGB", (8, 8), (255, 0, 0)).save(source_path, "PNG")
    metadata = {
        "created_at": "2026-06-07T12:00:00+00:00",
        "provider": "immich",
        "prompt": "already there",
    }
    write_embedded_metadata(source_path, metadata)

    class DownloadImmichClient:
        def __init__(self):
            self.asset_ids = []

        def download_asset(self, asset_id):
            self.asset_ids.append(asset_id)
            return source_path.read_bytes()

    immich_client = DownloadImmichClient()
    client = app_factory(
        IMAGEGEN_APP_CONFIG=immich_enabled_config(app_config),
        IMAGEGEN_IMMICH_CLIENT=immich_client,
    ).test_client()
    token = extract_csrf_token(client.get("/"))

    response = client.post(
        "/api/immich/assets/import",
        json={"asset_id": "asset-1"},
        headers={"X-CSRF-Token": token},
    )

    assert response.status_code == 201
    image = response.json["image"]
    assert image["filename"].startswith("import-")
    assert image["filename"].endswith(".png")
    assert image["url"] == f"/images/{image['filename']}"
    assert immich_client.asset_ids == ["asset-1"]
    assert read_embedded_metadata(app_config.output_dir / image["filename"]) == metadata


def test_api_import_immich_asset_rejects_missing_asset_id(app_config, app_factory):
    client = app_factory(
        IMAGEGEN_APP_CONFIG=immich_enabled_config(app_config),
        IMAGEGEN_IMMICH_CLIENT=object(),
    ).test_client()
    token = extract_csrf_token(client.get("/"))

    response = client.post(
        "/api/immich/assets/import",
        json={},
        headers={"X-CSRF-Token": token},
    )

    assert response.status_code == 400
    assert response.json == {"error": "Immich asset id is required."}


def test_api_import_immich_asset_rejects_unsupported_downloaded_data(
    app_config,
    app_factory,
):
    class GifImmichClient:
        def download_asset(self, asset_id):
            return image_bytes("GIF")

    client = app_factory(
        IMAGEGEN_APP_CONFIG=immich_enabled_config(app_config),
        IMAGEGEN_IMMICH_CLIENT=GifImmichClient(),
    ).test_client()
    token = extract_csrf_token(client.get("/"))

    response = client.post(
        "/api/immich/assets/import",
        json={"asset_id": "asset-1"},
        headers={"X-CSRF-Token": token},
    )

    assert response.status_code == 400
    assert response.json == {"error": "Unsupported image format: GIF."}


def test_api_import_immich_asset_returns_sanitized_download_failure(
    app_config,
    app_factory,
):
    class FailingImmichClient:
        def download_asset(self, asset_id):
            raise ImmichGalleryError("Immich asset download failed with status 404.")

    client = app_factory(
        IMAGEGEN_APP_CONFIG=immich_enabled_config(app_config, api_key="secret-key"),
        IMAGEGEN_IMMICH_CLIENT=FailingImmichClient(),
    ).test_client()
    token = extract_csrf_token(client.get("/"))

    response = client.post(
        "/api/immich/assets/import",
        json={"asset_id": "missing"},
        headers={"X-CSRF-Token": token},
    )

    assert response.status_code == 502
    assert response.json == {"error": "Immich asset download failed with status 404."}
    assert "secret-key" not in response.get_data(as_text=True)


def test_api_import_immich_asset_requires_csrf(app_config, app_factory):
    class DownloadImmichClient:
        def download_asset(self, asset_id):
            return image_bytes("PNG")

    client = app_factory(
        IMAGEGEN_APP_CONFIG=immich_enabled_config(app_config),
        IMAGEGEN_IMMICH_CLIENT=DownloadImmichClient(),
    ).test_client()
    client.get("/")

    response = client.post(
        "/api/immich/assets/import",
        json={"asset_id": "asset-1"},
    )

    assert response.status_code == 403
    assert response.json == {"error": "Invalid CSRF token."}


def immich_enabled_config(app_config, *, api_key="immich-key"):
    return replace(
        app_config,
        immich_url="https://immich.example.test",
        immich_upload_album_id="album-123",
        immich_api_key=api_key,
    )


def image_bytes(image_format):
    buffer = BytesIO()
    Image.new("RGB", (8, 8), (255, 0, 0)).save(buffer, image_format)
    return buffer.getvalue()
