"""Wiro asynchronous client contract tests using fake HTTP responses."""

from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from imagegen.image_store import StoredImage
from imagegen.model_registry import resolve_generation_target, resolve_model
from imagegen.wiro_client import (
    WiroRequestError,
    WiroRequestTimeout,
    generate_image_urls,
)


@dataclass
class FakeResponse:
    status_code: int
    body: dict

    def json(self):
        return self.body


class FakeHTTPClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def post(self, url, *, headers, json=None, data=None, files=None, timeout=None):
        self.calls.append(
            {
                "url": url,
                "headers": dict(headers),
                "json": json,
                "data": data,
                "files": files,
                "timeout": timeout,
            }
        )
        return self.responses.pop(0)


def app_config(tmp_path):
    return SimpleNamespace(
        wiro_api_key="wiro-key",
        output_dir=tmp_path,
        author="Test Author",
        replicate_poll_seconds=1.0,
        replicate_timeout_seconds=60.0,
    )


def test_wiro_text_request_submits_once_polls_same_task_and_persists_outputs(tmp_path):
    model = resolve_model("wiro", "seedream5-pro-uncensored")
    target = resolve_generation_target(
        "wiro", "seedream5-pro-uncensored", edit_mode=False
    )
    client = FakeHTTPClient(
        [
            FakeResponse(200, {"result": True, "errors": [], "taskid": "wiro-123"}),
            FakeResponse(
                200,
                {
                    "result": True,
                    "errors": [],
                    "tasklist": [{"status": "task_queue", "pexit": None}],
                },
            ),
            FakeResponse(
                200,
                {
                    "result": True,
                    "errors": [],
                    "tasklist": [
                        {
                            "id": "wiro-123",
                            "status": "task_postprocess_end",
                            "pexit": "0",
                            "debugoutput": "Request ended.",
                            "outputs": [
                                {
                                    "name": "0.jpg",
                                    "contenttype": "image/jpeg",
                                    "url": "https://cdn1.wiro.ai/output.jpg",
                                }
                            ],
                        }
                    ],
                },
            ),
        ]
    )
    persisted = []

    def persist_images(urls, **kwargs):
        persisted.append({"urls": list(urls), **kwargs})
        return [
            StoredImage(
                path=tmp_path / "seedream5-pro-uncensored-wiro-123-01.jpg",
                source_url=urls[0],
                content_type="image/jpeg",
                size_bytes=123,
                created_at="2026-09-06T12:00:00+00:00",
            )
        ]

    result = generate_image_urls(
        "a cookie (palette: warm tasty)",
        app_config(tmp_path),
        model=model,
        target=target,
        parameters={"resolution": "1k"},
        client=client,
        sleep=lambda _: None,
        clock=lambda: 0.0,
        persist_images=persist_images,
    )

    assert result.prediction_id == "wiro-123"
    assert result.output_urls == ["https://cdn1.wiro.ai/output.jpg"]
    assert result.logs == "Request ended."
    assert len(client.calls) == 3
    assert client.calls[0]["url"] == (
        "https://api.wiro.ai/v1/Run/bytedance/seedream-v5-pro-uncensored"
    )
    assert client.calls[0]["headers"]["x-api-key"] == "wiro-key"
    assert client.calls[0]["json"] == {
        "prompt": "a cookie tasty",
        "resolution": "1k",
        "aspectRatio": "1:1",
        "outputFormat": "jpeg",
        "watermark": "false",
    }
    assert client.calls[1]["json"] == {"taskid": "wiro-123"}
    assert client.calls[2]["json"] == {"taskid": "wiro-123"}
    assert persisted[0]["provider"] == "wiro"
    assert persisted[0]["model_alias"] == "seedream5-pro-uncensored"
    assert persisted[0]["provider_model"] == "bytedance/seedream-v5-pro-uncensored"
    assert persisted[0]["prompt"] == "a cookie (palette: warm tasty)"
    assert persisted[0]["prediction_input"]["prompt"] == "a cookie tasty"


