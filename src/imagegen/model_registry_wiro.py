"""Configured Wiro image model contracts."""

from __future__ import annotations

from imagegen.model_registry_base import (
    GenerationTarget,
    ModelParameter,
    ModelPricing,
    ParameterType,
    ProviderModel,
    SourceImageBinding,
)

ASPECT_RATIOS = ("1:1", "2:3", "3:2", "3:4", "4:3", "16:9", "9:16", "21:9")
SEEDREAM45_ASPECT_RATIOS = (
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
WATERMARK_CHOICES = ("false", "true")


def _parameter(
    name: str,
    description: str,
    type: ParameterType,
    default: object,
    *,
    choices: tuple[object, ...] = (),
    minimum: float | None = None,
    maximum: float | None = None,
    order: int,
) -> ModelParameter:
    return ModelParameter(
        name=name,
        description=description,
        type=type,
        default=default,
        choices=choices,
        minimum=minimum,
        maximum=maximum,
        order=order,
    )


def _pricing(price: str, title: str) -> ModelPricing:
    return ModelPricing(
        price=price,
        title=title,
        description="Wiro Tool Detail price.",
        type="per-unit",
        metric="image",
        metric_count=1,
        source="provider-api",
    )


def _pro_parameters(*, edit: bool) -> tuple[ModelParameter, ...]:
    source = (
        (
            _parameter(
                "inputImage",
                "Source image files for image-to-image generation.",
                "array",
                "",
                order=2,
            ),
        )
        if edit
        else ()
    )
    return (
        _parameter(
            "prompt",
            "Text prompt for image generation or editing.",
            "string",
            "",
            order=1,
        ),
        *source,
        _parameter(
            "resolution",
            "Output resolution.",
            "select",
            "1k",
            choices=("1k", "2k"),
            order=3 if edit else 2,
        ),
        _parameter(
            "aspectRatio",
            "Output aspect ratio.",
            "select",
            "1:1",
            choices=ASPECT_RATIOS,
            order=4 if edit else 3,
        ),
        _parameter(
            "outputFormat",
            "Output image format.",
            "select",
            "jpeg",
            choices=("jpeg", "png"),
            order=5 if edit else 4,
        ),
        _parameter(
            "watermark",
            "Whether to include a watermark.",
            "select",
            "false",
            choices=WATERMARK_CHOICES,
            order=6 if edit else 5,
        ),
    )


def _lite_parameters(
    *,
    edit: bool,
    resolution_choices: tuple[object, ...] = ("auto", "2k", "3k"),
    aspect_ratios: tuple[object, ...] = ("auto", *ASPECT_RATIOS),
) -> tuple[ModelParameter, ...]:
    source = (
        (
            _parameter(
                "inputImage",
                "Source image files for image-to-image generation.",
                "array",
                "",
                order=2,
            ),
        )
        if edit
        else ()
    )
    return (
        _parameter(
            "prompt",
            "Text prompt for image generation or editing.",
            "string",
            "",
            order=1,
        ),
        *source,
        _parameter(
            "resolution",
            "Output resolution.",
            "select",
            "auto",
            choices=resolution_choices,
            order=3 if edit else 2,
        ),
        _parameter(
            "aspectRatio",
            "Output aspect ratio.",
            "select",
            "auto",
            choices=aspect_ratios,
            order=4 if edit else 3,
        ),
        _parameter(
            "maxImages",
            "Number of images to generate.",
            "integer",
            1,
            minimum=1,
            maximum=15,
            order=5 if edit else 4,
        ),
        _parameter(
            "watermark",
            "Whether to include a watermark.",
            "select",
            "false",
            choices=WATERMARK_CHOICES,
            order=6 if edit else 5,
        ),
    )


def _target(
    *,
    alias: str,
    display_name: str,
    provider_model: str,
    parameters: tuple[ModelParameter, ...],
    edit: bool,
    pricing: tuple[ModelPricing, ...],
) -> GenerationTarget:
    return GenerationTarget(
        provider="wiro",
        alias=alias,
        display_name=display_name,
        provider_model=provider_model,
        documentation_url=f"https://wiro.ai/models/{provider_model}",
        runtime_url=f"https://api.wiro.ai/v1/Run/{provider_model}",
        mode="image-edit" if edit else "text-to-image",
        parameters=parameters,
        fixed_inputs={},
        pricing=pricing,
        source_images=(
            SourceImageBinding(
                provider_field="inputImage",
                max_count=10,
            )
            if edit and alias == "seedream5-pro-uncensored"
            else (
                SourceImageBinding(
                    provider_field="inputImage",
                    max_count=14,
                    max_total=15,
                    output_count_parameter="maxImages",
                )
                if edit
                else None
            )
        ),
        output_shape="image-urls",
    )


def _provider_model(
    *,
    alias: str,
    display_name: str,
    provider_model: str,
    text_parameters: tuple[ModelParameter, ...],
    edit_parameters: tuple[ModelParameter, ...],
    pricing: tuple[ModelPricing, ...],
) -> ProviderModel:
    return ProviderModel(
        provider="wiro",
        alias=alias,
        display_name=display_name,
        text_target=_target(
            alias=alias,
            display_name=display_name,
            provider_model=provider_model,
            parameters=text_parameters,
            edit=False,
            pricing=pricing,
        ),
        edit_target=_target(
            alias=alias,
            display_name=display_name,
            provider_model=provider_model,
            parameters=edit_parameters,
            edit=True,
            pricing=pricing,
        ),
    )


PROVIDER_MODEL = "bytedance/seedream-v5-pro-uncensored"
LITE_PROVIDER_MODEL = "bytedance/seedream-v5-lite-uncensored"
SEEDREAM45_PROVIDER_MODEL = "bytedance/seedream-v4-5-uncensored"

MODEL_REGISTRY: dict[str, ProviderModel] = {
    "seedream5-pro-uncensored": _provider_model(
        alias="seedream5-pro-uncensored",
        display_name="Seedream 5 Pro Uncensored",
        provider_model=PROVIDER_MODEL,
        text_parameters=_pro_parameters(edit=False),
        edit_parameters=_pro_parameters(edit=True),
        pricing=(_pricing("$0.045", "1K"), _pricing("$0.09", "2K")),
    ),
    "seedream5-lite-uncensored": _provider_model(
        alias="seedream5-lite-uncensored",
        display_name="Seedream 5 Lite Uncensored",
        provider_model=LITE_PROVIDER_MODEL,
        text_parameters=_lite_parameters(edit=False),
        edit_parameters=_lite_parameters(edit=True),
        pricing=(_pricing("$0.035", "per output"),),
    ),
    "seedream45-uncensored": _provider_model(
        alias="seedream45-uncensored",
        display_name="Seedream 4.5 Uncensored",
        provider_model=SEEDREAM45_PROVIDER_MODEL,
        text_parameters=_lite_parameters(
            edit=False,
            resolution_choices=("auto", "2k", "4k"),
            aspect_ratios=SEEDREAM45_ASPECT_RATIOS,
        ),
        edit_parameters=_lite_parameters(
            edit=True,
            resolution_choices=("auto", "2k", "4k"),
            aspect_ratios=SEEDREAM45_ASPECT_RATIOS,
        ),
        pricing=(_pricing("$0.04", "per output"),),
    ),
}
