"""Workspace page rendering tests.

Behaviors protected:
- The workspace page renders model metadata, palette data, and gallery source choices.
- Rendered asset URLs and app-version API expose the current UI checksum.
- Workspace rendering reflects configured Immich upload availability.
"""

from dataclasses import replace
from urllib.parse import parse_qs, urlparse

from imagegen.model_registry import MODEL_REGISTRY
from route_helpers import (
    extract_app_checksum,
    extract_attribute,
    extract_model_registry,
    extract_palette_data,
)

def test_index_renders_prompt_form(app_factory):
    client = app_factory().test_client()

    response = client.get("/")
    checksum = extract_app_checksum(response)

    assert response.status_code == 200
    assert b'name="csrf-token"' in response.data
    assert b'name="app-build"' in response.data
    assert len(checksum) == 16
    assert b'<form\n        class="prompt-form"' in response.data
    assert b'action="/generate"' not in response.data
    assert b'data-api-generate-url="/api/generate"' in response.data
    assert b'data-api-images-url="/api/images"' in response.data
    assert b'data-api-app-version-url="/api/app-version"' in response.data
    assert b'data-poll-seconds="1.0"' in response.data
    assert b'class="messages" aria-live="polite"' in response.data
    assert b'id="model-selector"' in response.data
    assert b'class="edit-toggle"' in response.data
    assert b'class="source-counter" aria-live="polite">0 selected' in response.data
    assert b'class="source-clear"' in response.data
    assert b'class="pricing-info"' in response.data
    assert b'aria-label="Pricing information"' in response.data
    assert b'class="pricing-tooltip"' in response.data
    assert b"$0.04 per output image or 25 images for $1" in response.data
    assert response.data.index(b'class="pricing-info"') > response.data.index(
        b'id="model-selector"'
    )
    assert response.data.index(b'class="pricing-info"') < response.data.index(
        b'class="generate-button"'
    )
    assert b'value="flux-flex"' in response.data
    assert b'value="seedream45" selected' in response.data
    assert b'name="prompt"' in response.data
    assert b'name="size"' in response.data
    assert b'name="aspect_ratio"' in response.data
    assert b'name="max_images"' in response.data
    assert b"disable_safety_checker" not in response.data
    assert b"Generate" in response.data

def test_index_exposes_model_registry_metadata(app_factory):
    client = app_factory().test_client()

    response = client.get("/")
    registry = extract_model_registry(response)

    aliases = {model["alias"] for model in registry}
    assert aliases == set(MODEL_REGISTRY)
    seedream = next(model for model in registry if model["alias"] == "seedream45")
    assert seedream["edit_capable"] is True
    assert seedream["source_image_max"] == 14
    assert seedream["pricing"] == [
        {
            "price": "$0.04",
            "title": "per output image",
            "description": "or 25 images for $1",
            "type": "per-unit",
            "metric": "image_output_count",
            "metric_count": 1,
        }
    ]
    flux = next(model for model in registry if model["alias"] == "flux-flex")
    assert flux["display_name"] == "Flux 2 Flex"
    assert flux["edit_capable"] is True
    assert flux["source_image_parameter"] == "input_images"
    assert flux["source_image_max"] == 10
    assert flux["pricing"] == [
        {
            "price": "$0.06",
            "title": "per input image megapixel",
            "description": "or around 16 megapixels for $1",
            "type": "per-unit",
            "metric": "image_input_megapixel_count",
            "metric_count": 1,
        },
        {
            "price": "$0.06",
            "title": "per output image megapixel",
            "description": "or around 16 megapixels for $1",
            "type": "per-unit",
            "metric": "image_output_megapixel_count",
            "metric_count": 1,
        },
    ]
    assert flux["custom_dimensions"] == {
        "activation_parameter": "aspect_ratio",
        "activation_value": "custom",
        "scale_parameter": "resolution",
        "width_parameter": "width",
        "height_parameter": "height",
    }
    assert {parameter["name"] for parameter in flux["parameters"]} >= {
        "guidance",
        "output_format",
    }
    seed = next(
        parameter for parameter in flux["parameters"] if parameter["name"] == "seed"
    )
    assert seed["semantic_type"] == "seed"
    assert "prompt" not in {parameter["name"] for parameter in flux["parameters"]}

def test_index_exposes_empty_palette_data_when_fragment_root_is_missing(app_factory):
    client = app_factory().test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert extract_palette_data(response) == []
    assert b'class="palette-controls"' not in response.data

