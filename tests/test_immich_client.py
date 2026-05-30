import httpx
import pytest

from imagegen.immich_client import ImmichClient, ImmichUploadError


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

    with pytest.raises(ImmichUploadError, match="status 403"):
        client.upload_image(image_path, client=http_client)


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

    with pytest.raises(ImmichUploadError, match="album attach failed with status 403"):
        client.upload_image(image_path, client=http_client)
