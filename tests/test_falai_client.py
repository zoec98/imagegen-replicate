"""fal.ai provider boundary tests.

Behaviors protected:
- fal.ai submissions use the resolved endpoint and provider-shaped request payload.
- Edit requests upload local source images and keep local filenames in stored metadata.
- fal.ai request ids, normalized outputs, timeouts, and failures are surfaced clearly.
"""

from dataclasses import replace
from pathlib import Path

import pytest
from fal_client.client import Completed, InProgress, Queued

from imagegen.config import AppConfig
from imagegen.falai_client import (
    FalAIRequestError,
    FalAIRequestTimeout,
    generate_image_urls,
    normalize_output_urls,
)
from imagegen.image_store import StoredImage
from imagegen.model_registry import (
    MODEL_REGISTRY,
    resolve_generation_target,
    resolve_model,
)


class FakeHandle:
    def __init__(self, *, request_id, statuses, result):
        self.request_id = request_id
        self._statuses = list(statuses)
        self._result = result
        self.status_calls = []

    def status(self, *, with_logs=False):
        self.status_calls.append(with_logs)
        if len(self._statuses) > 1:
            return self._statuses.pop(0)
        return self._statuses[0]

    def get(self):
        return self._result


class FakeFalClient:
    def __init__(self, *, handle, uploads=None):
        self.handle = handle
        self.uploads = uploads or {}
        self.submit_calls = []
        self.upload_calls = []

    def submit(self, application, arguments):
        self.submit_calls.append(
            {"application": application, "arguments": dict(arguments)}
        )
        return self.handle

    def upload_file(self, path):
        path = Path(path)
        self.upload_calls.append(path)
        return self.uploads[path]


def app_config(tmp_path):
    return AppConfig(
        replicate_api_token="",
        fal_key="fal-key",
        enabled_providers=("falai",),
        selected_provider="falai",
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


def test_falai_text_submission_uses_resolved_endpoint_and_persists_outputs(tmp_path):
    model = resolve_model("falai", "seedream45")
    target = resolve_generation_target("falai", "seedream45", edit_mode=False)
    handle = FakeHandle(
        request_id="fal-request-123",
        statuses=[
            Queued(position=1),
            InProgress(logs=[{"message": "rendering"}]),
            Completed(logs=[{"message": "done"}], metrics={}),
        ],
        result={"images": [{"url": "https://example.test/out.png"}]},
    )
    client = FakeFalClient(handle=handle)
    persisted = []

    def persist_images(urls, **kwargs):
        persisted.append({"urls": list(urls), **kwargs})
        return [
            StoredImage(
                path=tmp_path / "seedream45-fal-request-123-01.png",
                source_url=urls[0],
                content_type="image/png",
                size_bytes=123,
                created_at="2026-06-03T10:00:00+00:00",
            )
        ]

    result = generate_image_urls(
        "a red house",
        app_config(tmp_path),
        model=model,
        target=target,
        parameters={"image_size": "auto_4K"},
        client=client,
        sleep=lambda _: None,
        clock=lambda: 0.0,
        persist_images=persist_images,
    )

    assert client.submit_calls == [
        {
            "application": "fal-ai/bytedance/seedream/v4.5/text-to-image",
            "arguments": {
                "prompt": "a red house",
                "image_size": "auto_4K",
                "num_images": 1,
                "max_images": 1,
                "sync_mode": False,
                "enable_safety_checker": False,
            },
        }
    ]
    assert result.prediction_id == "fal-request-123"
    assert result.output_urls == ["https://example.test/out.png"]
    assert result.logs == "done"
    assert persisted[0]["provider"] == "falai"
    assert persisted[0]["model_alias"] == "seedream45"
    assert persisted[0]["provider_model"] == target.provider_model
    assert persisted[0]["prediction_input"]["prompt"] == "a red house"


def test_falai_edit_submission_uploads_source_images_and_keeps_local_names_in_metadata(
    tmp_path,
):
    model = resolve_model("falai", "seedream45")
    target = resolve_generation_target("falai", "seedream45", edit_mode=True)
    source_path = tmp_path / "images" / "source.png"
    source_path.parent.mkdir(parents=True)
    source_path.write_bytes(b"source")
    handle = FakeHandle(
        request_id="fal-request-456",
        statuses=[Completed(logs=[{"message": "done"}], metrics={})],
        result={"images": ["https://example.test/edited.png"]},
    )
    client = FakeFalClient(
        handle=handle,
        uploads={source_path: "https://uploads.test/source.png"},
    )
    persisted = []

    def persist_images(urls, **kwargs):
        persisted.append({"urls": list(urls), **kwargs})
        return []

    config = replace(app_config(tmp_path), data_dir=tmp_path)
    generate_image_urls(
        "edit this",
        config,
        model=model,
        target=target,
        parameters={"image_size": "auto_2K"},
        source_image_paths=[source_path],
        client=client,
        sleep=lambda _: None,
        clock=lambda: 0.0,
        persist_images=persist_images,
    )

    assert client.upload_calls == [source_path]
    assert (
        client.submit_calls[0]["application"] == "fal-ai/bytedance/seedream/v4.5/edit"
    )
    assert client.submit_calls[0]["arguments"]["image_urls"] == [
        "https://uploads.test/source.png"
    ]
    assert persisted[0]["prediction_input"]["image_urls"] == ["source.png"]


def test_falai_client_reports_actionable_provider_failures(tmp_path):
    model = resolve_model("falai", "seedream45")
    target = resolve_generation_target("falai", "seedream45", edit_mode=False)
    handle = FakeHandle(
        request_id="fal-request-789",
        statuses=[
            Completed(
                logs=[{"message": "validation failed"}],
                metrics={},
                error="bad prompt",
                error_type="validation_error",
            )
        ],
        result=None,
    )
    client = FakeFalClient(handle=handle)

    with pytest.raises(
        FalAIRequestError,
        match="fal-request-789 failed: validation_error: bad prompt",
    ):
        generate_image_urls(
            "a red house",
            app_config(tmp_path),
            model=model,
            target=target,
            client=client,
            sleep=lambda _: None,
            clock=lambda: 0.0,
            persist_images=lambda urls, **kwargs: [],
        )


def test_falai_client_times_out_when_request_never_completes(tmp_path):
    model = resolve_model("falai", "seedream45")
    target = resolve_generation_target("falai", "seedream45", edit_mode=False)
    handle = FakeHandle(
        request_id="fal-request-timeout",
        statuses=[Queued(position=1), Queued(position=1)],
        result=None,
    )
    client = FakeFalClient(handle=handle)
    times = iter([0.0, 0.0, 61.0])

    with pytest.raises(
        FalAIRequestTimeout,
        match="fal.ai request fal-request-timeout timed out after 60s.",
    ):
        generate_image_urls(
            "a red house",
            app_config(tmp_path),
            model=model,
            target=target,
            client=client,
            sleep=lambda _: None,
            clock=lambda: next(times),
            persist_images=lambda urls, **kwargs: [],
        )


def test_falai_output_normalization_handles_common_nested_shapes():
    assert normalize_output_urls(
        {
            "data": {
                "images": [
                    {"url": "https://example.test/one.png"},
                    {"url": "https://example.test/two.png"},
                ]
            }
        }
    ) == [
        "https://example.test/one.png",
        "https://example.test/two.png",
    ]
