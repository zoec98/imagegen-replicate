"""Shared provider-neutral generation result and error types."""

from __future__ import annotations

from dataclasses import dataclass

from imagegen.image_store import StoredImage


@dataclass(frozen=True)
class GenerationResult:
    prediction_id: str
    output_urls: list[str]
    stored_images: list[StoredImage]
    logs: str


class GenerationProviderTimeout(TimeoutError):
    pass
