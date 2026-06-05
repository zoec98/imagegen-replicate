"""Shared helpers for Flask route tests."""

import json


def extract_csrf_token(response):
    marker = b'<meta name="csrf-token" content="'
    start = response.data.index(marker) + len(marker)
    end = response.data.index(b'"', start)
    return response.data[start:end].decode("utf-8")


def extract_app_checksum(response):
    marker = b'<meta name="app-build" content="'
    start = response.data.index(marker) + len(marker)
    end = response.data.index(b'"', start)
    return response.data[start:end].decode("utf-8")


def extract_attribute(response, marker):
    start = response.data.index(marker) + len(marker)
    end = response.data.index(b'"', start)
    return response.data[start:end].decode("utf-8")


def extract_model_registry(response):
    marker = b'<script id="model-registry-data" type="application/json">'
    start = response.data.index(marker) + len(marker)
    end = response.data.index(b"</script>", start)
    return json.loads(response.data[start:end].decode("utf-8"))


def extract_palette_data(response):
    marker = b'<script id="palette-data" type="application/json">'
    start = response.data.index(marker) + len(marker)
    end = response.data.index(b"</script>", start)
    return json.loads(response.data[start:end].decode("utf-8"))


def expected_response_parameters(model, overrides=None):
    source_image_parameter = getattr(model, "source_image_parameter", None)
    if source_image_parameter is None:
        source_images = getattr(model, "source_images", None)
        source_image_parameter = (
            source_images.provider_field if source_images is not None else None
        )
    parameters = {
        parameter.name: parameter.default
        for parameter in model.parameters
        if parameter.name not in {"prompt", source_image_parameter}
        and parameter.default not in {"", ()}
    }
    parameters.update(overrides or {})
    return parameters
