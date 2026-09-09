"""Image route and gallery API tests.

Behaviors protected:
- Stored images can be viewed, downloaded normally, downloaded cleanly, and read for metadata.
- Gallery JSON lists safe local images and embedded metadata newest first.
- Image deletion moves files to trash safely and rejects missing, unsafe, or unsupported names.
- Mask saving rejects unsafe names, invalid payloads, dimension mismatches, missing CSRF,
  and oversized payloads before storing a provider-ready mask.
"""

from base64 import b64encode
from io import BytesIO

import pytest
from image_route_helpers import write_sample_png
from PIL import Image
from route_helpers import extract_csrf_token

from imagegen.mask_store import (
    MASK_DATA_URL_PREFIX,
    MASK_JSON_FIXED_OVERHEAD_BYTES,
    MASK_PNG_ABSOLUTE_DECODED_LIMIT_BYTES,
    MASK_PNG_BYTES_PER_PIXEL_LIMIT,
    MASK_PNG_FIXED_OVERHEAD_BYTES,
    mask_payload_limits,
)
from imagegen.metadata_embed import read_embedded_metadata, write_embedded_metadata


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
    assert image["filename"].startswith("crop-")
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
    existing = app_config.output_dir / "crop-collision.png"
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
    assert response.json["image"]["filename"] == "crop-unique.png"
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
    assert len(list(app_config.output_dir.glob("crop-*.png"))) == 0


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
    assert len(list(app_config.output_dir.glob("crop-*.png"))) == 0


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
    assert len(list(app_config.output_dir.glob("crop-*.png"))) == 0


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
    assert image["filename"].startswith("blur-")
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
            "crop-",
        ),
        (
            "blur",
            {
                "filename": "client-chosen.png",
                "blur_radius": 2,
                "mask_png": grayscale_png_payload([255] + [0] * 63, (8, 8)),
            },
            "blur-",
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
    assert len(list(app_config.output_dir.glob("blur-*.png"))) == 0


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
                "blur_radius": 50.1,
                "mask_png": grayscale_png_payload([255] + [0] * 63, (8, 8)),
            },
            "Blur radius must be between 0 and 50 pixels.",
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
    assert len(list(app_config.output_dir.glob("blur-*.png"))) == 0


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
    assert len(list(app_config.output_dir.glob("blur-*.png"))) == 0


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
