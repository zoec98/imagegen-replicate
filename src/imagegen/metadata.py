"""Generated image metadata access.

This module owns metadata lookup for generated images. The current
implementation reads legacy JSON sidecars, but callers use the provider
interface so the storage can later move into image EXIF without changing route
or gallery code.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class ImageMetadata:
    content_type: str | None = None
    created_at: str | None = None

    @property
    def exists(self) -> bool:
        return self.content_type is not None or self.created_at is not None

    def to_json(self) -> dict[str, str | None]:
        return {
            "content_type": self.content_type,
            "created_at": self.created_at,
        }


class ImageMetadataProvider(Protocol):
    def get(self, image_path: Path) -> ImageMetadata: ...


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
        return ImageMetadata(
            content_type=_metadata_string(value, "content_type"),
            created_at=_metadata_string(value, "created_at"),
        )


def sidecar_metadata_path(image_path: Path) -> Path:
    return image_path.with_name(image_path.name + ".json")


def _metadata_string(metadata: dict[str, object], key: str) -> str | None:
    value = metadata.get(key)
    return value if isinstance(value, str) else None
