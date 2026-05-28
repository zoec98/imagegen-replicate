from imagegen.model_registry import MODEL_REGISTRY


def test_seedream45_registry_entry_is_pinned():
    model = MODEL_REGISTRY["seedream45"]

    assert model.replicate_model == "bytedance/seedream-4.5"
    assert model.edit_capable is True
    assert model.fixed_inputs == {"disable_safety_checker": True}
    assert (
        model.version
        == "bd4492f8492cc564460074e069bff1d55428cf48286f0a0f4a4a39b50f088ff6"
    )
    assert model.pinned_model.endswith(model.version)
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
