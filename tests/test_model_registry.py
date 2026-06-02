from imagegen.model_registry import MODEL_REGISTRY


VALID_MODES = {"text-to-image", "image-edit"}
VALID_PARAMETER_TYPES = {"array", "boolean", "integer", "number", "select", "string"}


def test_registry_is_not_empty():
    assert MODEL_REGISTRY


def test_every_model_has_required_registry_shape():
    for alias, model in MODEL_REGISTRY.items():
        assert alias == model.alias
        assert model.display_name
        assert "/" in model.replicate_model
        assert model.documentation_url == (
            f"https://replicate.com/{model.replicate_model}/api/schema"
        )
        assert set(model.modes) <= VALID_MODES
        assert model.modes
        assert model.default_width > 0
        assert model.default_height > 0
        assert model.parameters
        assert model.parameters[0].name == "prompt"
        assert model.parameters[0].type == "string"


def test_every_model_parameter_has_useful_shape():
    for model in MODEL_REGISTRY.values():
        seen_names = set()
        for parameter in model.parameters:
            assert parameter.name
            assert parameter.name not in seen_names
            seen_names.add(parameter.name)
            assert parameter.description
            assert parameter.type in VALID_PARAMETER_TYPES
            if parameter.type == "select":
                assert parameter.choices
                assert parameter.default in parameter.choices
            if parameter.type in {"integer", "number"}:
                if parameter.minimum is not None and parameter.maximum is not None:
                    assert parameter.minimum <= parameter.maximum


def test_fixed_inputs_are_not_user_parameters():
    for model in MODEL_REGISTRY.values():
        parameter_names = {parameter.name for parameter in model.parameters}
        assert set(model.fixed_inputs).isdisjoint(parameter_names)


def test_edit_capable_models_declare_source_image_contract():
    for model in MODEL_REGISTRY.values():
        parameter_names = {parameter.name for parameter in model.parameters}
        if model.edit_capable:
            assert "image-edit" in model.modes
            assert model.source_image_parameter
            assert model.source_image_parameter in parameter_names
            assert model.source_image_max >= 1
        else:
            assert model.source_image_parameter is None


def test_custom_dimension_controls_reference_model_parameters():
    for model in MODEL_REGISTRY.values():
        control = model.custom_dimensions
        if control is None:
            continue
        parameter_names = {parameter.name for parameter in model.parameters}
        assert control.activation_parameter in parameter_names
        assert control.width_parameter in parameter_names
        assert control.height_parameter in parameter_names
        if control.scale_parameter:
            assert control.scale_parameter in parameter_names
