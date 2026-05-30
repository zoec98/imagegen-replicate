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
from imagegen.model_registry import MODEL_REGISTRY


def response_client(response):
    return httpx.Client(transport=httpx.MockTransport(lambda request: response))


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
        client=response_client(response),
    )

    assert stored.path == tmp_path / "seedream45-abc123-01.jpg"
    assert not (tmp_path / "seedream45-abc123-01.jpg.json").exists()
    metadata = EmbeddedImageMetadataProvider().get(stored.path)
    assert metadata.content_type == "image/jpeg"
    assert metadata.created_at == stored.created_at
    assert metadata.parameters is not None
    assert metadata.parameters["disable_safety_checker"] is True


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
        client=response_client(response),
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
            client=response_client(response),
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
            client=response_client(response),
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
            client=response_client(response),
        )


def test_max_download_bytes_uses_expected_bmp_size_plus_overhead():
    model = MODEL_REGISTRY["seedream45"]

    assert max_download_bytes(model) == 2048 * 2048 * 3 + 1024 * 1024
