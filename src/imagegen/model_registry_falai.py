"""Configured fal.ai models for imagegen."""

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


def _param(
    name: str,
    description: str,
    type: ParameterType,
    default: object = "",
    *,
    choices: tuple[object, ...] = (),
    minimum: float | int | None = None,
    maximum: float | int | None = None,
    order: int | None = None,
    semantic_type: ParameterSemanticType | None = None,
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
        semantic_type=semantic_type,
    )


def _falai_price(
    price: str,
    title: str,
    *,
    metric: str,
    description: str = "",
) -> ModelPricing:
    return ModelPricing(
        price=price,
        title=title,
        description=description,
        type="per-unit",
        metric=metric,
        metric_count=1,
        source="provider-api",
    )


IMAGE_SIZE_CHOICES = (
    "square_hd",
    "square",
    "portrait_4_3",
    "portrait_16_9",
    "landscape_4_3",
    "landscape_16_9",
)

ERNIE_IMAGE_SIZE_CHOICES = (
    *IMAGE_SIZE_CHOICES,
    "square_uhd",
    "portrait_3_2",
    "landscape_3_2",
    "portrait_hd",
    "landscape_hd",
)

SEEDREAM45_IMAGE_SIZE_CHOICES = (*IMAGE_SIZE_CHOICES, "auto_2K", "auto_4K")
SEEDREAM4_IMAGE_SIZE_CHOICES = (*IMAGE_SIZE_CHOICES, "auto", "auto_2K", "auto_4K")
SEEDREAM5_IMAGE_SIZE_CHOICES = (*IMAGE_SIZE_CHOICES, "auto_2K", "auto_3K", "auto_4K")
AUTO_IMAGE_SIZE_CHOICES = (*IMAGE_SIZE_CHOICES, "auto")
OUTPUT_FORMAT_CHOICES = ("jpeg", "png")
EXTENDED_OUTPUT_FORMAT_CHOICES = ("jpeg", "png", "webp")
SAFETY_TOLERANCE_CHOICES = ("1", "2", "3", "4", "5")
SAFETY_TOLERANCE_6_CHOICES = (*SAFETY_TOLERANCE_CHOICES, "6")
GPT_IMAGE15_SIZE_CHOICES = ("1024x1024", "1536x1024", "1024x1536")
GPT_IMAGE15_EDIT_SIZE_CHOICES = ("auto", *GPT_IMAGE15_SIZE_CHOICES)
NANO_BANANA_ASPECT_RATIO_CHOICES = (
    "auto",
    "21:9",
    "16:9",
    "3:2",
    "4:3",
    "5:4",
    "1:1",
    "4:5",
    "3:4",
    "2:3",
    "9:16",
    "4:1",
    "1:4",
    "8:1",
    "1:8",
)
GROK_ASPECT_RATIO_CHOICES = (
    "2:1",
    "20:9",
    "19.5:9",
    "16:9",
    "4:3",
    "3:2",
    "1:1",
    "2:3",
    "3:4",
    "9:16",
    "9:19.5",
    "9:20",
    "1:2",
)
GROK_EDIT_ASPECT_RATIO_CHOICES = ("auto", *GROK_ASPECT_RATIO_CHOICES)

BRIA_ASPECT_RATIO_CHOICES = (
    "1:1",
    "2:3",
    "3:2",
    "3:4",
    "4:3",
    "4:5",
    "5:4",
    "9:16",
    "16:9",
)

FALAI_FIXED_IMAGE_OUTPUT_INPUTS = {"sync_mode": False}
FALAI_FIXED_SAFE_IMAGE_INPUTS = {
    **FALAI_FIXED_IMAGE_OUTPUT_INPUTS,
    "enable_safety_checker": False,
}
FALAI_FIXED_SAFE_NO_PROMPT_EXPANSION_INPUTS = {
    **FALAI_FIXED_SAFE_IMAGE_INPUTS,
    "enable_prompt_expansion": False,
}


def _ernie_parameters(*, turbo: bool) -> tuple[ModelParameter, ...]:
    return (
        _param(
            "prompt",
            "Text prompt for image generation. Supports English, Chinese, and Japanese.",
            "string",
            order=1,
        ),
        _param(
            "image_size",
            "The size of the generated image.",
            "select",
            "square_hd",
            choices=ERNIE_IMAGE_SIZE_CHOICES,
            order=2,
        ),
        _param(
            "num_inference_steps",
            "Number of denoising steps.",
            "integer",
            8 if turbo else 50,
            minimum=1,
            maximum=20 if turbo else 100,
            order=3,
        ),
        _param(
            "guidance_scale",
            "Classifier-free guidance scale.",
            "number",
            1 if turbo else 5,
            minimum=1,
            maximum=20,
            order=4,
        ),
        _param(
            "seed",
            "Random seed for reproducibility.",
            "integer",
            "",
            order=5,
            semantic_type="seed",
        ),
        _param(
            "num_images",
            "Number of images to generate.",
            "integer",
            1,
            minimum=1,
            maximum=4,
            order=6,
        ),
        _param(
            "output_format",
            "Output image format.",
            "select",
            "jpeg",
            choices=("jpeg", "png"),
            order=10,
        ),
        _param(
            "acceleration",
            "The acceleration level to use for image generation.",
            "select",
            "regular",
            choices=("none", "regular", "high"),
            order=12,
        ),
    )


def _seedream45_parameters() -> tuple[ModelParameter, ...]:
    return (
        _param(
            "prompt",
            "The text prompt used to generate or edit the image.",
            "string",
            order=1,
        ),
        _param(
            "image_size",
            "The size of the generated image.",
            "select",
            "portrait_4_3",
            choices=SEEDREAM45_IMAGE_SIZE_CHOICES,
            order=2,
        ),
        _param(
            "num_images",
            "Number of separate model generations to run with the prompt.",
            "integer",
            1,
            minimum=1,
            maximum=6,
            order=3,
        ),
        _param(
            "max_images",
            "Maximum images to return for each generation.",
            "integer",
            1,
            minimum=1,
            maximum=6,
            order=4,
        ),
        _param(
            "seed",
            "Random seed for reproducibility.",
            "integer",
            "",
            order=5,
            semantic_type="seed",
        ),
    )


