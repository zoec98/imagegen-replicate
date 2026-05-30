"""Replicate prediction wrapper.

This module contains the only runtime Replicate API calls. It builds prediction
payloads from model metadata, creates predictions, polls them to completion, and
hands returned image URLs to the local image store.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO, Protocol

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
    parameters: dict[str, object] | None = None,
    source_image_paths: list[Path] | None = None,
    predictions_api: PredictionsApi | None = None,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
    persist_images: PersistImages = persist_generated_images,
) -> ReplicateResult:
    predictions = predictions_api or _replicate_predictions(app_config)
    source_image_files: list[BinaryIO] = []
    prediction_input = build_prediction_input(
        prompt,
        app_config.model,
        parameters=parameters,
        source_image_inputs=source_image_files,
    )
    if source_image_paths:
        source_image_files = [path.open("rb") for path in source_image_paths]
        prediction_input = build_prediction_input(
            prompt,
            app_config.model,
            parameters=parameters,
            source_image_inputs=source_image_files,
        )
    try:
        prediction = predictions.create(
            model=app_config.model.replicate_model,
            input=prediction_input,
        )
    finally:
        for source_image_file in source_image_files:
            source_image_file.close()

    prediction_metadata_input = build_prediction_input(
        prompt,
        app_config.model,
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
        model=app_config.model,
        prompt=prompt,
        prediction_id=prediction.id,
        prediction_input=prediction_metadata_input,
    )
    return ReplicateResult(
        prediction_id=prediction.id,
        output_urls=output_urls,
        stored_images=stored_images,
        logs=prediction.logs or "",
    )


def build_prediction_input(
    prompt: str,
    model: ReplicateModel,
    *,
    parameters: dict[str, object] | None = None,
    source_image_inputs: list[object] | None = None,
) -> dict[str, object]:
    custom_dimensions = model.custom_dimensions
    use_custom_dimensions = (
        custom_dimensions is not None
        and parameters is not None
        and parameters.get(custom_dimensions.activation_parameter)
        == custom_dimensions.activation_value
    )
    prediction_input: dict[str, object] = {}
    for parameter in model.parameters:
        if parameter.name == "prompt":
            prediction_input[parameter.name] = prompt
        elif parameter.name == model.source_image_parameter:
            continue
        elif (
            use_custom_dimensions
            and custom_dimensions is not None
            and parameter.name == custom_dimensions.scale_parameter
        ):
            continue
        elif parameter.default != "":
            prediction_input[parameter.name] = parameter.default
    if parameters:
        prediction_input.update(parameters)
    if use_custom_dimensions and custom_dimensions is not None:
        prediction_input.pop(custom_dimensions.scale_parameter, None)
    if source_image_inputs and model.source_image_parameter:
        prediction_input[model.source_image_parameter] = _source_image_input_value(
            model,
            source_image_inputs,
        )
    prediction_input.update(model.fixed_inputs)
    return prediction_input


def _source_image_input_value(
    model: ReplicateModel,
    source_image_inputs: list[object],
) -> object:
    if model.source_image_max == 1:
        return source_image_inputs[0]
    return source_image_inputs


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
