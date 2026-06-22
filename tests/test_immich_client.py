"""Immich upload boundary tests.

Behaviors protected:
- Immich uploads send local image assets and attach them to the configured album.
- Duplicate Immich responses map to success where appropriate.
- Immich failures return sanitized application errors.
"""

import httpx
import pytest

from imagegen.immich_client import (
    IMMICH_GALLERY_PAGE_SIZE,
    ImmichClient,
    ImmichGalleryError,
    ImmichUploadError,
)


def test_immich_client_uploads_asset_and_adds_it_to_album(tmp_path):
    image_path = tmp_path / "sample.png"
    image_path.write_bytes(b"image")
    calls = []

    def handler(request):
        calls.append(request)
        if request.method == "POST":
            return httpx.Response(
                201,
                json={"id": "asset-123", "status": "created"},
                request=request,
            )
        return httpx.Response(
            200,
            json=[{"id": "asset-123", "success": True}],
            request=request,
        )

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = ImmichClient(
        base_url="https://immich.example.test",
        api_key="test-key",
        album_id="album-123",
    )

    result = client.upload_image(image_path, client=http_client)

    assert result.status == "uploaded"
    assert result.asset_id == "asset-123"
    assert [call.method for call in calls] == ["POST", "PUT"]
    assert str(calls[0].url) == "https://immich.example.test/api/assets"
    assert calls[0].headers["x-api-key"] == "test-key"
    assert str(calls[1].url) == (
        "https://immich.example.test/api/albums/album-123/assets"
    )


def test_immich_client_maps_duplicate_upload_to_already_present(tmp_path):
    image_path = tmp_path / "sample.png"
    image_path.write_bytes(b"image")

    def handler(request):
        if request.method == "POST":
            return httpx.Response(
                200,
                json={"id": "asset-123", "status": "duplicate"},
                request=request,
            )
        return httpx.Response(200, json=[], request=request)

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = ImmichClient(
        base_url="https://immich.example.test",
        api_key="test-key",
        album_id="album-123",
    )

    result = client.upload_image(image_path, client=http_client)

    assert result.status == "already_present"
    assert result.asset_id == "asset-123"


def test_immich_client_raises_sanitized_upload_error(tmp_path):
    image_path = tmp_path / "sample.png"
    image_path.write_bytes(b"image")

    def handler(request):
        return httpx.Response(
            403,
            json={"message": "key test-key cannot upload"},
            request=request,
        )

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = ImmichClient(
        base_url="https://immich.example.test",
        api_key="test-key",
        album_id="album-123",
    )

    with pytest.raises(
        ImmichUploadError, match=r"key \[redacted\] cannot upload"
    ) as error:
        client.upload_image(image_path, client=http_client)
    assert "test-key" not in str(error.value)


def test_immich_client_raises_when_album_attach_fails(tmp_path):
    image_path = tmp_path / "sample.png"
    image_path.write_bytes(b"image")

    def handler(request):
        if request.method == "POST":
            return httpx.Response(
                201,
                json={"id": "asset-123", "status": "created"},
                request=request,
            )
        return httpx.Response(403, json={"message": "forbidden"}, request=request)

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = ImmichClient(
        base_url="https://immich.example.test",
        api_key="test-key",
        album_id="album-123",
    )

    with pytest.raises(ImmichUploadError, match="forbidden"):
        client.upload_image(image_path, client=http_client)


def test_immich_client_lists_first_gallery_page():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(
            200,
            json={
                "assets": {
                    "items": [
                        {
                            "id": "asset-1",
                            "type": "IMAGE",
                            "originalFileName": "sample.jpg",
                            "fileCreatedAt": "2026-06-07T12:00:00Z",
                            "exifInfo": {
                                "exifImageWidth": 1200,
                                "exifImageHeight": 800,
                            },
                        }
                    ],
                    "total": 25,
                }
            },
            request=request,
        )

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = ImmichClient(
        base_url="https://immich.example.test/",
        api_key="test-key",
        album_id="album-123",
    )

    page = client.list_main_gallery_assets(client=http_client)

    assert page.page == 1
    assert page.page_size == IMMICH_GALLERY_PAGE_SIZE
    assert page.next_page == 2
    assert page.previous_page is None
    assert len(page.assets) == 1
    assert page.assets[0].asset_id == "asset-1"
    assert page.assets[0].thumbnail_url == (
        "https://immich.example.test/api/assets/asset-1/thumbnail?size=thumbnail"
    )
    assert page.assets[0].label == "sample.jpg"
    assert page.assets[0].created_at == "2026-06-07T12:00:00Z"
    assert page.assets[0].width == 1200
    assert page.assets[0].height == 800
    assert page.assets[0].import_eligible is True
    assert calls[0].method == "POST"
    assert str(calls[0].url) == "https://immich.example.test/api/search/metadata"
    assert calls[0].headers["x-api-key"] == "test-key"
    assert calls[0].read()
    assert calls[0].content == (b'{"page":1,"size":20,"type":"IMAGE","withExif":true}')


