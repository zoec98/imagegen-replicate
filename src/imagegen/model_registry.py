"""Configured model metadata.

This module stores static model definitions, including Replicate model keys,
schema metadata, user-facing parameters, and fixed non-user-facing inputs.
"""

from dataclasses import dataclass
from typing import Literal


ParameterType = Literal["array", "boolean", "integer", "select", "string"]
ModelMode = Literal["text-to-image", "image-edit"]


@dataclass(frozen=True)
class ModelParameter:
    name: str
    description: str
    type: ParameterType
    default: object
    choices: tuple[object, ...] = ()
    minimum: int | None = None
    maximum: int | None = None
    order: int | None = None


@dataclass(frozen=True)
class ReplicateModel:
    alias: str
    display_name: str
    documentation_url: str
    replicate_model: str
    version: str
    edit_capable: bool
    fixed_inputs: dict[str, object]
    default_width: int
    default_height: int
    modes: tuple[ModelMode, ...]
    parameters: tuple[ModelParameter, ...]

    @property
    def pinned_model(self) -> str:
        return f"{self.replicate_model}:{self.version}"


SEEDREAM45 = ReplicateModel(
    alias="seedream45",
    display_name="Seedream 4.5",
    documentation_url="https://replicate.com/bytedance/seedream-4.5/api/schema",
    replicate_model="bytedance/seedream-4.5",
    version="bd4492f8492cc564460074e069bff1d55428cf48286f0a0f4a4a39b50f088ff6",
    edit_capable=True,
    fixed_inputs={"disable_safety_checker": True},
    default_width=2048,
    default_height=2048,
    modes=("text-to-image", "image-edit"),
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


MODEL_REGISTRY: dict[str, ReplicateModel] = {
    SEEDREAM45.alias: SEEDREAM45,
}


DEFAULT_MODEL_ALIAS = SEEDREAM45.alias
