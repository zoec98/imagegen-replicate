from imagegen.model_registry import MODEL_REGISTRY


def test_seedream45_registry_entry_identifies_replicate_model():
    model = MODEL_REGISTRY["seedream45"]

    assert model.replicate_model == "bytedance/seedream-4.5"
    assert model.edit_capable is True
    assert model.fixed_inputs == {"disable_safety_checker": True}
    assert model.documentation_url.endswith("/api/schema")


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
