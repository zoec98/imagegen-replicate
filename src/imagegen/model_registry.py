"""Provider-aware model registry facade."""

from __future__ import annotations

from imagegen.model_registry_base import (
    CustomDimensionsControl,
    GenerationTarget,
    ModelMode,
    ModelParameter,
    ModelPricing,
    ProviderId,
    ProviderInfo,
    ProviderModel,
    ReplicateModel,
    SourceImageBinding,
)
from imagegen.model_registry_falai import MODEL_REGISTRY as FALAI_MODEL_REGISTRY
from imagegen.model_registry_replicate import (
    DEFAULT_MODEL_ALIAS,
    MODEL_REGISTRY,
)

__all__ = [
    "DEFAULT_MODEL_ALIAS",
    "MODEL_REGISTRY",
    "PROVIDERS",
    "PROVIDER_REGISTRIES",
    "CustomDimensionsControl",
    "GenerationTarget",
    "ModelParameter",
    "ModelPricing",
    "ProviderId",
    "ProviderInfo",
    "ProviderModel",
    "RegistryLookupError",
    "ReplicateModel",
    "SourceImageBinding",
    "default_model_for_provider",
    "list_models_for_provider",
    "list_providers",
    "resolve_generation_target",
    "resolve_model",
    "resolve_model_ref",
]


PROVIDERS: tuple[ProviderInfo, ...] = (
    ProviderInfo(id="replicate", display_name="Replicate"),
    ProviderInfo(id="falai", display_name="fal.ai"),
)

class RegistryLookupError(ValueError):
    """Raised when a provider/model registry reference cannot be resolved."""


def list_providers() -> tuple[ProviderInfo, ...]:
    return PROVIDERS


def list_models_for_provider(provider: ProviderId) -> tuple[ProviderModel, ...]:
    registry = _provider_registry(provider)
    return tuple(
        model
        for model in sorted(registry.values(), key=lambda item: item.alias)
        if model.selectable
    )


def resolve_model(provider: ProviderId, alias: str) -> ProviderModel:
    registry = _provider_registry(provider)
    model = registry.get(alias)
    if model is None:
        choices = ", ".join(sorted(registry))
        raise RegistryLookupError(
            f"Unknown model `{alias}` for provider `{provider}`. Expected one of: {choices}."
        )
    return model


def resolve_model_ref(
    model_ref: str,
    *,
    selected_provider: ProviderId | None = None,
) -> ProviderModel:
    if ":" in model_ref:
        provider, alias = model_ref.split(":", 1)
        return resolve_model(_provider_id(provider), alias)
    if selected_provider is None:
        raise RegistryLookupError(
            "Bare model aliases require a selected provider."
        )
    return resolve_model(selected_provider, model_ref)


def resolve_generation_target(
    provider: ProviderId,
    alias: str,
    *,
    edit_mode: bool,
) -> GenerationTarget:
    model = resolve_model(provider, alias)
    if edit_mode:
        if model.edit_target is None:
            raise RegistryLookupError(
                f"Model `{provider}:{alias}` does not support image edit mode."
            )
        return model.edit_target
    return model.text_target


def default_model_for_provider(provider: ProviderId) -> ProviderModel | None:
    models = list_models_for_provider(provider)
    if not models:
        return None
    if provider == "replicate" and DEFAULT_MODEL_ALIAS in PROVIDER_REGISTRIES[provider]:
        return PROVIDER_REGISTRIES[provider][DEFAULT_MODEL_ALIAS]
    return models[0]


def _provider_registry(provider: ProviderId) -> dict[str, ProviderModel]:
    try:
        return PROVIDER_REGISTRIES[provider]
    except KeyError as error:
        raise RegistryLookupError(f"Unknown provider `{provider}`.") from error


def _provider_id(value: str) -> ProviderId:
    if value in {"replicate", "falai"}:
        return value
    raise RegistryLookupError(f"Unknown provider `{value}`.")


def _provider_model_from_replicate(model: ReplicateModel) -> ProviderModel:
    text_target = _target_from_replicate(model, mode="text-to-image")
    edit_target = (
        _target_from_replicate(model, mode="image-edit")
        if model.edit_capable
        else None
    )
    return ProviderModel(
        provider="replicate",
        alias=model.alias,
        display_name=model.display_name,
        text_target=text_target,
        edit_target=edit_target,
    )


def _target_from_replicate(
    model: ReplicateModel,
    *,
    mode: ModelMode,
) -> GenerationTarget:
    return GenerationTarget(
        provider="replicate",
        alias=model.alias,
        display_name=model.display_name,
        provider_model=model.replicate_model,
        documentation_url=model.documentation_url,
        runtime_url=f"https://replicate.com/{model.replicate_model}",
        mode=mode,
        parameters=model.parameters,
        fixed_inputs=model.fixed_inputs,
        source_images=(
            SourceImageBinding(
                provider_field=model.source_image_parameter,
                max_count=model.source_image_max,
            )
            if mode == "image-edit" and model.source_image_parameter
            else None
        ),
        pricing=model.pricing,
        custom_dimensions=model.custom_dimensions,
    )


PROVIDER_REGISTRIES: dict[ProviderId, dict[str, ProviderModel]] = {
    "replicate": {
        alias: _provider_model_from_replicate(model)
        for alias, model in MODEL_REGISTRY.items()
    },
    "falai": FALAI_MODEL_REGISTRY,
}
