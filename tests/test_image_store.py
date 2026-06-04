"""Generated image storage tests.

Behaviors protected:
- Generated image downloads reject unsafe content types and oversized responses.
- Generated image downloads reject unsafe URLs, private hosts, and unsafe redirects.
- Accepted image outputs are stored locally with embedded generation metadata.
- Batch persistence creates the output directory and stores each output safely.
"""

from ipaddress import ip_address
from io import BytesIO

import httpx
import pytest
from PIL import Image

from imagegen.image_store import (
    ImageDownloadError,
    download_image,
    max_download_bytes,
    persist_generated_images,
)
from imagegen.metadata import EmbeddedImageMetadataProvider
from imagegen.metadata_embed import read_embedded_metadata
from imagegen.model_registry import MODEL_REGISTRY


def response_client(response):
    return httpx.Client(transport=httpx.MockTransport(lambda request: response))


def safe_resolver(hostname):
    return [ip_address("93.184.216.34")]


def image_bytes(image_format):
    buffer = BytesIO()
    Image.new("RGB", (8, 8), (255, 0, 0)).save(buffer, image_format)
    return buffer.getvalue()


def test_download_image_writes_file_and_embedded_metadata(tmp_path):
    model = MODEL_REGISTRY["seedream45"]
    response = httpx.Response(
        200,
        headers={"content-type": "image/jpeg"},
        content=image_bytes("JPEG"),
        request=httpx.Request("GET", "https://example.com/out.jpg"),
    )

    stored = download_image(
        "https://example.com/out.jpg",
        output_dir=tmp_path,
        model=model,
        prompt="a cookie",
        prediction_id="abc123",
        sequence=1,
        prediction_input={"prompt": "a cookie", "disable_safety_checker": True},
        author="Zoé Cordelier",
        client=response_client(response),
        resolver=safe_resolver,
    )

    assert stored.path == tmp_path / "seedream45-abc123-01.jpg"
    assert not (tmp_path / "seedream45-abc123-01.jpg.json").exists()
    metadata = EmbeddedImageMetadataProvider().get(stored.path)
    assert metadata.content_type == "image/jpeg"
    assert metadata.created_at == stored.created_at
    assert metadata.provider == "replicate"
    assert metadata.parameters is not None
    assert metadata.parameters["disable_safety_checker"] is True
    payload = read_embedded_metadata(stored.path)
    assert payload is not None
    assert payload["provider"] == "replicate"
    assert payload["author"] == "Zoé Cordelier"
    assert payload["copyright"].endswith("Zoé Cordelier")
    assert payload["software"] == "https://github.com/zoec98/imagegen-replicate"


def test_persist_generated_images_creates_output_directory(tmp_path):
    model = MODEL_REGISTRY["seedream45"]
    output_dir = tmp_path / "missing" / "images"
    response = httpx.Response(
        200,
        headers={"content-type": "image/png"},
        content=image_bytes("PNG"),
        request=httpx.Request("GET", "https://example.com/out.png"),
    )

    stored = persist_generated_images(
        ["https://example.com/out.png"],
        output_dir=output_dir,
        model=model,
        prompt="a cookie",
        prediction_id="abc123",
        prediction_input={"prompt": "a cookie"},
        author="Zoé Cordelier",
        client=response_client(response),
        resolver=safe_resolver,
    )

    assert output_dir.exists()
    assert stored[0].path == output_dir / "seedream45-abc123-01.png"


def test_download_image_rejects_non_image_response(tmp_path):
    response = httpx.Response(
        200,
        headers={"content-type": "text/plain"},
        content=b"not an image",
        request=httpx.Request("GET", "https://example.com/out.txt"),
    )

    with pytest.raises(ImageDownloadError, match="Expected image content"):
        download_image(
            "https://example.com/out.txt",
            output_dir=tmp_path,
            model=MODEL_REGISTRY["seedream45"],
            prompt="a cookie",
            prediction_id="abc123",
            sequence=1,
            prediction_input={},
            author="Zoé Cordelier",
            client=response_client(response),
            resolver=safe_resolver,
        )


def test_download_image_rejects_gif_response(tmp_path):
    response = httpx.Response(
        200,
        headers={"content-type": "image/gif"},
        content=b"gif-data",
        request=httpx.Request("GET", "https://example.com/out.gif"),
    )

    with pytest.raises(ImageDownloadError, match="GIF image outputs are not supported"):
        download_image(
            "https://example.com/out.gif",
            output_dir=tmp_path,
            model=MODEL_REGISTRY["seedream45"],
            prompt="a cookie",
            prediction_id="abc123",
            sequence=1,
            prediction_input={},
            author="Zoé Cordelier",
            client=response_client(response),
            resolver=safe_resolver,
        )


def test_download_image_rejects_oversized_response(tmp_path):
    model = MODEL_REGISTRY["seedream45"]
    response = httpx.Response(
        200,
        headers={"content-type": "image/png"},
        content=b"x" * (max_download_bytes(model) + 1),
        request=httpx.Request("GET", "https://example.com/out.png"),
    )

    with pytest.raises(ImageDownloadError, match="exceeding limit"):
        download_image(
            "https://example.com/out.png",
            output_dir=tmp_path,
            model=model,
            prompt="a cookie",
            prediction_id="abc123",
            sequence=1,
            prediction_input={},
            author="Zoé Cordelier",
            client=response_client(response),
            resolver=safe_resolver,
        )