def _seedream_parameters(
    *,
    image_size_default: str,
    image_size_choices: tuple[object, ...],
    include_seed: bool,
    include_enhance_prompt_mode: bool = False,
) -> tuple[ModelParameter, ...]:
    parameters = [
        _param(
            "prompt",
            "The text prompt used to generate or edit the image.",
            "string",
            order=1,
        ),
        _param(
            "image_size",
            "The size of the generated image.",
            "select",
            image_size_default,
            choices=image_size_choices,
            order=2,
        ),
        _param(
            "num_images",
            "Number of separate model generations to run with the prompt.",
            "integer",
            1,
            minimum=1,
            maximum=6,
            order=3,
        ),
        _param(
            "max_images",
            "Maximum images to return for each generation.",
            "integer",
            1,
            minimum=1,
            maximum=6,
            order=4,
        ),
    ]
    if include_seed:
        parameters.append(
            _param(
                "seed",
                "Random seed for reproducibility.",
                "integer",
                "",
                order=5,
                semantic_type="seed",
            )
        )
    if include_enhance_prompt_mode:
        parameters.append(
            _param(
                "enhance_prompt_mode",
                "Prompt enhancement mode.",
                "select",
                "standard",
                choices=("standard", "fast"),
                order=8,
            )
        )
    return tuple(sorted(parameters, key=lambda item: item.order or 999))


def _nano_banana_2_parameters() -> tuple[ModelParameter, ...]:
    return (
        _param(
            "prompt",
            "The text prompt to generate or edit the image.",
            "string",
            order=1,
        ),
        _param(
            "num_images",
            "The number of images to generate.",
            "integer",
            1,
            minimum=1,
            maximum=4,
            order=2,
        ),
        _param(
            "seed",
            "Random seed for reproducibility.",
            "integer",
            "",
            order=3,
            semantic_type="seed",
        ),
        _param(
            "aspect_ratio",
            "The aspect ratio of the generated image.",
            "select",
            "auto",
            choices=NANO_BANANA_ASPECT_RATIO_CHOICES,
            order=4,
        ),
        _param(
            "output_format",
            "The format of the generated image.",
            "select",
            "jpeg",
            choices=EXTENDED_OUTPUT_FORMAT_CHOICES,
            order=5,
        ),
        _param(
            "safety_tolerance",
            "Safety tolerance level for content moderation.",
            "select",
            "6",
            choices=SAFETY_TOLERANCE_6_CHOICES,
            order=6,
        ),
        _param("system_prompt", "Optional system instruction.", "string", order=8),
        _param(
            "resolution",
            "The resolution of the image to generate.",
            "select",
            "1K",
            choices=("0.5K", "1K", "2K", "4K"),
            order=9,
        ),
        _param(
            "limit_generations",
            "Limit generations from each prompt round to one.",
            "boolean",
            True,
            order=10,
        ),
        _param(
            "enable_web_search",
            "Enable web search for the image generation task.",
            "boolean",
            False,
            order=11,
        ),
        _param(
            "thinking_level",
            "Optional model thinking level.",
            "string",
            order=12,
        ),
    )


def _hidream_parameters(
    *,
    steps: int,
    price_tier: str,
) -> tuple[ModelParameter, ...]:
    parameters = [
        _param(
            "prompt",
            "The prompt to generate an image from.",
            "string",
            order=1,
        ),
        _param(
            "image_size",
            "The size of the generated image.",
            "select",
            "square_hd",
            choices=IMAGE_SIZE_CHOICES,
            order=3,
        ),
        _param(
            "num_inference_steps",
            "The number of inference steps to perform.",
            "integer",
            steps,
            minimum=1,
            maximum=50,
            order=4,
        ),
        _param(
            "seed",
            "Random seed for reproducibility.",
            "integer",
            "",
            order=5,
            semantic_type="seed",
        ),
    ]
    if price_tier == "full":
        parameters.append(
            _param(
                "guidance_scale",
                "Classifier-free guidance scale.",
                "number",
                5,
                minimum=0,
                maximum=20,
                order=6,
            )
        )
        sync_order = 7
        num_images_order = 8
        output_order = 10
        parameters.append(
            _param(
                "loras",
                "LoRA weights to apply to the model.",
                "string",
                order=11,
            )
        )
    else:
        sync_order = 6
        num_images_order = 7
        output_order = 9

    parameters.extend(
        [
            _param(
                "sync_mode",
                "Return media inline instead of storing it in request history.",
                "boolean",
                False,
                order=sync_order,
            ),
            _param(
                "num_images",
                "The number of images to generate.",
                "integer",
                1,
                minimum=1,
                maximum=4,
                order=num_images_order,
            ),
            _param(
                "output_format",
                "The format of the generated image.",
                "select",
                "jpeg",
                choices=OUTPUT_FORMAT_CHOICES,
                order=output_order,
            ),
        ]
    )
    return tuple(sorted(parameters, key=lambda item: item.order or 999))


