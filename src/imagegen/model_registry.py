"""Configured Replicate models for imagegen."""

from dataclasses import dataclass
from typing import Literal


ParameterType = Literal["array", "boolean", "integer", "number", "select", "string"]
ModelMode = Literal["text-to-image", "image-edit"]
ParameterSemanticType = Literal["seed"]


@dataclass(frozen=True)
class ModelPricing:
    price: str
    title: str
    description: str
    type: str
    metric: str
    metric_count: int


@dataclass(frozen=True)
class CustomDimensionsControl:
    activation_parameter: str
    activation_value: object
    scale_parameter: str
    width_parameter: str
    height_parameter: str


@dataclass(frozen=True)
class ModelParameter:
    name: str
    description: str
    type: ParameterType
    default: object
    choices: tuple[object, ...] = ()
    minimum: float | int | None = None
    maximum: float | int | None = None
    order: int | None = None
    semantic_type: ParameterSemanticType | None = None


@dataclass(frozen=True)
class ReplicateModel:
    alias: str
    display_name: str
    documentation_url: str
    replicate_model: str
    edit_capable: bool
    fixed_inputs: dict[str, object]
    default_width: int
    default_height: int
    modes: tuple[ModelMode, ...]
    parameters: tuple[ModelParameter, ...]
    source_image_parameter: str | None = None
    source_image_max: int = 14
    custom_dimensions: CustomDimensionsControl | None = None
    pricing: tuple[ModelPricing, ...] = ()


SEEDREAM45 = ReplicateModel(
    alias="seedream45",
    display_name="Seedream 4.5",
    documentation_url="https://replicate.com/bytedance/seedream-4.5/api/schema",
    replicate_model="bytedance/seedream-4.5",
    edit_capable=True,
    fixed_inputs={"disable_safety_checker": True},
    default_width=2048,
    default_height=2048,
    modes=("text-to-image", "image-edit"),
    source_image_parameter="image_input",
    pricing=(
        ModelPricing(
            price="$0.04",
            title="per output image",
            description="or 25 images for $1",
            type="per-unit",
            metric="image_output_count",
            metric_count=1,
        ),
    ),
    parameters=(
        ModelParameter(
            name="prompt",
            description="Text prompt for image generation.",
            type="string",
            default="",
            order=0,
        ),
        ModelParameter(
            name="image_input",
            description=(
                "Input image(s) for image-to-image generation. List of 1-14 "
                "images for single or multi-reference generation."
            ),
            type="array",
            default=(),
            order=1,
        ),
        ModelParameter(
            name="size",
            description=(
                "Image resolution: 2K (2048px) or 4K (4096px). 1K resolution "
                "is not supported in Seedream 4.5."
            ),
            type="select",
            default="2K",
            choices=("2K", "4K"),
            order=2,
        ),
        ModelParameter(
            name="aspect_ratio",
            description=(
                "Image aspect ratio. Use match_input_image to automatically "
                "match the input image's aspect ratio."
            ),
            type="select",
            default="match_input_image",
            choices=(
                "match_input_image",
                "1:1",
                "4:3",
                "3:4",
                "16:9",
                "9:16",
                "3:2",
                "2:3",
                "21:9",
            ),
            order=3,
        ),
        ModelParameter(
            name="sequential_image_generation",
            description=(
                "Group image generation mode. disabled generates one image; "
                "auto lets the model decide whether to generate related images."
            ),
            type="select",
            default="disabled",
            choices=("disabled", "auto"),
            order=4,
        ),
        ModelParameter(
            name="max_images",
            description=(
                "Maximum images to generate when sequential_image_generation "
                "is auto. Total input and generated images cannot exceed 15."
            ),
            type="integer",
            default=1,
            minimum=1,
            maximum=15,
            order=5,
        ),
    ),
)


