"""Provider-neutral generation client interface.

This module defines the runtime boundary between the worker and provider-
specific generation clients. Providers are responsible for translating a queued
request into upstream API calls and normalizing the result into the shared
stored-image pipeline shape.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Protocol

from imagegen.config import AppConfig
from imagegen.generation_types import GenerationProviderTimeout, GenerationResult
from imagegen.model_registry import MODEL_REGISTRY, ProviderId
from imagegen.replicate_client import (
    ReplicatePredictionTimeout,
    generate_image_urls,
)
from imagegen.request_store import GenerationRequest
from imagegen.source_images import source_image_paths


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
        request_model = MODEL_REGISTRY[request_record.model_alias]
        request_config = replace(
            app_config,
            model_alias=request_model.alias,
            model=request_model,
        )
        try:
            return self._generate(
                request_record.prompt,
                request_config,
                parameters=request_record.parameters,
                source_image_paths=source_image_paths(
                    request_record.source_images,
                    output_dir=Path(app_config.output_dir),
                ),
            )
        except ReplicatePredictionTimeout as error:
            raise GenerationProviderTimeout(str(error)) from error


def default_generation_providers() -> dict[ProviderId, GenerationProvider]:
    return {"replicate": ReplicateGenerationProvider()}
