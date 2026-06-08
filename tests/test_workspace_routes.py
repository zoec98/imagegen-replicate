"""Workspace page rendering tests.

Behaviors protected:
- The workspace page renders model metadata, palette data, and gallery source choices.
- Rendered asset URLs and app-version API expose the current UI checksum.
- Workspace rendering reflects configured Immich upload availability.
"""

from dataclasses import replace
from urllib.parse import parse_qs, urlparse

from imagegen.metadata import EmbeddedImageMetadataProvider
from imagegen.model_registry import MODEL_REGISTRY
from imagegen.routes import _workspace_context
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
    assert b'id="provider-selector"' in response.data
    assert b'id="model-selector"' in response.data
    assert response.data.index(b'id="provider-selector"') < response.data.index(
        b'id="model-selector"'
    )
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
    assert b'name="image_input"' not in response.data
    assert b"disable_safety_checker" not in response.data
    assert b"Generate" in response.data
    assert b'class="mask-editor-overlay"' in response.data
    assert b'role="dialog"' in response.data
    assert b'aria-modal="true"' in response.data
    assert b'class="mask-editor-canvas-wrap"' in response.data
    assert b'class="mask-editor-source"' in response.data
    assert b'class="mask-editor-mask"' in response.data
    assert b'class="mask-editor-brush-size"' in response.data
    assert b'class="mask-editor-brush-falloff"' in response.data
    assert b'class="mask-editor-invert"' in response.data
    assert b'class="mask-editor-save"' in response.data
    assert b'class="mask-editor-close"' in response.data


def test_index_exposes_model_registry_metadata(app_factory):
    client = app_factory().test_client()

    response = client.get("/")
    registry = extract_model_registry(response)

    replicate_models = [model for model in registry if model["provider"] == "replicate"]
    falai_models = [model for model in registry if model["provider"] == "falai"]
    assert {model["alias"] for model in replicate_models} == set(MODEL_REGISTRY)
    assert falai_models == []
    seedream = next(
        model
        for model in registry
        if model["provider"] == "replicate" and model["alias"] == "seedream45"
    )
    assert seedream["provider_model"] == "bytedance/seedream-4.5"
    assert seedream["edit_capable"] is True
    assert seedream["source_image_max"] == 14
    assert "image_input" not in {
        parameter["name"] for parameter in seedream["parameters"]
    }
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
    flux = next(
        model
        for model in registry
        if model["provider"] == "replicate" and model["alias"] == "flux-flex"
    )
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


def test_index_honors_configured_start_model(app_config, app_factory):
    configured = replace(
        app_config,
        model_alias="gpt-image-2",
        model=MODEL_REGISTRY["gpt-image-2"],
    )
    client = app_factory(IMAGEGEN_APP_CONFIG=configured).test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert b'value="gpt-image-2" selected' in response.data
    assert b'value="seedream45" selected' not in response.data


def test_workspace_context_honors_configured_start_model(app_config):
    configured = replace(
        app_config,
        model_alias="gpt-image-2",
        model=MODEL_REGISTRY["gpt-image-2"],
    )

    context = _workspace_context(
        configured,
        image_url=lambda filename: f"/images/{filename}",
        metadata_url=lambda filename: f"/images/{filename}/metadata",
        metadata_provider=EmbeddedImageMetadataProvider(),
        csrf_token="token",
        app_checksum_value="checksum",
    )

    assert context["selected_provider_model"].alias == "gpt-image-2"
    assert context["parameters"]


def test_workspace_context_falls_back_when_configured_model_is_unavailable(
    app_config,
):
    configured = replace(
        app_config,
        fal_key="fal-key",
        enabled_providers=("falai",),
        selected_provider="falai",
        model_alias="flux-flex",
        model=MODEL_REGISTRY["flux-flex"],
    )

    context = _workspace_context(
        configured,
        image_url=lambda filename: f"/images/{filename}",
        metadata_url=lambda filename: f"/images/{filename}/metadata",
        metadata_provider=EmbeddedImageMetadataProvider(),
        csrf_token="token",
        app_checksum_value="checksum",
    )

    assert context["selected_provider_model"].provider == "falai"
    assert context["selected_provider_model"].alias == "bria-fibo"
    assert {provider["id"] for provider in context["providers"]} == {"falai"}


