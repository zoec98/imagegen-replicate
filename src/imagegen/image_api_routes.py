"""Local gallery, import, trash, and image-edit API route registration."""

from __future__ import annotations

import httpx
from flask import Flask, jsonify, request, url_for

from imagegen.filenames import safe_image_filename
from imagegen.gallery import count_gallery_images, list_gallery_images
from imagegen.image_api_helpers import gallery_image_by_filename, gallery_image_json
from imagegen.image_edits import ImageEditError, blur_image, crop_image
from imagegen.image_imports import (
    MAX_UPLOAD_BYTES,
    ImageImportError,
    ImageImportFetchError,
    import_image_from_url,
    store_imported_image,
)
from imagegen.mask_store import MaskPayloadError, save_mask_payload
from imagegen.security import require_api_csrf, require_multipart_api_csrf
from imagegen.trash import (
    count_trash_images,
    empty_trash,
    list_trash_images,
    move_gallery_image_to_trash,
    refresh_trash_count,
    restore_trash_image,
)


def register_image_api_routes(app: Flask) -> None:
    @app.get("/api/images")
    def api_images():
        app_config = app.config["IMAGEGEN_APP_CONFIG"]
        trash_count = _refresh_trash_count(app)
        images = list_gallery_images(
            app_config.output_dir,
            image_url=lambda filename: url_for("image_file", filename=filename),
            metadata_url=lambda filename: url_for(
                "image_metadata",
                filename=filename,
            ),
            metadata_provider=app.config["IMAGEGEN_METADATA_PROVIDER"],
        )
        return jsonify(
            {
                "images": [gallery_image_json(app, image) for image in images],
                "trash_count": trash_count,
            }
        )

    @app.post("/api/images/import-url")
    @require_api_csrf
    def api_import_image_url():
        payload = request.get_json(silent=True) or {}
        app_config = app.config["IMAGEGEN_APP_CONFIG"]
        close_client = False
        http_client = _image_import_http_client(app)
        if http_client is None:
            http_client = httpx.Client(timeout=30.0, follow_redirects=False)
            close_client = True
        try:
            imported = import_image_from_url(
                payload.get("url") if isinstance(payload, dict) else None,
                output_dir=app_config.output_dir,
                client=http_client,
                max_bytes=app.config.get(
                    "IMAGEGEN_IMAGE_IMPORT_MAX_BYTES",
                    MAX_UPLOAD_BYTES,
                ),
            )
        except (ImageImportError, ImageImportFetchError) as error:
            return jsonify({"error": str(error)}), 400
        finally:
            if close_client:
                http_client.close()

        image = gallery_image_by_filename(app, imported.path.name)
        return jsonify({"image": gallery_image_json(app, image)}), 201

    @app.post("/api/images/import-upload")
    @require_multipart_api_csrf
    def api_import_uploaded_image():
        app_config = app.config["IMAGEGEN_APP_CONFIG"]
        files = [
            uploaded_file
            for field_name in request.files
            for uploaded_file in request.files.getlist(field_name)
        ]
        if not files:
            return jsonify({"error": "Image file is required."}), 400
        if len(files) > 1:
            return jsonify(
                {"error": "Only one image file can be uploaded at a time."}
            ), 400

        try:
            imported = store_imported_image(
                files[0].read(),
                output_dir=app_config.output_dir,
                max_bytes=app.config.get(
                    "IMAGEGEN_IMAGE_IMPORT_MAX_BYTES",
                    MAX_UPLOAD_BYTES,
                ),
            )
        except ImageImportError as error:
            return jsonify({"error": str(error)}), 400

        image = gallery_image_by_filename(app, imported.path.name)
        return jsonify({"image": gallery_image_json(app, image)}), 201

    @app.get("/api/trash")
    def api_trash():
        app_config = app.config["IMAGEGEN_APP_CONFIG"]
        _refresh_trash_count(app)
        images = list_trash_images(app_config.trash_dir)
        return jsonify(
            {
                "images": [_trash_image_json(path.name) for path in images],
                "trash_count": len(images),
            }
        )

    @app.post("/api/trash/<path:filename>/restore")
    @require_api_csrf
    def api_restore_trash_image(filename: str):
        app_config = app.config["IMAGEGEN_APP_CONFIG"]
        try:
            restored_path = restore_trash_image(
                filename,
                trash_dir=app_config.trash_dir,
                output_dir=app_config.output_dir,
            )
        except FileNotFoundError:
            return jsonify({"error": "Trash image not found."}), 404
        return jsonify(
            {
                "filename": restored_path.name,
                "image_count": count_gallery_images(app_config.output_dir),
                "trash_count": count_trash_images(app_config.trash_dir),
            }
        )

    @app.post("/api/trash/empty")
    @require_api_csrf
    def api_empty_trash():
        app_config = app.config["IMAGEGEN_APP_CONFIG"]
        deleted = empty_trash(app_config.trash_dir)
        return jsonify(
            {
                "deleted": [path.name for path in deleted],
                "image_count": count_gallery_images(app_config.output_dir),
                "trash_count": count_trash_images(app_config.trash_dir),
            }
        )

    @app.post("/api/images/<path:filename>/delete")
    @require_api_csrf
    def api_delete_image(filename: str):
        safe_name = safe_image_filename(filename)
        if safe_name is None:
            return jsonify({"error": "Image not found."}), 404
        app_config = app.config["IMAGEGEN_APP_CONFIG"]
        try:
            move_gallery_image_to_trash(
                safe_name,
                output_dir=app_config.output_dir,
                trash_dir=app_config.trash_dir,
            )
        except FileNotFoundError:
            return jsonify({"error": "Image not found."}), 404
        return jsonify({"deleted": safe_name})

    @app.post("/api/images/<path:filename>/mask")
    @require_api_csrf
    def api_save_mask(filename: str):
        safe_name = safe_image_filename(filename)
        if safe_name is None:
            return jsonify({"error": "Image not found."}), 404
        app_config = app.config["IMAGEGEN_APP_CONFIG"]
        source_path = app_config.output_dir / safe_name
        if not source_path.is_file():
            return jsonify({"error": "Image not found."}), 404

        try:
            payload = request.get_json(silent=True) or {}
            saved_name = save_mask_payload(
                payload,
                source_filename=safe_name,
                source_path=source_path,
                output_dir=app_config.output_dir,
                content_length=request.content_length,
            )
        except MaskPayloadError as error:
            return jsonify({"error": str(error)}), 400
        return (
            jsonify(
                {
                    "filename": saved_name,
                    "url": url_for("image_file", filename=saved_name),
                }
            ),
            201,
        )

    @app.post("/api/images/<path:filename>/crop")
    @require_api_csrf
    def api_crop_image(filename: str):
        app_config = app.config["IMAGEGEN_APP_CONFIG"]
        try:
            edited = crop_image(
                request.get_json(silent=True) or {},
                source_filename=filename,
                output_dir=app_config.output_dir,
            )
        except ImageEditError as error:
            return jsonify({"error": str(error)}), 400
        except ValueError:
            return jsonify({"error": "Image not found."}), 404

        image = gallery_image_by_filename(app, edited.path.name)
        return jsonify({"image": gallery_image_json(app, image)}), 201

    @app.post("/api/images/<path:filename>/blur")
    @require_api_csrf
    def api_blur_image(filename: str):
        app_config = app.config["IMAGEGEN_APP_CONFIG"]
        try:
            edited = blur_image(
                request.get_json(silent=True) or {},
                source_filename=filename,
                output_dir=app_config.output_dir,
                content_length=request.content_length,
            )
        except ImageEditError as error:
            return jsonify({"error": str(error)}), 400
        except ValueError:
            return jsonify({"error": "Image not found."}), 404

        image = gallery_image_by_filename(app, edited.path.name)
        return jsonify({"image": gallery_image_json(app, image)}), 201


def _refresh_trash_count(app: Flask) -> int:
    app_config = app.config["IMAGEGEN_APP_CONFIG"]
    return refresh_trash_count(
        app_config.trash_dir,
        retention_days=app_config.trashcan_hold_limit_days,
    )


def _image_import_http_client(app: Flask) -> httpx.Client | None:
    configured = app.config.get("IMAGEGEN_IMAGE_IMPORT_HTTP_CLIENT")
    if configured is None:
        return None
    if not hasattr(configured, "stream"):
        msg = "IMAGEGEN_IMAGE_IMPORT_HTTP_CLIENT must provide stream(...)."
        raise TypeError(msg)
    return configured


def _trash_image_json(filename: str) -> dict[str, str]:
    return {
        "filename": filename,
        "url": url_for("trash_file", filename=filename),
        "restore_url": url_for("api_restore_trash_image", filename=filename),
    }
