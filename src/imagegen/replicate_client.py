"""Replicate prediction wrapper."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import replicate

from imagegen.config import AppConfig
from imagegen.image_store import StoredImage, persist_generated_images
from imagegen.model_registry import ReplicateModel


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


@dataclass(frozen=True)
class ReplicateResult:
    prediction_id: str
    output_urls: list[str]
    stored_images: list[StoredImage]
    logs: str


class ReplicatePredictionError(RuntimeError):
    pass


class ReplicatePredictionTimeout(TimeoutError):
    pass


def generate_image_urls(
    prompt: str,
    app_config: AppConfig,
    *,
    predictions_api: PredictionsApi | None = None,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
    persist_images: PersistImages = persist_generated_images,
) -> ReplicateResult:
    predictions = predictions_api or _replicate_predictions(app_config)
    prediction_input = build_prediction_input(prompt, app_config.model)
    prediction = predictions.create(
        model=app_config.model.replicate_model,
        input=prediction_input,
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
        model=app_config.model,
        prompt=prompt,
        prediction_id=prediction.id,
        prediction_input=prediction_input,
    )
    return ReplicateResult(
        prediction_id=prediction.id,
        output_urls=output_urls,
        stored_images=stored_images,
        logs=prediction.logs or "",
    )


def build_prediction_input(prompt: str, model: ReplicateModel) -> dict[str, object]:
    prediction_input: dict[str, object] = {}
    for parameter in model.parameters:
        if parameter.name == "prompt":
            prediction_input[parameter.name] = prompt
        elif parameter.default != "":
            prediction_input[parameter.name] = parameter.default
    prediction_input.update(model.fixed_inputs)
    return prediction_input


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


def _replicate_predictions(app_config: AppConfig) -> PredictionsApi:
    client = replicate.Client(api_token=app_config.replicate_api_token or None)
    client.poll_interval = app_config.replicate_poll_seconds
    return client.predictions
