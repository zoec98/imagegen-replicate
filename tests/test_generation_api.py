"""Generation API route tests.

Behaviors protected:
- Valid generation requests return pollable queued state and durable request history.
- Invalid generation payloads fail before worker jobs are started.
- Edit-mode source images and annotated prompts are preserved for app history and stripped for providers.
"""

from dataclasses import replace

from imagegen.model_registry import (
    MODEL_REGISTRY,
    PROVIDER_REGISTRIES,
    resolve_model,
)
from route_helpers import extract_csrf_token, expected_response_parameters


def test_api_generate_accepts_json_and_returns_request_id(app_factory):
    model = MODEL_REGISTRY["seedream45"]
    client = app_factory().test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    response = client.post(
        "/api/generate",
        json={
            "prompt": "a small red house",
            "parameters": {"size": "2K"},
        },
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 202
    assert response.json["request_id"]
    assert response.json["status_url"] == (
        f"/api/generation/{response.json['request_id']}"
    )
    assert response.json["poll_seconds"] == 1.0
    assert response.json["provider"] == "replicate"
    assert response.json["model"] == "seedream45"
    assert response.json["status"] == "queued"
    assert response.json["prompt"] == "a small red house"
    assert response.json["source_images"] == []
    assert response.json["parameters"] == expected_response_parameters(
        model,
        {"size": "2K"},
    )
    assert response.json["images"] == []


def test_api_generate_accepts_flux_flex_model_payload(app_factory):
    client = app_factory().test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    response = client.post(
        "/api/generate",
        json={
            "model": "flux-flex",
            "prompt": "a small red house",
            "parameters": {"guidance": "5.5", "output_format": "png"},
        },
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 202
    assert response.json["model"] == "flux-flex"
    assert response.json["parameters"] == {
        "aspect_ratio": "1:1",
        "resolution": "1 MP",
        "safety_tolerance": 2,
        "prompt_upsampling": True,
        "steps": 30,
        "guidance": 5.5,
        "output_format": "png",
        "output_quality": 80,
    }


def test_api_generate_accepts_flux_flex_custom_dimensions_and_blank_seed(app_factory):
    client = app_factory().test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    response = client.post(
        "/api/generate",
        json={
            "model": "flux-flex",
            "prompt": "a small red house",
            "parameters": {
                "aspect_ratio": "custom",
                "width": "1024",
                "height": "768",
                "seed": "",
            },
        },
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 202
    assert response.json["model"] == "flux-flex"
    assert response.json["parameters"] == {
        "aspect_ratio": "custom",
        "width": 1024,
        "height": 768,
        "safety_tolerance": 2,
        "prompt_upsampling": True,
        "steps": 30,
        "guidance": 4.5,
        "output_format": "webp",
        "output_quality": 80,
    }


def test_api_generate_rejects_flux_flex_dimensions_without_custom_aspect_ratio(
    app_factory,
):
    client = app_factory().test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    response = client.post(
        "/api/generate",
        json={
            "model": "flux-flex",
            "prompt": "a small red house",
            "parameters": {"width": 1024, "height": 768},
        },
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 400
    assert response.json == {
        "error": "width and height are only allowed when aspect_ratio is custom."
    }


def test_api_generate_rejects_unknown_model(app_factory):
    client = app_factory().test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    response = client.post(
        "/api/generate",
        json={"model": "unknown", "prompt": "a small red house"},
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 400
    choices = ", ".join(sorted(MODEL_REGISTRY))
    assert response.json == {
        "error": f"Unknown model: unknown. Expected one of: {choices}."
    }


def test_api_generate_rejects_unknown_provider(app_factory):
    client = app_factory().test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    response = client.post(
        "/api/generate",
        json={
            "provider": "unknown",
            "model": "seedream45",
            "prompt": "a small red house",
        },
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 400
    assert response.json == {
        "error": "Unknown provider: unknown. Expected one of: replicate."
    }


def test_api_generate_rejects_disabled_provider(app_factory):
    client = app_factory().test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    response = client.post(
        "/api/generate",
        json={
            "provider": "falai",
            "model": "seedream45",
            "prompt": "a small red house",
        },
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 400
    assert response.json == {"error": "Provider `falai` is not enabled."}


def test_api_generate_rejects_wrong_provider_model_alias(app_config, app_factory):
    app_config = replace(
        app_config,
        fal_key="fal-key",
        enabled_providers=("replicate", "falai"),
    )
    client = app_factory(IMAGEGEN_APP_CONFIG=app_config).test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    response = client.post(
        "/api/generate",
        json={
            "provider": "falai",
            "model": "flux-flex",
            "prompt": "a small red house",
        },
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 400
    assert response.json == {
        "error": "Unknown model: flux-flex. Expected one of: bria-fibo, ernie-image, ernie-image-turbo, flux-2, flux-2-pro, flux-2-realism, gpt-image-2, gpt-image15, grok, hidream-dev, hidream-fast, hidream-full, nano-banana-2, seedream, seedream45, seedream5, zit."
    }


def test_api_generate_logs_falai_edit_requests_to_linked_endpoint(
    app_config, app_factory
):
    app_config = replace(
        app_config,
        fal_key="fal-key",
        enabled_providers=("replicate", "falai"),
    )
    app_config.output_dir.mkdir(parents=True)
    (app_config.output_dir / "source.png").write_bytes(b"image")
    client = app_factory(IMAGEGEN_APP_CONFIG=app_config).test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    response = client.post(
        "/api/generate",
        json={
            "provider": "falai",
            "model": "seedream45",
            "prompt": "edit this",
            "edit_mode": True,
            "source_images": ["source.png"],
        },
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 202
    assert response.json["provider"] == "falai"
    request_log = client.application.config[
        "IMAGEGEN_GENERATION_LOG"
    ].get_logged_request(response.json["request_id"])
    assert request_log is not None
    assert request_log.model == "fal-ai/bytedance/seedream/v4.5/edit"
    assert request_log.request_sent["image_urls"] == ["source.png"]


def test_api_generate_rejects_falai_edit_mode_without_linked_endpoint(
    app_config,
    app_factory,
):
    app_config = replace(
        app_config,
        fal_key="fal-key",
        enabled_providers=("replicate", "falai"),
    )
    app_config.output_dir.mkdir(parents=True)
    (app_config.output_dir / "source.png").write_bytes(b"image")
    client = app_factory(IMAGEGEN_APP_CONFIG=app_config).test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    response = client.post(
        "/api/generate",
        json={
            "provider": "falai",
            "model": "ernie-image",
            "prompt": "edit this",
            "edit_mode": True,
            "source_images": ["source.png"],
        },
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 400
    assert response.json == {
        "error": "Model `falai:ernie-image` does not support image edit mode."
    }


def test_api_generate_rejects_invalid_annotation_before_request_creation(app_factory):
    class RecordingWorker:
        def __init__(self):
            self.started = []

        def start(self, request_record):
            self.started.append(request_record)

    worker = RecordingWorker()
    app = app_factory(IMAGEGEN_WORKER=worker)
    client = app.test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    response = client.post(
        "/api/generate",
        json={"prompt": "portrait of (character: zoe blue hair"},
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 400
    assert response.json == {"error": "Prompt annotation is missing a closing ')'."}
    assert worker.started == []


def test_api_generate_logs_recreatable_request_payload(app_factory):
    app = app_factory()
    model = MODEL_REGISTRY["seedream45"]
    client = app.test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    response = client.post(
        "/api/generate",
        json={
            "prompt": "a small red house",
            "parameters": {"size": "2K"},
        },
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 202
    request_log = app.config["IMAGEGEN_GENERATION_LOG"].get_logged_request(
        response.json["request_id"]
    )
    result = app.config["IMAGEGEN_GENERATION_LOG"].get_logged_result(
        response.json["request_id"]
    )
    assert request_log is not None
    assert result is not None
    assert result.status == "queued"
    assert request_log.model_alias == "seedream45"
    assert request_log.model == "bytedance/seedream-4.5"
    assert request_log.prompt == "a small red house"
    assert request_log.request_sent == {
        **expected_response_parameters(model, {"size": "2K"}),
        **model.fixed_inputs,
        "prompt": "a small red house",
    }


def test_api_generate_logs_annotated_prompt_and_stripped_provider_payload(app_factory):
    app = app_factory()
    client = app.test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)
    prompt = "portrait of (character: zoe blue hair)"

    response = client.post(
        "/api/generate",
        json={"prompt": prompt, "parameters": {"size": "2K"}},
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 202
    assert response.json["prompt"] == prompt
    request_log = app.config["IMAGEGEN_GENERATION_LOG"].get_logged_request(
        response.json["request_id"]
    )
    assert request_log is not None
    assert request_log.prompt == prompt
    assert request_log.request_sent["prompt"] == "portrait of blue hair"


def test_api_generate_starts_configured_worker(app_factory):
    class RecordingWorker:
        def __init__(self):
            self.records = []

        def start(self, request_record):
            self.records.append(request_record)

    worker = RecordingWorker()
    client = app_factory(IMAGEGEN_WORKER=worker).test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    response = client.post(
        "/api/generate",
        json={"prompt": "a small red house"},
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 202
    assert [record.request_id for record in worker.records] == [
        response.json["request_id"]
    ]


def test_api_generate_accepts_existing_source_images(app_config, app_factory):
    app_config.output_dir.mkdir(parents=True)
    (app_config.output_dir / "source.png").write_bytes(b"image")
    client = app_factory().test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    response = client.post(
        "/api/generate",
        json={
            "prompt": "edit this",
            "edit_mode": True,
            "source_images": ["source.png"],
        },
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 202
    assert response.json["source_images"] == ["source.png"]
    request_log = client.application.config[
        "IMAGEGEN_GENERATION_LOG"
    ].get_logged_request(response.json["request_id"])
    assert request_log is not None
    assert request_log.source_images == ["source.png"]
    assert request_log.request_sent["image_input"] == ["source.png"]


def test_api_generate_rejects_invalid_edit_mode(app_factory):
    client = app_factory().test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    response = client.post(
        "/api/generate",
        json={
            "prompt": "edit this",
            "edit_mode": "true",
        },
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 400
    assert response.json == {"error": "edit_mode must be a boolean."}


def test_api_generate_rejects_edit_mode_without_source_images(app_factory):
    client = app_factory().test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    response = client.post(
        "/api/generate",
        json={
            "prompt": "edit this",
            "edit_mode": True,
        },
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 400
    assert response.json == {"error": "edit_mode requires at least one source image."}


def test_api_generate_rejects_source_images_outside_edit_mode(
    app_config,
    app_factory,
):
    app_config.output_dir.mkdir(parents=True)
    (app_config.output_dir / "source.png").write_bytes(b"image")
    client = app_factory().test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    response = client.post(
        "/api/generate",
        json={
            "prompt": "edit this",
            "source_images": ["source.png"],
        },
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 400
    assert response.json == {
        "error": "source_images can only be submitted in edit mode."
    }


def test_api_generate_rejects_edit_mode_for_non_edit_model(
    app_config,
    app_factory,
    monkeypatch,
):
    app_config.output_dir.mkdir(parents=True)
    (app_config.output_dir / "source.png").write_bytes(b"image")
    text_only = replace(
        resolve_model("replicate", "seedream45"), alias="text-only", edit_target=None
    )
    monkeypatch.setitem(
        PROVIDER_REGISTRIES["replicate"],
        "text-only",
        text_only,
    )
    client = app_factory().test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    response = client.post(
        "/api/generate",
        json={
            "model": "text-only",
            "prompt": "edit this",
            "edit_mode": True,
            "source_images": ["source.png"],
        },
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 400
    assert response.json == {
        "error": "Model `replicate:text-only` does not support image edit mode."
    }


def test_api_generate_rejects_missing_source_image(app_factory):
    client = app_factory().test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    response = client.post(
        "/api/generate",
        json={
            "prompt": "edit this",
            "edit_mode": True,
            "source_images": ["missing.png"],
        },
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 400
    assert response.json == {"error": "Source image not found: missing.png."}


def test_api_generate_rejects_gif_source_image(app_config, app_factory):
    app_config.output_dir.mkdir(parents=True)
    (app_config.output_dir / "source.gif").write_bytes(b"gif")
    client = app_factory().test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    response = client.post(
        "/api/generate",
        json={
            "prompt": "edit this",
            "edit_mode": True,
            "source_images": ["source.gif"],
        },
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 400
    assert response.json == {"error": "Invalid source image filename: source.gif."}


def test_api_generate_rejects_blank_prompt(app_factory):
    client = app_factory().test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    response = client.post(
        "/api/generate",
        json={"prompt": "  "},
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 400
    assert response.json == {"error": "Prompt is required."}


def test_api_generate_rejects_non_object_parameters(app_factory):
    client = app_factory().test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    response = client.post(
        "/api/generate",
        json={"prompt": "a small red house", "parameters": ["size", "2K"]},
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 400
    assert response.json == {"error": "parameters must be an object."}


def test_api_generate_rejects_invalid_select_choice(app_factory):
    client = app_factory().test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    response = client.post(
        "/api/generate",
        json={
            "prompt": "a small red house",
            "parameters": {"size": "custom"},
        },
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 400
    assert response.json == {"error": "size must be one of: 2K, 4K."}


def test_api_generate_rejects_out_of_range_integer(app_factory):
    client = app_factory().test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    response = client.post(
        "/api/generate",
        json={
            "prompt": "a small red house",
            "parameters": {"max_images": 99},
        },
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 400
    assert response.json == {"error": "max_images must be at most 15."}


def test_api_generate_rejects_disable_safety_checker_override(app_factory):
    client = app_factory().test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    response = client.post(
        "/api/generate",
        json={
            "prompt": "a small red house",
            "parameters": {"disable_safety_checker": False},
        },
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 400
    assert response.json == {"error": "disable_safety_checker is fixed by the server."}


def test_api_generation_returns_known_request_status(app_factory):
    client = app_factory().test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)
    created = client.post(
        "/api/generate",
        json={"prompt": "a small red house"},
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    response = client.get(f"/api/generation/{created.json['request_id']}")

    assert response.status_code == 200
    assert response.json["request_id"] == created.json["request_id"]
    assert response.json["status_url"] == created.json["status_url"]
    assert response.json["poll_seconds"] == 1.0
    assert response.json["model"] == "seedream45"
    assert response.json["status"] == "queued"
    assert response.json["prompt"] == "a small red house"
    assert response.json["parameters"] == created.json["parameters"]
    assert response.json["source_images"] == []
    assert response.json["error"] is None
    assert response.json["prediction_id"] is None
    assert response.json["output_urls"] == []
    assert response.json["images"] == []
    assert response.json["logs"] == []
    assert response.json["created_at"]
    assert response.json["updated_at"]


def test_api_generation_unknown_request_id_returns_json_404(app_factory):
    client = app_factory().test_client()

    response = client.get("/api/generation/missing")

    assert response.status_code == 404
    assert response.json == {"error": "Generation request not found."}