def test_download_image_rejects_non_https_url_before_fetch(tmp_path):
    def handler(request):
        raise AssertionError("unsafe URL should not be fetched")

    with pytest.raises(ImageDownloadError, match="must use https"):
        download_image(
            "http://example.com/out.png",
            output_dir=tmp_path,
            model=MODEL_REGISTRY["seedream45"],
            prompt="a cookie",
            prediction_id="abc123",
            sequence=1,
            prediction_input={},
            author="Zoé Cordelier",
            client=httpx.Client(transport=httpx.MockTransport(handler)),
            resolver=safe_resolver,
        )


def test_download_image_rejects_unsupported_scheme_before_fetch(tmp_path):
    def handler(request):
        raise AssertionError("unsafe URL should not be fetched")

    with pytest.raises(ImageDownloadError, match="must use https"):
        download_image(
            "file:///tmp/out.png",
            output_dir=tmp_path,
            model=MODEL_REGISTRY["seedream45"],
            prompt="a cookie",
            prediction_id="abc123",
            sequence=1,
            prediction_input={},
            author="Zoé Cordelier",
            client=httpx.Client(transport=httpx.MockTransport(handler)),
            resolver=safe_resolver,
        )


def test_download_image_rejects_loopback_host_before_fetch(tmp_path):
    def handler(request):
        raise AssertionError("unsafe URL should not be fetched")

    with pytest.raises(ImageDownloadError, match="unsafe address"):
        download_image(
            "https://127.0.0.1/out.png",
            output_dir=tmp_path,
            model=MODEL_REGISTRY["seedream45"],
            prompt="a cookie",
            prediction_id="abc123",
            sequence=1,
            prediction_input={},
            author="Zoé Cordelier",
            client=httpx.Client(transport=httpx.MockTransport(handler)),
            resolver=lambda hostname: [ip_address(hostname)],
        )


def test_download_image_rejects_localhost_before_fetch(tmp_path):
    def handler(request):
        raise AssertionError("unsafe URL should not be fetched")

    with pytest.raises(ImageDownloadError, match="localhost"):
        download_image(
            "https://localhost/out.png",
            output_dir=tmp_path,
            model=MODEL_REGISTRY["seedream45"],
            prompt="a cookie",
            prediction_id="abc123",
            sequence=1,
            prediction_input={},
            author="Zoé Cordelier",
            client=httpx.Client(transport=httpx.MockTransport(handler)),
            resolver=safe_resolver,
        )


def test_download_image_rejects_private_resolved_host_before_fetch(tmp_path):
    def handler(request):
        raise AssertionError("unsafe URL should not be fetched")

    with pytest.raises(ImageDownloadError, match="unsafe address"):
        download_image(
            "https://images.example.test/out.png",
            output_dir=tmp_path,
            model=MODEL_REGISTRY["seedream45"],
            prompt="a cookie",
            prediction_id="abc123",
            sequence=1,
            prediction_input={},
            author="Zoé Cordelier",
            client=httpx.Client(transport=httpx.MockTransport(handler)),
            resolver=lambda hostname: [ip_address("192.168.1.10")],
        )


def test_download_image_rejects_redirect_to_unsafe_host_before_fetch(tmp_path):
    requested_urls = []

    def handler(request):
        requested_urls.append(str(request.url))
        if str(request.url) == "https://cdn.example.test/start":
            return httpx.Response(
                302,
                headers={"location": "https://127.0.0.1/out.png"},
            )
        raise AssertionError("unsafe redirect target should not be fetched")

    def resolver(hostname):
        if hostname == "cdn.example.test":
            return [ip_address("93.184.216.34")]
        if hostname == "127.0.0.1":
            return [ip_address("127.0.0.1")]
        raise AssertionError(f"unexpected hostname {hostname}")

    with pytest.raises(ImageDownloadError, match="unsafe address"):
        download_image(
            "https://cdn.example.test/start",
            output_dir=tmp_path,
            model=MODEL_REGISTRY["seedream45"],
            prompt="a cookie",
            prediction_id="abc123",
            sequence=1,
            prediction_input={},
            author="Zoé Cordelier",
            client=httpx.Client(transport=httpx.MockTransport(handler)),
            resolver=resolver,
        )

    assert requested_urls == ["https://cdn.example.test/start"]


def test_download_image_redacts_query_from_http_errors(tmp_path):
    response = httpx.Response(
        403,
        request=httpx.Request(
            "GET",
            "https://example.com/out.png?token=secret-token",
        ),
    )

    with pytest.raises(ImageDownloadError) as error:
        download_image(
            "https://example.com/out.png?token=secret-token",
            output_dir=tmp_path,
            model=MODEL_REGISTRY["seedream45"],
            prompt="a cookie",
            prediction_id="abc123",
            sequence=1,
            prediction_input={},
            author="Zoé Cordelier",
            client=response_client(response),
            resolver=safe_resolver,
        )

    assert "secret-token" not in str(error.value)
    assert "https://example.com/out.png" in str(error.value)


def test_max_download_bytes_uses_expected_bmp_size_plus_overhead():
    model = MODEL_REGISTRY["seedream45"]

    assert max_download_bytes(model) == 2048 * 2048 * 3 + 1024 * 1024
