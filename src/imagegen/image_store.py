"""Local storage for generated image files and metadata."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

import httpx

from imagegen.model_registry import ReplicateModel


CONTENT_TYPE_EXTENSIONS = {
    "image/gif": ".gif",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
DOWNLOAD_SIZE_OVERHEAD_BYTES = 1024 * 1024


@dataclass(frozen=True)
class StoredImage:
    path: Path
    metadata_path: Path
    source_url: str
    content_type: str
    size_bytes: int


class ImageDownloadError(RuntimeError):
    pass


def persist_generated_images(
    urls: list[str],
    *,
    output_dir: Path,
    model: ReplicateModel,
    prompt: str,
    prediction_id: str,
    prediction_input: dict[str, object],
    client: httpx.Client | None = None,
) -> list[StoredImage]:
    output_dir.mkdir(parents=True, exist_ok=True)
    close_client = client is None
    http_client = client or httpx.Client(timeout=30.0, follow_redirects=True)
    try:
        return [
            download_image(
                url,
                output_dir=output_dir,
                model=model,
                prompt=prompt,
                prediction_id=prediction_id,
                sequence=sequence,
                prediction_input=prediction_input,
                client=http_client,
            )
            for sequence, url in enumerate(urls, start=1)
        ]
    finally:
        if close_client:
            http_client.close()


def download_image(
    url: str,
    *,
    output_dir: Path,
    model: ReplicateModel,
    prompt: str,
    prediction_id: str,
    sequence: int,
    prediction_input: dict[str, object],
    client: httpx.Client,
) -> StoredImage:
    response = client.get(url)
    response.raise_for_status()

    content_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
    if not content_type.startswith("image/"):
        msg = f"Expected image content from {url}, got {content_type or 'unknown'}."
        raise ImageDownloadError(msg)

    content = response.content
    max_bytes = max_download_bytes(model)
    if len(content) > max_bytes:
        msg = f"Image from {url} is {len(content)} bytes, exceeding limit {max_bytes}."
        raise ImageDownloadError(msg)

    extension = _extension_for(content_type, url)
    filename = f"{model.alias}-{prediction_id}-{sequence:02d}{extension}"
    path = output_dir / filename
    metadata_path = path.with_name(path.name + ".json")
    path.write_bytes(content)
    metadata = {
        "created_at": datetime.now(UTC).isoformat(),
        "model_alias": model.alias,
        "model": model.replicate_model,
        "prediction_id": prediction_id,
        "sequence": sequence,
        "prompt": prompt,
        "parameters": prediction_input,
        "source_url": url,
        "content_type": content_type,
        "size_bytes": len(content),
        "filename": filename,
    }
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    return StoredImage(
        path=path,
        metadata_path=metadata_path,
        source_url=url,
        content_type=content_type,
        size_bytes=len(content),
    )


def max_download_bytes(model: ReplicateModel) -> int:
    return model.default_width * model.default_height * 3 + DOWNLOAD_SIZE_OVERHEAD_BYTES


def _extension_for(content_type: str, url: str) -> str:
    if content_type in CONTENT_TYPE_EXTENSIONS:
        return CONTENT_TYPE_EXTENSIONS[content_type]
    suffix = Path(urlparse(url).path).suffix.lower()
    if suffix in {".gif", ".jpeg", ".jpg", ".png", ".webp"}:
        return suffix
    return ".img"
