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
            if (
                parameter.type in {"integer", "number"}
                and parameter.minimum is not None
                and parameter.maximum is not None
            ):
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
        "wiro": "Wiro",
    }


def test_provider_model_lists_are_scoped_by_provider():
    replicate_models = list_models_for_provider("replicate")
    falai_models = list_models_for_provider("falai")
    falai_aliases = {model.alias for model in falai_models}

    assert {model.alias for model in replicate_models} == set(MODEL_REGISTRY)
    assert "seedream45" in {model.alias for model in replicate_models}
    assert {
        "bria-fibo",
        "flux-2",
        "flux-2-pro",
        "flux-2-realism",
        "gpt-image-2",
        "gpt-image-25-flare",
        "gpt-image-25-sunburst",
        "gpt-image15",
        "grok",
        "hidream-dev",
        "hidream-fast",
        "hidream-full",
        "krea-2-large",
        "krea-2-medium",
        "krea-2-turbo",
        "nano-banana-2",
        "seedream",
        "seedream45",
        "seedream5",
        "seedream5-pro",
        "zit",
    } <= falai_aliases
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


def test_model_display_name_resolves_case_insensitively_within_provider():
    model = resolve_model_ref(
        "sEeDrEaM 4.5",
        selected_provider="falai",
    )

    assert model.alias == "seedream45"
    assert model.provider == "falai"


def test_selectable_model_aliases_and_display_names_are_unique_per_provider():
    for provider in list_providers():
        models = list_models_for_provider(provider.id)
        assert len({model.alias for model in models}) == len(models)
        display_names = {model.display_name.casefold() for model in models}
        assert len(display_names) == len(models)


def test_replicate_seedream5_models_expose_supported_inputs_only():
    lite = resolve_model("replicate", "seedream5")
    pro = resolve_model("replicate", "seedream5-pro")

    assert lite.text_target.provider_model == "bytedance/seedream-5-lite"
    assert lite.edit_target is not None
    assert lite.edit_target.source_images is not None
    assert lite.edit_target.source_images.max_count == 14
    assert pro.text_target.provider_model == "bytedance/seedream-5-pro"
    assert pro.edit_target is not None
    assert pro.edit_target.source_images is not None
    assert pro.edit_target.source_images.max_count == 10

    for target in (lite.text_target, pro.text_target):
        names = [parameter.name for parameter in target.parameters]
        output_format = next(
            parameter
            for parameter in target.parameters
            if parameter.name == "output_format"
        )
        assert "return_byteplus_urls" not in names
        assert "layer_decomposition" not in names
        assert output_format.default == "jpeg"
        assert output_format.choices == ("jpeg",)

    assert [parameter.name for parameter in pro.text_target.parameters] == [
        "prompt",
        "image_input",
        "size",
        "aspect_ratio",
        "output_format",
    ]


