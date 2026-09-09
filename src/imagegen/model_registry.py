"""Provider-aware model registry facade."""

from __future__ import annotations

from imagegen.model_registry_base import (
    CustomDimensionsControl,
    GenerationTarget,
    ModelParameter,
    ModelPricing,
    ProviderId,
    ProviderInfo,
    ProviderModel,
    SourceImageBinding,
)
from imagegen.model_registry_falai import MODEL_REGISTRY as FALAI_MODEL_REGISTRY
from imagegen.model_registry_replicate import (
    DEFAULT_MODEL_ALIAS,
    MODEL_REGISTRY,
)
from imagegen.model_registry_wiro import MODEL_REGISTRY as WIRO_MODEL_REGISTRY

__all__ = [
    "DEFAULT_MODEL_ALIAS",
    "MODEL_REGISTRY",
    "PROVIDERS",
    "PROVIDER_IDS",
    "PROVIDER_REGISTRIES",
    "CustomDimensionsControl",
    "GenerationTarget",
    "ModelParameter",
    "ModelPricing",
    "ProviderId",
    "ProviderInfo",
    "ProviderModel",
    "RegistryLookupError",
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
    ProviderInfo(id="wiro", display_name="Wiro"),
)
PROVIDER_IDS: tuple[ProviderId, ...] = tuple(provider.id for provider in PROVIDERS)


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


def resolve_model(provider: ProviderId, model_ref: str) -> ProviderModel:
    registry = _provider_registry(provider)
    model = registry.get(model_ref)
    if model is None:
        matches = [
            candidate
            for candidate in registry.values()
            if candidate.display_name.casefold() == model_ref.casefold()
        ]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            aliases = ", ".join(sorted(candidate.alias for candidate in matches))
            raise RegistryLookupError(
                f"Ambiguous model display name `{model_ref}` for provider "
                f"`{provider}`. Use an alias: {aliases}."
            )
    if model is None:
        choices = ", ".join(sorted(registry))
        raise RegistryLookupError(
            f"Unknown model `{model_ref}` for provider `{provider}`. Expected one of: {choices}."
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
        raise RegistryLookupError("Bare model aliases require a selected provider.")
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
    if (
        provider == "wiro"
        and "seedream5-lite-uncensored" in PROVIDER_REGISTRIES[provider]
    ):
        return PROVIDER_REGISTRIES[provider]["seedream5-lite-uncensored"]
    return models[0]


def _provider_registry(provider: ProviderId) -> dict[str, ProviderModel]:
    try:
        return PROVIDER_REGISTRIES[provider]
    except KeyError as error:
        raise RegistryLookupError(f"Unknown provider `{provider}`.") from error


def _provider_id(value: str) -> ProviderId:
    if value in PROVIDER_IDS:
        return value
    raise RegistryLookupError(f"Unknown provider `{value}`.")


PROVIDER_REGISTRIES: dict[ProviderId, dict[str, ProviderModel]] = {
    "replicate": MODEL_REGISTRY,
    "falai": FALAI_MODEL_REGISTRY,
    "wiro": WIRO_MODEL_REGISTRY,
}
