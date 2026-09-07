"""Configured Wiro image model contracts."""

from __future__ import annotations

from imagegen.model_registry_base import (
    GenerationTarget,
    ModelParameter,
    ModelPricing,
    ParameterSemanticType,
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
GROK_ASPECT_RATIOS = (
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
    minimum_nonzero: float | None = None,
    multiple_of: float | None = None,
    semantic_type: ParameterSemanticType | None = None,
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
        minimum_nonzero=minimum_nonzero,
        multiple_of=multiple_of,
        semantic_type=semantic_type,
        order=order,
    )


def _pricing(
    price: str,
    title: str,
    *,
    description: str = "Wiro Tool Detail price.",
    pricing_type: str = "per-unit",
    metric: str = "image",
) -> ModelPricing:
    return ModelPricing(
        price=price,
        title=title,
        description=description,
        type=pricing_type,
        metric=metric,
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
    source_binding: SourceImageBinding | None,
    fixed_inputs: dict[str, object],
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
        fixed_inputs=fixed_inputs,
        pricing=pricing,
        source_images=source_binding if edit else None,
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
    source_binding: SourceImageBinding | None = None,
    fixed_inputs: dict[str, object] | None = None,
) -> ProviderModel:
    if source_binding is None:
        source_binding = (
            SourceImageBinding(provider_field="inputImage", max_count=10)
            if alias == "seedream5-pro-uncensored"
            else SourceImageBinding(
                provider_field="inputImage",
                max_count=14,
                max_total=15,
                output_count_parameter="maxImages",
            )
        )
    fixed_inputs = fixed_inputs or {}
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
            source_binding=source_binding,
            fixed_inputs=fixed_inputs,
        ),
        edit_target=_target(
            alias=alias,
            display_name=display_name,
            provider_model=provider_model,
            parameters=edit_parameters,
            edit=True,
            pricing=pricing,
            source_binding=source_binding,
            fixed_inputs=fixed_inputs,
        ),
    )


def _text_only_provider_model(
    *,
    alias: str,
    display_name: str,
    provider_model: str,
    parameters: tuple[ModelParameter, ...],
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
            parameters=parameters,
            edit=False,
            pricing=pricing,
            source_binding=None,
            fixed_inputs={},
        ),
    )


def _z_image_parameters() -> tuple[ModelParameter, ...]:
    return (
        _parameter(
            "prompt",
            "Text prompt for image generation.",
            "string",
            "",
            order=1,
        ),
        _parameter(
            "steps",
            "Number of inference steps.",
            "integer",
            9,
            minimum=1,
            maximum=50,
            order=2,
        ),
        _parameter(
            "scale",
            "Guidance scale.",
            "number",
            0.0,
            minimum=0,
            maximum=20,
            order=3,
        ),
        _parameter(
            "seed",
            "Seed for reproducible generation.",
            "string",
            "0",
            minimum=0,
            maximum=9_999_999_999,
            semantic_type="seed",
            order=4,
        ),
        _parameter(
            "resolution",
            "Output resolution tier.",
            "select",
            "480P",
            choices=("480P", "580P", "720P", "1080P"),
            order=5,
        ),
        _parameter(
            "aspectRatio",
            "Output aspect ratio.",
            "select",
            "1:1",
            choices=("16:9", "9:16", "1:1"),
            order=6,
        ),
    )


def _hidream_parameters(*, steps: int, flow_shift: float) -> tuple[ModelParameter, ...]:
    return (
        _parameter(
            "prompt",
            "Text prompt for image generation.",
            "string",
            "",
            order=1,
        ),
        _parameter(
            "negativePrompt",
            "Negative prompt.",
            "string",
            "",
            order=2,
        ),
        _parameter(
            "steps",
            "Number of inference steps.",
            "integer",
            steps,
            minimum=1,
            maximum=500,
            order=3,
        ),
        _parameter(
            "scale",
            "Guidance scale.",
            "number",
            0,
            minimum=0,
            maximum=20,
            order=4,
        ),
        _parameter(
            "flowShift",
            "Flow shift.",
            "number",
            flow_shift,
            minimum=1,
            maximum=10,
            order=5,
        ),
        _parameter(
            "samples",
            "Number of images to generate.",
            "integer",
            1,
            minimum=1,
            maximum=8,
            order=6,
        ),
        _parameter(
            "seed",
            "Seed for reproducible generation.",
            "string",
            "0",
            minimum=0,
            maximum=9_999_999_999,
            semantic_type="seed",
            order=7,
        ),
        _parameter(
            "width",
            "Output width in pixels.",
            "integer",
            1024,
            minimum=0,
            maximum=2048,
            order=8,
        ),
        _parameter(
            "height",
            "Output height in pixels.",
            "integer",
            1024,
            minimum=0,
            maximum=2048,
            order=9,
        ),
    )


