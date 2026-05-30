import json
import sqlite3

from imagegen.generation_log import SQLiteGenerationLog
from imagegen.image_store import StoredImage
from imagegen.request_store import RequestStore


def test_initialize_creates_schema_idempotently(tmp_path):
    log = SQLiteGenerationLog(tmp_path / "imagegen.sqlite3")

    log.initialize()
    log.initialize()

    with sqlite3.connect(log.path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
    assert "generation_requests" in tables
    assert "generation_results" in tables


def test_create_request_persists_recreatable_payload(tmp_path):
    log = SQLiteGenerationLog(tmp_path / "imagegen.sqlite3")
    log.initialize()
    record = RequestStore().create(
        prompt="edit this",
        parameters={"size": "2K"},
        source_images=["source.png"],
    )
    replicate_input = {
        "prompt": "edit this",
        "size": "2K",
        "image_input": ["source.png"],
        "disable_safety_checker": True,
    }

    log.create_request(
        record,
        model_alias="seedream45",
        model="bytedance/seedream-4.5",
        replicate_input=replicate_input,
    )

    row = log.get_request(record.request_id)
    assert row is not None
    assert row["status"] == "queued"
    assert row["model_alias"] == "seedream45"
    assert row["model"] == "bytedance/seedream-4.5"
    assert json.loads(row["replicate_input_json"]) == replicate_input
    assert json.loads(row["parameters_json"]) == {"size": "2K"}
    assert json.loads(row["source_image_filenames_json"]) == ["source.png"]


def test_lifecycle_updates_status_and_elapsed_time(tmp_path):
    log = SQLiteGenerationLog(tmp_path / "imagegen.sqlite3")
    log.initialize()
    record = RequestStore().create(prompt="prompt", parameters={})
    log.create_request(
        record,
        model_alias="seedream45",
        model="bytedance/seedream-4.5",
        replicate_input={"prompt": "prompt"},
    )

    log.mark_started(record.request_id)
    log.mark_finished(
        record.request_id,
        status="succeeded",
        prediction_id="prediction-123",
        logs=["created", "finished"],
    )

    row = log.get_request(record.request_id)
    assert row is not None
    assert row["status"] == "succeeded"
    assert row["started_at"]
    assert row["completed_at"]
    assert row["prediction_id"] == "prediction-123"
    assert json.loads(row["logs_json"]) == ["created", "finished"]
    assert row["elapsed_seconds"] >= 0


def test_failed_request_persists_error_detail(tmp_path):
    log = SQLiteGenerationLog(tmp_path / "imagegen.sqlite3")
    log.initialize()
    record = RequestStore().create(prompt="prompt", parameters={})
    log.create_request(
        record,
        model_alias="seedream45",
        model="bytedance/seedream-4.5",
        replicate_input={"prompt": "prompt"},
    )

    log.mark_started(record.request_id)
    log.mark_finished(record.request_id, status="failed", error="Replicate failed.")

    row = log.get_request(record.request_id)
    assert row is not None
    assert row["status"] == "failed"
    assert row["error"] == "Replicate failed."


def test_add_result_persists_stored_image_metadata(tmp_path):
    log = SQLiteGenerationLog(tmp_path / "imagegen.sqlite3")
    log.initialize()
    record = RequestStore().create(prompt="prompt", parameters={})
    log.create_request(
        record,
        model_alias="seedream45",
        model="bytedance/seedream-4.5",
        replicate_input={"prompt": "prompt"},
    )
    image = StoredImage(
        path=tmp_path / "seedream45-prediction-123-01.png",
        source_url="https://example.com/out.png",
        content_type="image/png",
        size_bytes=123,
        created_at="2026-05-30T12:00:00+00:00",
    )

    log.add_result(
        record.request_id,
        sequence=1,
        image=image,
        elapsed_seconds=1.25,
        logs=["done"],
    )

    rows = log.list_results(record.request_id)
    assert rows == [
        {
            "id": 1,
            "request_id": record.request_id,
            "sequence": 1,
            "filename": "seedream45-prediction-123-01.png",
            "source_url": "https://example.com/out.png",
            "content_type": "image/png",
            "size_bytes": 123,
            "created_at": "2026-05-30T12:00:00+00:00",
            "elapsed_seconds": 1.25,
            "logs_json": '["done"]',
            "error": None,
        }
    ]