def _flux2_parameters(
    *,
    image_size_default: object = "landscape_4_3",
    image_size_choices: tuple[object, ...] = IMAGE_SIZE_CHOICES,
) -> tuple[ModelParameter, ...]:
    return (
        _param(
            "prompt",
            "The prompt to generate or edit the image.",
            "string",
            order=1,
        ),
        _param(
            "guidance_scale",
            "Guidance scale for prompt adherence.",
            "number",
            2.5,
            minimum=0,
            maximum=20,
            order=2,
        ),
        _param(
            "seed",
            "Random seed for reproducibility.",
            "integer",
            "",
            order=3,
            semantic_type="seed",
        ),
        _param(
            "num_inference_steps",
            "The number of inference steps to perform.",
            "integer",
            28,
            minimum=4,
            maximum=50,
            order=4,
        ),
        _param(
            "image_size",
            "The size of the image.",
            "select",
            image_size_default,
            choices=image_size_choices,
            order=5,
        ),
        _param(
            "num_images",
            "The number of images to generate.",
            "integer",
            1,
            minimum=1,
            maximum=4,
            order=6,
        ),
        _param(
            "acceleration",
            "The acceleration level to use.",
            "select",
            "regular",
            choices=("none", "regular", "high"),
            order=7,
        ),
        _param(
            "sync_mode",
            "Return media inline instead of storing it in request history.",
            "boolean",
            False,
            order=9,
        ),
        _param(
            "output_format",
            "The format of the generated image.",
            "select",
            "jpeg",
            choices=EXTENDED_OUTPUT_FORMAT_CHOICES,
            order=11,
        ),
    )


def _flux2_pro_parameters(
    *,
    image_size_default: str = "landscape_4_3",
    image_size_choices: tuple[object, ...] = IMAGE_SIZE_CHOICES,
) -> tuple[ModelParameter, ...]:
    return (
        _param(
            "prompt",
            "The prompt to generate or edit the image.",
            "string",
            order=1,
        ),
        _param(
            "image_size",
            "The size of the generated image.",
            "select",
            image_size_default,
            choices=image_size_choices,
            order=2,
        ),
        _param(
            "seed",
            "Random seed for reproducibility.",
            "integer",
            "",
            order=3,
            semantic_type="seed",
        ),
        _param(
            "safety_tolerance",
            "Safety tolerance level for generated images.",
            "select",
            "2",
            choices=SAFETY_TOLERANCE_CHOICES,
            order=4,
        ),
        _param(
            "output_format",
            "The format of the generated image.",
            "select",
            "jpeg",
            choices=OUTPUT_FORMAT_CHOICES,
            order=6,
        ),
        _param(
            "sync_mode",
            "Return media inline instead of storing it in request history.",
            "boolean",
            False,
            order=7,
        ),
    )


def _flux2_realism_parameters() -> tuple[ModelParameter, ...]:
    return (
        _param(
            "prompt",
            "The prompt to generate a realistic image.",
            "string",
            order=1,
        ),
        _param(
            "image_size",
            "The size of the generated image.",
            "select",
            "landscape_4_3",
            choices=IMAGE_SIZE_CHOICES,
            order=2,
        ),
        _param(
            "guidance_scale",
            "Classifier-free guidance scale.",
            "number",
            2.5,
            minimum=0,
            maximum=20,
            order=3,
        ),
        _param(
            "num_inference_steps",
            "The number of inference steps to perform.",
            "integer",
            40,
            minimum=4,
            maximum=50,
            order=4,
        ),
        _param(
            "acceleration",
            "Acceleration level for image generation.",
            "select",
            "regular",
            choices=("none", "regular"),
            order=5,
        ),
        _param(
            "seed",
            "Random seed for reproducibility.",
            "integer",
            "",
            order=6,
            semantic_type="seed",
        ),
        _param(
            "sync_mode",
            "Return media inline instead of storing it in request history.",
            "boolean",
            False,
            order=7,
        ),
        _param(
            "output_format",
            "The format of the generated image.",
            "select",
            "jpeg",
            choices=("png", "jpeg", "webp"),
            order=9,
        ),
        _param(
            "num_images",
            "The number of images to generate.",
            "integer",
            1,
            minimum=1,
            maximum=4,
            order=10,
        ),
        _param(
            "lora_scale",
            "The strength of the realism effect.",
            "number",
            1,
            minimum=0,
            maximum=2,
            order=11,
        ),
    )


def _z_image_parameters(
    *,
    image_size_default: str = "landscape_4_3",
    image_size_choices: tuple[object, ...] = IMAGE_SIZE_CHOICES,
    include_strength: bool = False,
) -> tuple[ModelParameter, ...]:
    parameters = [
        _param(
            "prompt",
            "The prompt to generate or edit the image.",
            "string",
            order=1,
        ),
        _param(
            "image_size",
            "The size of the generated image.",
            "select",
            image_size_default,
            choices=image_size_choices,
            order=2,
        ),
        _param(
            "num_inference_steps",
            "The number of inference steps to perform.",
            "integer",
            8,
            minimum=1,
            maximum=8,
            order=3,
        ),
        _param(
            "seed",
            "Random seed for reproducibility.",
            "integer",
            "",
            order=4,
            semantic_type="seed",
        ),
        _param(
            "sync_mode",
            "Return media inline instead of storing it in request history.",
            "boolean",
            False,
            order=5,
        ),
        _param(
            "num_images",
            "The number of images to generate.",
            "integer",
            1,
            minimum=1,
            maximum=4,
            order=6,
        ),
        _param(
            "output_format",
            "The format of the generated image.",
            "select",
            "jpeg",
            choices=EXTENDED_OUTPUT_FORMAT_CHOICES,
            order=8,
        ),
        _param(
            "acceleration",
            "The acceleration level to use.",
            "select",
            "regular",
            choices=("none", "regular", "high"),
            order=9,
        ),
    ]
    if include_strength:
        parameters.append(
            _param(
                "strength",
                "The strength of image-to-image conditioning.",
                "number",
                0.6,
                maximum=1,
                order=12,
            )
        )
    return tuple(parameters)


