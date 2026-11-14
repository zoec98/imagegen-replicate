"""Replicate provider boundary tests.

Behaviors protected:
- Replicate payloads include registry defaults, fixed inputs, prompts, and source images.
- Replicate predictions are created, polled, timed out, and failed through the provider boundary.
- Successful outputs are normalized and handed to local image persistence with metadata.
"""

import json
from dataclasses import dataclass, replace

import httpx
import pytest

from imagegen.config import AppConfig
from imagegen.model_registry import (
    MODEL_REGISTRY,
    resolve_generation_target,
    resolve_model,
)
from imagegen.replicate_client import (
    ReplicatePredictionError,
    ReplicatePredictionTimeout,
    _replicate_predictions,
)
from imagegen.replicate_client import (
    generate_image_urls as _generate_image_urls,
)


@dataclass
class FakePrediction:
    id: str
    status: str
    output: object = None
    error: str | None = None
    logs: str | None = None


class FakePredictionsApi:
    def __init__(self, created, updates):
        self.created = created
        self.updates = list(updates)
        self.create_calls = []
        self.get_calls = []

    def create(self, *, model, input):
        self.create_calls.append({"model": model, "input": input})
        return self.created

    def get(self, id):
        self.get_calls.append(id)
        return self.updates.pop(0)


class FailingCreatePredictionsApi:
    def __init__(self):
        self.input = None

    def create(self, *, model, input):
        self.input = input
        raise RuntimeError("create failed")

    def get(self, id):
        raise AssertionError("get should not be called")


def app_config(tmp_path):
    return AppConfig(
        replicate_api_token="test-token",
        fal_key="",
        enabled_providers=("replicate",),
        selected_provider="replicate",
        data_dir=tmp_path,
        author="Test Author",
        immich_url="",
        immich_upload_album_id="",
        immich_api_key="",
        model_alias="seedream45",
        model=MODEL_REGISTRY["seedream45"],
        flask_secret_key="test-secret",
        replicate_poll_seconds=1.0,
        replicate_timeout_seconds=60.0,
        trashcan_hold_limit_days=7,
    )


def config_for_model(tmp_path, alias):
    model = MODEL_REGISTRY[alias]
    return replace(app_config(tmp_path), model_alias=alias, model=model)


def generate_image_urls(prompt, config, *, source_image_paths=None, **kwargs):
    model = resolve_model("replicate", config.model_alias)
    target = resolve_generation_target(
        "replicate",
        config.model_alias,
        edit_mode=bool(source_image_paths),
    )
    return _generate_image_urls(
        prompt,
        config,
        model=model,
        target=target,
        source_image_paths=source_image_paths,
        **kwargs,
    )


def test_provider_payload_includes_defaults_and_fixed_inputs(tmp_path):
    target = resolve_generation_target("replicate", "seedream45", edit_mode=False)
    api = FakePredictionsApi(
        FakePrediction(id="abc123", status="succeeded", output=[]),
        [],
    )

    generate_image_urls(
        "a red house",
        config_for_model(tmp_path, "seedream45"),
        predictions_api=api,
        persist_images=lambda urls, **kwargs: [],
    )

    payload = api.create_calls[0]["input"]
    assert payload["prompt"] == "a red house"
    assert payload == {
        "prompt": "a red house",
        "size": "4K",
        "aspect_ratio": "3:4",
        "sequential_image_generation": "disabled",
        "max_images": 1,
        "disable_safety_checker": True,
    }
    assert payload["disable_safety_checker"] is True
    assert (
        target.source_images is None
        or target.source_images.provider_field not in payload
    )


def test_provider_payload_applies_validated_parameters(tmp_path):
    api = FakePredictionsApi(
        FakePrediction(id="abc123", status="succeeded", output=[]),
        [],
    )

    generate_image_urls(
        "a red house",
        config_for_model(tmp_path, "seedream45"),
        parameters={
            "size": "4K",
            "aspect_ratio": "1:1",
            "sequential_image_generation": "auto",
            "max_images": 3,
        },
        predictions_api=api,
        persist_images=lambda urls, **kwargs: [],
    )

    payload = api.create_calls[0]["input"]
    assert payload["prompt"] == "a red house"
    assert payload["size"] == "4K"
    assert payload["aspect_ratio"] == "1:1"
    assert payload["sequential_image_generation"] == "auto"
    assert payload["max_images"] == 3
    assert payload["disable_safety_checker"] is True


