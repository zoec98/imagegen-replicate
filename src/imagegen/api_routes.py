"""JSON API route registration and response shaping.

This module owns the `/api/*` route surface for the app-like UI. It keeps the
initial endpoints small and JSON-only so later tickets can replace the
placeholder request tracking with a real request state store and background
worker without changing browser-facing route names.
"""

from __future__ import annotations

from pathlib import Path

from flask import Flask, jsonify, request, url_for

from imagegen.app_version import app_checksum
from imagegen.gallery import GalleryImage, list_gallery_images
from imagegen.generation_log import GenerationLog
from imagegen.immich_client import ImmichClient, ImmichUploadError
from imagegen.model_registry import MODEL_REGISTRY, ReplicateModel
from imagegen.replicate_client import build_prediction_input
from imagegen.request_store import GenerationRequest, RequestStore
from imagegen.security import require_api_csrf
from imagegen.validation import ValidationError, validate_generation_payload
from imagegen.worker import GenerationWorker
from imagegen.routes import safe_image_filename


def register_api_routes(app: Flask) -> None:
    @app.get("/api/app-version")
    def api_app_version():
        return jsonify({"app_checksum": app_checksum()})

    @app.post("/api/generate")
    @require_api_csrf
    def api_generate():
        payload = request.get_json(silent=True) or {}
        app_config = app.config["IMAGEGEN_APP_CONFIG"]
        try:
            selected_model = _selected_model(
                payload, default_alias=app_config.model_alias
            )
        except ValidationError as error:
            return jsonify({"error": str(error)}), 400
        try:
            validated = validate_generation_payload(
                payload,
                model=selected_model,
                output_dir=Path(app.config["IMAGEGEN_OUTPUT_DIR"]),
            )
        except ValidationError as error:
            return jsonify({"error": str(error)}), 400

        record = _request_store(app).create(
            model_alias=selected_model.alias,
            prompt=validated.prompt,
            parameters=validated.parameters,
            source_images=validated.source_images,
        )
        _generation_log(app).create_request(
            record,
            model_alias=selected_model.alias,
            model=selected_model.replicate_model,
            replicate_input=build_prediction_input(
                validated.prompt,
                selected_model,
                parameters=validated.parameters,
                source_image_inputs=validated.source_images,
            ),
        )
        _generation_worker(app).start(record)
        return jsonify(_request_json(app, record)), 202

    @app.get("/api/generation/<request_id>")
    def api_generation_status(request_id: str):
        record = _request_store(app).get(request_id)
        if record is None:
            return jsonify({"error": "Generation request not found."}), 404
        return jsonify(_request_json(app, record))

    @app.get("/api/images")
    def api_images():
        images = list_gallery_images(
            Path(app.config["IMAGEGEN_OUTPUT_DIR"]),
            image_url=lambda filename: url_for("image_file", filename=filename),
            metadata_url=lambda filename: url_for(
                "image_metadata",
                filename=filename,
            ),
            metadata_provider=app.config["IMAGEGEN_METADATA_PROVIDER"],
        )
        return jsonify(
            {"images": [_gallery_image_json(app, image) for image in images]}
        )

    @app.post("/api/images/<path:filename>/immich-upload")
    @require_api_csrf
    def api_immich_upload(filename: str):
        if not _immich_enabled(app):
            return jsonify({"error": "Immich upload is not configured."}), 404
        safe_name = safe_image_filename(filename)
        if safe_name is None:
            return jsonify({"error": "Image not found."}), 404
        image_path = Path(app.config["IMAGEGEN_OUTPUT_DIR"]) / safe_name
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
        image_path = Path(app.config["IMAGEGEN_OUTPUT_DIR"]) / safe_name
        if not image_path.is_file():
            return jsonify({"error": "Image not found."}), 404
        image_path.unlink()
        return jsonify({"deleted": safe_name})

    if app.config.get("IMAGEGEN_ENABLE_TEST_API"):

        @app.post("/api/_test")
        @require_api_csrf
        def api_test():
            return jsonify({"ok": True})


def _request_store(app: Flask) -> RequestStore:
    store = app.config["IMAGEGEN_REQUEST_STORE"]
    if not isinstance(store, RequestStore):
        msg = "IMAGEGEN_REQUEST_STORE must be a RequestStore instance."
        raise TypeError(msg)
    return store


def _generation_worker(app: Flask) -> GenerationWorker:
    worker = app.config["IMAGEGEN_WORKER"]
    if not hasattr(worker, "start"):
        msg = "IMAGEGEN_WORKER must provide a start(request_record) method."
        raise TypeError(msg)
    return worker


def _generation_log(app: Flask) -> GenerationLog:
    generation_log = app.config["IMAGEGEN_GENERATION_LOG"]
    if not hasattr(generation_log, "create_request"):
        msg = "IMAGEGEN_GENERATION_LOG must provide generation log methods."
        raise TypeError(msg)
    return generation_log


def _immich_enabled(app: Flask) -> bool:
    return bool(app.config["IMAGEGEN_APP_CONFIG"].immich_enabled)


def _immich_client(app: Flask) -> ImmichClient:
    configured = app.config.get("IMAGEGEN_IMMICH_CLIENT")
    if configured is not None:
        if not hasattr(configured, "upload_image"):
            msg = "IMAGEGEN_IMMICH_CLIENT must provide upload_image(image_path)."
            raise TypeError(msg)
        return configured
    app_config = app.config["IMAGEGEN_APP_CONFIG"]
    return ImmichClient(
        base_url=app_config.immich_url,
        api_key=app_config.immich_api_key,
        album_id=app_config.immich_gallery_id,
    )


def _selected_model(
    payload: dict[str, object], *, default_alias: str
) -> ReplicateModel:
    alias = payload.get("model", default_alias)
    if not isinstance(alias, str) or not alias.strip():
        raise ValidationError("model must be a valid model id.")
    model = MODEL_REGISTRY.get(alias.strip())
    if model is None:
        choices = ", ".join(sorted(MODEL_REGISTRY))
        raise ValidationError(f"Unknown model: {alias}. Expected one of: {choices}.")
    return model


def _request_json(app: Flask, record: GenerationRequest) -> dict[str, object]:
    payload = record.to_json()
    payload["status_url"] = url_for(
        "api_generation_status",
        request_id=record.request_id,
    )
    payload["poll_seconds"] = app.config["IMAGEGEN_APP_CONFIG"].replicate_poll_seconds
    return payload


def _gallery_image_json(app: Flask, image: GalleryImage) -> dict[str, str | None]:
    payload = {
        "filename": image.filename,
        "url": image.url,
        "delete_url": url_for("api_delete_image", filename=image.filename),
        "metadata_url": image.metadata_url,
        "content_type": image.content_type,
        "created_at": image.created_at,
    }
    app_config = app.config["IMAGEGEN_APP_CONFIG"]
    if app_config.immich_enabled:
        payload["immich_upload_url"] = url_for(
            "api_immich_upload",
            filename=image.filename,
        )
    return payload