def test_fully_qualified_and_bare_model_refs_resolve_by_provider():
    assert resolve_model_ref("replicate:seedream45").provider == "replicate"
    assert resolve_model_ref("falai:seedream45").provider == "falai"
    assert (
        resolve_model_ref(
            "seedream45", selected_provider="falai"
        ).text_target.provider_model
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


def test_wiro_registry_contains_distinct_uncensored_seedream_contracts():
    models = list_models_for_provider("wiro")
    assert {model.alias for model in models} == {
        "seedream5-pro-uncensored",
        "seedream5-lite-uncensored",
        "seedream45-uncensored",
        "z-image-turbo",
        "hidream-dev",
        "hidream-fast",
        "grok-imagine",
        "nano-banana-2",
        "nano-banana-pro",
        "flux-2-flex",
        "gpt-image-15",
        "gpt-image-2",
    }
    assert all(
        "Uncensored" in model.display_name
        for model in models
        if model.alias
        in {
            "seedream5-pro-uncensored",
            "seedream5-lite-uncensored",
            "seedream45-uncensored",
        }
    )
    assert {model.provider for model in models} == {"wiro"}

    pro = resolve_model("wiro", "seedream5-pro-uncensored")
    assert pro.text_target.provider_model == "bytedance/seedream-v5-pro-uncensored"
    assert pro.edit_target is not None
    assert pro.edit_target.source_images is not None
    assert pro.edit_target.source_images.provider_field == "inputImage"
    assert pro.edit_target.source_images.max_count == 10
    assert [parameter.name for parameter in pro.text_target.parameters] == [
        "prompt",
        "resolution",
        "aspectRatio",
        "outputFormat",
        "watermark",
    ]
    assert pro.text_target.parameters[1].choices == ("1k", "2k")
    assert pro.text_target.parameters[3].default == "jpeg"
    assert pro.text_target.parameters[-1].choices == ("false", "true")
    assert {price.price for price in pro.text_target.pricing} == {"$0.045", "$0.09"}
    assert all(price.source == "provider-api" for price in pro.text_target.pricing)

    lite = resolve_model("wiro", "seedream5-lite-uncensored")
    assert lite.text_target.provider_model == "bytedance/seedream-v5-lite-uncensored"
    assert lite.edit_target is not None
    assert lite.edit_target.source_images is not None
    assert lite.edit_target.source_images.max_count == 14
    assert lite.edit_target.source_images.max_total == 15
    assert lite.edit_target.source_images.output_count_parameter == "maxImages"
    assert (
        next(
            parameter
            for parameter in lite.text_target.parameters
            if parameter.name == "watermark"
        ).default
        == "false"
    )
    assert resolve_model_ref("wiro:Seedream 5 Lite Uncensored").alias == (
        "seedream5-lite-uncensored"
    )


def test_wiro_registry_contains_seedream45_uncensored_contract():
    model = resolve_model("wiro", "seedream45-uncensored")

    assert model.display_name == "Seedream 4.5 Uncensored"
    assert model.text_target.provider_model == "bytedance/seedream-v4-5-uncensored"
    assert model.text_target.mode == "text-to-image"
    assert model.edit_target is not None
    assert model.edit_target.mode == "image-edit"
    assert model.edit_target.source_images is not None
    assert model.edit_target.source_images.provider_field == "inputImage"
    assert model.edit_target.source_images.max_count == 14
    assert model.edit_target.source_images.max_total == 15
    assert model.edit_target.source_images.output_count_parameter == "maxImages"

    parameters = {
        parameter.name: parameter for parameter in model.text_target.parameters
    }
    assert parameters["resolution"].default == "auto"
    assert parameters["resolution"].choices == ("auto", "2k", "4k")
    assert parameters["aspectRatio"].choices == (
        "auto",
        "1:1",
        "2:3",
        "3:2",
        "3:4",
        "4:3",
        "4:5",
        "5:4",
        "16:9",
        "9:16",
        "21:9",
        "9:21",
    )
    assert parameters["aspectRatio"].default == "auto"
    assert parameters["maxImages"].default == 1
    assert parameters["maxImages"].minimum == 1
    assert parameters["maxImages"].maximum == 15
    assert parameters["watermark"].default == "false"
    assert parameters["watermark"].choices == ("false", "true")
    assert {price.price for price in model.text_target.pricing} == {"$0.04"}


def test_wiro_registry_contains_z_image_turbo_text_contract():
    model = resolve_model("wiro", "z-image-turbo")

    assert model.display_name == "Z-Image Turbo"
    assert model.text_target.provider_model == "tongyi-mai/z-image-turbo"
    assert model.edit_target is None
    parameters = {
        parameter.name: parameter for parameter in model.text_target.parameters
    }
    assert parameters["prompt"].type == "string"
    assert parameters["steps"].default == 9
    assert parameters["steps"].minimum == 1
    assert parameters["steps"].maximum == 50
    assert parameters["scale"].default == 0.0
    assert parameters["scale"].minimum == 0
    assert parameters["scale"].maximum == 20
    assert parameters["seed"].type == "string"
    assert parameters["seed"].semantic_type == "seed"
    assert parameters["seed"].default == "0"
    assert parameters["seed"].minimum == 0
    assert parameters["seed"].maximum == 9_999_999_999
    assert parameters["resolution"].choices == ("480P", "580P", "720P", "1080P")
    assert parameters["resolution"].default == "480P"
    assert parameters["aspectRatio"].choices == ("16:9", "9:16", "1:1")
    assert parameters["aspectRatio"].default == "1:1"
    assert {price.price for price in model.text_target.pricing} == {"$0.006"}


def test_wiro_registry_contains_hidream_text_variants():
    expected = {
        "hidream-dev": ("hidreamai/hidream-i1-dev", 30, 6.0),
        "hidream-fast": ("hidreamai/hidream-i1-fast", 20, 3.0),
    }

    for alias, (provider_model, steps, flow_shift) in expected.items():
        model = resolve_model("wiro", alias)
        assert model.edit_target is None
        assert model.text_target.provider_model == provider_model
        parameters = {
            parameter.name: parameter for parameter in model.text_target.parameters
        }
        assert parameters["negativePrompt"].type == "string"
        assert parameters["steps"].default == steps
        assert parameters["steps"].minimum == 1
        assert parameters["steps"].maximum == 500
        assert parameters["scale"].default == 0
        assert parameters["scale"].minimum == 0
        assert parameters["scale"].maximum == 20
        assert parameters["flowShift"].default == flow_shift
        assert parameters["flowShift"].minimum == 1
        assert parameters["flowShift"].maximum == 10
        assert parameters["samples"].default == 1
        assert parameters["samples"].minimum == 1
        assert parameters["samples"].maximum == 8
        assert parameters["seed"].default == "0"
        assert parameters["seed"].semantic_type == "seed"
        assert parameters["width"].default == 1024
        assert parameters["height"].default == 1024
        assert model.text_target.pricing == ()


def test_wiro_registry_contains_grok_imagine_contract():
    model = resolve_model("wiro", "grok-imagine")

    assert model.display_name == "Grok Imagine Image"
    assert model.text_target.provider_model == "xai/grok-imagine-image"
    assert model.edit_target is not None
    assert model.edit_target.source_images is not None
    assert model.edit_target.source_images.provider_field == "inputImage"
    assert model.edit_target.source_images.max_count == 1
    assert model.edit_target.source_images.max_total is None
    parameters = {
        parameter.name: parameter for parameter in model.text_target.parameters
    }
    assert parameters["samples"].default == 1
    assert parameters["samples"].minimum == 1
    assert parameters["samples"].maximum == 10
    assert parameters["aspectRatio"].default == "16:9"
    assert parameters["aspectRatio"].choices == (
        "16:9",
        "9:16",
        "1:1",
        "4:3",
        "3:4",
        "3:2",
        "2:3",
        "2:1",
        "1:2",
        "19.5:9",
        "9:19.5",
        "20:9",
        "9:20",
    )
    assert parameters["resolution"].choices == ("1k", "2k")
    assert parameters["resolution"].default == "1k"
    assert {price.price for price in model.text_target.pricing} == {"$0.02"}


def test_wiro_registry_contains_nano_banana_variants_with_fixed_safety():
    expected = {
        "nano-banana-2": (
            "google/nano-banana-2",
            ("512", "1K", "2K", "4K"),
            "1K",
            "$0.045-$0.151",
        ),
        "nano-banana-pro": (
            "google/nano-banana-pro",
            ("1K", "2K", "4K"),
            "1K",
            "$0.14-$0.24",
        ),
    }

    for alias, (
        provider_model,
        resolutions,
        resolution_default,
        price,
    ) in expected.items():
        model = resolve_model("wiro", alias)
        assert model.text_target.provider_model == provider_model
        assert model.edit_target is not None
        assert model.edit_target.source_images is not None
        assert model.edit_target.source_images.provider_field == "inputImage"
        assert model.edit_target.source_images.max_count == 14
        assert model.edit_target.source_images.max_total is None
        assert model.text_target.fixed_inputs == {"safetySetting": "OFF"}
        assert model.edit_target.fixed_inputs == {"safetySetting": "OFF"}
        parameters = {
            parameter.name: parameter for parameter in model.text_target.parameters
        }
        assert "safetySetting" not in parameters
        assert parameters["resolution"].choices == resolutions
        assert parameters["resolution"].default == resolution_default
        assert {price_entry.price for price_entry in model.text_target.pricing} == {
            price
        }


def test_wiro_registry_contains_flux_flex_contract():
    model = resolve_model("wiro", "flux-2-flex")

    assert model.display_name == "Flux 2 Flex"
    assert model.text_target.provider_model == "black-forest-labs/flux-2-flex"
    assert model.edit_target is not None
    assert model.edit_target.source_images is not None
    assert model.edit_target.source_images.provider_field == "inputImage"
    assert model.edit_target.source_images.max_count == 8
    assert model.text_target.fixed_inputs == {"safetyTolerance": 5}
    assert model.edit_target.fixed_inputs == {"safetyTolerance": 5}
    parameters = {
        parameter.name: parameter for parameter in model.text_target.parameters
    }
    assert "safetyTolerance" not in parameters
    for name in ("width", "height"):
        assert parameters[name].default == 1024
        assert parameters[name].minimum == 0
        assert parameters[name].maximum == 2048
        assert parameters[name].minimum_nonzero == 64
        assert parameters[name].multiple_of == 16
    assert parameters["outputFormat"].default == "jpeg"
    assert parameters["outputFormat"].choices == ("jpeg", "png")
    assert {price.price for price in model.text_target.pricing} == {"$0.06/MP"}


def test_wiro_registry_contains_gpt_image_variants_with_fixed_moderation():
    expected = {
        "gpt-image-15": (
            "openai/gpt-image-1-5",
            ("auto", "1:1", "3:2", "2:3"),
            "auto",
            ("auto", "transparent", "opaque"),
            "$0.009–$0.200",
        ),
        "gpt-image-2": (
            "openai/gpt-image-2",
            ("1k", "2k", "4k"),
            "1k",
            ("auto", "opaque"),
            "$0.003–$0.712",
        ),
    }

    for alias, (
        provider_model,
        size_choices,
        size_default,
        background_choices,
        price,
    ) in expected.items():
        model = resolve_model("wiro", alias)
        assert model.text_target.provider_model == provider_model
        assert model.edit_target is not None
        assert model.edit_target.source_images is not None
        assert model.edit_target.source_images.provider_field == "inputImage"
        assert model.edit_target.source_images.max_count == 16
        assert model.text_target.fixed_inputs == {"moderation": "low"}
        assert model.edit_target.fixed_inputs == {"moderation": "low"}
        parameters = {
            parameter.name: parameter for parameter in model.text_target.parameters
        }
        assert "inputImageMask" not in parameters
        assert parameters["quality"].choices == ("low", "medium", "high")
        assert parameters["quality"].default == "low"
        size_name = "size" if alias == "gpt-image-15" else "resolution"
        assert parameters[size_name].choices == size_choices
        assert parameters[size_name].default == size_default
        assert parameters["background"].choices == background_choices
        if alias == "gpt-image-2":
            assert parameters["ratio"].default == "1:1"
            assert parameters["ratio"].choices == (
                "1:1",
                "3:2",
                "2:3",
                "4:3",
                "3:4",
                "16:9",
                "9:16",
            )
        assert parameters["outputFormat"].default == "jpeg"
        assert parameters["outputFormat"].choices == ("png", "jpeg", "webp")
        assert parameters["outputCompression"].minimum == 0
        assert parameters["outputCompression"].maximum == 100
        assert parameters["samples"].minimum == 1
        assert parameters["samples"].maximum == 10
        assert {price_entry.price for price_entry in model.text_target.pricing} == {
            price
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


@pytest.mark.parametrize("variant", ["flare", "sunburst"])
def test_falai_gpt_image25_variants_contract(variant):
    model = resolve_model("falai", f"gpt-image-25-{variant}")
    text_parameters = {
        parameter.name: parameter for parameter in model.text_target.parameters
    }
    edit_parameters = {
        parameter.name: parameter for parameter in model.edit_target.parameters
    }

    assert model.text_target.provider_model == (
        f"openai/gpt-image-2.5/{variant}/text-to-image"
    )
    assert model.edit_target.provider_model == f"openai/gpt-image-2.5/{variant}/edit"
    assert model.text_target.fixed_inputs == {"sync_mode": False}
    assert model.edit_target.fixed_inputs == {"sync_mode": False}
    assert model.edit_target.source_images is not None
    assert model.edit_target.source_images.provider_field == "image_urls"
    assert model.edit_target.source_images.max_count == 16
    assert "image_urls" not in edit_parameters
    assert "mask_url" not in text_parameters
    assert "mask_url" in edit_parameters
    assert text_parameters["image_size"].default == "landscape_4_3"
    assert edit_parameters["image_size"].default == "auto"
    assert text_parameters["quality"].choices == (
        "auto",
        "low",
        "medium",
        "high",
        "xhigh",
        "max",
    )
    assert text_parameters["num_images"].maximum == 10
    assert text_parameters["output_format"].default == "jpeg"
    assert text_parameters["output_compression"].minimum == 0
    assert text_parameters["output_compression"].maximum == 100


def test_falai_plan_ticket_models_use_linked_edit_endpoints():
    models = list_models_for_provider("falai")
    selectable_endpoint_ids = {model.text_target.provider_model for model in models}

    expected = {
        "flux-2": ("fal-ai/flux-2/edit", "image_urls", 4),
        "flux-2-pro": ("fal-ai/flux-2-pro/edit", "image_urls", 10),
        "gpt-image-2": ("openai/gpt-image-2/edit", "image_urls", 10),
        "gpt-image-25-flare": (
            "openai/gpt-image-2.5/flare/edit",
            "image_urls",
            16,
        ),
        "gpt-image-25-sunburst": (
            "openai/gpt-image-2.5/sunburst/edit",
            "image_urls",
            16,
        ),
        "gpt-image15": ("fal-ai/gpt-image-1.5/edit", "image_urls", 10),
        "grok": ("xai/grok-imagine-image/edit", "image_urls", 3),
        "krea-2-turbo": ("fal-ai/krea-2/turbo/style", "reference_image_urls", 3),
        "nano-banana-2": ("fal-ai/nano-banana-2/edit", "image_urls", 10),
        "seedream": ("fal-ai/bytedance/seedream/v4/edit", "image_urls", 10),
        "seedream5": (
            "fal-ai/bytedance/seedream/v5/lite/edit",
            "image_urls",
            10,
        ),
        "seedream5-pro": (
            "bytedance/seedream/v5/pro/edit",
            "image_urls",
            10,
        ),
        "zit": ("fal-ai/z-image/turbo/image-to-image", "image_url", 1),
    }
    for alias, (provider_model, source_field, max_count) in expected.items():
        target = resolve_generation_target("falai", alias, edit_mode=True)
        assert provider_model not in selectable_endpoint_ids
        assert target.provider_model == provider_model
        assert target.source_images is not None
        assert target.source_images.provider_field == source_field
        assert target.source_images.max_count == max_count


def test_falai_krea_models_use_documented_text_endpoints():
    expected = {
        "krea-2-turbo": {
            "provider_model": "fal-ai/krea-2/turbo",
            "parameters": {
                "prompt",
                "seed",
                "image_size",
                "num_images",
                "acceleration",
                "enable_prompt_expansion",
                "output_format",
            },
            "fixed_inputs": {
                "enable_safety_checker": False,
                "sync_mode": False,
            },
        },
        "krea-2-large": {
            "provider_model": "krea/v2/large/text-to-image",
            "parameters": {"prompt", "aspect_ratio", "creativity", "seed"},
            "fixed_inputs": {},
        },
        "krea-2-medium": {
            "provider_model": "krea/v2/medium/text-to-image",
            "parameters": {"prompt", "aspect_ratio", "creativity", "seed"},
            "fixed_inputs": {},
        },
    }

    for alias, expectation in expected.items():
        target = resolve_generation_target("falai", alias, edit_mode=False)
        parameter_names = {parameter.name for parameter in target.parameters}

        assert target.provider_model == expectation["provider_model"]
        assert parameter_names == expectation["parameters"]
        assert target.fixed_inputs == expectation["fixed_inputs"]
        if alias == "krea-2-turbo":
            prompt_expansion = next(
                parameter
                for parameter in target.parameters
                if parameter.name == "enable_prompt_expansion"
            )
            assert prompt_expansion.default is False


def test_falai_krea_turbo_style_model_uses_source_images_for_reference_urls():
    target = resolve_generation_target("falai", "krea-2-turbo", edit_mode=True)
    parameter_names = {parameter.name for parameter in target.parameters}
    prompt_expansion = next(
        parameter
        for parameter in target.parameters
        if parameter.name == "enable_prompt_expansion"
    )

    assert target.provider_model == "fal-ai/krea-2/turbo/style"
    assert target.mode == "image-edit"
    assert "reference_image_urls" not in parameter_names
    assert "style_scale" in parameter_names
    assert prompt_expansion.default is False
    assert target.fixed_inputs == {
        "enable_safety_checker": False,
        "sync_mode": False,
    }
    assert target.source_images is not None
    assert target.source_images.provider_field == "reference_image_urls"
    assert target.source_images.max_count == 3


def test_falai_models_keep_safety_checker_fixed_when_supported():
    for alias in (
        "flux-2",
        "flux-2-pro",
        "flux-2-realism",
        "hidream-dev",
        "hidream-fast",
        "hidream-full",
        "krea-2-turbo",
        "seedream",
        "seedream5",
        "seedream5-pro",
        "zit",
    ):
        target = resolve_generation_target("falai", alias, edit_mode=False)
        assert target.fixed_inputs["enable_safety_checker"] is False


def test_falai_seedream5_pro_uses_documented_endpoints_and_parameters():
    text_target = resolve_generation_target("falai", "seedream5-pro", edit_mode=False)
    edit_target = resolve_generation_target("falai", "seedream5-pro", edit_mode=True)
    parameter_names = {parameter.name for parameter in text_target.parameters}
    image_size = next(
        parameter
        for parameter in text_target.parameters
        if parameter.name == "image_size"
    )

    assert text_target.provider_model == "bytedance/seedream/v5/pro/text-to-image"
    assert edit_target.provider_model == "bytedance/seedream/v5/pro/edit"
    assert parameter_names == {"prompt", "image_size", "num_images", "output_format"}
    assert image_size.default == "auto_2K"
    assert image_size.choices == (
        "square_hd",
        "square",
        "portrait_4_3",
        "portrait_16_9",
        "landscape_4_3",
        "landscape_16_9",
        "auto_1K",
        "auto_2K",
    )
    assert text_target.fixed_inputs == {
        "enable_safety_checker": False,
        "sync_mode": False,
    }
    assert edit_target.source_images is not None
    assert edit_target.source_images.provider_field == "image_urls"
    assert edit_target.source_images.max_count == 10


def test_falai_models_do_not_expose_byteplus_url_outputs():
    for model in list_models_for_provider("falai"):
        targets = [model.text_target]
        if model.edit_target is not None:
            targets.append(model.edit_target)
        for target in targets:
            parameter_names = {parameter.name for parameter in target.parameters}
            assert "return_byteplus_urls" not in parameter_names


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
