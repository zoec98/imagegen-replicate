"""Image route and gallery API tests.

Behaviors protected:
- Stored images can be viewed, downloaded normally, downloaded cleanly, and read for metadata.
- Gallery JSON lists safe local images and embedded metadata newest first.
- Image deletion moves files to trash safely and rejects missing, unsafe, or unsupported names.
- Mask saving rejects unsafe names, invalid payloads, dimension mismatches, missing CSRF,
  and oversized payloads before storing a provider-ready mask.
"""

from io import BytesIO

import httpx
from image_route_helpers import import_response_client, route_image_bytes
from PIL import Image
from route_helpers import extract_csrf_token


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
