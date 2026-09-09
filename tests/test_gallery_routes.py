"""Image route and gallery API tests.

Behaviors protected:
- Stored images can be viewed, downloaded normally, downloaded cleanly, and read for metadata.
- Gallery JSON lists safe local images and embedded metadata newest first.
- Image deletion moves files to trash safely and rejects missing, unsafe, or unsupported names.
- Mask saving rejects unsafe names, invalid payloads, dimension mismatches, missing CSRF,
  and oversized payloads before storing a provider-ready mask.
"""

import os
from dataclasses import replace

from image_route_helpers import write_sample_png

from imagegen.metadata_embed import write_embedded_metadata


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
