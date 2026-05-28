from imagegen.model_registry import MODEL_REGISTRY


def test_seedream45_registry_entry_is_pinned():
    model = MODEL_REGISTRY["seedream45"]

    assert model.replicate_model == "bytedance/seedream-4.5"
    assert (
        model.version
        == "fffbf9ea3e7a8a0738faef42766157b0fed74d4831ddcf1e96344096eb186553"
    )
    assert model.pinned_model.endswith(model.version)


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
