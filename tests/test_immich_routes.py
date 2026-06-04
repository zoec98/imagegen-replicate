"""Immich API route tests.

Behaviors protected:
- Gallery JSON exposes Immich upload actions only when configured.
- Immich upload routes require configuration, CSRF, and safe image filenames.
- Immich upload errors are returned as sanitized API responses.
"""

from dataclasses import replace

from imagegen.immich_client import ImmichUploadError, ImmichUploadResult
from route_helpers import extract_csrf_token


def test_api_images_exposes_immich_upload_url_only_when_configured(
    app_config,
    app_factory,
):
    app_config.output_dir.mkdir(parents=True)
    (app_config.output_dir / "sample.png").write_bytes(b"image")
    disabled = app_factory().test_client().get("/api/images")
    immich_config = replace(
        app_config,
        immich_url="https://immich.example.test",
        immich_gallery_id="album-123",
        immich_api_key="immich-key",
    )
    enabled = (
        app_factory(IMAGEGEN_APP_CONFIG=immich_config).test_client().get("/api/images")
    )

    assert disabled.status_code == 200
    assert "immich_upload_url" not in disabled.json["images"][0]
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


def test_api_immich_upload_requires_csrf(app_config, app_factory):
    app_config.output_dir.mkdir(parents=True)
    (app_config.output_dir / "sample.png").write_bytes(b"image")
    immich_config = replace(
        app_config,
        immich_url="https://immich.example.test",
        immich_gallery_id="album-123",
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
        immich_gallery_id="album-123",
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
        immich_gallery_id="album-123",
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
        immich_gallery_id="album-123",
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
        immich_gallery_id="album-123",
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
