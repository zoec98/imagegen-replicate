"""HTTP route registration and request handlers.

This module owns Flask routes for the generation workspace, image generation
submission, and local image serving. App construction remains in app.py.
"""

from __future__ import annotations

from pathlib import Path

from flask import (
    Flask,
    abort,
    redirect,
    render_template,
    send_from_directory,
    url_for,
)
from werkzeug.utils import secure_filename

from imagegen.app_version import app_checksum
from imagegen.gallery import IMAGE_EXTENSIONS, list_gallery_images
from imagegen.security import ensure_csrf_token


def register_routes(app: Flask) -> None:
    @app.get("/")
    def index():
        app_config = app.config["IMAGEGEN_APP_CONFIG"]
        return render_template(
            "index.html",
            images=list_gallery_images(
                Path(app.config["IMAGEGEN_OUTPUT_DIR"]),
                image_url=lambda filename: url_for("image_file", filename=filename),
                metadata_url=lambda filename: url_for(
                    "image_metadata",
                    filename=filename,
                ),
                metadata_provider=app.config["IMAGEGEN_METADATA_PROVIDER"],
            ),
            model=app_config.model,
            app_config=app_config,
            parameters=[
                parameter
                for parameter in sorted(
                    app_config.model.parameters,
                    key=lambda item: item.order if item.order is not None else 999,
                )
                if parameter.name not in {"prompt", "image_input"}
            ],
            prompt="",
            csrf_token=ensure_csrf_token(),
            app_checksum=app_checksum(),
        )

    @app.get("/images/<path:filename>")
    def image_file(filename: str):
        safe_name = safe_image_filename(filename)
        if safe_name is None:
            abort(404)
        return send_from_directory(app.config["IMAGEGEN_OUTPUT_DIR"], safe_name)

    @app.get("/images/<path:filename>/view")
    def image_view(filename: str):
        safe_name = safe_image_filename(filename)
        if safe_name is None:
            abort(404)
        return redirect(url_for("image_file", filename=safe_name))

    @app.get("/images/<path:filename>/metadata")
    def image_metadata(filename: str):
        safe_name = safe_image_filename(filename)
        if safe_name is None:
            abort(404)
        image_path = Path(app.config["IMAGEGEN_OUTPUT_DIR"]) / safe_name
        metadata = app.config["IMAGEGEN_METADATA_PROVIDER"].get(image_path)
        if not metadata.exists:
            abort(404)
        return metadata.to_json()


def safe_image_filename(filename: str) -> str | None:
    safe_name = secure_filename(filename)
    if safe_name != filename or Path(filename).suffix.lower() not in IMAGE_EXTENSIONS:
        return None
    return safe_name
