"""Flask application factory.

This module owns construction of the Flask app object and registration of
application routes. Route handlers, gallery helpers, configuration loading, and
external service wrappers live in their own modules.
"""

from __future__ import annotations

from typing import Any

from flask import Flask

from imagegen.api_routes import register_api_routes
from imagegen.config import AppConfig, load_config
from imagegen.generation_provider import default_generation_providers
from imagegen.generation_log import SQLiteGenerationLog
from imagegen.image_export import clean_tmp_exports
from imagegen.metadata import EmbeddedImageMetadataProvider
from imagegen.request_store import RequestStore
from imagegen.routes import register_routes
from imagegen.security import no_cors_response
from imagegen.worker import ThreadedGenerationWorker


def create_app(config: dict[str, Any] | None = None) -> Flask:
    app_config = _resolve_app_config(config)
    _ensure_data_directories(app_config)
    app = Flask(__name__)
    app.secret_key = app_config.flask_secret_key
    app.config.update(
        IMAGEGEN_APP_CONFIG=app_config,
        IMAGEGEN_METADATA_PROVIDER=EmbeddedImageMetadataProvider(),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=False,
    )
    if config:
        app.config.update(config)
    request_store = app.config.setdefault("IMAGEGEN_REQUEST_STORE", RequestStore())
    generation_log = app.config.setdefault(
        "IMAGEGEN_GENERATION_LOG",
        SQLiteGenerationLog(app_config.generation_log_path),
    )
    generation_log.initialize()
    app.config.setdefault(
        "IMAGEGEN_WORKER",
        ThreadedGenerationWorker(
            store=request_store,
            app_config=app_config,
            generation_log=generation_log,
            providers=default_generation_providers(),
        ),
    )
    app.after_request(no_cors_response)
    register_routes(app)
    register_api_routes(app)
    return app


def _ensure_data_directories(app_config: AppConfig) -> None:
    for directory in (
        app_config.data_dir,
        app_config.output_dir,
        app_config.fragment_root,
        app_config.trash_dir,
        app_config.tmp_dir,
    ):
        directory.mkdir(parents=True, exist_ok=True)
    clean_tmp_exports(app_config.tmp_dir)


def _resolve_app_config(config: dict[str, Any] | None) -> AppConfig:
    if config and "IMAGEGEN_APP_CONFIG" in config:
        value = config["IMAGEGEN_APP_CONFIG"]
        if not isinstance(value, AppConfig):
            msg = "IMAGEGEN_APP_CONFIG must be an AppConfig instance."
            raise TypeError(msg)
        return value
    env_path = config.get("IMAGEGEN_ENV_PATH", ".env") if config else ".env"
    return load_config(env_path)
