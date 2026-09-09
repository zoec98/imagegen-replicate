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
from io import BytesIO

from PIL import Image
from route_helpers import extract_csrf_token

from imagegen.mask_store import (
    MASK_DATA_URL_PREFIX,
    MASK_JSON_FIXED_OVERHEAD_BYTES,
    MASK_PNG_BYTES_PER_PIXEL_LIMIT,
    MASK_PNG_FIXED_OVERHEAD_BYTES,
)


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