def _gpt_image15_parameters(*, edit: bool) -> tuple[ModelParameter, ...]:
    parameters = [
        _param(
            "prompt", "The prompt for image generation or editing.", "string", order=1
        ),
        _param(
            "image_size",
            "Aspect ratio for the generated image.",
            "select",
            "auto" if edit else "1024x1024",
            choices=GPT_IMAGE15_EDIT_SIZE_CHOICES if edit else GPT_IMAGE15_SIZE_CHOICES,
            order=3 if edit else 2,
        ),
        _param(
            "background",
            "Background for the generated image.",
            "select",
            "auto",
            choices=("auto", "transparent", "opaque"),
            order=4 if edit else 3,
        ),
        _param(
            "quality",
            "Quality for the generated image.",
            "select",
            "high",
            choices=("low", "medium", "high"),
            order=5 if edit else 4,
        ),
    ]
    if edit:
        parameters.append(
            _param(
                "input_fidelity",
                "Input fidelity for the generated image.",
                "select",
                "high",
                choices=("low", "high"),
                order=6,
            )
        )
    parameters.extend(
        [
            _param(
                "num_images",
                "Number of images to generate.",
                "integer",
                1,
                minimum=1,
                maximum=4,
                order=7 if edit else 5,
            ),
            _param(
                "output_format",
                "Output format for the images.",
                "select",
                "jpeg",
                choices=EXTENDED_OUTPUT_FORMAT_CHOICES,
                order=8 if edit else 6,
            ),
        ]
    )
    if edit:
        parameters.append(
            _param(
                "mask_image_url",
                "Mask image URL for edits.",
                "string",
                order=10,
            )
        )
    return tuple(sorted(parameters, key=lambda item: item.order or 999))


def _gpt_image2_parameters(*, edit: bool) -> tuple[ModelParameter, ...]:
    parameters = [
        _param(
            "prompt", "The prompt for image generation or editing.", "string", order=1
        ),
        _param(
            "image_size",
            "The size of the generated image.",
            "select",
            "auto" if edit else "landscape_4_3",
            choices=AUTO_IMAGE_SIZE_CHOICES,
            order=3 if edit else 2,
        ),
        _param(
            "quality",
            "Quality for the generated image.",
            "select",
            "high",
            choices=("auto", "low", "medium", "high"),
            order=4 if edit else 3,
        ),
        _param(
            "num_images",
            "Number of images to generate.",
            "integer",
            1,
            minimum=1,
            maximum=4,
            order=5 if edit else 4,
        ),
        _param(
            "output_format",
            "Output format for the images.",
            "select",
            "jpeg",
            choices=EXTENDED_OUTPUT_FORMAT_CHOICES,
            order=6 if edit else 5,
        ),
    ]
    if edit:
        parameters.append(
            _param("mask_url", "Mask image URL for edits.", "string", order=8)
        )
    return tuple(parameters)


def _grok_parameters(*, edit: bool) -> tuple[ModelParameter, ...]:
    return (
        _param("prompt", "Text description of the desired image.", "string", order=1),
        _param(
            "num_images",
            "Number of images to generate.",
            "integer",
            1,
            minimum=1,
            maximum=4,
            order=2,
        ),
        _param(
            "aspect_ratio",
            "Aspect ratio of the generated or edited image.",
            "select",
            "auto" if edit else "1:1",
            choices=GROK_EDIT_ASPECT_RATIO_CHOICES
            if edit
            else GROK_ASPECT_RATIO_CHOICES,
            order=3,
        ),
        _param(
            "resolution",
            "Resolution of the generated image.",
            "select",
            "1k",
            choices=("1k", "2k"),
            order=4,
        ),
        _param(
            "output_format",
            "The format of the generated image.",
            "select",
            "jpeg",
            choices=EXTENDED_OUTPUT_FORMAT_CHOICES,
            order=5,
        ),
    )


def _bria_text_parameters() -> tuple[ModelParameter, ...]:
    return (
        _param("prompt", "Prompt for image generation.", "string", order=1),
        _param(
            "seed",
            "Random seed for reproducibility.",
            "integer",
            "",
            order=2,
            semantic_type="seed",
        ),
        _param(
            "steps_num",
            "Number of inference steps.",
            "integer",
            50,
            minimum=20,
            maximum=50,
            order=3,
        ),
        _param(
            "aspect_ratio",
            "Output image aspect ratio.",
            "select",
            "1:1",
            choices=BRIA_ASPECT_RATIO_CHOICES,
            order=4,
        ),
        _param(
            "resolution",
            "Output image resolution.",
            "select",
            "1MP",
            choices=("1MP", "4MP"),
            order=8,
        ),
    )


def _bria_edit_parameters() -> tuple[ModelParameter, ...]:
    return (
        _param("mask_url", "Mask image URL.", "string", order=2),
        _param("instruction", "Instruction for image editing.", "string", order=3),
        _param(
            "structured_instruction",
            "Structured instruction for image editing.",
            "string",
            order=4,
        ),
        _param(
            "original_vgl",
            "Original VGL used to generate the image.",
            "string",
            order=5,
        ),
        _param(
            "new_vgl", "New VGL describing the image after edit.", "string", order=6
        ),
        _param(
            "seed",
            "Random seed for reproducibility.",
            "integer",
            "",
            order=7,
            semantic_type="seed",
        ),
        _param(
            "steps_num",
            "Number of inference steps.",
            "integer",
            30,
            minimum=20,
            maximum=50,
            order=8,
        ),
        _param("guidance_scale", "Guidance scale for text.", "number", 5, order=9),
    )