def test_index_renders_only_enabled_provider_options(app_config, app_factory):
    app = app_factory(
        IMAGEGEN_APP_CONFIG=replace(
            app_config,
            replicate_api_token="replicate-token",
            fal_key="fal-key",
            enabled_providers=("replicate", "falai"),
            selected_provider="replicate",
        )
    )
    client = app.test_client()

    response = client.get("/")

    assert b'<option value="replicate" selected>Replicate</option>' in response.data
    assert b'<option value="falai" >fal.ai</option>' in response.data


def test_index_exposes_provider_scoped_models_when_falai_is_enabled(
    app_config,
    app_factory,
):
    app = app_factory(
        IMAGEGEN_APP_CONFIG=replace(
            app_config,
            replicate_api_token="replicate-token",
            fal_key="fal-key",
            enabled_providers=("replicate", "falai"),
            selected_provider="replicate",
        )
    )
    client = app.test_client()

    response = client.get("/")
    registry = extract_model_registry(response)

    falai_seedream = next(
        model
        for model in registry
        if model["provider"] == "falai" and model["alias"] == "seedream45"
    )
    assert falai_seedream["provider_model"] == (
        "fal-ai/bytedance/seedream/v4.5/text-to-image"
    )
    assert {parameter["name"] for parameter in falai_seedream["parameters"]} >= {
        "image_size",
        "num_images",
    }
    assert "size" not in {
        parameter["name"] for parameter in falai_seedream["parameters"]
    }


def test_index_renders_no_provider_state(app_config, app_factory):
    app = app_factory(
        IMAGEGEN_APP_CONFIG=replace(
            app_config,
            replicate_api_token="",
            fal_key="",
            enabled_providers=(),
            selected_provider=None,
        )
    )
    client = app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert b"No image generation provider is configured." in response.data
    assert b'id="provider-selector" name="provider" disabled' in response.data
    assert b'id="model-selector" name="model" disabled' in response.data
    assert b'class="generate-button"' in response.data
    assert b"disabled\n              >Generate" in response.data


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


def test_index_renders_trashcan_button_and_overlay_shell(app_config, app_factory):
    style = app_config.fragment_root / "style"
    style.mkdir(parents=True)
    (style / "photo.txt").write_text("photo", encoding="utf-8")
    app_config.trash_dir.mkdir(parents=True)
    (app_config.trash_dir / "deleted.png").write_bytes(b"image")
    (app_config.trash_dir / "ignored.txt").write_text("ignored", encoding="utf-8")
    client = app_factory().test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert b'class="trashcan-toggle"' in response.data
    assert b'data-api-trash-url="/api/trash"' in response.data
    assert b'data-api-empty-trash-url="/api/trash/empty"' in response.data
    assert b'<span class="trashcan-count" aria-live="polite">1</span>' in (
        response.data
    )
    assert response.data.index(b'class="trashcan-toggle"') < (
        response.data.index(b'class="upload-toggle"')
    )
    assert response.data.index(b'class="upload-toggle"') < (
        response.data.index(b'class="palette-editor-toggle"')
    )
    assert response.data.index(b'class="palette-editor-toggle"') < (
        response.data.index(b'class="pricing-info"')
    )
    assert b'class="trash-overlay"' in response.data
    assert b'aria-labelledby="trash-title" hidden' in response.data
    assert b'id="trash-title">Trash' in response.data
    assert b'class="trash-empty" type="button">Empty trash' in response.data
    assert b'class="trash-empty-state" hidden>Trash is empty.' in response.data
    assert b'class="trash-gallery" aria-label="Trash images"' in response.data
    assert b'class="trash-close"' in response.data


