import pytest

from imagegen.model_registry import MODEL_REGISTRY
from imagegen.validation import (
    ValidationError,
    validate_generation_payload,
    validate_model_parameters,
)


def test_validate_generation_payload_accepts_defaults():
    result = validate_generation_payload(
        {"prompt": "a small red house"},
        model=MODEL_REGISTRY["seedream45"],
    )

    assert result.prompt == "a small red house"
    assert result.parameters == {
        "aspect_ratio": "match_input_image",
        "max_images": 1,
        "sequential_image_generation": "disabled",
        "size": "2K",
    }


def test_validate_generation_payload_preserves_prompt_without_length_limit():
    prompt = "x" * 10_000

    result = validate_generation_payload(
        {"prompt": prompt},
        model=MODEL_REGISTRY["seedream45"],
    )

    assert result.prompt == prompt


def test_validate_generation_payload_rejects_blank_prompt():
    with pytest.raises(ValidationError, match="Prompt is required."):
        validate_generation_payload(
            {"prompt": "   "}, model=MODEL_REGISTRY["seedream45"]
        )


def test_validate_model_parameters_accepts_valid_values_and_integer_strings():
    result = validate_model_parameters(
        {
            "size": "4K",
            "aspect_ratio": "1:1",
            "sequential_image_generation": "auto",
            "max_images": "3",
        },
        model=MODEL_REGISTRY["seedream45"],
    )

    assert result == {
        "aspect_ratio": "1:1",
        "max_images": 3,
        "sequential_image_generation": "auto",
        "size": "4K",
    }


def test_validate_model_parameters_rejects_invalid_select_choice():
    with pytest.raises(ValidationError, match="size must be one of: 2K, 4K."):
        validate_model_parameters(
            {"size": "custom"},
            model=MODEL_REGISTRY["seedream45"],
        )


def test_validate_model_parameters_rejects_integer_below_minimum():
    with pytest.raises(ValidationError, match="max_images must be at least 1."):
        validate_model_parameters(
            {"max_images": 0},
            model=MODEL_REGISTRY["seedream45"],
        )


def test_validate_model_parameters_rejects_integer_above_maximum():
    with pytest.raises(ValidationError, match="max_images must be at most 15."):
        validate_model_parameters(
            {"max_images": 16},
            model=MODEL_REGISTRY["seedream45"],
        )


def test_validate_model_parameters_rejects_fixed_input_override():
    with pytest.raises(
        ValidationError,
        match="disable_safety_checker is fixed by the server.",
    ):
        validate_model_parameters(
            {"disable_safety_checker": False},
            model=MODEL_REGISTRY["seedream45"],
        )


def test_validate_model_parameters_rejects_image_input_for_mvp():
    with pytest.raises(ValidationError, match="image_input is not supported"):
        validate_model_parameters(
            {"image_input": ["image.png"]},
            model=MODEL_REGISTRY["seedream45"],
        )


def test_validate_model_parameters_rejects_unknown_parameter():
    with pytest.raises(ValidationError, match="Unknown parameter: width."):
        validate_model_parameters(
            {"width": 1024},
            model=MODEL_REGISTRY["seedream45"],
        )