ERNIE_IMAGE = ProviderModel(
    provider="falai",
    alias="ernie-image",
    display_name="Ernie Image",
    text_target=GenerationTarget(
        provider="falai",
        alias="ernie-image",
        display_name="Ernie Image",
        provider_model="fal-ai/ernie-image",
        documentation_url="https://fal.ai/models/fal-ai/ernie-image/api",
        runtime_url="https://fal.run/fal-ai/ernie-image",
        mode="text-to-image",
        parameters=_ernie_parameters(turbo=False),
        fixed_inputs=FALAI_FIXED_SAFE_IMAGE_INPUTS,
        pricing=(
            _falai_price(
                "$0.03", "per output megapixel", metric="image_output_megapixel_count"
            ),
        ),
    ),
)

ERNIE_IMAGE_TURBO = ProviderModel(
    provider="falai",
    alias="ernie-image-turbo",
    display_name="Ernie Image Turbo",
    text_target=GenerationTarget(
        provider="falai",
        alias="ernie-image-turbo",
        display_name="Ernie Image Turbo",
        provider_model="fal-ai/ernie-image/turbo",
        documentation_url="https://fal.ai/models/fal-ai/ernie-image/turbo/api",
        runtime_url="https://fal.run/fal-ai/ernie-image/turbo",
        mode="text-to-image",
        parameters=_ernie_parameters(turbo=True),
        fixed_inputs=FALAI_FIXED_SAFE_IMAGE_INPUTS,
        pricing=(
            _falai_price(
                "$0.01", "per output megapixel", metric="image_output_megapixel_count"
            ),
        ),
    ),
)

SEEDREAM45 = ProviderModel(
    provider="falai",
    alias="seedream45",
    display_name="Seedream 4.5",
    text_target=GenerationTarget(
        provider="falai",
        alias="seedream45",
        display_name="Seedream 4.5",
        provider_model="fal-ai/bytedance/seedream/v4.5/text-to-image",
        documentation_url="https://fal.ai/models/fal-ai/bytedance/seedream/v4.5/text-to-image/api",
        runtime_url="https://fal.run/fal-ai/bytedance/seedream/v4.5/text-to-image",
        mode="text-to-image",
        parameters=_seedream45_parameters(),
        fixed_inputs=FALAI_FIXED_SAFE_IMAGE_INPUTS,
        pricing=(
            _falai_price("$0.04", "per output image", metric="image_output_count"),
        ),
    ),
    edit_target=GenerationTarget(
        provider="falai",
        alias="seedream45",
        display_name="Seedream 4.5",
        provider_model="fal-ai/bytedance/seedream/v4.5/edit",
        documentation_url="https://fal.ai/models/fal-ai/bytedance/seedream/v4.5/edit/api",
        runtime_url="https://fal.run/fal-ai/bytedance/seedream/v4.5/edit",
        mode="image-edit",
        parameters=_seedream45_parameters(),
        fixed_inputs=FALAI_FIXED_SAFE_IMAGE_INPUTS,
        source_images=SourceImageBinding(provider_field="image_urls", max_count=10),
        pricing=(
            _falai_price("$0.04", "per output image", metric="image_output_count"),
        ),
    ),
)

BRIA_FIBO = ProviderModel(
    provider="falai",
    alias="bria-fibo",
    display_name="Bria Fibo",
    text_target=GenerationTarget(
        provider="falai",
        alias="bria-fibo",
        display_name="Bria Fibo",
        provider_model="bria/fibo/generate",
        documentation_url="https://fal.ai/models/bria/fibo/generate/api",
        runtime_url="https://fal.run/bria/fibo/generate",
        mode="text-to-image",
        parameters=_bria_text_parameters(),
        fixed_inputs=FALAI_FIXED_IMAGE_OUTPUT_INPUTS,
        pricing=(
            _falai_price("$0.04", "per output image", metric="image_output_count"),
        ),
    ),
    edit_target=GenerationTarget(
        provider="falai",
        alias="bria-fibo",
        display_name="Bria Fibo",
        provider_model="bria/fibo-edit/edit",
        documentation_url="https://fal.ai/models/bria/fibo-edit/edit/api",
        runtime_url="https://fal.run/bria/fibo-edit/edit",
        mode="image-edit",
        parameters=_bria_edit_parameters(),
        fixed_inputs=FALAI_FIXED_IMAGE_OUTPUT_INPUTS,
        source_images=SourceImageBinding(provider_field="image_url", max_count=1),
        pricing=(
            _falai_price("$0.04", "per output image", metric="image_output_count"),
        ),
    ),
)

HIDREAM_FAST = ProviderModel(
    provider="falai",
    alias="hidream-fast",
    display_name="HiDream I1 Fast",
    text_target=GenerationTarget(
        provider="falai",
        alias="hidream-fast",
        display_name="HiDream I1 Fast",
        provider_model="fal-ai/hidream-i1-fast",
        documentation_url="https://fal.ai/models/fal-ai/hidream-i1-fast/api",
        runtime_url="https://fal.run/fal-ai/hidream-i1-fast",
        mode="text-to-image",
        parameters=_hidream_parameters(steps=16, price_tier="fast"),
        fixed_inputs=FALAI_FIXED_SAFE_IMAGE_INPUTS,
        pricing=(
            _falai_price(
                "$0.01", "per output megapixel", metric="image_output_megapixel_count"
            ),
        ),
    ),
)

HIDREAM_DEV = ProviderModel(
    provider="falai",
    alias="hidream-dev",
    display_name="HiDream I1 Dev",
    text_target=GenerationTarget(
        provider="falai",
        alias="hidream-dev",
        display_name="HiDream I1 Dev",
        provider_model="fal-ai/hidream-i1-dev",
        documentation_url="https://fal.ai/models/fal-ai/hidream-i1-dev/api",
        runtime_url="https://fal.run/fal-ai/hidream-i1-dev",
        mode="text-to-image",
        parameters=_hidream_parameters(steps=28, price_tier="dev"),
        fixed_inputs=FALAI_FIXED_SAFE_IMAGE_INPUTS,
        pricing=(
            _falai_price(
                "$0.03", "per output megapixel", metric="image_output_megapixel_count"
            ),
        ),
    ),
)

