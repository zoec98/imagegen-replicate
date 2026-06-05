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
    send_file,
    send_from_directory,
    url_for,
)

from imagegen.app_version import app_checksum
from imagegen.filenames import safe_image_filename
from imagegen.gallery import list_gallery_images
from imagegen.image_export import ImageExportError, clean_image_export
from imagegen.model_registry import (
    CustomDimensionsControl,
    GenerationTarget,
    ModelPricing,
    ModelParameter,
    ProviderInfo,
    ProviderModel,
    RegistryLookupError,
    default_model_for_provider,
    list_models_for_provider,
    list_providers,
    resolve_model,
)
from imagegen.palettes import Palette, PaletteFragment, PaletteRepository
from imagegen.security import ensure_csrf_token
from imagegen.trash import count_trash_images


def register_routes(app: Flask) -> None:
    @app.get("/")
    def index():
        app_config = app.config["IMAGEGEN_APP_CONFIG"]
        selected_provider = app_config.selected_provider
        selected_provider_model = (
            _initial_provider_model(app_config)
            if selected_provider is not None
            else None
        )
        target = (
            selected_provider_model.text_target
            if selected_provider_model is not None
            else None
        )
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
            selected_provider=selected_provider,
            selected_provider_model=selected_provider_model,
            has_generation_provider=app_config.has_generation_provider,
            providers=[
                _provider_json(provider)
                for provider in list_providers()
                if provider.id in app_config.enabled_providers
            ],
            model_registry=[
                _provider_model_json(provider_model)
                for provider in app_config.enabled_providers
                for provider_model in list_models_for_provider(provider)
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
                for parameter in _target_parameters(selected_provider_model, target)
            ],
            prompt="",
            csrf_token=ensure_csrf_token(),
            app_checksum=app_checksum(),
            immich_enabled=app_config.immich_enabled,
            trash_count=count_trash_images(app_config.trash_dir),
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

    @app.get("/images/<path:filename>/download")
    def image_download(filename: str):
        safe_name = safe_image_filename(filename)
        if safe_name is None:
            abort(404)
        image_path = app.config["IMAGEGEN_APP_CONFIG"].output_dir / safe_name
        if not image_path.is_file():
            abort(404)
        return send_from_directory(
            app.config["IMAGEGEN_APP_CONFIG"].output_dir,
            safe_name,
            as_attachment=True,
            download_name=safe_name,
        )

    @app.get("/images/<path:filename>/download-clean")
    def image_download_clean(filename: str):
        safe_name = safe_image_filename(filename)
        if safe_name is None:
            abort(404)
        app_config = app.config["IMAGEGEN_APP_CONFIG"]
        image_path = app_config.output_dir / safe_name
        if not image_path.is_file():
            abort(404)
        try:
            export_path = clean_image_export(image_path, tmp_dir=app_config.tmp_dir)
        except ImageExportError:
            abort(400)
        return send_file(
            export_path,
            as_attachment=True,
            download_name=clean_download_name(safe_name),
        )

    @app.get("/images/<path:filename>/metadata")
    def image_metadata(filename: str):
        safe_name = safe_image_filename(filename)
        if safe_name is None:
            abort(404)
        image_path = app.config["IMAGEGEN_APP_CONFIG"].output_dir / safe_name
        metadata = app.config["IMAGEGEN_METADATA_PROVIDER"].get(image_path)
        if not metadata.exists:
            abort(404)
        return _metadata_json(metadata.to_json(), image_path.parent)

    @app.get("/trash/<path:filename>")
    def trash_file(filename: str):
        safe_name = safe_image_filename(filename)
        if safe_name is None:
            abort(404)
        return send_from_directory(
            app.config["IMAGEGEN_APP_CONFIG"].trash_dir,
            safe_name,
        )


def _initial_provider_model(app_config) -> ProviderModel | None:
    selected_provider = app_config.selected_provider
    if selected_provider is None:
        return None
    try:
        return resolve_model(selected_provider, app_config.model_alias)
    except RegistryLookupError:
        return default_model_for_provider(selected_provider)


def _metadata_json(
    payload: dict[str, object],
    image_dir: Path,
) -> dict[str, object]:
    source_images = payload.get("source_images")
    if not isinstance(source_images, list):
        return payload

    available: list[str] = []
    invalid_count = 0
    missing_count = 0
    for filename in source_images:
        if not isinstance(filename, str):
            invalid_count += 1
            continue
        safe_name = safe_image_filename(filename)
        if safe_name is None:
            invalid_count += 1
            continue
        if not (image_dir / safe_name).is_file():
            missing_count += 1
            continue
        available.append(safe_name)

    payload["source_images"] = available
    warnings: list[str] = []
    if invalid_count:
        warnings.append(
            "Some saved source image references were ignored because they are unsafe."
        )
    if missing_count:
        warnings.append("Some saved source images are no longer available.")
    if warnings:
        payload["warnings"] = warnings
    return payload


def clean_download_name(filename: str) -> str:
    path = Path(filename)
    return f"{path.stem}-clean{path.suffix}"


def _provider_json(provider: ProviderInfo) -> dict[str, object]:
    return {
        "id": provider.id,
        "display_name": provider.display_name,
    }


def _provider_model_json(model) -> dict[str, object]:
    target = model.text_target
    return {
        "provider": model.provider,
        "alias": model.alias,
        "display_name": model.display_name,
        "provider_model": target.provider_model,
        "replicate_model": (
            target.provider_model if model.provider == "replicate" else None
        ),
        "edit_capable": model.edit_capable,
        "source_image_parameter": (
            model.edit_target.source_images.provider_field
            if model.edit_target is not None
            and model.edit_target.source_images is not None
            else None
        ),
        "source_image_max": (
            model.edit_target.source_images.max_count
            if model.edit_target is not None
            and model.edit_target.source_images is not None
            else 0
        ),
        "custom_dimensions": _custom_dimensions_json(target.custom_dimensions),
        "pricing": [_pricing_json(pricing) for pricing in target.pricing],
        "parameters": _target_parameter_json(model, target),
    }


def _target_parameter_json(
    model: ProviderModel,
    target: GenerationTarget,
) -> list[dict[str, object]]:
    return [
        _parameter_json(parameter) for parameter in _target_parameters(model, target)
    ]


def _target_parameters(
    model: ProviderModel | None,
    target: GenerationTarget | None,
) -> list[ModelParameter]:
    if model is None or target is None:
        return []
    source_parameter = (
        target.source_images.provider_field
        if target.source_images is not None
        else _replicate_edit_source_parameter(model)
    )
    return [
        parameter
        for parameter in sorted(
            target.parameters,
            key=lambda item: item.order if item.order is not None else 999,
        )
        if parameter.name not in {"prompt", source_parameter}
        and parameter.name not in target.fixed_inputs
    ]


def _replicate_edit_source_parameter(model: ProviderModel) -> str | None:
    if model.provider != "replicate":
        return None
    if model.edit_target is None or model.edit_target.source_images is None:
        return None
    return model.edit_target.source_images.provider_field


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
