"""Shared browser-facing gallery image response helpers."""

from __future__ import annotations

from flask import Flask, url_for

from imagegen.gallery import GalleryImage, list_gallery_images


def gallery_image_json(app: Flask, image: GalleryImage) -> dict[str, str | None]:
    payload = {
        "filename": image.filename,
        "url": image.url,
        "mask_url": image.mask_url,
        "blur_save_url": url_for("api_blur_image", filename=image.filename),
        "crop_save_url": url_for("api_crop_image", filename=image.filename),
        "mask_save_url": url_for("api_save_mask", filename=image.filename),
        "download_url": url_for("image_download", filename=image.filename),
        "clean_download_url": url_for(
            "image_download_clean",
            filename=image.filename,
        ),
        "delete_url": url_for("api_delete_image", filename=image.filename),
        "metadata_url": image.metadata_url,
        "content_type": image.content_type,
        "created_at": image.created_at,
    }
    app_config = app.config["IMAGEGEN_APP_CONFIG"]
    if app_config.immich_upload_enabled:
        payload["immich_upload_url"] = url_for(
            "api_immich_upload",
            filename=image.filename,
        )
    return payload


def gallery_image_by_filename(app: Flask, filename: str) -> GalleryImage:
    app_config = app.config["IMAGEGEN_APP_CONFIG"]
    images = list_gallery_images(
        app_config.output_dir,
        image_url=lambda image_filename: url_for(
            "image_file",
            filename=image_filename,
        ),
        metadata_url=lambda image_filename: url_for(
            "image_metadata",
            filename=image_filename,
        ),
        metadata_provider=app.config["IMAGEGEN_METADATA_PROVIDER"],
    )
    for image in images:
        if image.filename == filename:
            return image
    raise FileNotFoundError(filename)
