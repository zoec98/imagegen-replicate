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


def _ernie_parameters(*, turbo: bool) -> tuple[ModelParameter, ...]:
    return (
        _param(
            "prompt",
            "Text prompt for image generation. Supports English, Chinese, and Japanese.",
            "string",
            order=1,
        ),
        _param(
            "negative_prompt",
            "Negative prompt to guide what should not be in the image.",
            "string",
            order=2,
        ),
        _param(
            "image_size",
            "The size of the generated image.",
            "select",
            "square_hd",
            choices=ERNIE_IMAGE_SIZE_CHOICES,
            order=3,
        ),
        _param(
            "num_inference_steps",
            "Number of denoising steps.",
            "integer",
            8 if turbo else 50,
            minimum=1,
            maximum=20 if turbo else 100,
            order=4,
        ),
        _param(
            "guidance_scale",
            "Classifier-free guidance scale.",
            "number",
            1 if turbo else 5,
            minimum=1,
            maximum=20,
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
            "num_images",
            "Number of images to generate.",
            "integer",
            1,
            minimum=1,
            maximum=4,
            order=7,
        ),
        _param(
            "enable_prompt_expansion",
            "Enhance the prompt using an LLM for more detailed results.",
            "boolean",
            True,
            order=8,
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
            "auto_2K",
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


def _bria_text_parameters() -> tuple[ModelParameter, ...]:
    return (
        _param("prompt", "Prompt for image generation.", "string", order=1),
        _param(
            "structured_prompt",
            "Structured prompt for image generation.",
            "string",
            order=2,
        ),
        _param("image_url", "Reference image URL.", "string", order=3),
        _param("seed", "Random seed for reproducibility.", "integer", 5555, order=4),
        _param(
            "steps_num",
            "Number of inference steps.",
            "integer",
            50,
            minimum=20,
            maximum=50,
            order=5,
        ),
        _param(
            "aspect_ratio",
            "Output image aspect ratio.",
            "select",
            "1:1",
            choices=BRIA_ASPECT_RATIO_CHOICES,
            order=6,
        ),
        _param(
            "negative_prompt",
            "Negative prompt for image generation.",
            "string",
            order=7,
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
        _param("seed", "Random seed for reproducibility.", "integer", 5555, order=7),
        _param(
            "steps_num",
            "Number of inference steps.",
            "integer",
            30,
            minimum=20,
            maximum=50,
            order=8,
        ),
        _param(
            "negative_prompt",
            "Negative prompt for image generation.",
            "string",
            order=9,
        ),
        _param("guidance_scale", "Guidance scale for text.", "number", 5, order=10),
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


MODEL_REGISTRY: dict[str, ProviderModel] = {
    BRIA_FIBO.alias: BRIA_FIBO,
    ERNIE_IMAGE.alias: ERNIE_IMAGE,
    ERNIE_IMAGE_TURBO.alias: ERNIE_IMAGE_TURBO,
    SEEDREAM45.alias: SEEDREAM45,
}