def test_provider_payload_fixed_inputs_override_parameters(tmp_path):
    api = FakePredictionsApi(
        FakePrediction(id="abc123", status="succeeded", output=[]),
        [],
    )

    generate_image_urls(
        "a red house",
        config_for_model(tmp_path, "seedream45"),
        parameters={"disable_safety_checker": False},
        predictions_api=api,
        persist_images=lambda urls, **kwargs: [],
    )

    assert api.create_calls[0]["input"]["disable_safety_checker"] is True


def test_provider_payload_applies_source_image_inputs(tmp_path):
    source_path = tmp_path / "source.png"
    source_path.write_bytes(b"source-bytes")
    api = FakePredictionsApi(
        FakePrediction(id="abc123", status="succeeded", output=[]),
        [],
    )

    generate_image_urls(
        "edit this",
        config_for_model(tmp_path, "seedream45"),
        source_image_paths=[source_path],
        predictions_api=api,
        persist_images=lambda urls, **kwargs: [],
    )

    payload = api.create_calls[0]["input"]
    assert payload["prompt"] == "edit this"
    assert len(payload["image_input"]) == 1
    assert payload["image_input"][0].name == str(source_path)
    assert payload["image_input"][0].closed is True
    assert payload["disable_safety_checker"] is True


def test_provider_payload_uses_model_specific_source_image_field(tmp_path):
    source_path = tmp_path / "source.png"
    source_path.write_bytes(b"source-bytes")
    api = FakePredictionsApi(
        FakePrediction(id="abc123", status="succeeded", output=[]),
        [],
    )

    generate_image_urls(
        "edit this",
        config_for_model(tmp_path, "flux-flex"),
        parameters={"guidance": 5.5},
        source_image_paths=[source_path],
        predictions_api=api,
        persist_images=lambda urls, **kwargs: [],
    )

    payload = api.create_calls[0]["input"]
    assert payload["prompt"] == "edit this"
    assert len(payload["input_images"]) == 1
    assert payload["input_images"][0].name == str(source_path)
    assert payload["guidance"] == 5.5
    assert payload["output_format"] == "webp"
    assert "image_input" not in payload
    assert "disable_safety_checker" not in payload


def test_provider_payload_uses_single_source_image_field(tmp_path):
    source_path = tmp_path / "source.png"
    source_path.write_bytes(b"source-bytes")
    api = FakePredictionsApi(
        FakePrediction(id="abc123", status="succeeded", output=[]),
        [],
    )

    generate_image_urls(
        "edit this",
        config_for_model(tmp_path, "qwen-2512"),
        source_image_paths=[source_path],
        predictions_api=api,
        persist_images=lambda urls, **kwargs: [],
    )

    payload = api.create_calls[0]["input"]
    assert payload["image"].name == str(source_path)
    assert payload["image"].closed is True
    assert payload["disable_safety_checker"] is True


def test_provider_payload_omits_flux_resolution_for_custom_dimensions(tmp_path):
    api = FakePredictionsApi(
        FakePrediction(id="abc123", status="succeeded", output=[]),
        [],
    )

    generate_image_urls(
        "edit this",
        config_for_model(tmp_path, "flux-flex"),
        parameters={
            "aspect_ratio": "custom",
            "width": 1024,
            "height": 768,
        },
        predictions_api=api,
        persist_images=lambda urls, **kwargs: [],
    )

    payload = api.create_calls[0]["input"]
    assert payload["aspect_ratio"] == "custom"
    assert payload["width"] == 1024
    assert payload["height"] == 768
    assert "resolution" not in payload


def test_generate_image_urls_creates_prediction_and_polls(tmp_path):
    created = FakePrediction(id="abc123", status="processing")
    completed = FakePrediction(
        id="abc123",
        status="succeeded",
        output=["https://example.com/one.png"],
        logs="done",
    )
    api = FakePredictionsApi(created, [completed])
    sleeps = []
    stored = []

    def fake_persist(urls, **kwargs):
        stored.append((urls, kwargs))
        return [tmp_path / "seedream45-abc123-01.png"]

    result = generate_image_urls(
        "a red house",
        app_config(tmp_path),
        parameters={"size": "4K"},
        predictions_api=api,
        sleep=sleeps.append,
        local_request_id="local-request-uuid",
        persist_images=fake_persist,
    )

    assert result.prediction_id == "abc123"
    assert result.output_urls == ["https://example.com/one.png"]
    assert result.stored_images == [tmp_path / "seedream45-abc123-01.png"]
    assert result.logs == "done"
    assert sleeps == [1.0]
    target = resolve_generation_target("replicate", "seedream45", edit_mode=False)
    assert api.create_calls[0]["model"] == target.provider_model
    assert api.create_calls[0]["input"]["size"] == "4K"
    assert api.create_calls[0]["input"]["disable_safety_checker"] is True
    assert api.get_calls == ["abc123"]
    assert stored[0][0] == ["https://example.com/one.png"]
    assert stored[0][1]["prediction_id"] == "abc123"
    assert stored[0][1]["local_request_id"] == "local-request-uuid"
    assert stored[0][1]["author"] == "Test Author"


