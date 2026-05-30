from dataclasses import replace

import pytest

from imagegen.model_registry import MODEL_REGISTRY
from imagegen.validation import (
    ValidationError,
    validate_generation_payload,
    validate_model_parameters,
)


def test_validate_generation_payload_accepts_defaults(tmp_path):
    result = validate_generation_payload(
        {"prompt": "a small red house"},
        model=MODEL_REGISTRY["seedream45"],
        output_dir=tmp_path,
    )

    assert result.prompt == "a small red house"
    assert result.parameters == {
        "aspect_ratio": "match_input_image",
        "max_images": 1,
        "sequential_image_generation": "disabled",
        "size": "2K",
    }
    assert result.source_images == []
    assert result.edit_mode is False


def test_validate_generation_payload_preserves_prompt_without_length_limit(tmp_path):
    prompt = "x" * 10_000

    result = validate_generation_payload(
        {"prompt": prompt},
        model=MODEL_REGISTRY["seedream45"],
        output_dir=tmp_path,
    )

    assert result.prompt == prompt


def test_validate_generation_payload_accepts_valid_annotated_prompt(tmp_path):
    prompt = "portrait of (character: zoe blue hair)"

    result = validate_generation_payload(
        {"prompt": prompt},
        model=MODEL_REGISTRY["seedream45"],
        output_dir=tmp_path,
    )

    assert result.prompt == prompt


def test_validate_generation_payload_rejects_blank_prompt(tmp_path):
    with pytest.raises(ValidationError, match="Prompt is required."):
        validate_generation_payload(
            {"prompt": "   "},
            model=MODEL_REGISTRY["seedream45"],
            output_dir=tmp_path,
        )


def test_validate_generation_payload_rejects_invalid_annotated_prompt(tmp_path):
    with pytest.raises(ValidationError, match="missing a closing"):
        validate_generation_payload(
            {"prompt": "portrait of (character: zoe blue hair"},
            model=MODEL_REGISTRY["seedream45"],
            output_dir=tmp_path,
        )


def test_validate_generation_payload_accepts_existing_source_images(tmp_path):
    (tmp_path / "source.png").write_bytes(b"image")

    result = validate_generation_payload(
        {
            "prompt": "edit this",
            "edit_mode": True,
            "source_images": ["source.png"],
        },
        model=MODEL_REGISTRY["seedream45"],
        output_dir=tmp_path,
    )

    assert result.source_images == ["source.png"]
    assert result.edit_mode is True


def test_validate_generation_payload_rejects_invalid_edit_mode(tmp_path):
    with pytest.raises(ValidationError, match="edit_mode must be a boolean."):
        validate_generation_payload(
            {"prompt": "edit this", "edit_mode": "true"},
            model=MODEL_REGISTRY["seedream45"],
            output_dir=tmp_path,
        )


def test_validate_generation_payload_rejects_edit_mode_without_sources(tmp_path):
    with pytest.raises(
        ValidationError,
        match="edit_mode requires at least one source image.",
    ):
        validate_generation_payload(
            {"prompt": "edit this", "edit_mode": True},
            model=MODEL_REGISTRY["seedream45"],
            output_dir=tmp_path,
        )


def test_validate_generation_payload_rejects_sources_outside_edit_mode(tmp_path):
    (tmp_path / "source.png").write_bytes(b"image")

    with pytest.raises(
        ValidationError,
        match="source_images can only be submitted in edit mode.",
    ):
        validate_generation_payload(
            {"prompt": "edit this", "source_images": ["source.png"]},
            model=MODEL_REGISTRY["seedream45"],
            output_dir=tmp_path,
        )


def test_validate_generation_payload_rejects_edit_mode_for_text_only_model(tmp_path):
    text_only_model = replace(MODEL_REGISTRY["seedream45"], edit_capable=False)
    (tmp_path / "source.png").write_bytes(b"image")

    with pytest.raises(
        ValidationError,
        match="This model does not accept edit requests.",
    ):
        validate_generation_payload(
            {
                "prompt": "edit this",
                "edit_mode": True,
                "source_images": ["source.png"],
            },
            model=text_only_model,
            output_dir=tmp_path,
        )


def test_validate_generation_payload_rejects_non_array_source_images(tmp_path):
    with pytest.raises(ValidationError, match="source_images must be an array."):
        validate_generation_payload(
            {"prompt": "edit this", "edit_mode": True, "source_images": "source.png"},
            model=MODEL_REGISTRY["seedream45"],
            output_dir=tmp_path,
        )


def test_validate_generation_payload_rejects_missing_source_image(tmp_path):
    with pytest.raises(ValidationError, match="Source image not found: missing.png."):
        validate_generation_payload(
            {
                "prompt": "edit this",
                "edit_mode": True,
                "source_images": ["missing.png"],
            },
            model=MODEL_REGISTRY["seedream45"],
            output_dir=tmp_path,
        )


def test_validate_generation_payload_rejects_gif_source_image(tmp_path):
    (tmp_path / "source.gif").write_bytes(b"image")

    with pytest.raises(ValidationError, match="Invalid source image filename"):
        validate_generation_payload(
            {
                "prompt": "edit this",
                "edit_mode": True,
                "source_images": ["source.gif"],
            },
            model=MODEL_REGISTRY["seedream45"],
            output_dir=tmp_path,
        )