HIDREAM_FULL = ProviderModel(
    provider="falai",
    alias="hidream-full",
    display_name="HiDream I1 Full",
    text_target=GenerationTarget(
        provider="falai",
        alias="hidream-full",
        display_name="HiDream I1 Full",
        provider_model="fal-ai/hidream-i1-full",
        documentation_url="https://fal.ai/models/fal-ai/hidream-i1-full/api",
        runtime_url="https://fal.run/fal-ai/hidream-i1-full",
        mode="text-to-image",
        parameters=_hidream_parameters(steps=50, price_tier="full"),
        fixed_inputs=FALAI_FIXED_SAFE_IMAGE_INPUTS,
        pricing=(
            _falai_price(
                "$0.05", "per output megapixel", metric="image_output_megapixel_count"
            ),
        ),
    ),
)

FLUX_2 = ProviderModel(
    provider="falai",
    alias="flux-2",
    display_name="Flux 2",
    text_target=GenerationTarget(
        provider="falai",
        alias="flux-2",
        display_name="Flux 2",
        provider_model="fal-ai/flux-2",
        documentation_url="https://fal.ai/models/fal-ai/flux-2/api",
        runtime_url="https://fal.run/fal-ai/flux-2",
        mode="text-to-image",
        parameters=_flux2_parameters(),
        fixed_inputs=FALAI_FIXED_SAFE_NO_PROMPT_EXPANSION_INPUTS,
        pricing=(
            _falai_price("$0.00167", "per compute second", metric="compute_seconds"),
        ),
    ),
    edit_target=GenerationTarget(
        provider="falai",
        alias="flux-2",
        display_name="Flux 2",
        provider_model="fal-ai/flux-2/edit",
        documentation_url="https://fal.ai/models/fal-ai/flux-2/edit/api",
        runtime_url="https://fal.run/fal-ai/flux-2/edit",
        mode="image-edit",
        parameters=_flux2_parameters(),
        fixed_inputs=FALAI_FIXED_SAFE_NO_PROMPT_EXPANSION_INPUTS,
        source_images=SourceImageBinding(provider_field="image_urls", max_count=4),
        pricing=(
            _falai_price("$0.00167", "per compute second", metric="compute_seconds"),
        ),
    ),
)

FLUX_2_PRO = ProviderModel(
    provider="falai",
    alias="flux-2-pro",
    display_name="Flux 2 Pro",
    text_target=GenerationTarget(
        provider="falai",
        alias="flux-2-pro",
        display_name="Flux 2 Pro",
        provider_model="fal-ai/flux-2-pro",
        documentation_url="https://fal.ai/models/fal-ai/flux-2-pro/api",
        runtime_url="https://fal.run/fal-ai/flux-2-pro",
        mode="text-to-image",
        parameters=_flux2_pro_parameters(),
        fixed_inputs=FALAI_FIXED_SAFE_IMAGE_INPUTS,
        pricing=(
            _falai_price(
                "$0.03",
                "per processed megapixel",
                metric="image_processed_megapixel_count",
            ),
        ),
    ),
    edit_target=GenerationTarget(
        provider="falai",
        alias="flux-2-pro",
        display_name="Flux 2 Pro",
        provider_model="fal-ai/flux-2-pro/edit",
        documentation_url="https://fal.ai/models/fal-ai/flux-2-pro/edit/api",
        runtime_url="https://fal.run/fal-ai/flux-2-pro/edit",
        mode="image-edit",
        parameters=_flux2_pro_parameters(
            image_size_default="auto",
            image_size_choices=AUTO_IMAGE_SIZE_CHOICES,
        ),
        fixed_inputs=FALAI_FIXED_SAFE_IMAGE_INPUTS,
        source_images=SourceImageBinding(provider_field="image_urls", max_count=10),
        pricing=(
            _falai_price(
                "$0.03",
                "per processed megapixel",
                metric="image_processed_megapixel_count",
            ),
        ),
    ),
)

FLUX_2_REALISM = ProviderModel(
    provider="falai",
    alias="flux-2-realism",
    display_name="Flux 2 Realism",
    text_target=GenerationTarget(
        provider="falai",
        alias="flux-2-realism",
        display_name="Flux 2 Realism",
        provider_model="fal-ai/flux-2-lora-gallery/realism",
        documentation_url="https://fal.ai/models/fal-ai/flux-2-lora-gallery/realism/api",
        runtime_url="https://fal.run/fal-ai/flux-2-lora-gallery/realism",
        mode="text-to-image",
        parameters=_flux2_realism_parameters(),
        fixed_inputs=FALAI_FIXED_SAFE_IMAGE_INPUTS,
        pricing=(
            _falai_price(
                "$0.021", "per output megapixel", metric="image_output_megapixel_count"
            ),
        ),
    ),
)

Z_IMAGE_TURBO = ProviderModel(
    provider="falai",
    alias="zit",
    display_name="Z-Image Turbo",
    text_target=GenerationTarget(
        provider="falai",
        alias="zit",
        display_name="Z-Image Turbo",
        provider_model="fal-ai/z-image/turbo",
        documentation_url="https://fal.ai/models/fal-ai/z-image/turbo/api",
        runtime_url="https://fal.run/fal-ai/z-image/turbo",
        mode="text-to-image",
        parameters=_z_image_parameters(),
        fixed_inputs=FALAI_FIXED_SAFE_NO_PROMPT_EXPANSION_INPUTS,
        pricing=(
            _falai_price(
                "$0.005", "per output megapixel", metric="image_output_megapixel_count"
            ),
        ),
    ),
    edit_target=GenerationTarget(
        provider="falai",
        alias="zit",
        display_name="Z-Image Turbo",
        provider_model="fal-ai/z-image/turbo/image-to-image",
        documentation_url="https://fal.ai/models/fal-ai/z-image/turbo/image-to-image/api",
        runtime_url="https://fal.run/fal-ai/z-image/turbo/image-to-image",
        mode="image-edit",
        parameters=_z_image_parameters(
            image_size_default="auto",
            image_size_choices=AUTO_IMAGE_SIZE_CHOICES,
            include_strength=True,
        ),
        fixed_inputs=FALAI_FIXED_SAFE_NO_PROMPT_EXPANSION_INPUTS,
        source_images=SourceImageBinding(provider_field="image_url", max_count=1),
        pricing=(
            _falai_price(
                "$0.005", "per output megapixel", metric="image_output_megapixel_count"
            ),
        ),
    ),
)