def test_generate_image_urls_strips_provider_prompt_but_persists_annotated_prompt(
    tmp_path,
):
    created = FakePrediction(id="abc123", status="succeeded", output=[])
    api = FakePredictionsApi(created, [])
    stored = []
    prompt = "portrait of (character: zoe blue hair)"

    def fake_persist(urls, **kwargs):
        stored.append((urls, kwargs))
        return []

    generate_image_urls(
        prompt,
        app_config(tmp_path),
        predictions_api=api,
        persist_images=fake_persist,
    )

    assert api.create_calls[0]["input"]["prompt"] == "portrait of blue hair"
    assert stored[0][1]["prompt"] == prompt
    assert stored[0][1]["prediction_input"]["prompt"] == "portrait of blue hair"


def test_generate_image_urls_passes_source_image_files_and_metadata(tmp_path):
    source_path = tmp_path / "source.png"
    source_path.write_bytes(b"source-bytes")
    created = FakePrediction(id="abc123", status="succeeded", output=[])
    api = FakePredictionsApi(created, [])
    stored = []

    def fake_persist(urls, **kwargs):
        stored.append((urls, kwargs))
        return []

    generate_image_urls(
        "edit this",
        app_config(tmp_path),
        source_image_paths=[source_path],
        predictions_api=api,
        persist_images=fake_persist,
    )

    image_input = api.create_calls[0]["input"]["image_input"]
    assert len(image_input) == 1
    assert image_input[0].name == str(source_path)
    assert image_input[0].closed is True
    assert stored[0][1]["prediction_input"]["image_input"] == ["source.png"]


def test_generate_image_urls_closes_source_files_when_prediction_create_fails(tmp_path):
    source_path = tmp_path / "source.png"
    source_path.write_bytes(b"source-bytes")
    api = FailingCreatePredictionsApi()

    with pytest.raises(RuntimeError, match="create failed"):
        generate_image_urls(
            "edit this",
            app_config(tmp_path),
            source_image_paths=[source_path],
            predictions_api=api,
        )

    assert api.input is not None
    image_input = api.input["image_input"]
    assert len(image_input) == 1
    assert image_input[0].closed is True


def test_generate_image_urls_raises_on_failed_prediction(tmp_path):
    api = FakePredictionsApi(
        FakePrediction(id="abc123", status="processing"),
        [FakePrediction(id="abc123", status="failed", error="bad prompt")],
    )

    with pytest.raises(ReplicatePredictionError, match="bad prompt"):
        generate_image_urls(
            "a red house",
            app_config(tmp_path),
            predictions_api=api,
            sleep=lambda seconds: None,
            persist_images=lambda urls, **kwargs: [],
        )


def test_generate_image_urls_times_out(tmp_path):
    api = FakePredictionsApi(
        FakePrediction(id="abc123", status="processing"),
        [FakePrediction(id="abc123", status="processing")],
    )
    now = iter([0.0, 61.0])

    with pytest.raises(ReplicatePredictionTimeout):
        generate_image_urls(
            "a red house",
            app_config(tmp_path),
            predictions_api=api,
            sleep=lambda seconds: None,
            clock=lambda: next(now),
            persist_images=lambda urls, **kwargs: [],
        )


@pytest.mark.parametrize(
    ("provider_output", "expected_urls"),
    [
        (None, []),
        ("https://example.com/file.png", ["https://example.com/file.png"]),
    ],
)
def test_generate_image_urls_normalizes_common_provider_output_shapes(
    tmp_path,
    provider_output,
    expected_urls,
):
    api = FakePredictionsApi(
        FakePrediction(id="abc123", status="succeeded", output=provider_output),
        [],
    )
    persisted = []

    def fake_persist(urls, **kwargs):
        persisted.append(urls)
        return []

    result = generate_image_urls(
        "a red house",
        app_config(tmp_path),
        predictions_api=api,
        persist_images=fake_persist,
    )

    assert result.output_urls == expected_urls
    assert persisted == [expected_urls]


def test_generate_image_urls_normalizes_nested_provider_output_objects(tmp_path):
    class UrlObject:
        url = "https://example.com/file.webp"

    api = FakePredictionsApi(
        FakePrediction(
            id="abc123",
            status="succeeded",
            output=["https://example.com/a.png", UrlObject()],
        ),
        [],
    )

    result = generate_image_urls(
        "a red house",
        app_config(tmp_path),
        predictions_api=api,
        persist_images=lambda urls, **kwargs: [],
    )

    assert result.output_urls == [
        "https://example.com/a.png",
        "https://example.com/file.webp",
    ]