def test_immich_client_lists_subsequent_gallery_page():
    def handler(request):
        assert request.read()
        assert request.content == (
            b'{"page":2,"size":20,"type":"IMAGE","withExif":true}'
        )
        return httpx.Response(
            200,
            json={
                "assets": {
                    "items": [
                        {"id": f"asset-{index}", "type": "IMAGE"} for index in range(20)
                    ],
                    "total": 40,
                }
            },
            request=request,
        )

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = ImmichClient(
        base_url="https://immich.example.test",
        api_key="test-key",
        album_id="album-123",
    )

    page = client.list_main_gallery_assets(page=2, client=http_client)

    assert page.previous_page == 1
    assert page.next_page is None
    assert len(page.assets) == 20


def test_immich_client_lists_empty_gallery_page():
    def handler(request):
        return httpx.Response(
            200,
            json={"assets": {"items": [], "total": 0}},
            request=request,
        )

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = ImmichClient(
        base_url="https://immich.example.test",
        api_key="test-key",
        album_id="album-123",
    )

    page = client.list_main_gallery_assets(client=http_client)

    assert page.assets == []
    assert page.next_page is None
    assert page.previous_page is None


def test_immich_client_raises_sanitized_gallery_api_error():
    def handler(request):
        return httpx.Response(
            403,
            json={"message": "Missing required permission: asset.read"},
            request=request,
        )

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = ImmichClient(
        base_url="https://immich.example.test",
        api_key="test-key",
        album_id="album-123",
    )

    with pytest.raises(
        ImmichGalleryError, match="Missing required permission: asset.read"
    ):
        client.list_main_gallery_assets(client=http_client)


def test_immich_client_raises_for_malformed_gallery_response():
    def handler(request):
        return httpx.Response(
            200,
            json={"assets": {"items": "not a list"}},
            request=request,
        )

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = ImmichClient(
        base_url="https://immich.example.test",
        api_key="test-key",
        album_id="album-123",
    )

    with pytest.raises(ImmichGalleryError, match="response was malformed"):
        client.list_main_gallery_assets(client=http_client)


def test_immich_client_downloads_asset_original():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, content=b"image bytes", request=request)

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = ImmichClient(
        base_url="https://immich.example.test",
        api_key="test-key",
        album_id="album-123",
    )

    content = client.download_asset("asset 1", client=http_client)

    assert content == b"image bytes"
    assert calls[0].method == "GET"
    assert str(calls[0].url) == (
        "https://immich.example.test/api/assets/asset%201/original"
    )
    assert calls[0].headers["x-api-key"] == "test-key"


def test_immich_client_raises_sanitized_asset_download_error():
    def handler(request):
        return httpx.Response(
            404,
            json={"message": "asset missing for key test-key"},
            request=request,
        )

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = ImmichClient(
        base_url="https://immich.example.test",
        api_key="test-key",
        album_id="album-123",
    )

    with pytest.raises(
        ImmichGalleryError, match=r"asset missing for key \[redacted\]"
    ) as error:
        client.download_asset("missing-asset", client=http_client)
    assert "test-key" not in str(error.value)


def test_immich_client_downloads_asset_thumbnail():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(
            200,
            content=b"thumbnail bytes",
            headers={"Content-Type": "image/webp; charset=utf-8"},
            request=request,
        )

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = ImmichClient(
        base_url="https://immich.example.test",
        api_key="test-key",
        album_id="album-123",
    )

    content, content_type = client.download_thumbnail("asset 1", client=http_client)

    assert content == b"thumbnail bytes"
    assert content_type == "image/webp"
    assert calls[0].method == "GET"
    assert str(calls[0].url) == (
        "https://immich.example.test/api/assets/asset%201/thumbnail?size=thumbnail"
    )
    assert calls[0].headers["x-api-key"] == "test-key"


def test_immich_client_raises_sanitized_asset_thumbnail_error():
    def handler(request):
        return httpx.Response(
            403,
            json={"message": "Missing required permission: asset.view"},
            request=request,
        )

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = ImmichClient(
        base_url="https://immich.example.test",
        api_key="test-key",
        album_id="album-123",
    )

    with pytest.raises(
        ImmichGalleryError, match="Missing required permission: asset.view"
    ):
        client.download_thumbnail("asset-1", client=http_client)
