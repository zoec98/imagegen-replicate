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
from imagegen.replicate_client import generate_image_urls
from imagegen.request_store import RequestStore
from imagegen.routes import register_routes
from imagegen.security import no_cors_response
from imagegen.worker import ThreadedGenerationWorker


def create_app(config: dict[str, Any] | None = None) -> Flask:
    app_config = _resolve_app_config(config)
    request_store = RequestStore()
    app = Flask(__name__)
    app.secret_key = app_config.flask_secret_key
    app.config.update(
        IMAGEGEN_APP_CONFIG=app_config,
        IMAGEGEN_GENERATE=generate_image_urls,
        IMAGEGEN_OUTPUT_DIR=app_config.output_dir,
        IMAGEGEN_REQUEST_STORE=request_store,
        IMAGEGEN_WORKER=ThreadedGenerationWorker(
            store=request_store,
            app_config=app_config,
            generate=generate_image_urls,
        ),
    )
    if config:
        app.config.update(config)
    app.after_request(no_cors_response)
    register_routes(app)
    register_api_routes(app)
    return app


def _resolve_app_config(config: dict[str, Any] | None) -> AppConfig:
    if config and "IMAGEGEN_APP_CONFIG" in config:
        value = config["IMAGEGEN_APP_CONFIG"]
        if not isinstance(value, AppConfig):
            msg = "IMAGEGEN_APP_CONFIG must be an AppConfig instance."
            raise TypeError(msg)
        return value
    env_path = config.get("IMAGEGEN_ENV_PATH", ".env") if config else ".env"
    return load_config(env_path)