NANO_BANANA_2 = ProviderModel(
    provider="falai",
    alias="nano-banana-2",
    display_name="Nano Banana 2",
    text_target=GenerationTarget(
        provider="falai",
        alias="nano-banana-2",
        display_name="Nano Banana 2",
        provider_model="fal-ai/nano-banana-2",
        documentation_url="https://fal.ai/models/fal-ai/nano-banana-2/api",
        runtime_url="https://fal.run/fal-ai/nano-banana-2",
        mode="text-to-image",
        parameters=_nano_banana_2_parameters(),
        fixed_inputs=FALAI_FIXED_IMAGE_OUTPUT_INPUTS,
        pricing=(
            _falai_price("$0.08", "per output image", metric="image_output_count"),
        ),
    ),
    edit_target=GenerationTarget(
        provider="falai",
        alias="nano-banana-2",
        display_name="Nano Banana 2",
        provider_model="fal-ai/nano-banana-2/edit",
        documentation_url="https://fal.ai/models/fal-ai/nano-banana-2/edit/api",
        runtime_url="https://fal.run/fal-ai/nano-banana-2/edit",
        mode="image-edit",
        parameters=_nano_banana_2_parameters(),
        fixed_inputs=FALAI_FIXED_IMAGE_OUTPUT_INPUTS,
        source_images=SourceImageBinding(provider_field="image_urls", max_count=10),
        pricing=(
            _falai_price("$0.08", "per output image", metric="image_output_count"),
        ),
    ),
)

SEEDREAM5 = ProviderModel(
    provider="falai",
    alias="seedream5",
    display_name="Seedream 5 Lite",
    text_target=GenerationTarget(
        provider="falai",
        alias="seedream5",
        display_name="Seedream 5 Lite",
        provider_model="fal-ai/bytedance/seedream/v5/lite/text-to-image",
        documentation_url="https://fal.ai/models/fal-ai/bytedance/seedream/v5/lite/text-to-image/api",
        runtime_url="https://fal.run/fal-ai/bytedance/seedream/v5/lite/text-to-image",
        mode="text-to-image",
        parameters=_seedream_parameters(
            image_size_default="portrait_4_3",
            image_size_choices=SEEDREAM5_IMAGE_SIZE_CHOICES,
            include_seed=False,
        ),
        fixed_inputs=FALAI_FIXED_SAFE_IMAGE_INPUTS,
        pricing=(
            _falai_price("$0.035", "per output image", metric="image_output_count"),
        ),
    ),
    edit_target=GenerationTarget(
        provider="falai",
        alias="seedream5",
        display_name="Seedream 5 Lite",
        provider_model="fal-ai/bytedance/seedream/v5/lite/edit",
        documentation_url="https://fal.ai/models/fal-ai/bytedance/seedream/v5/lite/edit/api",
        runtime_url="https://fal.run/fal-ai/bytedance/seedream/v5/lite/edit",
        mode="image-edit",
        parameters=_seedream_parameters(
            image_size_default="portrait_4_3",
            image_size_choices=SEEDREAM5_IMAGE_SIZE_CHOICES,
            include_seed=False,
        ),
        fixed_inputs=FALAI_FIXED_SAFE_IMAGE_INPUTS,
        source_images=SourceImageBinding(provider_field="image_urls", max_count=10),
        pricing=(
            _falai_price("$0.035", "per output image", metric="image_output_count"),
        ),
    ),
)

SEEDREAM4 = ProviderModel(
    provider="falai",
    alias="seedream",
    display_name="Seedream 4",
    text_target=GenerationTarget(
        provider="falai",
        alias="seedream",
        display_name="Seedream 4",
        provider_model="fal-ai/bytedance/seedream/v4/text-to-image",
        documentation_url="https://fal.ai/models/fal-ai/bytedance/seedream/v4/text-to-image/api",
        runtime_url="https://fal.run/fal-ai/bytedance/seedream/v4/text-to-image",
        mode="text-to-image",
        parameters=_seedream_parameters(
            image_size_default="portrait_4_3",
            image_size_choices=SEEDREAM4_IMAGE_SIZE_CHOICES,
            include_seed=True,
            include_enhance_prompt_mode=True,
        ),
        fixed_inputs=FALAI_FIXED_SAFE_IMAGE_INPUTS,
        pricing=(
            _falai_price("$0.03", "per output image", metric="image_output_count"),
        ),
    ),
    edit_target=GenerationTarget(
        provider="falai",
        alias="seedream",
        display_name="Seedream 4",
        provider_model="fal-ai/bytedance/seedream/v4/edit",
        documentation_url="https://fal.ai/models/fal-ai/bytedance/seedream/v4/edit/api",
        runtime_url="https://fal.run/fal-ai/bytedance/seedream/v4/edit",
        mode="image-edit",
        parameters=_seedream_parameters(
            image_size_default="portrait_4_3",
            image_size_choices=SEEDREAM4_IMAGE_SIZE_CHOICES,
            include_seed=True,
            include_enhance_prompt_mode=True,
        ),
        fixed_inputs=FALAI_FIXED_SAFE_IMAGE_INPUTS,
        source_images=SourceImageBinding(provider_field="image_urls", max_count=10),
        pricing=(
            _falai_price("$0.03", "per output image", metric="image_output_count"),
        ),
    ),
)