def _grok_parameters(*, edit: bool) -> tuple[ModelParameter, ...]:
    source = (
        (
            _parameter(
                "inputImage",
                "Source image file for image-to-image generation.",
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
            "samples",
            "Number of images to generate.",
            "integer",
            1,
            minimum=1,
            maximum=10,
            order=3 if edit else 2,
        ),
        _parameter(
            "aspectRatio",
            "Output aspect ratio.",
            "select",
            "16:9",
            choices=GROK_ASPECT_RATIOS,
            order=4 if edit else 3,
        ),
        _parameter(
            "resolution",
            "Output resolution tier.",
            "select",
            "1k",
            choices=("1k", "2k"),
            order=5 if edit else 4,
        ),
    )


def _nano_parameters(
    *,
    edit: bool,
    resolution_choices: tuple[object, ...],
    aspect_ratios: tuple[object, ...],
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
            "aspectRatio",
            "Output aspect ratio.",
            "select",
            "1:1",
            choices=aspect_ratios,
            order=3 if edit else 2,
        ),
        _parameter(
            "resolution",
            "Output resolution tier.",
            "select",
            "1K",
            choices=resolution_choices,
            order=4 if edit else 3,
        ),
    )


def _flux_parameters(*, edit: bool) -> tuple[ModelParameter, ...]:
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
            "width",
            "Output width in pixels; 0 matches the input image.",
            "integer",
            1024,
            minimum=0,
            maximum=2048,
            minimum_nonzero=64,
            multiple_of=16,
            order=3 if edit else 2,
        ),
        _parameter(
            "height",
            "Output height in pixels; 0 matches the input image.",
            "integer",
            1024,
            minimum=0,
            maximum=2048,
            minimum_nonzero=64,
            multiple_of=16,
            order=4 if edit else 3,
        ),
        _parameter(
            "seed",
            "Seed for reproducible generation.",
            "integer",
            123,
            minimum=0,
            maximum=9_999_999,
            semantic_type="seed",
            order=5 if edit else 4,
        ),
        _parameter(
            "guidance",
            "Prompt guidance strength.",
            "number",
            4.5,
            minimum=1.5,
            maximum=10,
            order=6 if edit else 5,
        ),
        _parameter(
            "steps",
            "Number of inference steps.",
            "integer",
            50,
            minimum=1,
            maximum=50,
            order=7 if edit else 6,
        ),
        _parameter(
            "outputFormat",
            "Output image format.",
            "select",
            "jpeg",
            choices=("jpeg", "png"),
            order=8 if edit else 7,
        ),
    )


def _gpt_parameters(
    *,
    edit: bool,
    size_name: str,
    size_choices: tuple[object, ...],
    size_default: object,
    background_choices: tuple[object, ...],
    ratio_choices: tuple[object, ...] = (),
    ratio_default: object = "",
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
    fidelity = (
        (
            _parameter(
                "inputFidelity",
                "How closely to preserve source-image details.",
                "select",
                "high",
                choices=("high", "low"),
                order=9,
            ),
        )
        if edit
        else ()
    )
    ratio = (
        (
            _parameter(
                "ratio",
                "Output aspect ratio.",
                "select",
                ratio_default,
                choices=ratio_choices,
                order=4 if edit else 3,
            ),
        )
        if ratio_choices
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
            size_name,
            "Output size or resolution.",
            "select",
            size_default,
            choices=size_choices,
            order=3 if edit else 2,
        ),
        *ratio,
        _parameter(
            "quality",
            "Output quality tier.",
            "select",
            "low",
            choices=("low", "medium", "high"),
            order=(5 if edit else 4) if ratio_choices else (4 if edit else 3),
        ),
        _parameter(
            "background",
            "Output background mode.",
            "select",
            "auto",
            choices=background_choices,
            order=(6 if edit else 5) if ratio_choices else (5 if edit else 4),
        ),
        _parameter(
            "outputFormat",
            "Output image format.",
            "select",
            "jpeg",
            choices=("png", "jpeg", "webp"),
            order=(7 if edit else 6) if ratio_choices else (6 if edit else 5),
        ),
        _parameter(
            "outputCompression",
            "Output compression level.",
            "integer",
            100,
            minimum=0,
            maximum=100,
            order=(8 if edit else 7) if ratio_choices else (7 if edit else 6),
        ),
        _parameter(
            "samples",
            "Number of images to generate.",
            "integer",
            1,
            minimum=1,
            maximum=10,
            order=(9 if edit else 8) if ratio_choices else (8 if edit else 7),
        ),
        *fidelity,
    )


