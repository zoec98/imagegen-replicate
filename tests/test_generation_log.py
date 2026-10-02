"""Durable generation history tests.

Behaviors protected:
- Generation history initializes and migrates durable SQLite storage.
- Requests store recreatable provider payloads and submitted source metadata.
- Lifecycle updates persist status, timing, provider ids, logs, errors, and assets.
"""

import sqlite3

import pytest

from imagegen.generation_log import SQLiteGenerationLog
from imagegen.image_store import StoredImage
from imagegen.request_store import RequestStore


def test_log_operations_close_connections_without_garbage_collection(
    tmp_path, monkeypatch
):
    connections = []
    connect = sqlite3.connect

    def tracked_connect(*args, **kwargs):
        connection = connect(*args, **kwargs)
        connections.append(connection)
        return connection

    monkeypatch.setattr(sqlite3, "connect", tracked_connect)
    log = SQLiteGenerationLog(tmp_path / "imagegen.sqlite3")
    log.initialize()
    for sequence in range(10):
        record = RequestStore().create(
            provider="replicate", prompt="test", parameters={}
        )
        log.create_request(
            record, model_alias="test", model="test/model", replicate_input={}
        )
        log.mark_started(record.request_id)
        log.add_result(
            record.request_id,
            sequence=sequence,
            image=StoredImage(
                path=tmp_path / "test.png",
                source_url="https://example.com/test.png",
                content_type="image/png",
                size_bytes=1,
                created_at=record.created_at.isoformat(),
            ),
        )
        log.mark_finished(record.request_id, status="succeeded")
        assert log.get_logged_request(record.request_id) is not None
        assert log.get_logged_result(record.request_id).status == "succeeded"
        assert len(log.list_logged_assets(record.request_id)) == 1

    try:
        for connection in connections:
            with pytest.raises(sqlite3.ProgrammingError, match="closed database"):
                connection.execute("SELECT 1")
    finally:
        for connection in connections:
            connection.close()


def test_failed_log_write_rolls_back_and_closes_connection(tmp_path, monkeypatch):
    log = SQLiteGenerationLog(tmp_path / "imagegen.sqlite3")
    log.initialize()
    connection = sqlite3.connect(log.path)
    monkeypatch.setattr(sqlite3, "connect", lambda *args, **kwargs: connection)
    record = RequestStore().create(provider="replicate", prompt="test", parameters={})
    # The first insert succeeds; the second fails and must roll back both.
    connection.execute("DROP TABLE generation_results")
    connection.commit()
    try:
        with pytest.raises(sqlite3.OperationalError, match="generation_results"):
            log.create_request(
                record, model_alias="test", model="test/model", replicate_input={}
            )
        with pytest.raises(sqlite3.ProgrammingError, match="closed database"):
            connection.execute("SELECT 1")
    finally:
        connection.close()
    with sqlite3.Connection(log.path) as check:
        assert (
            check.execute("SELECT COUNT(*) FROM generation_requests").fetchone()[0] == 0
        )
    check.close()


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
    assert "generation_assets" in tables
    assert "schema_version" in tables
    with sqlite3.connect(log.path) as connection:
        version = connection.execute("SELECT version FROM schema_version").fetchone()[0]
    assert version == 3


def test_initialize_migrates_v1_schema(tmp_path):
    log = SQLiteGenerationLog(tmp_path / "imagegen.sqlite3")
    log.path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(log.path) as connection:
        connection.executescript(
            """
            CREATE TABLE schema_version (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                version INTEGER NOT NULL
            );
            INSERT INTO schema_version VALUES (1, 1);
            CREATE TABLE generation_requests (
                id TEXT PRIMARY KEY,
                sent_at TEXT NOT NULL,
                model_alias TEXT NOT NULL,
                model TEXT NOT NULL,
                request_sent_json TEXT NOT NULL,
                parameters_json TEXT NOT NULL,
                source_image_filenames_json TEXT NOT NULL
            );
            INSERT INTO generation_requests
            VALUES ('old', '2026-05-30T12:00:00+00:00',
                'seedream45', 'bytedance/seedream-4.5', '{}', '{}', '[]');
            """
        )

    log.initialize()

    with sqlite3.connect(log.path) as connection:
        connection.row_factory = sqlite3.Row
        version = connection.execute("SELECT version FROM schema_version").fetchone()[0]
        row = connection.execute(
            "SELECT prompt, provider FROM generation_requests WHERE id = 'old'"
        ).fetchone()
    assert version == 3
    assert row["prompt"] == ""
    assert row["provider"] == "replicate"


