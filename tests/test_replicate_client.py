from dataclasses import dataclass

import pytest

from imagegen.config import AppConfig
from imagegen.model_registry import MODEL_REGISTRY
from imagegen.replicate_client import (
    ReplicatePredictionError,
    ReplicatePredictionTimeout,
    build_prediction_input,
    generate_image_urls,
    normalize_output_urls,
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
        data_dir=tmp_path,
        author="Test Author",
        immich_url="",
        immich_gallery_id="",
        immich_api_key="",
        model_alias="seedream45",
        model=MODEL_REGISTRY["seedream45"],
        flask_secret_key="test-secret",
        replicate_poll_seconds=1.0,
        replicate_timeout_seconds=60.0,
    )


def test_build_prediction_input_includes_defaults_and_fixed_inputs():
    payload = build_prediction_input("a red house", MODEL_REGISTRY["seedream45"])

    assert payload["prompt"] == "a red house"
    assert payload["size"] == "2K"
    assert payload["aspect_ratio"] == "match_input_image"
    assert payload["sequential_image_generation"] == "disabled"
    assert payload["max_images"] == 1
    assert payload["disable_safety_checker"] is True
    assert "image_input" not in payload


def test_build_prediction_input_applies_validated_parameters():
    payload = build_prediction_input(
        "a red house",
        MODEL_REGISTRY["seedream45"],
        parameters={
            "size": "4K",
            "aspect_ratio": "1:1",
            "sequential_image_generation": "auto",
            "max_images": 3,
        },
    )

    assert payload["prompt"] == "a red house"
    assert payload["size"] == "4K"
    assert payload["aspect_ratio"] == "1:1"
    assert payload["sequential_image_generation"] == "auto"
    assert payload["max_images"] == 3
    assert payload["disable_safety_checker"] is True


def test_build_prediction_input_applies_source_image_inputs():
    payload = build_prediction_input(
        "edit this",
        MODEL_REGISTRY["seedream45"],
        source_image_inputs=["source.png"],
    )

    assert payload["prompt"] == "edit this"
    assert payload["image_input"] == ["source.png"]
    assert payload["disable_safety_checker"] is True


def test_build_prediction_input_fixed_inputs_override_parameters():
    payload = build_prediction_input(
        "a red house",
        MODEL_REGISTRY["seedream45"],
        parameters={"disable_safety_checker": False},
    )

    assert payload["disable_safety_checker"] is True


def test_build_prediction_input_uses_model_specific_source_image_field():
    payload = build_prediction_input(
        "edit this",
        MODEL_REGISTRY["flux-flex"],
        parameters={"guidance": 5.5},
        source_image_inputs=["source.png"],
    )

    assert payload["prompt"] == "edit this"
    assert payload["input_images"] == ["source.png"]
    assert payload["guidance"] == 5.5
    assert payload["output_format"] == "webp"
    assert "image_input" not in payload
    assert "disable_safety_checker" not in payload


def test_build_prediction_input_uses_single_source_image_field():
    payload = build_prediction_input(
        "edit this",
        MODEL_REGISTRY["qwen-2512"],
        source_image_inputs=["source.png"],
    )

    assert payload["image"] == "source.png"
    assert payload["disable_safety_checker"] is True


def test_build_prediction_input_omits_flux_resolution_for_custom_dimensions():
    payload = build_prediction_input(
        "edit this",
        MODEL_REGISTRY["flux-flex"],
        parameters={
            "aspect_ratio": "custom",
            "width": 1024,
            "height": 768,
        },
    )

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
        persist_images=fake_persist,
    )

    assert result.prediction_id == "abc123"
    assert result.output_urls == ["https://example.com/one.png"]
    assert result.stored_images == [tmp_path / "seedream45-abc123-01.png"]
    assert result.logs == "done"
    assert sleeps == [1.0]
    assert api.create_calls[0]["model"] == MODEL_REGISTRY["seedream45"].replicate_model
    assert api.create_calls[0]["input"]["size"] == "4K"
    assert api.create_calls[0]["input"]["disable_safety_checker"] is True
    assert api.get_calls == ["abc123"]
    assert stored[0][0] == ["https://example.com/one.png"]
    assert stored[0][1]["prediction_id"] == "abc123"


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


def test_normalize_output_urls_handles_common_shapes():
    class UrlObject:
        url = "https://example.com/file.webp"

    assert normalize_output_urls(None) == []
    assert normalize_output_urls("https://example.com/file.png") == [
        "https://example.com/file.png"
    ]
    assert normalize_output_urls(["https://example.com/a.png", UrlObject()]) == [
        "https://example.com/a.png",
        "https://example.com/file.webp",
    ]