PROVIDER_MODEL = "bytedance/seedream-v5-pro-uncensored"
LITE_PROVIDER_MODEL = "bytedance/seedream-v5-lite-uncensored"
SEEDREAM45_PROVIDER_MODEL = "bytedance/seedream-v4-5-uncensored"
Z_IMAGE_PROVIDER_MODEL = "tongyi-mai/z-image-turbo"
HIDREAM_DEV_PROVIDER_MODEL = "hidreamai/hidream-i1-dev"
HIDREAM_FAST_PROVIDER_MODEL = "hidreamai/hidream-i1-fast"
GROK_PROVIDER_MODEL = "xai/grok-imagine-image"
NANO_BANANA_2_PROVIDER_MODEL = "google/nano-banana-2"
NANO_BANANA_PRO_PROVIDER_MODEL = "google/nano-banana-pro"
FLUX_FLEX_PROVIDER_MODEL = "black-forest-labs/flux-2-flex"
GPT_IMAGE_15_PROVIDER_MODEL = "openai/gpt-image-1-5"
GPT_IMAGE_2_PROVIDER_MODEL = "openai/gpt-image-2"

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
    "z-image-turbo": _text_only_provider_model(
        alias="z-image-turbo",
        display_name="Z-Image Turbo",
        provider_model=Z_IMAGE_PROVIDER_MODEL,
        parameters=_z_image_parameters(),
        pricing=(_pricing("$0.006", "per run"),),
    ),
    "hidream-dev": _text_only_provider_model(
        alias="hidream-dev",
        display_name="HiDream I1 Dev",
        provider_model=HIDREAM_DEV_PROVIDER_MODEL,
        parameters=_hidream_parameters(steps=30, flow_shift=6.0),
        pricing=(),
    ),
    "hidream-fast": _text_only_provider_model(
        alias="hidream-fast",
        display_name="HiDream I1 Fast",
        provider_model=HIDREAM_FAST_PROVIDER_MODEL,
        parameters=_hidream_parameters(steps=20, flow_shift=3.0),
        pricing=(),
    ),
    "grok-imagine": _provider_model(
        alias="grok-imagine",
        display_name="Grok Imagine Image",
        provider_model=GROK_PROVIDER_MODEL,
        text_parameters=_grok_parameters(edit=False),
        edit_parameters=_grok_parameters(edit=True),
        pricing=(_pricing("$0.02", "per output"),),
        source_binding=SourceImageBinding(provider_field="inputImage", max_count=1),
    ),
    "nano-banana-2": _provider_model(
        alias="nano-banana-2",
        display_name="Nano Banana 2",
        provider_model=NANO_BANANA_2_PROVIDER_MODEL,
        text_parameters=_nano_parameters(
            edit=False,
            resolution_choices=("512", "1K", "2K", "4K"),
            aspect_ratios=(
                "Match Input Image",
                "1:1",
                "1:4",
                "1:8",
                "2:3",
                "3:2",
                "3:4",
                "4:1",
                "4:3",
                "4:5",
                "5:4",
                "8:1",
                "9:16",
                "16:9",
                "21:9",
            ),
        ),
        edit_parameters=_nano_parameters(
            edit=True,
            resolution_choices=("512", "1K", "2K", "4K"),
            aspect_ratios=(
                "Match Input Image",
                "1:1",
                "1:4",
                "1:8",
                "2:3",
                "3:2",
                "3:4",
                "4:1",
                "4:3",
                "4:5",
                "5:4",
                "8:1",
                "9:16",
                "16:9",
                "21:9",
            ),
        ),
        pricing=(_pricing("$0.045-$0.151", "price range"),),
        source_binding=SourceImageBinding(provider_field="inputImage", max_count=14),
        fixed_inputs={"safetySetting": "OFF"},
    ),
    "nano-banana-pro": _provider_model(
        alias="nano-banana-pro",
        display_name="Nano Banana Pro",
        provider_model=NANO_BANANA_PRO_PROVIDER_MODEL,
        text_parameters=_nano_parameters(
            edit=False,
            resolution_choices=("1K", "2K", "4K"),
            aspect_ratios=(
                "Match Input Image",
                "1:1",
                "2:3",
                "3:2",
                "3:4",
                "4:3",
                "4:5",
                "5:4",
                "9:16",
                "16:9",
                "21:9",
            ),
        ),
        edit_parameters=_nano_parameters(
            edit=True,
            resolution_choices=("1K", "2K", "4K"),
            aspect_ratios=(
                "Match Input Image",
                "1:1",
                "2:3",
                "3:2",
                "3:4",
                "4:3",
                "4:5",
                "5:4",
                "9:16",
                "16:9",
                "21:9",
            ),
        ),
        pricing=(_pricing("$0.14-$0.24", "price range"),),
        source_binding=SourceImageBinding(provider_field="inputImage", max_count=14),
        fixed_inputs={"safetySetting": "OFF"},
    ),
    "flux-2-flex": _provider_model(
        alias="flux-2-flex",
        display_name="Flux 2 Flex",
        provider_model=FLUX_FLEX_PROVIDER_MODEL,
        text_parameters=_flux_parameters(edit=False),
        edit_parameters=_flux_parameters(edit=True),
        pricing=(
            _pricing(
                "$0.06/MP",
                "from",
                description="Provider pricing varies with input and output megapixels.",
                pricing_type="provider-variable",
                metric="megapixel",
            ),
        ),
        source_binding=SourceImageBinding(provider_field="inputImage", max_count=8),
        fixed_inputs={"safetyTolerance": 5},
    ),
    "gpt-image-15": _provider_model(
        alias="gpt-image-15",
        display_name="GPT Image 1.5",
        provider_model=GPT_IMAGE_15_PROVIDER_MODEL,
        text_parameters=_gpt_parameters(
            edit=False,
            size_name="size",
            size_choices=("auto", "1:1", "3:2", "2:3"),
            size_default="auto",
            background_choices=("auto", "transparent", "opaque"),
        ),
        edit_parameters=_gpt_parameters(
            edit=True,
            size_name="size",
            size_choices=("auto", "1:1", "3:2", "2:3"),
            size_default="auto",
            background_choices=("auto", "transparent", "opaque"),
        ),
        pricing=(
            _pricing(
                "$0.009–$0.200",
                "price range",
                description="Wiro Tool Detail per-run price matrix; provider billing remains authoritative.",
                pricing_type="provider-variable",
                metric="run",
            ),
        ),
        source_binding=SourceImageBinding(provider_field="inputImage", max_count=16),
        fixed_inputs={"moderation": "low"},
    ),
    "gpt-image-2": _provider_model(
        alias="gpt-image-2",
        display_name="GPT Image 2",
        provider_model=GPT_IMAGE_2_PROVIDER_MODEL,
        text_parameters=_gpt_parameters(
            edit=False,
            size_name="resolution",
            size_choices=("1k", "2k", "4k"),
            size_default="1k",
            background_choices=("auto", "opaque"),
            ratio_choices=("1:1", "3:2", "2:3", "4:3", "3:4", "16:9", "9:16"),
            ratio_default="1:1",
        ),
        edit_parameters=_gpt_parameters(
            edit=True,
            size_name="resolution",
            size_choices=("1k", "2k", "4k"),
            size_default="1k",
            background_choices=("auto", "opaque"),
            ratio_choices=("1:1", "3:2", "2:3", "4:3", "3:4", "16:9", "9:16"),
            ratio_default="1:1",
        ),
        pricing=(
            _pricing(
                "$0.003–$0.712",
                "price range",
                description="Wiro Tool Detail per-run price matrix; provider billing remains authoritative.",
                pricing_type="provider-variable",
                metric="run",
            ),
        ),
        source_binding=SourceImageBinding(provider_field="inputImage", max_count=16),
        fixed_inputs={"moderation": "low"},
    ),
}
