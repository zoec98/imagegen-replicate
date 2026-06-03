"""Provider request payload construction.

This module builds provider-ready request payloads from validated app state and
provider target metadata. It is shared by API request logging and non-Replicate
provider clients so they serialize prompts, defaults, fixed inputs, custom
dimensions, and source-image bindings consistently.
"""

from __future__ import annotations

from imagegen.model_registry import GenerationTarget, ProviderModel


def build_provider_request(
    prompt: str,
    model: ProviderModel,
    target: GenerationTarget,
    *,
    parameters: dict[str, object] | None = None,
    source_image_inputs: list[object] | None = None,
) -> dict[str, object]:
    custom_dimensions = target.custom_dimensions
    use_custom_dimensions = (
        custom_dimensions is not None
        and parameters is not None
        and parameters.get(custom_dimensions.activation_parameter)
        == custom_dimensions.activation_value
    )
    provider_request: dict[str, object] = {}
    source_image_parameter = (
        model.edit_target.source_images.provider_field
        if model.edit_target is not None and model.edit_target.source_images is not None
        else (
            target.source_images.provider_field
            if target.source_images is not None
            else None
        )
    )
    for parameter in target.parameters:
        if parameter.name == "prompt":
            provider_request[parameter.name] = prompt
        elif parameter.name == source_image_parameter:
            continue
        elif (
            use_custom_dimensions
            and custom_dimensions is not None
            and parameter.name == custom_dimensions.scale_parameter
        ):
            continue
        elif parameter.default != "":
            provider_request[parameter.name] = parameter.default
    if parameters:
        provider_request.update(parameters)
    if use_custom_dimensions and custom_dimensions is not None:
        provider_request.pop(custom_dimensions.scale_parameter, None)
    if source_image_inputs and target.source_images is not None:
        provider_request[target.source_images.provider_field] = (
            source_image_inputs[0]
            if target.source_images.max_count == 1
            else source_image_inputs
        )
    provider_request.update(target.fixed_inputs)
    return provider_request
