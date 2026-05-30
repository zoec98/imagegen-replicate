"""Generated image metadata access."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from imagegen.metadata_embed import read_embedded_metadata


@dataclass(frozen=True)
class ImageMetadata:
    content_type: str | None = None
    created_at: str | None = None
    parameters: dict[str, object] | None = None

    @property
    def exists(self) -> bool:
        return (
            self.content_type is not None
            or self.created_at is not None
            or self.parameters is not None
        )

    def to_json(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "content_type": self.content_type,
            "created_at": self.created_at,
        }
        if self.parameters is not None:
            payload["parameters"] = self.parameters
        return payload


class ImageMetadataProvider(Protocol):
    def get(self, image_path: Path) -> ImageMetadata: ...


class EmbeddedImageMetadataProvider:
    def __init__(self, fallback: ImageMetadataProvider | None = None) -> None:
        self._fallback = fallback

    def get(self, image_path: Path) -> ImageMetadata:
        value = read_embedded_metadata(image_path)
        if isinstance(value, dict):
            metadata = image_metadata_from_dict(value)
            if metadata.exists:
                return metadata
        if self._fallback is not None:
            return self._fallback.get(image_path)
        return ImageMetadata()


class SidecarImageMetadataProvider:
    def get(self, image_path: Path) -> ImageMetadata:
        metadata_path = sidecar_metadata_path(image_path)
        if not metadata_path.is_file():
            return ImageMetadata()
        try:
            value = json.loads(metadata_path.read_text(encoding="utf-8"))
        except OSError, json.JSONDecodeError:
            return ImageMetadata()
        if not isinstance(value, dict):
            return ImageMetadata()
        return image_metadata_from_dict(value)


def image_metadata_from_dict(metadata: dict[str, object]) -> ImageMetadata:
    parameters = metadata.get("parameters")
    return ImageMetadata(
        content_type=_metadata_string(metadata, "content_type"),
        created_at=_metadata_string(metadata, "created_at"),
        parameters=parameters if isinstance(parameters, dict) else None,
    )


def sidecar_metadata_path(image_path: Path) -> Path:
    return image_path.with_name(image_path.name + ".json")


def _metadata_string(metadata: dict[str, object], key: str) -> str | None:
    value = metadata.get(key)
    return value if isinstance(value, str) else None
