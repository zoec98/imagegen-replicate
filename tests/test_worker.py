"""Generation worker behavior tests.

Behaviors protected:
- Generation workers update request state for success, failure, and timeout outcomes.
- Worker runs persist lifecycle and generated asset history.
- Background worker start returns before generation work completes.
"""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event

from imagegen.generation_log import SQLiteGenerationLog
from imagegen.image_store import StoredImage
from imagegen.replicate_client import ReplicatePredictionTimeout, ReplicateResult
from imagegen.request_store import RequestStore
from imagegen.worker import ThreadedGenerationWorker, run_generation_request


def test_run_generation_request_succeeded_updates_request(app_config):
    store = RequestStore()
    source_path = app_config.output_dir / "source.png"
    source_path.parent.mkdir(parents=True)
    source_path.write_bytes(b"image")
    record = store.create(
        provider="replicate",
        prompt="a red house",
        parameters={"size": "2K"},
        source_images=["source.png"],
        edit_mode=True,
    )

    def fake_generate(prompt, config, *, parameters, source_image_paths):
        assert prompt == "a red house"
        assert config.output_dir == app_config.output_dir
        assert config.model_alias == "seedream45"
        assert parameters == {"size": "2K"}
        assert source_image_paths == [source_path]
        return ReplicateResult(
            prediction_id="prediction-123",
            output_urls=["https://example.test/image.png"],
            stored_images=[Path("seedream45-prediction-123-01.png")],
            logs="created\nfinished",
        )

    run_generation_request(store, record, app_config, fake_generate)

    assert record.status == "succeeded"
    assert record.prediction_id == "prediction-123"
    assert record.output_urls == ["https://example.test/image.png"]
    assert record.images == ["seedream45-prediction-123-01.png"]
    assert record.logs == ["created", "finished"]
    assert record.error is None


def test_run_generation_request_failed_updates_error(app_config):
    store = RequestStore()
    record = store.create(provider="replicate", prompt="a red house", parameters={})

    def fake_generate(prompt, config, *, parameters, source_image_paths):
        raise RuntimeError("Replicate failed.")

    run_generation_request(store, record, app_config, fake_generate)

    assert record.status == "failed"
    assert record.error == "Replicate failed."


def test_run_generation_request_timeout_updates_timeout(app_config):
    store = RequestStore()
    record = store.create(provider="replicate", prompt="a red house", parameters={})

    def fake_generate(prompt, config, *, parameters, source_image_paths):
        raise ReplicatePredictionTimeout("Timed out.")

    run_generation_request(store, record, app_config, fake_generate)

    assert record.status == "timeout"
    assert record.error == "Timed out."


def test_run_generation_request_logs_lifecycle_and_results(app_config):
    store = RequestStore()
    record = store.create(provider="replicate", prompt="a red house", parameters={})
    generation_log = SQLiteGenerationLog(app_config.generation_log_path)
    generation_log.initialize()
    generation_log.create_request(
        record,
        model_alias="seedream45",
        model="bytedance/seedream-4.5",
        replicate_input={"prompt": "a red house"},
    )
    stored_image = StoredImage(
        path=app_config.output_dir / "seedream45-prediction-123-01.png",
        source_url="https://example.test/image.png",
        content_type="image/png",
        size_bytes=123,
        created_at="2026-05-30T12:00:00+00:00",
    )

    def fake_generate(prompt, config, *, parameters, source_image_paths):
        return ReplicateResult(
            prediction_id="prediction-123",
            output_urls=["https://example.test/image.png"],
            stored_images=[stored_image],
            logs="created\nfinished",
        )

    run_generation_request(
        store,
        record,
        app_config,
        fake_generate,
        generation_log,
    )

    result = generation_log.get_logged_result(record.request_id)
    assets = generation_log.list_logged_assets(record.request_id)
    assert result is not None
    assert result.status == "succeeded"
    assert result.started_at
    assert result.completed_at
    assert result.prediction_id == "prediction-123"
    assert result.logs == ["created", "finished"]
    assert result.elapsed_seconds is not None
    assert result.elapsed_seconds >= 0
    assert len(assets) == 1
    assert assets[0].sequence == 1
    assert assets[0].filename == "seedream45-prediction-123-01.png"
    assert assets[0].source_url == "https://example.test/image.png"
    assert assets[0].content_type == "image/png"
    assert assets[0].size_bytes == 123


