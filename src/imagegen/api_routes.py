"""Coordinate focused JSON API route registration for the app-like UI."""

from __future__ import annotations

from flask import Flask, jsonify

from imagegen.app_version import app_checksum
from imagegen.generation_api_routes import register_generation_api_routes
from imagegen.immich_api_routes import register_immich_api_routes
from imagegen.local_image_api_routes import register_local_image_api_routes
from imagegen.palette_api_routes import register_palette_api_routes
from imagegen.security import require_api_csrf


def register_api_routes(app: Flask) -> None:
    register_generation_api_routes(app)
    register_immich_api_routes(app)
    register_palette_api_routes(app)
    register_local_image_api_routes(app)

    @app.get("/api/app-version")
    def api_app_version():
        return jsonify({"app_checksum": app_checksum()})

    if app.config.get("IMAGEGEN_ENABLE_TEST_API"):

        @app.post("/api/_test")
        @require_api_csrf
        def api_test():
            return jsonify({"ok": True})
