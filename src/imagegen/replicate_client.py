"""Replicate prediction wrapper.

This module contains the only runtime Replicate API calls. It builds prediction
payloads from model metadata, creates predictions, polls them to completion, and
hands returned image URLs to the local image store.
"""

from __future__ import annotations

import io
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO, Protocol
from urllib.parse import quote

import httpx
import replicate

from imagegen.config import AppConfig
from imagegen.generation_types import GenerationResult
from imagegen.image_store import StoredImage, persist_generated_images
from imagegen.model_registry import GenerationTarget, ProviderModel
from imagegen.prompt_annotations import strip_prompt_annotations
from imagegen.provider_requests import build_provider_request

TERMINAL_STATUSES = {"succeeded", "failed", "canceled"}
PersistImages = Callable[..., list[StoredImage]]


class PredictionLike(Protocol):
    id: str
    status: str
    output: Any
    error: str | None
    logs: str | None


class PredictionsApi(Protocol):
    def create(
        self,
        *,
        model: str,
        input: dict[str, object],
    ) -> PredictionLike: ...

    def get(self, id: str) -> PredictionLike: ...


class ReplicatePredictionError(RuntimeError):
    pass


class ReplicatePredictionTimeout(TimeoutError):
    pass


def generate_image_urls(
    prompt: str,
    app_config: AppConfig,
    *,
    model: ProviderModel,
    target: GenerationTarget,
    parameters: dict[str, object] | None = None,
    source_image_paths: list[Path] | None = None,
    local_request_id: str | None = None,
    predictions_api: PredictionsApi | None = None,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
    persist_images: PersistImages = persist_generated_images,
) -> ReplicateResult:
    predictions = predictions_api or _replicate_predictions(app_config)
    provider_prompt = strip_prompt_annotations(prompt)
    source_image_files: list[BinaryIO] = []
    if source_image_paths:
        source_image_files = [path.open("rb") for path in source_image_paths]
    prediction_input = build_provider_request(
        provider_prompt,
        model,
        target,
        parameters=parameters,
        source_image_inputs=source_image_files,
    )
    try:
        prediction = predictions.create(
            model=target.provider_model,
            input=prediction_input,
        )
    finally:
        for source_image_file in source_image_files:
            source_image_file.close()

    prediction_metadata_input = build_provider_request(
        provider_prompt,
        model,
        target,
        parameters=parameters,
        source_image_inputs=[path.name for path in source_image_paths or []],
    )
    prediction = wait_for_prediction(
        predictions,
        prediction,
        timeout_seconds=app_config.replicate_timeout_seconds,
        poll_seconds=app_config.replicate_poll_seconds,
        sleep=sleep,
        clock=clock,
    )
    output_urls = normalize_output_urls(prediction.output)
    stored_images = persist_images(
        output_urls,
        output_dir=Path(app_config.output_dir),
        model=model,
        provider="replicate",
        model_alias=model.alias,
        provider_model=target.provider_model,
        prompt=prompt,
        prediction_id=prediction.id,
        local_request_id=local_request_id,
        prediction_input=prediction_metadata_input,
        author=app_config.author,
    )
    return GenerationResult(
        prediction_id=prediction.id,
        output_urls=output_urls,
        stored_images=stored_images,
        logs=prediction.logs or "",
    )


ReplicateResult = GenerationResult


def wait_for_prediction(
    predictions: PredictionsApi,
    prediction: PredictionLike,
    *,
    timeout_seconds: float,
    poll_seconds: float,
    sleep: Callable[[float], None],
    clock: Callable[[], float],
) -> PredictionLike:
    deadline = clock() + timeout_seconds
    current = prediction
    while current.status not in TERMINAL_STATUSES:
        if clock() >= deadline:
            msg = f"Replicate prediction {current.id} timed out after {timeout_seconds:g}s."
            raise ReplicatePredictionTimeout(msg)
        sleep(poll_seconds)
        current = predictions.get(current.id)

    if current.status != "succeeded":
        detail = current.error or current.logs or "No error detail returned."
        msg = f"Replicate prediction {current.id} ended with status {current.status}: {detail}"
        raise ReplicatePredictionError(msg)
    return current


