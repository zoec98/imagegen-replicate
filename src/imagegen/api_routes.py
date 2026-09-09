"""JSON API route registration and response shaping.

This module owns the `/api/*` route surface for the app-like UI. It keeps the
initial endpoints small and JSON-only so later tickets can replace the
placeholder request tracking with a real request state store and background
worker without changing browser-facing route names.
"""

from __future__ import annotations

import httpx
from flask import Flask, Response, jsonify, request, url_for

from imagegen.app_version import app_checksum
from imagegen.filenames import safe_image_filename
from imagegen.gallery import (
    GalleryImage,
    count_gallery_images,
    list_gallery_images,
)
from imagegen.generation_api_routes import register_generation_api_routes
from imagegen.image_edits import ImageEditError, blur_image, crop_image
from imagegen.image_imports import (
    MAX_UPLOAD_BYTES,
    ImageImportError,
    ImageImportFetchError,
    import_image_from_url,
    store_imported_image,
)
from imagegen.immich_client import (
    IMMICH_GALLERY_PAGE_SIZE,
    ImmichClient,
    ImmichGalleryAsset,
    ImmichGalleryError,
    ImmichGalleryPage,
    ImmichUploadError,
)
from imagegen.mask_store import MaskPayloadError, save_mask_payload
from imagegen.palette_api_routes import register_palette_api_routes
from imagegen.security import require_api_csrf, require_multipart_api_csrf
from imagegen.trash import (
    count_trash_images,
    empty_trash,
    list_trash_images,
    move_gallery_image_to_trash,
    refresh_trash_count,
    restore_trash_image,
)


def register_api_routes(app: Flask) -> None:
    register_generation_api_routes(app)
    register_palette_api_routes(app)

    @app.get("/api/app-version")
    def api_app_version():
        return jsonify({"app_checksum": app_checksum()})

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
                "images": [_gallery_image_json(app, image) for image in images],
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

        image = _gallery_image_by_filename(app, imported.path.name)
        return jsonify({"image": _gallery_image_json(app, image)}), 201

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

        image = _gallery_image_by_filename(app, imported.path.name)
        return jsonify({"image": _gallery_image_json(app, image)}), 201

    @app.get("/api/immich/assets")
    def api_immich_assets():
        if not _immich_import_enabled(app):
            return jsonify({"error": "Immich import is not configured."}), 404
        try:
            page_number = _positive_page_number(request.args.get("page"))
        except ValueError as error:
            return jsonify({"error": str(error)}), 400
        try:
            page = _immich_client(app).list_main_gallery_assets(
                page=page_number,
                page_size=IMMICH_GALLERY_PAGE_SIZE,
            )
        except ImmichGalleryError as error:
            return jsonify({"error": str(error)}), 502
        return jsonify(_immich_gallery_page_json(page))

    @app.get("/api/immich/assets/<path:asset_id>/thumbnail")
    def api_immich_asset_thumbnail(asset_id: str):
        if not _immich_import_enabled(app):
            return jsonify({"error": "Immich import is not configured."}), 404
        if not asset_id.strip():
            return jsonify({"error": "Immich asset id is required."}), 400
        try:
            thumbnail, content_type = _immich_client(app).download_thumbnail(
                asset_id.strip()
            )
        except ImmichGalleryError as error:
            return jsonify({"error": str(error)}), 502
        return Response(thumbnail, content_type=content_type)

    @app.post("/api/immich/assets/import")
    @require_api_csrf
    def api_import_immich_asset():
        if not _immich_import_enabled(app):
            return jsonify({"error": "Immich import is not configured."}), 404
        payload = request.get_json(silent=True) or {}
        asset_id = payload.get("asset_id") if isinstance(payload, dict) else None
        if not isinstance(asset_id, str) or not asset_id.strip():
            return jsonify({"error": "Immich asset id is required."}), 400
        app_config = app.config["IMAGEGEN_APP_CONFIG"]
        try:
            image_bytes = _immich_client(app).download_asset(asset_id.strip())
            imported = store_imported_image(
                image_bytes,
                output_dir=app_config.output_dir,
                max_bytes=app.config.get(
                    "IMAGEGEN_IMAGE_IMPORT_MAX_BYTES",
                    MAX_UPLOAD_BYTES,
                ),
            )
        except ImmichGalleryError as error:
            return jsonify({"error": str(error)}), 502
        except ImageImportError as error:
            return jsonify({"error": str(error)}), 400

        image = _gallery_image_by_filename(app, imported.path.name)
        return jsonify({"image": _gallery_image_json(app, image)}), 201

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

    @app.post("/api/images/<path:filename>/immich-upload")
    @require_api_csrf
    def api_immich_upload(filename: str):
        if not _immich_upload_enabled(app):
            return jsonify({"error": "Immich upload is not configured."}), 404
        safe_name = safe_image_filename(filename)
        if safe_name is None:
            return jsonify({"error": "Image not found."}), 404
        image_path = app.config["IMAGEGEN_APP_CONFIG"].output_dir / safe_name
        if not image_path.is_file():
            return jsonify({"error": "Image not found."}), 404
        try:
            result = _immich_client(app).upload_image(image_path)
        except ImmichUploadError as error:
            return jsonify({"error": str(error)}), 502
        return jsonify({"filename": safe_name, "status": result.status})

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

        image = _gallery_image_by_filename(app, edited.path.name)
        return jsonify({"image": _gallery_image_json(app, image)}), 201

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

        image = _gallery_image_by_filename(app, edited.path.name)
        return jsonify({"image": _gallery_image_json(app, image)}), 201

    if app.config.get("IMAGEGEN_ENABLE_TEST_API"):

        @app.post("/api/_test")
        @require_api_csrf
        def api_test():
            return jsonify({"ok": True})


