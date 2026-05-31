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
from imagegen.model_registry import (
    MODEL_REGISTRY,
    CustomDimensionsControl,
    ModelPricing,
    ModelParameter,
    ReplicateModel,
)
from imagegen.palettes import Palette, PaletteFragment, PaletteRepository
from imagegen.security import ensure_csrf_token


def register_routes(app: Flask) -> None:
    @app.get("/")
    def index():
        app_config = app.config["IMAGEGEN_APP_CONFIG"]
        return render_template(
            "index.html",
            images=list_gallery_images(
                app_config.output_dir,
                image_url=lambda filename: url_for("image_file", filename=filename),
                metadata_url=lambda filename: url_for(
                    "image_metadata",
                    filename=filename,
                ),
                metadata_provider=app.config["IMAGEGEN_METADATA_PROVIDER"],
            ),
            model=app_config.model,
            model_registry=[
                _model_json(model)
                for model in sorted(
                    MODEL_REGISTRY.values(), key=lambda item: item.alias
                )
            ],
            palettes=[
                _palette_json(palette)
                for palette in PaletteRepository(
                    app_config.fragment_root
                ).list_palettes()
            ],
            app_config=app_config,
            parameters=[
                parameter
                for parameter in sorted(
                    app_config.model.parameters,
                    key=lambda item: item.order if item.order is not None else 999,
                )
                if parameter.name
                not in {"prompt", app_config.model.source_image_parameter}
            ],
            prompt="",
            csrf_token=ensure_csrf_token(),
            app_checksum=app_checksum(),
            immich_enabled=app_config.immich_enabled,
        )

    @app.get("/images/<path:filename>")
    def image_file(filename: str):
        safe_name = safe_image_filename(filename)
        if safe_name is None:
            abort(404)
        return send_from_directory(
            app.config["IMAGEGEN_APP_CONFIG"].output_dir,
            safe_name,
        )

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
        image_path = app.config["IMAGEGEN_APP_CONFIG"].output_dir / safe_name
        metadata = app.config["IMAGEGEN_METADATA_PROVIDER"].get(image_path)
        if not metadata.exists:
            abort(404)
        return metadata.to_json()


def safe_image_filename(filename: str) -> str | None:
    safe_name = secure_filename(filename)
    if safe_name != filename or Path(filename).suffix.lower() not in IMAGE_EXTENSIONS:
        return None
    return safe_name


def _model_json(model: ReplicateModel) -> dict[str, object]:
    return {
        "alias": model.alias,
        "display_name": model.display_name,
        "replicate_model": model.replicate_model,
        "edit_capable": model.edit_capable,
        "source_image_parameter": model.source_image_parameter,
        "source_image_max": model.source_image_max,
        "custom_dimensions": _custom_dimensions_json(model.custom_dimensions),
        "pricing": [_pricing_json(pricing) for pricing in model.pricing],
        "parameters": [
            _parameter_json(parameter)
            for parameter in sorted(
                model.parameters,
                key=lambda item: item.order if item.order is not None else 999,
            )
            if parameter.name not in {"prompt", model.source_image_parameter}
        ],
    }


def _pricing_json(pricing: ModelPricing) -> dict[str, object]:
    return {
        "price": pricing.price,
        "title": pricing.title,
        "description": pricing.description,
        "type": pricing.type,
        "metric": pricing.metric,
        "metric_count": pricing.metric_count,
    }


def _parameter_json(parameter: ModelParameter) -> dict[str, object]:
    return {
        "name": parameter.name,
        "description": parameter.description,
        "type": parameter.type,
        "default": parameter.default,
        "choices": list(parameter.choices),
        "minimum": parameter.minimum,
        "maximum": parameter.maximum,
        "order": parameter.order,
        "semantic_type": parameter.semantic_type,
    }


def _custom_dimensions_json(
    control: CustomDimensionsControl | None,
) -> dict[str, object] | None:
    if control is None:
        return None
    return {
        "activation_parameter": control.activation_parameter,
        "activation_value": control.activation_value,
        "scale_parameter": control.scale_parameter,
        "width_parameter": control.width_parameter,
        "height_parameter": control.height_parameter,
    }


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