def test_index_exposes_palette_data(app_config, app_factory):
    character = app_config.fragment_root / "character"
    style = app_config.fragment_root / "style"
    character.mkdir(parents=True)
    style.mkdir()
    (character / "zoe.txt").write_text("blue hair", encoding="utf-8")
    (character / "aoife.txt").write_text("red hair", encoding="utf-8")
    (style / "comic_lawrence.txt").write_text("ink style", encoding="utf-8")
    client = app_factory().test_client()

    response = client.get("/")
    palettes = extract_palette_data(response)

    assert response.status_code == 200
    assert b'class="palette-controls" aria-label="Prompt palettes"' in response.data
    assert b'class="palette-editor-toggle"' in response.data
    assert b'class="palette-editor" hidden' in response.data
    assert b'id="palette-editor-palette"' in response.data
    assert b'id="palette-character" data-palette-name="character"' in response.data
    assert b'<option value="">Select character</option>' in response.data
    assert b'<option value="aoife">aoife</option>' in response.data
    assert b'<option value="comic_lawrence">comic lawrence</option>' in response.data
    assert palettes == [
        {
            "name": "character",
            "display_name": "character",
            "fragments": [
                {
                    "name": "aoife",
                    "display_name": "aoife",
                    "content": "red hair",
                },
                {
                    "name": "zoe",
                    "display_name": "zoe",
                    "content": "blue hair",
                },
            ],
        },
        {
            "name": "style",
            "display_name": "style",
            "fragments": [
                {
                    "name": "comic_lawrence",
                    "display_name": "comic lawrence",
                    "content": "ink style",
                },
            ],
        },
    ]

def test_index_excludes_invalid_palette_fragments(app_config, app_factory):
    style = app_config.fragment_root / "style"
    style.mkdir(parents=True)
    (style / "valid.txt").write_text("valid content", encoding="utf-8")
    (style / "bad.txt").write_text("bad: content", encoding="utf-8")
    (style / "ignore.md").write_text("ignored", encoding="utf-8")
    client = app_factory().test_client()

    response = client.get("/")
    palettes = extract_palette_data(response)

    assert response.status_code == 200
    assert palettes[0]["fragments"] == [
        {
            "name": "valid",
            "display_name": "valid",
            "content": "valid content",
        },
    ]

def test_index_static_asset_urls_are_cache_busted(app_factory):
    client = app_factory().test_client()

    response = client.get("/")
    checksum = extract_app_checksum(response)
    css_url = extract_attribute(response, b'<link rel="stylesheet" href="')
    js_url = extract_attribute(response, b'<script defer src="')

    assert urlparse(css_url).path == "/static/app.css"
    assert urlparse(js_url).path == "/static/app.js"
    assert parse_qs(urlparse(css_url).query) == {"v": [checksum]}
    assert parse_qs(urlparse(js_url).query) == {"v": [checksum]}

def test_api_app_version_matches_rendered_checksum(app_factory):
    client = app_factory().test_client()
    index = client.get("/")
    checksum = extract_app_checksum(index)

    response = client.get("/api/app-version")

    assert response.status_code == 200
    assert response.json == {"app_checksum": checksum}

def test_index_lists_existing_images(app_config, app_factory):
    output_dir = app_config.output_dir
    output_dir.mkdir(parents=True)
    (output_dir / "first.png").write_bytes(b"not really an image")
    (output_dir / "animated.gif").write_bytes(b"gif")
    (output_dir / "ignore.txt").write_text("ignore", encoding="utf-8")
    client = app_factory().test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert b"first.png" in response.data
    assert b'href="/images/first.png"' in response.data
    assert b"animated.gif" not in response.data
    assert b"ignore.txt" not in response.data

def test_index_exposes_gallery_filenames_for_source_selection(app_config, app_factory):
    app_config.output_dir.mkdir(parents=True)
    (app_config.output_dir / "source.png").write_bytes(b"image")
    client = app_factory().test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert b'data-filename="source.png"' in response.data
    assert b'data-delete-url="/api/images/source.png/delete"' in response.data
    assert b'href="/images/source.png/download"' in response.data
    assert b'href="/images/source.png/download-clean"' in response.data
    assert b'class="gallery-action gallery-download"' in response.data
    assert b'class="gallery-action gallery-download-clean"' in response.data
    assert b'aria-label="Download source.png"' in response.data
    assert b'aria-label="Download clean source.png"' in response.data
    assert b'aria-label="Select source.png as source image"' in response.data
    assert b'title="Load metadata"' in response.data
    assert b'title="Download with metadata"' in response.data
    assert b'title="Download without metadata"' in response.data
    assert b'title="Delete image"' in response.data
    assert b'class="image-type"' not in response.data
    assert b"gallery-immich" not in response.data

def test_index_renders_immich_upload_action_when_configured(
    app_config,
    app_factory,
):
    app_config.output_dir.mkdir(parents=True)
    (app_config.output_dir / "source.png").write_bytes(b"image")
    immich_config = replace(
        app_config,
        immich_url="https://immich.example.test",
        immich_gallery_id="album-123",
        immich_api_key="immich-key",
    )
    client = app_factory(IMAGEGEN_APP_CONFIG=immich_config).test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert (
        b'data-immich-upload-url="/api/images/source.png/immich-upload"'
        in response.data
    )
    assert b'class="gallery-action gallery-immich"' in response.data
    assert b'aria-label="Upload source.png to Immich"' in response.data
    assert b'title="Upload to Immich"' in response.data