def _immich_import_enabled(app: Flask) -> bool:
    return bool(app.config["IMAGEGEN_APP_CONFIG"].immich_import_enabled)


def _immich_upload_enabled(app: Flask) -> bool:
    return bool(app.config["IMAGEGEN_APP_CONFIG"].immich_upload_enabled)


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


def _immich_client(app: Flask) -> ImmichClient:
    configured = app.config.get("IMAGEGEN_IMMICH_CLIENT")
    if configured is not None:
        if not any(
            hasattr(configured, method)
            for method in (
                "upload_image",
                "list_main_gallery_assets",
                "download_asset",
                "download_thumbnail",
            )
        ):
            msg = (
                "IMAGEGEN_IMMICH_CLIENT must provide an Immich client method "
                "such as upload_image, list_main_gallery_assets, download_asset, "
                "or download_thumbnail."
            )
            raise TypeError(msg)
        return configured
    app_config = app.config["IMAGEGEN_APP_CONFIG"]
    return ImmichClient(
        base_url=app_config.immich_url,
        api_key=app_config.immich_api_key,
        album_id=app_config.immich_upload_album_id,
    )


def _gallery_image_json(app: Flask, image: GalleryImage) -> dict[str, str | None]:
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


def _gallery_image_by_filename(app: Flask, filename: str) -> GalleryImage:
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


def _positive_page_number(value: str | None) -> int:
    if value is None or not value.strip():
        return 1
    try:
        page = int(value)
    except ValueError as error:
        raise ValueError("Immich page must be a positive integer.") from error
    if page < 1:
        raise ValueError("Immich page must be a positive integer.")
    return page


def _immich_gallery_page_json(page: ImmichGalleryPage) -> dict[str, object]:
    return {
        "assets": [_immich_gallery_asset_json(asset) for asset in page.assets],
        "page": page.page,
        "page_size": page.page_size,
        "next_page": page.next_page,
        "previous_page": page.previous_page,
    }


def _immich_gallery_asset_json(asset: ImmichGalleryAsset) -> dict[str, object]:
    return {
        "asset_id": asset.asset_id,
        "thumbnail_url": url_for(
            "api_immich_asset_thumbnail",
            asset_id=asset.asset_id,
        ),
        "label": asset.label,
        "created_at": asset.created_at,
        "width": asset.width,
        "height": asset.height,
        "import_eligible": asset.import_eligible,
    }


def _trash_image_json(filename: str) -> dict[str, str]:
    return {
        "filename": filename,
        "url": url_for("trash_file", filename=filename),
        "restore_url": url_for("api_restore_trash_image", filename=filename),
    }
