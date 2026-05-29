"""HTTP route registration and request handlers.

This module owns Flask routes for the generation workspace, image generation
submission, and local image serving. App construction remains in app.py.
"""

from __future__ import annotations

from pathlib import Path

from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from werkzeug.utils import secure_filename

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
            ),
            model=app_config.model,
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
        )

    @app.post("/generate")
    def generate():
        prompt = request.form.get("prompt", "").strip()
        if not prompt:
            flash("Prompt is required.", "error")
            return redirect(url_for("index"))

        app_config = app.config["IMAGEGEN_APP_CONFIG"]
        generator = app.config["IMAGEGEN_GENERATE"]
        try:
            result = generator(prompt, app_config)
        except Exception as error:
            flash(str(error), "error")
            return redirect(url_for("index"))

        output_count = len(getattr(result, "stored_images", []))
        flash(
            f"Generation finished and saved {output_count} image(s).",
            "success",
        )
        return redirect(url_for("index"))

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


def safe_image_filename(filename: str) -> str | None:
    safe_name = secure_filename(filename)
    if safe_name != filename or Path(filename).suffix.lower() not in IMAGE_EXTENSIONS:
        return None
    return safe_name