def normalize_output_urls(output: Any) -> list[str]:
    if output is None:
        return []
    if isinstance(output, str):
        return [output]
    if isinstance(output, list | tuple):
        return [url for item in output for url in normalize_output_urls(item)]
    url = getattr(output, "url", None)
    if isinstance(url, str):
        return [url]
    return [str(output)]


@dataclass
class ReplicatePrediction:
    """Minimal Replicate prediction record accepting nullable `version` fields."""

    id: str
    status: str
    output: Any = None
    error: str | None = None
    logs: str | None = None


def _encode_prediction_input(value: Any, client: replicate.Client) -> Any:
    """Recursively upload file handles inside a prediction payload."""
    if isinstance(value, Mapping):
        return {
            key: _encode_prediction_input(item, client) for key, item in value.items()
        }
    if isinstance(value, list | tuple):
        return [_encode_prediction_input(item, client) for item in value]
    if isinstance(value, io.IOBase):
        return client.files.create(value).urls["get"]
    return value


def _prediction_path_for_model(model: str) -> str:
    """Build the Replicate predictions endpoint path for an `owner/name` model."""
    parts = model.split("/")
    if len(parts) != 2 or not parts[0] or not parts[1] or ":" in model:
        msg = f"Invalid Replicate model identifier: {model!r}"
        raise ValueError(msg)
    owner = quote(parts[0], safe="")
    name = quote(parts[1], safe="")
    return f"/v1/models/{owner}/{name}/predictions"


def _parse_prediction_response(payload: object) -> ReplicatePrediction:
    """Validate and extract prediction fields from a Replicate API JSON body."""
    if not isinstance(payload, Mapping):
        msg = "Replicate returned a non-object prediction payload."
        raise ReplicatePredictionError(msg)
    prediction_id = payload.get("id")
    status = payload.get("status")
    if (
        not isinstance(prediction_id, str)
        or not prediction_id
        or not isinstance(status, str)
        or not status
    ):
        msg = "Replicate returned a prediction payload without id or status."
        raise ReplicatePredictionError(msg)
    error = payload.get("error")
    logs = payload.get("logs")
    return ReplicatePrediction(
        id=prediction_id,
        status=status,
        output=payload.get("output"),
        error=error if error is None or isinstance(error, str) else str(error),
        logs=logs if logs is None or isinstance(logs, str) else str(logs),
    )


class _ReplicatePredictionsClient:
    """Adapter around `replicate.Client` that tolerates `version: null` predictions."""

    def __init__(self, client: replicate.Client) -> None:
        self._client = client

    def create(
        self,
        *,
        model: str,
        input: dict[str, object],
    ) -> ReplicatePrediction:
        path = _prediction_path_for_model(model)
        encoded_input = _encode_prediction_input(input, self._client)
        # Replicate's 1.0.7 Prediction Pydantic model rejects `version: null`
        # returned by versionless models (e.g. gpt-image-2.5/2.6), so parse the
        # prediction JSON directly instead of using client.predictions.create.
        response = self._client._request("POST", path, json={"input": encoded_input})
        return _parse_prediction_response(response.json())

    def get(self, id: str) -> ReplicatePrediction:
        prediction_id = quote(id, safe="")
        response = self._client._request("GET", f"/v1/predictions/{prediction_id}")
        return _parse_prediction_response(response.json())


def _replicate_predictions(
    app_config: AppConfig,
    *,
    transport: httpx.BaseTransport | None = None,
) -> PredictionsApi:
    token = app_config.replicate_api_token or None
    client = (
        replicate.Client(api_token=token, transport=transport)
        if transport is not None
        else replicate.Client(api_token=token)
    )
    client.poll_interval = app_config.replicate_poll_seconds
    return _ReplicatePredictionsClient(client)
