"""Flask application factory and routes."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from flask import (
    Flask,
    abort,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from werkzeug.utils import secure_filename

from imagegen.config import AppConfig, load_config


IMAGE_EXTENSIONS = {".gif", ".jpeg", ".jpg", ".png", ".webp"}
GenerateHandler = Callable[[str, AppConfig], Any]


@dataclass(frozen=True)
class GalleryImage:
    filename: str
    url: str
    view_url: str


def create_app(config: dict[str, Any] | None = None) -> Flask:
    app_config = _resolve_app_config(config)
    app = Flask(__name__)
    app.secret_key = app_config.flask_secret_key
    app.config.update(
        IMAGEGEN_APP_CONFIG=app_config,
        IMAGEGEN_GENERATE=_not_implemented_generate,
        IMAGEGEN_OUTPUT_DIR=app_config.output_dir,
    )
    if config:
        app.config.update(config)

    @app.get("/")
    def index():
        return render_template(
            "index.html",
            images=list_gallery_images(
                Path(app.config["IMAGEGEN_OUTPUT_DIR"]),
            ),
            model=app_config.model,
            prompt="",
            error=None,
        )

    @app.post("/generate")
    def generate():
        prompt = request.form.get("prompt", "").strip()
        if not prompt:
            return (
                render_template(
                    "index.html",
                    images=list_gallery_images(Path(app.config["IMAGEGEN_OUTPUT_DIR"])),
                    model=app_config.model,
                    prompt=request.form.get("prompt", ""),
                    error="Prompt is required.",
                ),
                400,
            )

        generator = app.config["IMAGEGEN_GENERATE"]
        try:
            generator(prompt, app_config)
        except NotImplementedError:
            return (
                render_template(
                    "index.html",
                    images=list_gallery_images(Path(app.config["IMAGEGEN_OUTPUT_DIR"])),
                    model=app_config.model,
                    prompt=prompt,
                    error="Generation service is not implemented yet.",
                ),
                501,
            )

        return redirect(url_for("index"))

    @app.get("/images/<path:filename>")
    def image_file(filename: str):
        safe_name = _safe_image_filename(filename)
        if safe_name is None:
            abort(404)
        return send_from_directory(app.config["IMAGEGEN_OUTPUT_DIR"], safe_name)

    @app.get("/images/<path:filename>/view")
    def image_view(filename: str):
        safe_name = _safe_image_filename(filename)
        if safe_name is None:
            abort(404)
        return render_template(
            "image_view.html",
            filename=safe_name,
            image_url=url_for("image_file", filename=safe_name),
        )

    return app


def list_gallery_images(output_dir: Path) -> list[GalleryImage]:
    if not output_dir.exists():
        return []

    files = [
        path
        for path in output_dir.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    ]
    files.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    return [
        GalleryImage(
            filename=path.name,
            url=url_for("image_file", filename=path.name),
            view_url=url_for("image_view", filename=path.name),
        )
        for path in files
    ]


def _resolve_app_config(config: dict[str, Any] | None) -> AppConfig:
    if config and "IMAGEGEN_APP_CONFIG" in config:
        value = config["IMAGEGEN_APP_CONFIG"]
        if not isinstance(value, AppConfig):
            msg = "IMAGEGEN_APP_CONFIG must be an AppConfig instance."
            raise TypeError(msg)
        return value
    env_path = config.get("IMAGEGEN_ENV_PATH", ".env") if config else ".env"
    return load_config(env_path)


def _not_implemented_generate(prompt: str, app_config: AppConfig) -> None:
    raise NotImplementedError


def _safe_image_filename(filename: str) -> str | None:
    safe_name = secure_filename(filename)
    if safe_name != filename or Path(filename).suffix.lower() not in IMAGE_EXTENSIONS:
        return None
    return safe_name
