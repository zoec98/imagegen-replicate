"""Provider-neutral generation client interface.

This module defines the runtime boundary between the worker and provider-
specific generation clients. Providers are responsible for translating a queued
request into upstream API calls and normalizing the result into the shared
stored-image pipeline shape.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from imagegen.config import AppConfig
from imagegen.falai_client import (
    FalAIRequestTimeout,
)
from imagegen.falai_client import (
    generate_image_urls as generate_falai_image_urls,
)
from imagegen.generation_types import GenerationProviderTimeout, GenerationResult
from imagegen.model_registry import (
    ProviderId,
    resolve_generation_target,
    resolve_model,
)
from imagegen.replicate_client import (
    ReplicatePredictionTimeout,
    generate_image_urls,
)
from imagegen.request_store import GenerationRequest
from imagegen.source_images import source_image_paths
from imagegen.wiro_client import (
    WiroRequestTimeout,
)
from imagegen.wiro_client import (
    generate_image_urls as generate_wiro_image_urls,
)


class GenerationProvider(Protocol):
    def generate(
        self,
        request_record: GenerationRequest,
        app_config: AppConfig,
    ) -> GenerationResult: ...


class ReplicateGenerationProvider:
    def __init__(self, *, generate=generate_image_urls) -> None:
        self._generate = generate

    def generate(
        self,
        request_record: GenerationRequest,
        app_config: AppConfig,
    ) -> GenerationResult:
        request_model = resolve_model("replicate", request_record.model_alias)
        request_target = resolve_generation_target(
            "replicate",
            request_record.model_alias,
            edit_mode=request_record.edit_mode,
        )
        try:
            return self._generate(
                request_record.prompt,
                app_config,
                model=request_model,
                target=request_target,
                parameters=request_record.parameters,
                source_image_paths=source_image_paths(
                    request_record.source_images,
                    output_dir=Path(app_config.output_dir),
                ),
            )
        except ReplicatePredictionTimeout as error:
            raise GenerationProviderTimeout(str(error)) from error


class FalAIGenerationProvider:
    def __init__(self, *, generate=generate_falai_image_urls) -> None:
        self._generate = generate

    def generate(
        self,
        request_record: GenerationRequest,
        app_config: AppConfig,
    ) -> GenerationResult:
        request_model = resolve_model("falai", request_record.model_alias)
        request_target = resolve_generation_target(
            "falai",
            request_record.model_alias,
            edit_mode=request_record.edit_mode,
        )
        try:
            return self._generate(
                request_record.prompt,
                app_config,
                model=request_model,
                target=request_target,
                parameters=request_record.parameters,
                source_image_paths=source_image_paths(
                    request_record.source_images,
                    output_dir=Path(app_config.output_dir),
                ),
            )
        except FalAIRequestTimeout as error:
            raise GenerationProviderTimeout(str(error)) from error


class WiroGenerationProvider:
    def __init__(self, *, generate=generate_wiro_image_urls) -> None:
        self._generate = generate

    def generate(
        self,
        request_record: GenerationRequest,
        app_config: AppConfig,
    ) -> GenerationResult:
        request_model = resolve_model("wiro", request_record.model_alias)
        request_target = resolve_generation_target(
            "wiro",
            request_record.model_alias,
            edit_mode=request_record.edit_mode,
        )
        try:
            return self._generate(
                request_record.prompt,
                app_config,
                model=request_model,
                target=request_target,
                parameters=request_record.parameters,
                source_image_paths=source_image_paths(
                    request_record.source_images,
                    output_dir=Path(app_config.output_dir),
                ),
            )
        except WiroRequestTimeout as error:
            raise GenerationProviderTimeout(str(error)) from error


def default_generation_providers() -> dict[ProviderId, GenerationProvider]:
    return {
        "replicate": ReplicateGenerationProvider(),
        "falai": FalAIGenerationProvider(),
        "wiro": WiroGenerationProvider(),
    }
