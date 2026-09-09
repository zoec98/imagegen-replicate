"""Immich API route registration and response shaping."""

from __future__ import annotations

from flask import Flask, Response, jsonify, request, url_for

from imagegen.filenames import safe_image_filename
from imagegen.image_api_helpers import gallery_image_by_filename, gallery_image_json
from imagegen.image_imports import (
    MAX_UPLOAD_BYTES,
    ImageImportError,
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
from imagegen.security import require_api_csrf


def register_immich_api_routes(app: Flask) -> None:
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

        image = gallery_image_by_filename(app, imported.path.name)
        return jsonify({"image": gallery_image_json(app, image)}), 201

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


def _immich_import_enabled(app: Flask) -> bool:
    return bool(app.config["IMAGEGEN_APP_CONFIG"].immich_import_enabled)


def _immich_upload_enabled(app: Flask) -> bool:
    return bool(app.config["IMAGEGEN_APP_CONFIG"].immich_upload_enabled)


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
