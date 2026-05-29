from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event

from imagegen.replicate_client import ReplicatePredictionTimeout, ReplicateResult
from imagegen.request_store import RequestStore
from imagegen.worker import ThreadedGenerationWorker, run_generation_request


def test_run_generation_request_succeeded_updates_request(app_config):
    store = RequestStore()
    source_path = app_config.output_dir / "source.png"
    source_path.write_bytes(b"image")
    record = store.create(
        prompt="a red house",
        parameters={"size": "2K"},
        source_images=["source.png"],
    )

    def fake_generate(prompt, config, *, parameters, source_image_paths):
        assert prompt == "a red house"
        assert config is app_config
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
    record = store.create(prompt="a red house", parameters={})

    def fake_generate(prompt, config, *, parameters, source_image_paths):
        raise RuntimeError("Replicate failed.")

    run_generation_request(store, record, app_config, fake_generate)

    assert record.status == "failed"
    assert record.error == "Replicate failed."


def test_run_generation_request_timeout_updates_timeout(app_config):
    store = RequestStore()
    record = store.create(prompt="a red house", parameters={})

    def fake_generate(prompt, config, *, parameters, source_image_paths):
        raise ReplicatePredictionTimeout("Timed out.")

    run_generation_request(store, record, app_config, fake_generate)

    assert record.status == "timeout"
    assert record.error == "Timed out."


def test_threaded_worker_start_returns_before_generation_completes(app_config):
    store = RequestStore()
    record = store.create(prompt="a red house", parameters={})
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