def test_initialize_migrates_v2_schema_with_provider_backfill(tmp_path):
    log = SQLiteGenerationLog(tmp_path / "imagegen.sqlite3")
    log.path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(log.path) as connection:
        connection.executescript(
            """
            CREATE TABLE schema_version (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                version INTEGER NOT NULL
            );
            INSERT INTO schema_version VALUES (1, 2);
            CREATE TABLE generation_requests (
                id TEXT PRIMARY KEY,
                sent_at TEXT NOT NULL,
                model_alias TEXT NOT NULL,
                model TEXT NOT NULL,
                prompt TEXT NOT NULL,
                request_sent_json TEXT NOT NULL,
                parameters_json TEXT NOT NULL,
                source_image_filenames_json TEXT NOT NULL
            );
            INSERT INTO generation_requests
            VALUES ('old', '2026-05-30T12:00:00+00:00',
                'seedream45', 'bytedance/seedream-4.5', 'prompt', '{}', '{}', '[]');
            """
        )

    log.initialize()

    with sqlite3.connect(log.path) as connection:
        connection.row_factory = sqlite3.Row
        version = connection.execute("SELECT version FROM schema_version").fetchone()[0]
        row = connection.execute(
            "SELECT provider FROM generation_requests WHERE id = 'old'"
        ).fetchone()
    assert version == 3
    assert row["provider"] == "replicate"


def test_initialize_rebuilds_unversioned_lab_schema(tmp_path):
    log = SQLiteGenerationLog(tmp_path / "imagegen.sqlite3")
    log.path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(log.path) as connection:
        connection.executescript(
            """
            CREATE TABLE generation_requests (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                status TEXT NOT NULL,
                model_alias TEXT NOT NULL,
                model TEXT NOT NULL,
                replicate_input_json TEXT NOT NULL,
                prompt TEXT NOT NULL,
                parameters_json TEXT NOT NULL,
                source_image_filenames_json TEXT NOT NULL
            );
            INSERT INTO generation_requests
            VALUES ('old', '2026-05-30T12:00:00+00:00', 'queued',
                'seedream45', 'bytedance/seedream-4.5', '{}', 'old', '{}', '[]');
            """
        )

    log.initialize()

    with sqlite3.connect(log.path) as connection:
        columns = [
            row[1]
            for row in connection.execute("PRAGMA table_info(generation_requests)")
        ]
        count = connection.execute(
            "SELECT count(*) FROM generation_requests"
        ).fetchone()[0]
    assert columns == [
        "id",
        "sent_at",
        "provider",
        "model_alias",
        "model",
        "prompt",
        "request_sent_json",
        "parameters_json",
        "source_image_filenames_json",
    ]
    assert count == 0


