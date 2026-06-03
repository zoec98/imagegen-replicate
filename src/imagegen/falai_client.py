"""fal.ai generation wrapper.

This module contains the runtime fal.ai API calls. It uploads local edit
sources when needed, submits generation requests to the resolved endpoint,
polls them to completion, normalizes returned image URLs, and hands them to the
shared local image store.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol, cast

from fal_client.client import Completed, InProgress, Queued, SyncClient

from imagegen.config import AppConfig
from imagegen.generation_types import GenerationResult
from imagegen.image_store import StoredImage, persist_generated_images
from imagegen.model_registry import GenerationTarget, ProviderModel
from imagegen.prompt_annotations import strip_prompt_annotations
from imagegen.provider_requests import build_provider_request


PersistImages = Callable[..., list[StoredImage]]


class FalAIHandle(Protocol):
    request_id: str

    def status(self, *, with_logs: bool = False) -> object: ...

    def get(self) -> Any: ...


class FalAIClient(Protocol):
    def submit(self, application: str, arguments: dict[str, object]) -> FalAIHandle: ...

    def upload_file(self, path: Path) -> str: ...


class FalAIRequestError(RuntimeError):
    pass


class FalAIRequestTimeout(TimeoutError):
    pass


def generate_image_urls(
    prompt: str,
    app_config: AppConfig,
    *,
    model: ProviderModel,
    target: GenerationTarget,
    parameters: dict[str, object] | None = None,
    source_image_paths: list[Path] | None = None,
    client: FalAIClient | None = None,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
    persist_images: PersistImages = persist_generated_images,
) -> GenerationResult:
    fal_client = client or SyncClient(
        key=app_config.fal_key or None,
        default_timeout=app_config.replicate_timeout_seconds,
    )
    provider_prompt = strip_prompt_annotations(prompt)
    uploaded_source_images = [
        fal_client.upload_file(path) for path in source_image_paths or []
    ]
    submission_input = build_provider_request(
        provider_prompt,
        model,
        target,
        parameters=parameters,
        source_image_inputs=uploaded_source_images,
    )
    metadata_input = build_provider_request(
        provider_prompt,
        model,
        target,
        parameters=parameters,
        source_image_inputs=[path.name for path in source_image_paths or []],
    )
    handle = fal_client.submit(target.provider_model, arguments=submission_input)
    completed, logs = wait_for_request(
        handle,
        timeout_seconds=app_config.replicate_timeout_seconds,
        poll_seconds=app_config.replicate_poll_seconds,
        sleep=sleep,
        clock=clock,
    )
    if completed.error:
        error_detail = completed.error
        if completed.error_type:
            error_detail = f"{completed.error_type}: {error_detail}"
        msg = f"fal.ai request {handle.request_id} failed: {error_detail}"
        raise FalAIRequestError(msg)

    output_urls = normalize_output_urls(handle.get())
    if not output_urls:
        msg = f"fal.ai request {handle.request_id} returned no image URLs."
        raise FalAIRequestError(msg)

    stored_images = persist_images(
        output_urls,
        output_dir=Path(app_config.output_dir),
        model=model,
        provider="falai",
        model_alias=model.alias,
        provider_model=target.provider_model,
        prompt=prompt,
        prediction_id=handle.request_id,
        prediction_input=metadata_input,
        author=app_config.author,
    )
    return GenerationResult(
        prediction_id=handle.request_id,
        output_urls=output_urls,
        stored_images=stored_images,
        logs=logs,
    )


def wait_for_request(
    handle: FalAIHandle,
    *,
    timeout_seconds: float,
    poll_seconds: float,
    sleep: Callable[[float], None],
    clock: Callable[[], float],
) -> tuple[Completed, str]:
    deadline = clock() + timeout_seconds
    current = handle.status(with_logs=True)
    last_logs = _status_logs(current)
    while not isinstance(current, Completed):
        if clock() >= deadline:
            msg = f"fal.ai request {handle.request_id} timed out after {timeout_seconds:g}s."
            raise FalAIRequestTimeout(msg)
        sleep(poll_seconds)
        current = handle.status(with_logs=True)
        current_logs = _status_logs(current)
        if current_logs:
            last_logs = current_logs
    completed = cast(Completed, current)
    completed_logs = _status_logs(completed) or last_logs
    return completed, _format_logs(completed_logs)


def normalize_output_urls(output: Any) -> list[str]:
    urls = _normalize_output_urls(output)
    deduped: list[str] = []
    for url in urls:
        if url not in deduped:
            deduped.append(url)
    return deduped


def _normalize_output_urls(output: Any) -> list[str]:
    if output is None:
        return []
    if isinstance(output, str):
        return [output] if _looks_like_url(output) else []
    if isinstance(output, list | tuple):
        return [url for item in output for url in _normalize_output_urls(item)]
    url = getattr(output, "url", None)
    if isinstance(url, str) and _looks_like_url(url):
        return [url]
    if isinstance(output, dict):
        direct_url = output.get("url")
        if isinstance(direct_url, str) and _looks_like_url(direct_url):
            return [direct_url]
        urls: list[str] = []
        for key in ("images", "image", "output", "outputs", "result", "data"):
            if key in output:
                urls.extend(_normalize_output_urls(output[key]))
        if urls:
            return urls
        for key, value in output.items():
            lowered = key.lower()
            if "url" in lowered or "image" in lowered:
                urls.extend(_normalize_output_urls(value))
        return urls
    return []


def _looks_like_url(value: str) -> bool:
    return value.startswith(("http://", "https://"))


def _status_logs(status: object) -> list[dict[str, Any]] | None:
    if isinstance(status, InProgress | Completed):
        return status.logs
    if isinstance(status, Queued):
        return None
    logs = getattr(status, "logs", None)
    if isinstance(logs, list):
        return logs
    return None


def _format_logs(entries: list[dict[str, Any]] | None) -> str:
    if not entries:
        return ""
    lines: list[str] = []
    for entry in entries:
        if not isinstance(entry, dict):
            lines.append(str(entry))
            continue
        for key in ("message", "msg", "event_message"):
            value = entry.get(key)
            if isinstance(value, str) and value.strip():
                lines.append(value.strip())
                break
        else:
            lines.append(json.dumps(entry, sort_keys=True))
    return "\n".join(lines)