@pytest.mark.parametrize(
    "alias",
    [
        "gpt-image-25-flare",
        "gpt-image-25-sunburst",
        "gpt-image-26-flare",
        "gpt-image-26-sunburst",
    ],
)
def test_replicate_predictions_accepts_null_version_for_versionless_models(
    tmp_path, alias
):
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append((request.method, request.url.path, request.content))
        if request.method == "POST":
            return httpx.Response(
                201,
                json={
                    "id": "pred-123",
                    "model": f"openai/{alias}",
                    "version": None,
                    "status": "starting",
                    "output": None,
                    "error": None,
                    "logs": None,
                },
            )
        if request.method == "GET" and request.url.path == "/v1/predictions/pred-123":
            return httpx.Response(
                200,
                json={
                    "id": "pred-123",
                    "model": f"openai/{alias}",
                    "version": None,
                    "status": "succeeded",
                    "output": ["https://replicate.delivery/out.webp"],
                    "error": None,
                    "logs": "ok",
                },
            )
        raise AssertionError(f"Unexpected request: {request.method} {request.url}")

    api = _replicate_predictions(
        config_for_model(tmp_path, alias),
        transport=httpx.MockTransport(handler),
    )

    result = generate_image_urls(
        "a red house",
        config_for_model(tmp_path, alias),
        predictions_api=api,
        sleep=lambda seconds: None,
        persist_images=lambda urls, **kwargs: [],
    )

    model_slug = MODEL_REGISTRY[alias].text_target.provider_model
    assert requests[0][:2] == ("POST", f"/v1/models/{model_slug}/predictions")
    assert json.loads(requests[0][2])["input"]["prompt"] == "a red house"
    assert requests[1][:2] == ("GET", "/v1/predictions/pred-123")
    assert result.prediction_id == "pred-123"
    assert result.output_urls == ["https://replicate.delivery/out.webp"]
    assert result.logs == "ok"


def test_replicate_predictions_uploads_source_images_with_null_version(tmp_path):
    source_path = tmp_path / "source.png"
    source_path.write_bytes(b"png-bytes")
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append((request.method, request.url.path, request.content))
        if request.url.path == "/v1/files":
            return httpx.Response(
                201,
                json={
                    "id": "file-1",
                    "name": "source.png",
                    "content_type": "image/png",
                    "size": 9,
                    "etag": "etag",
                    "checksums": {},
                    "metadata": {},
                    "created_at": "2026-11-13T00:00:00Z",
                    "expires_at": None,
                    "urls": {"get": "https://api.replicate.com/v1/files/file-1"},
                },
            )
        if request.url.path == "/v1/models/openai/gpt-image-2.6-flare/predictions":
            return httpx.Response(
                201,
                json={
                    "id": "pred-edit",
                    "status": "succeeded",
                    "output": ["https://replicate.delivery/edited.webp"],
                },
            )
        raise AssertionError(f"Unexpected request: {request.method} {request.url}")

    api = _replicate_predictions(
        config_for_model(tmp_path, "gpt-image-26-flare"),
        transport=httpx.MockTransport(handler),
    )

    result = generate_image_urls(
        "make it blue",
        config_for_model(tmp_path, "gpt-image-26-flare"),
        source_image_paths=[source_path],
        predictions_api=api,
        persist_images=lambda urls, **kwargs: [],
    )

    assert requests[0][:2] == ("POST", "/v1/files")
    assert requests[1][:2] == (
        "POST",
        "/v1/models/openai/gpt-image-2.6-flare/predictions",
    )
    payload = json.loads(requests[1][2])
    assert payload["input"]["input_images"] == [
        "https://api.replicate.com/v1/files/file-1"
    ]
    assert result.output_urls == ["https://replicate.delivery/edited.webp"]


def test_replicate_predictions_rejects_invalid_payload_or_model(tmp_path):
    def bad_payload_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(201, json={"status": "starting"})

    api = _replicate_predictions(
        app_config(tmp_path),
        transport=httpx.MockTransport(bad_payload_handler),
    )

    with pytest.raises(ReplicatePredictionError, match="without id or status"):
        api.create(model="openai/gpt-image-2.6-flare", input={"prompt": "test"})

    with pytest.raises(ValueError, match="Invalid Replicate model identifier"):
        api.create(model="openai/gpt-image-2.6-flare:abc", input={"prompt": "test"})
