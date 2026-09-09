"""Palette API route registration and response shaping."""

from __future__ import annotations

from flask import Flask, jsonify, request

from imagegen.palettes import (
    Palette,
    PaletteConflictError,
    PaletteError,
    PaletteFragment,
    PaletteNotFoundError,
    PaletteRepository,
)
from imagegen.security import require_api_csrf


def register_palette_api_routes(app: Flask) -> None:
    @app.get("/api/palettes")
    def api_palettes():
        try:
            palettes = _palette_repository(app).list_palettes()
        except PaletteError as error:
            return jsonify({"error": str(error)}), 400
        return jsonify({"palettes": [_palette_json(palette) for palette in palettes]})

    @app.get("/api/palettes/<palette_name>/fragments/<fragment_name>")
    def api_palette_fragment(palette_name: str, fragment_name: str):
        try:
            fragment = _palette_repository(app).read_fragment(
                palette_name,
                fragment_name,
            )
        except PaletteNotFoundError as error:
            return jsonify({"error": str(error)}), 404
        except PaletteError as error:
            return jsonify({"error": str(error)}), 400
        return jsonify({"fragment": _palette_fragment_json(fragment)})

    @app.post("/api/palettes/<palette_name>/fragments")
    @require_api_csrf
    def api_create_palette_fragment(palette_name: str):
        payload = request.get_json(silent=True) or {}
        try:
            name, content = _fragment_payload(payload, require_name=True)
            fragment = _palette_repository(app).create_fragment(
                palette_name,
                name,
                content,
            )
        except PaletteNotFoundError as error:
            return jsonify({"error": str(error)}), 404
        except PaletteConflictError as error:
            return jsonify({"error": str(error)}), 409
        except PaletteError as error:
            return jsonify({"error": str(error)}), 400
        return jsonify({"fragment": _palette_fragment_json(fragment)}), 201

    @app.put("/api/palettes/<palette_name>/fragments/<fragment_name>")
    @require_api_csrf
    def api_update_palette_fragment(palette_name: str, fragment_name: str):
        payload = request.get_json(silent=True) or {}
        try:
            _, content = _fragment_payload(payload, require_name=False)
            fragment = _palette_repository(app).update_fragment(
                palette_name,
                fragment_name,
                content,
            )
        except PaletteNotFoundError as error:
            return jsonify({"error": str(error)}), 404
        except PaletteError as error:
            return jsonify({"error": str(error)}), 400
        return jsonify({"fragment": _palette_fragment_json(fragment)})

    @app.delete("/api/palettes/<palette_name>/fragments/<fragment_name>")
    @require_api_csrf
    def api_delete_palette_fragment(palette_name: str, fragment_name: str):
        try:
            _palette_repository(app).delete_fragment(palette_name, fragment_name)
        except PaletteNotFoundError as error:
            return jsonify({"error": str(error)}), 404
        except PaletteError as error:
            return jsonify({"error": str(error)}), 400
        return jsonify({"deleted": fragment_name})


def _palette_repository(app: Flask) -> PaletteRepository:
    return PaletteRepository(app.config["IMAGEGEN_APP_CONFIG"].fragment_root)


def _fragment_payload(
    payload: object,
    *,
    require_name: bool,
) -> tuple[str, str]:
    if not isinstance(payload, dict):
        raise PaletteError("Palette fragment payload must be an object.")
    name = payload.get("name", "")
    content = payload.get("content", "")
    if require_name and not isinstance(name, str):
        raise PaletteError("Fragment name is required.")
    if not isinstance(content, str):
        raise PaletteError("Fragment content must be a string.")
    return str(name), content


def _palette_json(palette: Palette) -> dict[str, object]:
    return {
        "name": palette.name,
        "display_name": palette.display_name,
        "fragments": [
            _palette_fragment_json(fragment) for fragment in palette.fragments
        ],
    }


def _palette_fragment_json(fragment: PaletteFragment) -> dict[str, str]:
    return {
        "name": fragment.name,
        "display_name": fragment.display_name,
        "content": fragment.content,
    }
