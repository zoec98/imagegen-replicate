"""JSON API route registration and response shaping.

This module owns the `/api/*` route surface for the app-like UI. It keeps the
initial endpoints small and JSON-only so later tickets can replace the
placeholder request tracking with a real request state store and background
worker without changing browser-facing route names.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, request, url_for

from imagegen.gallery import GalleryImage, list_gallery_images
from imagegen.security import require_api_csrf


def register_api_routes(app: Flask) -> None:
    @app.post("/api/generate")
    @require_api_csrf
    def api_generate():
        payload = request.get_json(silent=True) or {}
        prompt = str(payload.get("prompt", "")).strip()
        if not prompt:
            return jsonify({"error": "Prompt is required."}), 400

        parameters = payload.get("parameters", {})
        if not isinstance(parameters, dict):
            return jsonify({"error": "parameters must be an object."}), 400

        request_id = uuid.uuid4().hex
        record = {
            "request_id": request_id,
            "status": "queued",
            "prompt": prompt,
            "parameters": parameters,
            "images": [],
        }
        _request_records(app)[request_id] = record
        return jsonify(record), 202

    @app.get("/api/generation/<request_id>")
    def api_generation_status(request_id: str):
        record = _request_records(app).get(request_id)
        if record is None:
            return jsonify({"error": "Generation request not found."}), 404
        return jsonify(record)

    @app.get("/api/images")
    def api_images():
        images = list_gallery_images(
            Path(app.config["IMAGEGEN_OUTPUT_DIR"]),
            image_url=lambda filename: url_for("image_file", filename=filename),
        )
        return jsonify({"images": [_gallery_image_json(image) for image in images]})

    if app.config.get("IMAGEGEN_ENABLE_TEST_API"):

        @app.post("/api/_test")
        @require_api_csrf
        def api_test():
            return jsonify({"ok": True})


def _request_records(app: Flask) -> dict[str, dict[str, Any]]:
    return app.config.setdefault("IMAGEGEN_API_REQUESTS", {})


def _gallery_image_json(image: GalleryImage) -> dict[str, str | None]:
    return {
        "filename": image.filename,
        "url": image.url,
        "metadata_url": None,
        "content_type": None,
        "created_at": None,
    }