def test_validate_generation_payload_rejects_unsafe_source_image(tmp_path):
    with pytest.raises(
        ValidationError,
        match=r"Invalid source image filename: ../sample.png.",
    ):
        validate_generation_payload(
            {
                "prompt": "edit this",
                "edit_mode": True,
                "source_images": ["../sample.png"],
            },
            model=MODEL_REGISTRY["seedream45"],
            output_dir=tmp_path,
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
    with pytest.raises(
        ValidationError,
        match="image_input must be submitted as source_images.",
    ):
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


def test_validate_flux_flex_parameters_accepts_defaults_and_numbers():
    result = validate_model_parameters(
        {
            "guidance": "5.5",
            "prompt_upsampling": False,
        },
        model=MODEL_REGISTRY["flux-flex"],
    )

    assert result == {
        "aspect_ratio": "1:1",
        "resolution": "1 MP",
        "safety_tolerance": 2,
        "prompt_upsampling": False,
        "steps": 30,
        "guidance": 5.5,
        "output_format": "webp",
        "output_quality": 80,
    }


def test_validate_flux_flex_parameters_omits_optional_width_height_seed_by_default():
    result = validate_model_parameters({}, model=MODEL_REGISTRY["flux-flex"])

    assert "width" not in result
    assert "height" not in result
    assert "seed" not in result


def test_validate_flux_flex_seed_omits_blank_value():
    result = validate_model_parameters(
        {"seed": ""},
        model=MODEL_REGISTRY["flux-flex"],
    )

    assert "seed" not in result


def test_validate_flux_flex_custom_dimensions_require_width_and_height():
    with pytest.raises(
        ValidationError,
        match="width is required when aspect_ratio is custom.",
    ):
        validate_model_parameters(
            {"aspect_ratio": "custom", "height": 768},
            model=MODEL_REGISTRY["flux-flex"],
        )


def test_validate_flux_flex_custom_dimensions_omit_resolution():
    result = validate_model_parameters(
        {
            "aspect_ratio": "custom",
            "width": "1024",
            "height": 768,
            "resolution": "2 MP",
        },
        model=MODEL_REGISTRY["flux-flex"],
    )

    assert result == {
        "aspect_ratio": "custom",
        "width": 1024,
        "height": 768,
        "safety_tolerance": 2,
        "prompt_upsampling": True,
        "steps": 30,
        "guidance": 4.5,
        "output_format": "webp",
        "output_quality": 80,
    }


def test_validate_flux_flex_rejects_width_height_without_custom_dimensions():
    with pytest.raises(
        ValidationError,
        match="width and height are only allowed when aspect_ratio is custom.",
    ):
        validate_model_parameters(
            {"width": 1024, "height": 768},
            model=MODEL_REGISTRY["flux-flex"],
        )


def test_validate_flux_flex_rejects_seedream_only_parameter():
    with pytest.raises(
        ValidationError,
        match="Unknown parameter: sequential_image_generation.",
    ):
        validate_model_parameters(
            {"sequential_image_generation": "auto"},
            model=MODEL_REGISTRY["flux-flex"],
        )


def test_validate_seedream_rejects_flux_only_parameter():
    with pytest.raises(ValidationError, match="Unknown parameter: guidance."):
        validate_model_parameters(
            {"guidance": 4.5},
            model=MODEL_REGISTRY["seedream45"],
        )


def test_validate_flux_flex_rejects_out_of_range_guidance():
    with pytest.raises(ValidationError, match="guidance must be at most 10."):
        validate_model_parameters(
            {"guidance": 10.5},
            model=MODEL_REGISTRY["flux-flex"],
        )


def test_validate_flux_flex_rejects_source_parameter_in_parameters():
    with pytest.raises(
        ValidationError,
        match="input_images must be submitted as source_images.",
    ):
        validate_model_parameters(
            {"input_images": ["source.png"]},
            model=MODEL_REGISTRY["flux-flex"],
        )


def test_validate_flux_flex_source_images_use_model_limit(tmp_path):
    filenames = []
    for index in range(11):
        filename = f"source-{index}.png"
        (tmp_path / filename).write_bytes(b"image")
        filenames.append(filename)

    with pytest.raises(
        ValidationError,
        match="source_images cannot contain more than 10 files.",
    ):
        validate_generation_payload(
            {"prompt": "edit this", "edit_mode": True, "source_images": filenames},
            model=MODEL_REGISTRY["flux-flex"],
            output_dir=tmp_path,
        )


def test_validate_single_source_image_model_uses_model_limit(tmp_path):
    for filename in ("source-1.png", "source-2.png"):
        (tmp_path / filename).write_bytes(b"image")

    with pytest.raises(
        ValidationError,
        match="source_images cannot contain more than 1 files.",
    ):
        validate_generation_payload(
            {
                "prompt": "edit this",
                "edit_mode": True,
                "source_images": ["source-1.png", "source-2.png"],
            },
            model=MODEL_REGISTRY["qwen-2512"],
            output_dir=tmp_path,
        )


def test_validate_qwen_rejects_source_parameter_in_parameters():
    with pytest.raises(
        ValidationError,
        match="image must be submitted as source_images.",
    ):
        validate_model_parameters(
            {"image": "source.png"},
            model=MODEL_REGISTRY["qwen-2512"],
        )


def test_validate_qwen_custom_dimensions_require_width_and_height():
    with pytest.raises(
        ValidationError,
        match="width is required when aspect_ratio is custom.",
    ):
        validate_model_parameters(
            {"aspect_ratio": "custom"},
            model=MODEL_REGISTRY["qwen-2512"],
        )