def test_wiro_failed_task_keeps_task_id_without_accepting_outputs(tmp_path):
    model = resolve_model("wiro", "seedream5-lite-uncensored")
    target = resolve_generation_target(
        "wiro", "seedream5-lite-uncensored", edit_mode=False
    )
    client = FakeHTTPClient(
        [
            FakeResponse(200, {"result": True, "errors": [], "taskid": "wiro-456"}),
            FakeResponse(
                200,
                {
                    "result": True,
                    "errors": [],
                    "tasklist": [
                        {
                            "status": "task_postprocess_end",
                            "pexit": "1",
                            "debugoutput": "provider rejected prompt",
                            "outputs": [],
                        }
                    ],
                },
            ),
        ]
    )

    with pytest.raises(WiroRequestError, match="wiro-456.*pexit 1") as raised:
        generate_image_urls(
            "a cookie",
            app_config(tmp_path),
            model=model,
            target=target,
            client=client,
            sleep=lambda _: None,
            clock=lambda: 0.0,
        )
    assert raised.value.task_id == "wiro-456"
    assert "wiro-key" not in str(raised.value)


def test_wiro_polling_timeout_does_not_submit_again(tmp_path):
    model = resolve_model("wiro", "seedream5-pro-uncensored")
    target = resolve_generation_target(
        "wiro", "seedream5-pro-uncensored", edit_mode=False
    )
    client = FakeHTTPClient(
        [
            FakeResponse(200, {"result": True, "errors": [], "taskid": "wiro-789"}),
            FakeResponse(
                200,
                {
                    "result": True,
                    "errors": [],
                    "tasklist": [{"status": "task_start", "pexit": None}],
                },
            ),
        ]
    )
    clock_values = iter((0.0, 61.0))

    with pytest.raises(WiroRequestTimeout, match="wiro-789") as raised:
        generate_image_urls(
            "a cookie",
            app_config(tmp_path),
            model=model,
            target=target,
            client=client,
            sleep=lambda _: None,
            clock=lambda: next(clock_values),
        )
    assert raised.value.task_id == "wiro-789"
    assert len(client.calls) == 2


def test_wiro_rejects_success_without_https_image_output(tmp_path):
    model = resolve_model("wiro", "seedream5-pro-uncensored")
    target = resolve_generation_target(
        "wiro", "seedream5-pro-uncensored", edit_mode=False
    )
    client = FakeHTTPClient(
        [
            FakeResponse(200, {"result": True, "errors": [], "taskid": "wiro-999"}),
            FakeResponse(
                200,
                {
                    "result": True,
                    "errors": [],
                    "tasklist": [
                        {
                            "status": "task_postprocess_end",
                            "pexit": "0",
                            "outputs": [{"url": "http://unsafe.example/out.png"}],
                        }
                    ],
                },
            ),
        ]
    )

    with pytest.raises(WiroRequestError, match="no valid HTTPS image URLs"):
        generate_image_urls(
            "a cookie",
            app_config(tmp_path),
            model=model,
            target=target,
            client=client,
            sleep=lambda _: None,
            clock=lambda: 0.0,
        )


@pytest.mark.parametrize(
    ("status_code", "message", "expected"),
    [
        (401, "bad key", "authentication failed"),
        (429, "slow down", "rate limit"),
        (422, "invalid resolution", "HTTP 422"),
    ],
)
def test_wiro_http_failures_are_actionable_without_credentials(
    tmp_path,
    status_code,
    message,
    expected,
):
    model = resolve_model("wiro", "seedream5-pro-uncensored")
    target = resolve_generation_target(
        "wiro", "seedream5-pro-uncensored", edit_mode=False
    )
    client = FakeHTTPClient(
        [FakeResponse(status_code, {"result": False, "errors": [{"message": message}]})]
    )

    with pytest.raises(WiroRequestError, match=expected) as raised:
        generate_image_urls(
            "a cookie",
            app_config(tmp_path),
            model=model,
            target=target,
            client=client,
        )
    assert "wiro-key" not in str(raised.value)


def test_wiro_rejects_malformed_task_detail_response(tmp_path):
    model = resolve_model("wiro", "seedream5-pro-uncensored")
    target = resolve_generation_target(
        "wiro", "seedream5-pro-uncensored", edit_mode=False
    )
    client = FakeHTTPClient(
        [
            FakeResponse(200, {"result": True, "errors": [], "taskid": "wiro-bad"}),
            FakeResponse(200, {"result": True, "errors": [], "tasklist": []}),
        ]
    )

    with pytest.raises(WiroRequestError, match="did not include a task object"):
        generate_image_urls(
            "a cookie",
            app_config(tmp_path),
            model=model,
            target=target,
            client=client,
            sleep=lambda _: None,
            clock=lambda: 0.0,
        )
