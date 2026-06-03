"""Model registry shape and policy tests.

Behaviors protected:
- Every configured model has a valid registry shape.
- Model parameters expose coherent types, defaults, choices, and bounds.
- Fixed inputs and edit/source-image metadata follow application policy.
"""

import pytest

from imagegen.model_registry import (
    MODEL_REGISTRY,
    RegistryLookupError,
    default_model_for_provider,
    list_models_for_provider,
    list_providers,
    resolve_generation_target,
    resolve_model,
    resolve_model_ref,
)


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


def test_provider_registry_lists_supported_providers():
    providers = {provider.id: provider.display_name for provider in list_providers()}

    assert providers == {
        "replicate": "Replicate",
        "falai": "fal.ai",
    }


def test_provider_model_lists_are_scoped_by_provider():
    replicate_models = list_models_for_provider("replicate")
    falai_models = list_models_for_provider("falai")

    assert {model.alias for model in replicate_models} == set(MODEL_REGISTRY)
    assert "seedream45" in {model.alias for model in replicate_models}
    assert "seedream45" in {model.alias for model in falai_models}
    assert {model.provider for model in replicate_models} == {"replicate"}
    assert {model.provider for model in falai_models} == {"falai"}


def test_duplicate_aliases_resolve_inside_selected_provider():
    replicate = resolve_model("replicate", "seedream45")
    falai = resolve_model("falai", "seedream45")

    assert replicate.alias == falai.alias
    assert replicate.provider == "replicate"
    assert falai.provider == "falai"
    assert replicate.text_target.provider_model == "bytedance/seedream-4.5"
    assert falai.text_target.provider_model == (
        "fal-ai/bytedance/seedream/v4.5/text-to-image"
    )


def test_fully_qualified_and_bare_model_refs_resolve_by_provider():
    assert resolve_model_ref("replicate:seedream45").provider == "replicate"
    assert resolve_model_ref("falai:seedream45").provider == "falai"
    assert (
        resolve_model_ref("seedream45", selected_provider="falai").text_target.provider_model
        == "fal-ai/bytedance/seedream/v4.5/text-to-image"
    )

    with pytest.raises(RegistryLookupError, match="Bare model aliases"):
        resolve_model_ref("seedream45")


def test_generation_target_resolution_keeps_provider_parameters_distinct():
    replicate = resolve_generation_target("replicate", "seedream45", edit_mode=False)
    falai = resolve_generation_target("falai", "seedream45", edit_mode=False)
    replicate_parameters = {parameter.name for parameter in replicate.parameters}
    falai_parameters = {parameter.name for parameter in falai.parameters}

    assert replicate.provider_model == "bytedance/seedream-4.5"
    assert falai.provider_model == "fal-ai/bytedance/seedream/v4.5/text-to-image"
    assert "size" in replicate_parameters
    assert "image_size" not in replicate_parameters
    assert "image_size" in falai_parameters
    assert "size" not in falai_parameters
    assert replicate.fixed_inputs == {"disable_safety_checker": True}
    assert falai.fixed_inputs == {
        "enable_safety_checker": False,
        "sync_mode": False,
    }


def test_falai_edit_target_uses_linked_endpoint_not_selector_duplicate():
    models = list_models_for_provider("falai")
    seedream = resolve_model("falai", "seedream45")
    edit_target = resolve_generation_target("falai", "seedream45", edit_mode=True)
    selectable_endpoint_ids = {model.text_target.provider_model for model in models}

    assert [model.alias for model in models].count("seedream45") == 1
    assert "fal-ai/bytedance/seedream/v4.5/edit" not in selectable_endpoint_ids
    assert seedream.edit_capable
    assert edit_target.provider_model == "fal-ai/bytedance/seedream/v4.5/edit"
    assert edit_target.source_images is not None
    assert edit_target.source_images.provider_field == "image_urls"
    assert edit_target.source_images.max_count == 10


def test_falai_text_mode_resolves_selectable_endpoint():
    target = resolve_generation_target("falai", "seedream45", edit_mode=False)

    assert target.mode == "text-to-image"
    assert target.provider_model == "fal-ai/bytedance/seedream/v4.5/text-to-image"
    assert target.source_images is None


def test_edit_target_resolution_fails_when_provider_model_has_no_edit_endpoint():
    with pytest.raises(RegistryLookupError, match="does not support image edit"):
        resolve_generation_target("falai", "ernie-image", edit_mode=True)


def test_default_model_for_provider_prefers_replicate_default_only_for_replicate():
    assert default_model_for_provider("replicate").alias == "seedream45"
    assert default_model_for_provider("falai").provider == "falai"
