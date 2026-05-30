"""Generated image metadata access."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from imagegen.metadata_embed import read_embedded_metadata


@dataclass(frozen=True)
class ImageMetadata:
    content_type: str | None = None
    created_at: str | None = None
    model_alias: str | None = None
    model: str | None = None
    prompt: str | None = None
    parameters: dict[str, object] | None = None

    @property
    def exists(self) -> bool:
        return (
            self.content_type is not None
            or self.created_at is not None
            or self.model_alias is not None
            or self.model is not None
            or self.prompt is not None
            or self.parameters is not None
        )

    def to_json(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "content_type": self.content_type,
            "created_at": self.created_at,
            "model_alias": self.model_alias,
            "model": self.model,
            "prompt": self.prompt,
        }
        if self.parameters is not None:
            payload["parameters"] = self.parameters
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
    return ImageMetadata(
        content_type=_metadata_string(metadata, "content_type"),
        created_at=_metadata_string(metadata, "created_at"),
        model_alias=_metadata_string(metadata, "model_alias"),
        model=_metadata_string(metadata, "model"),
        prompt=_metadata_string(metadata, "prompt"),
        parameters=parameters if isinstance(parameters, dict) else None,
    )


def _metadata_string(metadata: dict[str, object], key: str) -> str | None:
    value = metadata.get(key)
    return value if isinstance(value, str) else None