FLUX_FLEX = ReplicateModel(
    alias="flux-flex",
    display_name="Flux 2 Flex",
    documentation_url="https://replicate.com/black-forest-labs/flux-2-flex/api/schema",
    replicate_model="black-forest-labs/flux-2-flex",
    edit_capable=True,
    fixed_inputs={},
    default_width=1024,
    default_height=1024,
    modes=("text-to-image", "image-edit"),
    source_image_parameter="input_images",
    source_image_max=10,
    pricing=(
        ModelPricing(
            price="$0.06",
            title="per input image megapixel",
            description="or around 16 megapixels for $1",
            type="per-unit",
            metric="image_input_megapixel_count",
            metric_count=1,
        ),
        ModelPricing(
            price="$0.06",
            title="per output image megapixel",
            description="or around 16 megapixels for $1",
            type="per-unit",
            metric="image_output_megapixel_count",
            metric_count=1,
        ),
    ),
    parameters=(
        ModelParameter(
            name="prompt",
            description="Text prompt for image generation.",
            type="string",
            default="",
            order=0,
        ),
        ModelParameter(
            name="input_images",
            description=(
                "Input images for image-to-image generation. List of up to "
                "10 jpeg, png, gif, or webp images according to the upstream schema."
            ),
            type="array",
            default=(),
            order=1,
        ),
        ModelParameter(
            name="aspect_ratio",
            description=(
                "Aspect ratio for the generated image. Use match_input_image "
                "to match the first input image's aspect ratio."
            ),
            type="select",
            default="1:1",
            choices=(
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
            ),
            order=2,
        ),
        ModelParameter(
            name="resolution",
            description="Resolution in megapixels.",
            type="select",
            default="1 MP",
            choices=("match_input_image", "0.5 MP", "1 MP", "2 MP", "4 MP"),
            order=3,
        ),
        ModelParameter(
            name="width",
            description="Width when aspect_ratio is custom. Rounded to a multiple of 16.",
            type="integer",
            default="",
            minimum=256,
            maximum=2048,
            order=4,
        ),
        ModelParameter(
            name="height",
            description="Height when aspect_ratio is custom. Rounded to a multiple of 16.",
            type="integer",
            default="",
            minimum=256,
            maximum=2048,
            order=5,
        ),
        ModelParameter(
            name="safety_tolerance",
            description="Safety tolerance, 1 is most strict and 5 is most permissive.",
            type="integer",
            default=2,
            minimum=1,
            maximum=5,
            order=6,
        ),
        ModelParameter(
            name="seed",
            description="Random seed. Set for reproducible generation.",
            type="integer",
            default="",
            order=7,
            semantic_type="seed",
        ),
        ModelParameter(
            name="prompt_upsampling",
            description="Automatically modify the prompt for more creative generation.",
            type="boolean",
            default=True,
            order=8,
        ),
        ModelParameter(
            name="steps",
            description="Number of inference steps.",
            type="integer",
            default=30,
            minimum=1,
            maximum=50,
            order=9,
        ),
        ModelParameter(
            name="guidance",
            description="Guidance scale for generation.",
            type="number",
            default=4.5,
            minimum=1.5,
            maximum=10,
            order=10,
        ),
        ModelParameter(
            name="output_format",
            description="Format of the output images.",
            type="select",
            default="webp",
            choices=("webp", "jpg", "png"),
            order=11,
        ),
        ModelParameter(
            name="output_quality",
            description="Quality when saving output images, from 0 to 100.",
            type="integer",
            default=80,
            minimum=0,
            maximum=100,
            order=12,
        ),
    ),
    custom_dimensions=CustomDimensionsControl(
        activation_parameter="aspect_ratio",
        activation_value="custom",
        scale_parameter="resolution",
        width_parameter="width",
        height_parameter="height",
    ),
)


MODEL_REGISTRY: dict[str, ReplicateModel] = {
    FLUX_FLEX.alias: FLUX_FLEX,
    SEEDREAM45.alias: SEEDREAM45,
}


DEFAULT_MODEL_ALIAS = SEEDREAM45.alias