def test_index_renders_upload_button_and_overlay_shell(app_factory):
    client = app_factory().test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert b'class="upload-toggle"' in response.data
    assert b'aria-haspopup="dialog"' in response.data
    assert b'class="upload-overlay"' in response.data
    assert b'role="dialog"' in response.data
    assert b'aria-modal="true"' in response.data
    assert b'aria-labelledby="upload-title"' in response.data
    assert b'aria-labelledby="upload-title"\n      data-api-import-url=' in response.data
    assert b'data-api-import-url="/api/images/import-url"' in response.data
    assert b'data-api-upload-url="/api/images/import-upload"' in response.data
    assert b'id="upload-title">Upload' in response.data
    assert b'class="upload-close"' in response.data
    assert b'id="upload-url"' in response.data
    assert b'class="upload-url"' in response.data
    assert b'class="upload-url-load" type="button">Load' in response.data
    assert b'class="upload-drop-target"' in response.data
    assert b'aria-label="Choose or drop one image file to upload"' in response.data
    assert b'class="upload-file-input" type="file" accept="image/*" hidden' in (
        response.data
    )
    assert b'class="upload-file-choose" type="button">Choose image' in response.data
    assert b'image/*' in response.data
    assert b'class="upload-status" aria-live="polite"' in response.data
    assert b'class="upload-immich-browser"' not in response.data
    assert b'data-api-immich-assets-url' not in response.data
    assert b'data-api-immich-import-url' not in response.data


def test_index_renders_upload_immich_browser_when_configured(
    app_config,
    app_factory,
):
    immich_config = replace(
        app_config,
        immich_url="https://immich.example.test",
        immich_upload_album_id="",
        immich_api_key="immich-key",
    )
    client = app_factory(IMAGEGEN_APP_CONFIG=immich_config).test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert b'data-api-immich-assets-url="/api/immich/assets"' in response.data
    assert b'data-api-immich-import-url="/api/immich/assets/import"' in response.data
    assert b'class="upload-immich-browser" aria-label="Immich main gallery"' in (
        response.data
    )
    assert b'class="upload-immich-prev" type="button" disabled>Previous' in (
        response.data
    )
    assert b'class="upload-immich-page" aria-live="polite">Page 1' in response.data
    assert b'class="upload-immich-next" type="button" disabled>Next' in response.data
    assert b'class="upload-immich-empty" hidden>No Immich images loaded.' in (
        response.data
    )
    assert b'class="upload-immich-gallery" aria-label="Immich images"' in (
        response.data
    )


def test_index_hides_immich_upload_action_without_upload_album(
    app_config,
    app_factory,
):
    app_config.output_dir.mkdir(parents=True)
    (app_config.output_dir / "source.png").write_bytes(b"image")
    immich_config = replace(
        app_config,
        immich_url="https://immich.example.test",
        immich_upload_album_id="",
        immich_api_key="immich-key",
    )
    client = app_factory(IMAGEGEN_APP_CONFIG=immich_config).test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert b'data-api-immich-assets-url="/api/immich/assets"' in response.data
    assert b'data-immich-upload-url="/api/images/source.png/immich-upload"' not in (
        response.data
    )
    assert b"class=\"gallery-action gallery-immich\"" not in response.data


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
    assert b'class="gallery image-gallery"' in response.data
    assert b'class="gallery-item image-card"' in response.data
    assert b'class="image-card-media" href="/images/source.png"' in response.data
    assert b'class="image-card-ribbon"' in response.data
    assert b'data-filename="source.png"' in response.data
    assert b'data-delete-url="/api/images/source.png/delete"' in response.data
    assert b'data-mask-url="/images/source-mask.png"' in response.data
    assert b'data-mask-save-url="/api/images/source.png/mask"' in response.data
    assert b'href="/images/source.png/download"' in response.data
    assert b'href="/images/source.png/download-clean"' in response.data
    assert b'class="gallery-action gallery-download"' in response.data
    assert b'class="gallery-action gallery-download-clean"' in response.data
    assert b'class="gallery-action gallery-mask"' in response.data
    assert b'aria-label="Download source.png"' in response.data
    assert b'aria-label="Download clean source.png"' in response.data
    assert b'aria-label="Create mask for source.png"' in response.data
    assert b'aria-label="Select source.png as source image"' in response.data
    assert b'title="Load metadata"' in response.data
    assert b'title="Download with metadata"' in response.data
    assert b'title="Download without metadata"' in response.data
    assert b'title="Create mask"' in response.data
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
        immich_upload_album_id="album-123",
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