GPT_IMAGE15 = ProviderModel(
    provider="falai",
    alias="gpt-image15",
    display_name="GPT Image 1.5",
    text_target=GenerationTarget(
        provider="falai",
        alias="gpt-image15",
        display_name="GPT Image 1.5",
        provider_model="fal-ai/gpt-image-1.5",
        documentation_url="https://fal.ai/models/fal-ai/gpt-image-1.5/api",
        runtime_url="https://fal.run/fal-ai/gpt-image-1.5",
        mode="text-to-image",
        parameters=_gpt_image15_parameters(edit=False),
        fixed_inputs=FALAI_FIXED_IMAGE_OUTPUT_INPUTS,
        pricing=(_falai_price("$1", "per billing unit", metric="billing_unit_count"),),
    ),
    edit_target=GenerationTarget(
        provider="falai",
        alias="gpt-image15",
        display_name="GPT Image 1.5",
        provider_model="fal-ai/gpt-image-1.5/edit",
        documentation_url="https://fal.ai/models/fal-ai/gpt-image-1.5/edit/api",
        runtime_url="https://fal.run/fal-ai/gpt-image-1.5/edit",
        mode="image-edit",
        parameters=_gpt_image15_parameters(edit=True),
        fixed_inputs=FALAI_FIXED_IMAGE_OUTPUT_INPUTS,
        source_images=SourceImageBinding(provider_field="image_urls", max_count=10),
        pricing=(_falai_price("$1", "per billing unit", metric="billing_unit_count"),),
    ),
)

GPT_IMAGE2 = ProviderModel(
    provider="falai",
    alias="gpt-image-2",
    display_name="GPT Image 2",
    text_target=GenerationTarget(
        provider="falai",
        alias="gpt-image-2",
        display_name="GPT Image 2",
        provider_model="openai/gpt-image-2",
        documentation_url="https://fal.ai/models/openai/gpt-image-2/api",
        runtime_url="https://fal.run/openai/gpt-image-2",
        mode="text-to-image",
        parameters=_gpt_image2_parameters(edit=False),
        fixed_inputs=FALAI_FIXED_IMAGE_OUTPUT_INPUTS,
        pricing=(_falai_price("$1", "per billing unit", metric="billing_unit_count"),),
    ),
    edit_target=GenerationTarget(
        provider="falai",
        alias="gpt-image-2",
        display_name="GPT Image 2",
        provider_model="openai/gpt-image-2/edit",
        documentation_url="https://fal.ai/models/openai/gpt-image-2/edit/api",
        runtime_url="https://fal.run/openai/gpt-image-2/edit",
        mode="image-edit",
        parameters=_gpt_image2_parameters(edit=True),
        fixed_inputs=FALAI_FIXED_IMAGE_OUTPUT_INPUTS,
        source_images=SourceImageBinding(provider_field="image_urls", max_count=10),
        pricing=(_falai_price("$1", "per billing unit", metric="billing_unit_count"),),
    ),
)

GROK = ProviderModel(
    provider="falai",
    alias="grok",
    display_name="Grok Imagine Image",
    text_target=GenerationTarget(
        provider="falai",
        alias="grok",
        display_name="Grok Imagine Image",
        provider_model="xai/grok-imagine-image",
        documentation_url="https://fal.ai/models/xai/grok-imagine-image/api",
        runtime_url="https://fal.run/xai/grok-imagine-image",
        mode="text-to-image",
        parameters=_grok_parameters(edit=False),
        fixed_inputs=FALAI_FIXED_IMAGE_OUTPUT_INPUTS,
        pricing=(
            _falai_price("$0.02", "per output image", metric="image_output_count"),
        ),
    ),
    edit_target=GenerationTarget(
        provider="falai",
        alias="grok",
        display_name="Grok Imagine Image",
        provider_model="xai/grok-imagine-image/edit",
        documentation_url="https://fal.ai/models/xai/grok-imagine-image/edit/api",
        runtime_url="https://fal.run/xai/grok-imagine-image/edit",
        mode="image-edit",
        parameters=_grok_parameters(edit=True),
        fixed_inputs=FALAI_FIXED_IMAGE_OUTPUT_INPUTS,
        source_images=SourceImageBinding(provider_field="image_urls", max_count=3),
        pricing=(
            _falai_price("$0.02", "per output image", metric="image_output_count"),
        ),
    ),
)


MODEL_REGISTRY: dict[str, ProviderModel] = {
    BRIA_FIBO.alias: BRIA_FIBO,
    ERNIE_IMAGE.alias: ERNIE_IMAGE,
    ERNIE_IMAGE_TURBO.alias: ERNIE_IMAGE_TURBO,
    FLUX_2.alias: FLUX_2,
    FLUX_2_PRO.alias: FLUX_2_PRO,
    FLUX_2_REALISM.alias: FLUX_2_REALISM,
    GPT_IMAGE15.alias: GPT_IMAGE15,
    GPT_IMAGE2.alias: GPT_IMAGE2,
    GROK.alias: GROK,
    HIDREAM_DEV.alias: HIDREAM_DEV,
    HIDREAM_FAST.alias: HIDREAM_FAST,
    HIDREAM_FULL.alias: HIDREAM_FULL,
    NANO_BANANA_2.alias: NANO_BANANA_2,
    SEEDREAM4.alias: SEEDREAM4,
    SEEDREAM45.alias: SEEDREAM45,
    SEEDREAM5.alias: SEEDREAM5,
    Z_IMAGE_TURBO.alias: Z_IMAGE_TURBO,
}
