"""Local storage for generated image files and embedded metadata.

This module downloads Replicate image outputs, validates basic response safety,
writes files under the configured output directory, and embeds metadata.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

import httpx

from imagegen.metadata_embed import write_embedded_metadata
from imagegen.metadata_policy import synthesize_copyright
from imagegen.model_registry import ReplicateModel


SOFTWARE_NAME = "https://github.com/zoec98/imagegen-replicate"


CONTENT_TYPE_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
DOWNLOAD_SIZE_OVERHEAD_BYTES = 1024 * 1024


@dataclass(frozen=True)
class StoredImage:
    path: Path
    source_url: str
    content_type: str
    size_bytes: int
    created_at: str


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
    author: str,
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
                author=author,
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
    author: str,
    client: httpx.Client,
) -> StoredImage:
    response = client.get(url)
    response.raise_for_status()

    content_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
    if content_type == "image/gif":
        msg = f"GIF image outputs are not supported from {url}."
        raise ImageDownloadError(msg)
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
    path.write_bytes(content)
    created_at = datetime.now(UTC).isoformat()
    metadata = {
        "created_at": created_at,
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
        "author": author,
        "copyright": synthesize_copyright(author, created_at),
        "software": SOFTWARE_NAME,
    }
    write_embedded_metadata(path, metadata)
    return StoredImage(
        path=path,
        source_url=url,
        content_type=content_type,
        size_bytes=len(content),
        created_at=created_at,
    )


def max_download_bytes(model: ReplicateModel) -> int:
    return model.default_width * model.default_height * 3 + DOWNLOAD_SIZE_OVERHEAD_BYTES


def _extension_for(content_type: str, url: str) -> str:
    if content_type in CONTENT_TYPE_EXTENSIONS:
        return CONTENT_TYPE_EXTENSIONS[content_type]
    suffix = Path(urlparse(url).path).suffix.lower()
    if suffix in {".jpeg", ".jpg", ".png", ".webp"}:
        return suffix
    return ".img"