def test_create_request_persists_recreatable_payload(tmp_path):
    log = SQLiteGenerationLog(tmp_path / "imagegen.sqlite3")
    log.initialize()
    record = RequestStore().create(
        provider="replicate",
        prompt="edit this",
        parameters={"size": "2K"},
        source_images=["source.png"],
        edit_mode=True,
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

    request = log.get_logged_request(record.request_id)
    result = log.get_logged_result(record.request_id)
    assert request is not None
    assert result is not None
    assert result.status == "queued"
    assert result.logs == []
    assert request.provider == "replicate"
    assert request.model_alias == "seedream45"
    assert request.model == "bytedance/seedream-4.5"
    assert request.prompt == "edit this"
    assert request.request_sent == replicate_input
    assert request.parameters == {"size": "2K"}
    assert request.source_images == ["source.png"]


def test_create_request_persists_provider_for_falai_rows(tmp_path):
    log = SQLiteGenerationLog(tmp_path / "imagegen.sqlite3")
    log.initialize()
    record = RequestStore().create(
        provider="falai",
        prompt="edit this",
        parameters={},
        source_images=["source.png"],
        edit_mode=True,
        model_alias="seedream45",
    )

    log.create_request(
        record,
        model_alias="seedream45",
        model="fal-ai/bytedance/seedream/v4.5/edit",
        replicate_input={"prompt": "edit this", "image_urls": ["source.png"]},
    )

    request = log.get_logged_request(record.request_id)
    assert request is not None
    assert request.provider == "falai"
    assert request.model_alias == "seedream45"
    assert request.model == "fal-ai/bytedance/seedream/v4.5/edit"


def test_create_request_persists_provider_for_wiro_rows(tmp_path):
    log = SQLiteGenerationLog(tmp_path / "imagegen.sqlite3")
    log.initialize()
    record = RequestStore().create(
        provider="wiro",
        prompt="a cookie",
        parameters={"watermark": "false"},
        model_alias="seedream5",
    )

    log.create_request(
        record,
        model_alias="seedream5",
        model="bytedance/seedream-v5-lite-uncensored",
        replicate_input={"prompt": "a cookie", "watermark": "false"},
    )

    request = log.get_logged_request(record.request_id)
    assert request is not None
    assert request.provider == "wiro"


def test_lifecycle_updates_status_and_elapsed_time(tmp_path):
    log = SQLiteGenerationLog(tmp_path / "imagegen.sqlite3")
    log.initialize()
    record = RequestStore().create(provider="replicate", prompt="prompt", parameters={})
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

    request = log.get_logged_request(record.request_id)
    result = log.get_logged_result(record.request_id)
    assert request is not None
    assert result is not None
    assert result.status == "succeeded"
    assert result.started_at
    assert result.completed_at
    assert result.prediction_id == "prediction-123"
    assert result.logs == ["created", "finished"]
    assert result.elapsed_seconds is not None
    assert result.elapsed_seconds >= 0


def test_failed_request_persists_error_detail(tmp_path):
    log = SQLiteGenerationLog(tmp_path / "imagegen.sqlite3")
    log.initialize()
    record = RequestStore().create(provider="replicate", prompt="prompt", parameters={})
    log.create_request(
        record,
        model_alias="seedream45",
        model="bytedance/seedream-4.5",
        replicate_input={"prompt": "prompt"},
    )

    log.mark_started(record.request_id)
    log.mark_finished(record.request_id, status="failed", error="Replicate failed.")

    result = log.get_logged_result(record.request_id)
    assert result is not None
    assert result.status == "failed"
    assert result.error == "Replicate failed."
    assert log.list_logged_assets(record.request_id) == []


def test_add_result_persists_stored_image_metadata(tmp_path):
    log = SQLiteGenerationLog(tmp_path / "imagegen.sqlite3")
    log.initialize()
    record = RequestStore().create(provider="replicate", prompt="prompt", parameters={})
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

    assets = log.list_logged_assets(record.request_id)
    assert assets
    assert assets[0].request_id == record.request_id
    assert assets[0].sequence == 1
    assert assets[0].filename == "seedream45-prediction-123-01.png"
    assert assets[0].source_url == "https://example.com/out.png"
    assert assets[0].content_type == "image/png"
    assert assets[0].size_bytes == 123
    assert assets[0].created_at == "2026-05-30T12:00:00+00:00"


def test_multiple_assets_share_one_lifecycle_row(tmp_path):
    log = SQLiteGenerationLog(tmp_path / "imagegen.sqlite3")
    log.initialize()
    record = RequestStore().create(provider="replicate", prompt="prompt", parameters={})
    log.create_request(
        record,
        model_alias="seedream45",
        model="bytedance/seedream-4.5",
        replicate_input={"prompt": "prompt"},
    )
    log.mark_finished(record.request_id, status="succeeded", prediction_id="prediction")

    for sequence in (1, 2):
        log.add_result(
            record.request_id,
            sequence=sequence,
            image=StoredImage(
                path=tmp_path / f"seedream45-prediction-{sequence:02}.png",
                source_url=f"https://example.com/out-{sequence}.png",
                content_type="image/png",
                size_bytes=123 + sequence,
                created_at="2026-05-30T12:00:00+00:00",
            ),
        )

    result = log.get_logged_result(record.request_id)
    assets = log.list_logged_assets(record.request_id)
    assert result is not None
    assert result.status == "succeeded"
    assert [asset.sequence for asset in assets] == [1, 2]
    assert {asset.request_id for asset in assets} == {record.request_id}
