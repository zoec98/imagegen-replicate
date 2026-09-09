"""Generation API route registration and request selection helpers."""

from __future__ import annotations

from dataclasses import dataclass

from flask import Flask, jsonify, request, url_for

from imagegen.generation_log import GenerationLog
from imagegen.model_registry import (
    PROVIDER_IDS,
    GenerationTarget,
    ProviderId,
    ProviderModel,
    RegistryLookupError,
    default_model_for_provider,
    list_models_for_provider,
    resolve_generation_target,
    resolve_model_ref,
)
from imagegen.prompt_annotations import strip_prompt_annotations
from imagegen.provider_requests import build_provider_request
from imagegen.request_store import GenerationRequest, RequestStore
from imagegen.security import require_api_csrf
from imagegen.validation import ValidationError, validate_generation_payload
from imagegen.worker import GenerationWorker


def register_generation_api_routes(app: Flask) -> None:
    @app.post("/api/generate")
    @require_api_csrf
    def api_generate():
        payload = request.get_json(silent=True) or {}
        app_config = app.config["IMAGEGEN_APP_CONFIG"]
        try:
            selection = _selected_generation_model(payload, app_config=app_config)
        except ValidationError as error:
            return jsonify({"error": str(error)}), 400
        try:
            validated = validate_generation_payload(
                payload,
                model=selection.model,
                target=selection.target,
                output_dir=app_config.output_dir,
            )
        except ValidationError as error:
            return jsonify({"error": str(error)}), 400

        record = _request_store(app).create(
            provider=selection.provider,
            model_alias=selection.model.alias,
            prompt=validated.prompt,
            parameters=validated.parameters,
            source_images=validated.source_images,
            edit_mode=validated.edit_mode,
        )
        _generation_log(app).create_request(
            record,
            model_alias=selection.model.alias,
            model=selection.target.provider_model,
            replicate_input=_build_provider_request(
                strip_prompt_annotations(validated.prompt),
                selection.model,
                selection.target,
                parameters=validated.parameters,
                source_image_inputs=validated.source_images,
            ),
        )
        _generation_worker(app).start(record)
        return jsonify(_request_json(app, record)), 202

    @app.get("/api/generation/<request_id>")
    def api_generation_status(request_id: str):
        record = _request_store(app).get(request_id)
        if record is None:
            return jsonify({"error": "Generation request not found."}), 404
        return jsonify(_request_json(app, record))


def _request_store(app: Flask) -> RequestStore:
    store = app.config["IMAGEGEN_REQUEST_STORE"]
    if not isinstance(store, RequestStore):
        msg = "IMAGEGEN_REQUEST_STORE must be a RequestStore instance."
        raise TypeError(msg)
    return store


def _generation_worker(app: Flask) -> GenerationWorker:
    worker = app.config["IMAGEGEN_WORKER"]
    if not hasattr(worker, "start"):
        msg = "IMAGEGEN_WORKER must provide a start(request_record) method."
        raise TypeError(msg)
    return worker


def _generation_log(app: Flask) -> GenerationLog:
    generation_log = app.config["IMAGEGEN_GENERATION_LOG"]
    if not hasattr(generation_log, "create_request"):
        msg = "IMAGEGEN_GENERATION_LOG must provide generation log methods."
        raise TypeError(msg)
    return generation_log


@dataclass(frozen=True)
class SelectedGenerationModel:
    provider: ProviderId
    model: ProviderModel
    target: GenerationTarget


def _selected_generation_model(
    payload: dict[str, object],
    *,
    app_config,
) -> SelectedGenerationModel:
    provider = _selected_provider(payload, app_config=app_config)
    edit_mode = _selected_edit_mode(payload)
    model = _selected_provider_model(payload, provider=provider)
    try:
        target = resolve_generation_target(
            provider,
            model.alias,
            edit_mode=edit_mode,
        )
    except RegistryLookupError as error:
        raise ValidationError(str(error)) from error
    return SelectedGenerationModel(provider=provider, model=model, target=target)


def _selected_provider(payload: dict[str, object], *, app_config) -> ProviderId:
    if not app_config.enabled_providers:
        raise ValidationError("No image generation provider is configured.")
    raw_provider = payload.get("provider", app_config.selected_provider)
    if raw_provider is None:
        raise ValidationError("No image generation provider is configured.")
    if not isinstance(raw_provider, str) or not raw_provider.strip():
        raise ValidationError("provider must be a valid provider id.")
    provider = raw_provider.strip()
    if provider not in PROVIDER_IDS:
        choices = ", ".join(app_config.enabled_providers)
        raise ValidationError(
            f"Unknown provider: {provider}. Expected one of: {choices}."
        )
    if provider not in app_config.enabled_providers:
        raise ValidationError(f"Provider `{provider}` is not enabled.")
    return provider


def _selected_edit_mode(payload: dict[str, object]) -> bool:
    edit_mode = payload.get("edit_mode", False)
    if not isinstance(edit_mode, bool):
        raise ValidationError("edit_mode must be a boolean.")
    return edit_mode


def _selected_provider_model(
    payload: dict[str, object],
    *,
    provider: ProviderId,
) -> ProviderModel:
    raw_model = payload.get("model")
    if raw_model is None:
        model = default_model_for_provider(provider)
        if model is None:
            raise ValidationError(f"Provider `{provider}` has no configured models.")
        return model
    if not isinstance(raw_model, str) or not raw_model.strip():
        raise ValidationError("model must be a valid model id.")
    model_ref = raw_model.strip()
    try:
        model = resolve_model_ref(model_ref, selected_provider=provider)
    except RegistryLookupError as error:
        if ":" not in model_ref:
            choices = ", ".join(
                provider_model.alias
                for provider_model in list_models_for_provider(provider)
            )
            raise ValidationError(
                f"Unknown model: {model_ref}. Expected one of: {choices}."
            ) from error
        raise ValidationError(str(error)) from error
    if model.provider != provider:
        raise ValidationError(
            f"Model `{model_ref}` does not belong to provider `{provider}`."
        )
    return model


def _build_provider_request(
    prompt: str,
    model: ProviderModel,
    target: GenerationTarget,
    *,
    parameters: dict[str, object] | None = None,
    source_image_inputs: list[object] | None = None,
) -> dict[str, object]:
    return build_provider_request(
        prompt,
        model,
        target,
        parameters=parameters,
        source_image_inputs=source_image_inputs,
    )


def _request_json(app: Flask, record: GenerationRequest) -> dict[str, object]:
    payload = record.to_json()
    payload["status_url"] = url_for(
        "api_generation_status",
        request_id=record.request_id,
    )
    payload["poll_seconds"] = app.config["IMAGEGEN_APP_CONFIG"].replicate_poll_seconds
    return payload
