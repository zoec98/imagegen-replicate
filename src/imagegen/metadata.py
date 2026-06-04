"""Generated image metadata access."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from imagegen.metadata_embed import read_embedded_metadata
from imagegen.model_registry import ProviderId, RegistryLookupError, resolve_model


@dataclass(frozen=True)
class ImageMetadata:
    content_type: str | None = None
    created_at: str | None = None
    provider: ProviderId | None = None
    model_alias: str | None = None
    model: str | None = None
    prompt: str | None = None
    parameters: dict[str, object] | None = None
    edit_mode: bool = False
    source_images: list[str] | None = None

    @property
    def exists(self) -> bool:
        return (
            self.content_type is not None
            or self.created_at is not None
            or self.provider is not None
            or self.model_alias is not None
            or self.model is not None
            or self.prompt is not None
            or self.parameters is not None
            or self.edit_mode
            or self.source_images is not None
        )

    def to_json(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "content_type": self.content_type,
            "created_at": self.created_at,
            "model_alias": self.model_alias,
            "model": self.model,
            "prompt": self.prompt,
        }
        if self.provider is not None:
            payload["provider"] = self.provider
        if self.parameters is not None:
            payload["parameters"] = self.parameters
        payload["edit_mode"] = self.edit_mode
        if self.source_images is not None:
            payload["source_images"] = self.source_images
        return payload


class ImageMetadataProvider(Protocol):
    def get(self, image_path: Path) -> ImageMetadata: ...


class EmbeddedImageMetadataProvider:
    def get(self, image_path: Path) -> ImageMetadata:
        value = read_embedded_metadata(image_path)
        if isinstance(value, dict):
            metadata = image_metadata_from_dict(value)
            if metadata.exists:
                return metadata
        return ImageMetadata()


def image_metadata_from_dict(metadata: dict[str, object]) -> ImageMetadata:
    parameters = metadata.get("parameters")
    parameters = parameters if isinstance(parameters, dict) else None
    provider = _metadata_provider(metadata)
    model_alias = _metadata_string(metadata, "model_alias")
    source_images = _metadata_source_images(
        metadata,
        provider=provider,
        model_alias=model_alias,
        parameters=parameters,
    )
    return ImageMetadata(
        content_type=_metadata_string(metadata, "content_type"),
        created_at=_metadata_string(metadata, "created_at"),
        provider=provider,
        model_alias=model_alias,
        model=_metadata_string(metadata, "model"),
        prompt=_metadata_string(metadata, "prompt"),
        parameters=parameters,
        edit_mode=bool(source_images),
        source_images=source_images,
    )


def _metadata_string(metadata: dict[str, object], key: str) -> str | None:
    value = metadata.get(key)
    return value if isinstance(value, str) else None


def _metadata_provider(metadata: dict[str, object]) -> ProviderId | None:
    value = metadata.get("provider")
    if value in {"replicate", "falai"}:
        return value
    model_alias = _metadata_string(metadata, "model_alias")
    provider_model = _metadata_string(metadata, "model")
    if model_alias is None or provider_model is None:
        return None
    for provider in ("replicate", "falai"):
        try:
            model = resolve_model(provider, model_alias)
        except RegistryLookupError:
            continue
        target_models = [model.text_target.provider_model]
        if model.edit_target is not None:
            target_models.append(model.edit_target.provider_model)
        if provider_model in target_models:
            return provider
    return None


def _metadata_source_images(
    metadata: dict[str, object],
    *,
    provider: ProviderId | None,
    model_alias: str | None,
    parameters: dict[str, object] | None,
) -> list[str] | None:
    explicit = _source_images_value(metadata.get("source_images"))
    if explicit:
        return explicit
    if provider is None or model_alias is None or parameters is None:
        return None
    source_parameter = _source_image_parameter(provider, model_alias)
    if source_parameter is None:
        return None
    return _source_images_value(parameters.get(source_parameter))


def _source_image_parameter(provider: ProviderId, model_alias: str) -> str | None:
    try:
        model = resolve_model(provider, model_alias)
    except RegistryLookupError:
        return None
    if model.edit_target is not None and model.edit_target.source_images is not None:
        return model.edit_target.source_images.provider_field
    return None


def _source_images_value(value: object) -> list[str] | None:
    if isinstance(value, str) and value.strip():
        return [value]
    if isinstance(value, list):
        filenames = [item for item in value if isinstance(item, str) and item.strip()]
        return filenames or None
    return None
