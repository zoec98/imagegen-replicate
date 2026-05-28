"""Configured Replicate models for imagegen."""

from dataclasses import dataclass
from typing import Literal


ParameterType = Literal["array", "integer", "select", "string"]
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


@dataclass(frozen=True)
class ReplicateModel:
    alias: str
    display_name: str
    documentation_url: str
    replicate_model: str
    version: str
    modes: tuple[ModelMode, ...]
    parameters: tuple[ModelParameter, ...]

    @property
    def pinned_model(self) -> str:
        return f"{self.replicate_model}:{self.version}"


SEEDREAM45 = ReplicateModel(
    alias="seedream45",
    display_name="Seedream 4.5",
    documentation_url="https://replicate.com/bytedance/seedream-4.5/api",
    replicate_model="bytedance/seedream-4.5",
    version="fffbf9ea3e7a8a0738faef42766157b0fed74d4831ddcf1e96344096eb186553",
    modes=("text-to-image", "image-edit"),
    parameters=(
        ModelParameter(
            name="prompt",
            description="Text prompt for image generation.",
            type="string",
            default="",
        ),
        ModelParameter(
            name="image_input",
            description=(
                "Input image(s) for image-to-image generation. List of 1-14 "
                "images for single or multi-reference generation."
            ),
            type="array",
            default=(),
        ),
        ModelParameter(
            name="size",
            description=(
                "Output size. Only 2K resolution is supported at this point "
                "in the beta phase."
            ),
            type="select",
            default="2K",
            choices=("2K",),
        ),
        ModelParameter(
            name="aspect_ratio",
            description=(
                "Image aspect ratio. Only 1:1 is supported for generation at "
                "this point in the beta phase; match_input_image is available "
                "for image-edit workflows."
            ),
            type="select",
            default="match_input_image",
            choices=("match_input_image", "1:1"),
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
        ),
    ),
)


MODEL_REGISTRY: dict[str, ReplicateModel] = {
    SEEDREAM45.alias: SEEDREAM45,
}


DEFAULT_MODEL_ALIAS = SEEDREAM45.alias
