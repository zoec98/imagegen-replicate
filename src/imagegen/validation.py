"""Server-side generation request validation.

This module validates browser-submitted prompt and model parameters against the
active model registry entry. Browser widgets are convenience only; this module
is the authoritative request boundary before background work is queued.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from imagegen.model_registry import ModelParameter, ReplicateModel
from imagegen.source_images import SourceImageError, validate_source_images


MVP_PARAMETER_NAMES = {
    "size",
    "aspect_ratio",
    "sequential_image_generation",
    "max_images",
}


@dataclass(frozen=True)
class ValidatedGenerationRequest:
    prompt: str
    parameters: dict[str, object]
    source_images: list[str]


class ValidationError(ValueError):
    pass


def validate_generation_payload(
    payload: dict[str, Any],
    *,
    model: ReplicateModel,
    output_dir: Path,
) -> ValidatedGenerationRequest:
    prompt = str(payload.get("prompt", "")).strip()
    if not prompt:
        raise ValidationError("Prompt is required.")

    raw_parameters = payload.get("parameters", {})
    if raw_parameters is None:
        raw_parameters = {}
    if not isinstance(raw_parameters, dict):
        raise ValidationError("parameters must be an object.")

    try:
        source_images = validate_source_images(
            payload.get("source_images"),
            model=model,
            output_dir=output_dir,
        )
    except SourceImageError as error:
        raise ValidationError(str(error)) from error

    parameters = validate_model_parameters(raw_parameters, model=model)
    return ValidatedGenerationRequest(
        prompt=prompt,
        parameters=parameters,
        source_images=source_images,
    )


def validate_model_parameters(
    raw_parameters: dict[str, Any],
    *,
    model: ReplicateModel,
) -> dict[str, object]:
    registry_parameters = {parameter.name: parameter for parameter in model.parameters}
    validated: dict[str, object] = {}

    for name in raw_parameters:
        if name in model.fixed_inputs:
            raise ValidationError(f"{name} is fixed by the server.")
        if name == "prompt":
            raise ValidationError("prompt must be submitted as a top-level field.")
        if name == "image_input":
            raise ValidationError("image_input is not supported by the MVP API yet.")
        if name not in MVP_PARAMETER_NAMES or name not in registry_parameters:
            raise ValidationError(f"Unknown parameter: {name}.")

    for name in sorted(MVP_PARAMETER_NAMES):
        parameter = registry_parameters.get(name)
        if parameter is None:
            continue
        raw_value = raw_parameters.get(name, parameter.default)
        validated[name] = _validate_parameter_value(parameter, raw_value)

    return validated


def _validate_parameter_value(parameter: ModelParameter, value: Any) -> object:
    if parameter.type == "select":
        return _validate_select(parameter, value)
    if parameter.type == "integer":
        return _validate_integer(parameter, value)
    if parameter.type == "boolean":
        if not isinstance(value, bool):
            raise ValidationError(f"{parameter.name} must be a boolean.")
        return value
    if parameter.type == "string":
        if not isinstance(value, str):
            raise ValidationError(f"{parameter.name} must be a string.")
        return value
    if parameter.type == "array":
        if not isinstance(value, list):
            raise ValidationError(f"{parameter.name} must be an array.")
        return value

    raise ValidationError(f"{parameter.name} has unsupported parameter type.")


def _validate_select(parameter: ModelParameter, value: Any) -> object:
    if value not in parameter.choices:
        choices = ", ".join(str(choice) for choice in parameter.choices)
        raise ValidationError(f"{parameter.name} must be one of: {choices}.")
    return value


def _validate_integer(parameter: ModelParameter, value: Any) -> int:
    if isinstance(value, bool):
        raise ValidationError(f"{parameter.name} must be an integer.")
    if isinstance(value, int):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = int(value, 10)
        except ValueError as error:
            raise ValidationError(f"{parameter.name} must be an integer.") from error
    else:
        raise ValidationError(f"{parameter.name} must be an integer.")

    if parameter.minimum is not None and parsed < parameter.minimum:
        raise ValidationError(f"{parameter.name} must be at least {parameter.minimum}.")
    if parameter.maximum is not None and parsed > parameter.maximum:
        raise ValidationError(f"{parameter.name} must be at most {parameter.maximum}.")
    return parsed
