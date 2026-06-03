"""Shared model registry types.

These types describe app-facing model metadata and provider-specific generation
targets. They intentionally do not assume that models with the same display name
share parameters, capabilities, or endpoint shapes across providers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Mapping


ProviderId = Literal["replicate", "falai"]
ParameterType = Literal["array", "boolean", "integer", "number", "select", "string"]
ModelMode = Literal["text-to-image", "image-edit"]
ParameterSemanticType = Literal["seed"]
PricingSource = Literal["provider-api", "static", "unknown"]


@dataclass(frozen=True)
class ModelPricing:
    price: str
    title: str
    description: str
    type: str
    metric: str
    metric_count: int
    source: PricingSource = "static"


@dataclass(frozen=True)
class CustomDimensionsControl:
    activation_parameter: str
    activation_value: object
    scale_parameter: str
    width_parameter: str
    height_parameter: str


@dataclass(frozen=True)
class ModelParameter:
    name: str
    description: str
    type: ParameterType
    default: object
    choices: tuple[object, ...] = ()
    minimum: float | int | None = None
    maximum: float | int | None = None
    order: int | None = None
    semantic_type: ParameterSemanticType | None = None


@dataclass(frozen=True)
class SourceImageBinding:
    provider_field: str
    max_count: int


@dataclass(frozen=True)
class GenerationTarget:
    provider: ProviderId
    alias: str
    display_name: str
    provider_model: str
    documentation_url: str
    runtime_url: str
    mode: ModelMode
    parameters: tuple[ModelParameter, ...]
    fixed_inputs: Mapping[str, object]
    pricing: tuple[ModelPricing, ...] = ()
    source_images: SourceImageBinding | None = None
    version: str | None = None
    custom_dimensions: CustomDimensionsControl | None = None
    output_shape: str = "image-urls"


@dataclass(frozen=True)
class ProviderModel:
    provider: ProviderId
    alias: str
    display_name: str
    text_target: GenerationTarget
    edit_target: GenerationTarget | None = None
    selectable: bool = True

    @property
    def edit_capable(self) -> bool:
        return self.edit_target is not None


@dataclass(frozen=True)
class ProviderInfo:
    id: ProviderId
    display_name: str


@dataclass(frozen=True)
class ReplicateModel:
    alias: str
    display_name: str
    documentation_url: str
    replicate_model: str
    edit_capable: bool
    fixed_inputs: dict[str, object]
    default_width: int
    default_height: int
    modes: tuple[ModelMode, ...]
    parameters: tuple[ModelParameter, ...]
    source_image_parameter: str | None = None
    source_image_max: int = 14
    custom_dimensions: CustomDimensionsControl | None = None
    pricing: tuple[ModelPricing, ...] = ()