def test_run_generation_request_persists_multiple_assets(app_config):
    store = RequestStore()
    record = store.create(provider="replicate", prompt="a red house", parameters={})
    generation_log = SQLiteGenerationLog(app_config.generation_log_path)
    generation_log.initialize()
    generation_log.create_request(
        record,
        model_alias="seedream45",
        model="bytedance/seedream-4.5",
        replicate_input={"prompt": "a red house"},
    )
    stored_images = [
        StoredImage(
            path=app_config.output_dir / "seedream45-prediction-123-01.png",
            source_url="https://example.test/image-1.png",
            content_type="image/png",
            size_bytes=123,
            created_at="2026-05-30T12:00:00+00:00",
        ),
        StoredImage(
            path=app_config.output_dir / "seedream45-prediction-123-02.png",
            source_url="https://example.test/image-2.png",
            content_type="image/png",
            size_bytes=456,
            created_at="2026-05-30T12:00:01+00:00",
        ),
    ]

    def fake_generate(prompt, config, *, parameters, source_image_paths):
        return ReplicateResult(
            prediction_id="prediction-123",
            output_urls=[
                "https://example.test/image-1.png",
                "https://example.test/image-2.png",
            ],
            stored_images=stored_images,
            logs="created\nfinished",
        )

    run_generation_request(
        store,
        record,
        app_config,
        fake_generate,
        generation_log,
    )

    result = generation_log.get_logged_result(record.request_id)
    assets = generation_log.list_logged_assets(record.request_id)
    assert result is not None
    assert result.status == "succeeded"
    assert result.prediction_id == "prediction-123"
    assert [asset.filename for asset in assets] == [
        "seedream45-prediction-123-01.png",
        "seedream45-prediction-123-02.png",
    ]


def test_run_generation_request_logs_failure(app_config):
    store = RequestStore()
    record = store.create(provider="replicate", prompt="a red house", parameters={})
    generation_log = SQLiteGenerationLog(app_config.generation_log_path)
    generation_log.initialize()
    generation_log.create_request(
        record,
        model_alias="seedream45",
        model="bytedance/seedream-4.5",
        replicate_input={"prompt": "a red house"},
    )

    def fake_generate(prompt, config, *, parameters, source_image_paths):
        raise RuntimeError("Replicate failed.")

    run_generation_request(
        store,
        record,
        app_config,
        fake_generate,
        generation_log,
    )

    result = generation_log.get_logged_result(record.request_id)
    assert result is not None
    assert result.status == "failed"
    assert result.started_at
    assert result.completed_at
    assert result.error == "Replicate failed."
    assert generation_log.list_logged_assets(record.request_id) == []


def test_run_generation_request_uses_request_model(app_config):
    store = RequestStore()
    record = store.create(
        provider="replicate",
        model_alias="flux-flex",
        prompt="a red house",
        parameters={"guidance": 5.5},
    )

    def fake_generate(prompt, config, *, parameters, source_image_paths):
        assert config.model_alias == "flux-flex"
        assert config.model.replicate_model == "black-forest-labs/flux-2-flex"
        return ReplicateResult(
            prediction_id="prediction-123",
            output_urls=[],
            stored_images=[],
            logs="done",
        )

    run_generation_request(store, record, app_config, fake_generate)

    assert record.status == "succeeded"


def test_threaded_worker_start_returns_before_generation_completes(app_config):
    store = RequestStore()
    record = store.create(provider="replicate", prompt="a red house", parameters={})
    started = Event()
    release = Event()

    def fake_generate(prompt, config, *, parameters, source_image_paths):
        started.set()
        release.wait(timeout=1.0)
        return ReplicateResult(
            prediction_id="prediction-123",
            output_urls=[],
            stored_images=[],
            logs="done",
        )

    executor = ThreadPoolExecutor(max_workers=1)
    try:
        worker = ThreadedGenerationWorker(
            store=store,
            app_config=app_config,
            generate=fake_generate,
            executor=executor,
        )

        worker.start(record)

        assert started.wait(timeout=1.0)
        assert record.status == "running"
        release.set()
    finally:
        executor.shutdown(wait=True)

    assert record.status == "succeeded"
