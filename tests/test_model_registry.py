from imagegen.model_registry import MODEL_REGISTRY


REQUESTED_MODEL_ALIASES = {
    "flux-flex",
    "gpt-image-2",
    "gpt-image-15",
    "grok-imagine",
    "imagen-4",
    "imagen-4-fast",
    "imagen-4-ultra",
    "nano-banana-2",
    "nano-banana-pro",
    "qwen-2512",
    "seedream45",
    "wan-27-pro",
}


def test_registry_contains_requested_models():
    assert REQUESTED_MODEL_ALIASES <= set(MODEL_REGISTRY)


def test_seedream45_registry_entry_identifies_replicate_model():
    model = MODEL_REGISTRY["seedream45"]

    assert model.replicate_model == "bytedance/seedream-4.5"
    assert model.edit_capable is True
    assert model.fixed_inputs == {"disable_safety_checker": True}
    assert model.documentation_url.endswith("/api/schema")


def test_seedream45_registry_entry_has_pricing():
    model = MODEL_REGISTRY["seedream45"]

    assert model.pricing[0].price == "$0.04"
    assert model.pricing[0].title == "per output image"
    assert model.pricing[0].description == "or 25 images for $1"
    assert model.pricing[0].type == "per-unit"
    assert model.pricing[0].metric == "image_output_count"
    assert model.pricing[0].metric_count == 1


def test_seedream45_registry_entry_has_mvp_parameters():
    parameter_names = {
        parameter.name for parameter in MODEL_REGISTRY["seedream45"].parameters
    }

    assert {
        "prompt",
        "image_input",
        "size",
        "aspect_ratio",
        "sequential_image_generation",
        "max_images",
    } <= parameter_names
    assert "disable_safety_checker" not in parameter_names


def test_flux_flex_registry_entry_identifies_replicate_model():
    model = MODEL_REGISTRY["flux-flex"]

    assert model.display_name == "Flux 2 Flex"
    assert model.replicate_model == "black-forest-labs/flux-2-flex"
    assert model.documentation_url == (
        "https://replicate.com/black-forest-labs/flux-2-flex/api/schema"
    )
    assert model.edit_capable is True
    assert model.source_image_parameter == "input_images"
    assert model.source_image_max == 10
    assert model.fixed_inputs == {}


def test_flux_flex_registry_entry_has_pricing():
    model = MODEL_REGISTRY["flux-flex"]

    assert [pricing.metric for pricing in model.pricing] == [
        "image_input_megapixel_count",
        "image_output_megapixel_count",
    ]
    assert all(pricing.price == "$0.06" for pricing in model.pricing)
    assert model.pricing[0].title == "per input image megapixel"
    assert model.pricing[1].title == "per output image megapixel"


def test_flux_flex_registry_entry_has_schema_parameters():
    parameters = {
        parameter.name: parameter
        for parameter in MODEL_REGISTRY["flux-flex"].parameters
    }
    control = MODEL_REGISTRY["flux-flex"].custom_dimensions

    assert {
        "prompt",
        "input_images",
        "aspect_ratio",
        "resolution",
        "width",
        "height",
        "safety_tolerance",
        "seed",
        "prompt_upsampling",
        "steps",
        "guidance",
        "output_format",
        "output_quality",
    } <= set(parameters)
    assert parameters["aspect_ratio"].choices == (
        "match_input_image",
        "custom",
        "1:1",
        "16:9",
        "3:2",
        "2:3",
        "4:5",
        "5:4",
        "9:16",
        "3:4",
        "4:3",
    )
    assert parameters["guidance"].type == "number"
    assert parameters["guidance"].default == 4.5
    assert parameters["seed"].semantic_type == "seed"
    assert control is not None
    assert control.activation_parameter == "aspect_ratio"
    assert control.activation_value == "custom"
    assert control.scale_parameter == "resolution"
    assert control.width_parameter == "width"
    assert control.height_parameter == "height"


def test_requested_model_registry_entries_use_schema_metadata():
    expected = {
        "gpt-image-2": ("openai/gpt-image-2", True, "input_images", 10),
        "gpt-image-15": ("openai/gpt-image-1.5", True, "input_images", 10),
        "nano-banana-2": ("google/nano-banana-2", True, "image_input", 14),
        "nano-banana-pro": ("google/nano-banana-pro", True, "image_input", 14),
        "grok-imagine": ("xai/grok-imagine-image", True, "image", 1),
        "imagen-4-ultra": ("google/imagen-4-ultra", False, None, 14),
        "imagen-4": ("google/imagen-4", False, None, 14),
        "imagen-4-fast": ("google/imagen-4-fast", False, None, 14),
        "wan-27-pro": ("wan-video/wan-2.7-image-pro", True, "images", 9),
        "qwen-2512": ("qwen/qwen-image-2512", True, "image", 1),
    }

    for alias, (
        replicate_model,
        edit_capable,
        source_parameter,
        source_max,
    ) in expected.items():
        model = MODEL_REGISTRY[alias]
        assert model.replicate_model == replicate_model
        assert (
            model.documentation_url
            == f"https://replicate.com/{replicate_model}/api/schema"
        )
        assert model.edit_capable is edit_capable
        assert model.source_image_parameter == source_parameter
        assert model.source_image_max == source_max
        assert model.pricing
        assert model.parameters[0].name == "prompt"


def test_qwen_registry_entry_uses_fixed_safety_checker_and_custom_dimensions():
    model = MODEL_REGISTRY["qwen-2512"]

    assert model.fixed_inputs == {"disable_safety_checker": True}
    assert "disable_safety_checker" not in {
        parameter.name for parameter in model.parameters
    }
    assert model.custom_dimensions is not None
    assert model.custom_dimensions.activation_parameter == "aspect_ratio"
    assert model.custom_dimensions.activation_value == "custom"
    assert model.custom_dimensions.width_parameter == "width"
    assert model.custom_dimensions.height_parameter == "height"
