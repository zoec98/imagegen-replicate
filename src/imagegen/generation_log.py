"""SQLite-backed durable generation request log."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from imagegen.image_store import StoredImage
from imagegen.request_store import GenerationRequest, RequestStatus


class GenerationLog(Protocol):
    def initialize(self) -> None: ...

    def create_request(
        self,
        record: GenerationRequest,
        *,
        model_alias: str,
        model: str,
        replicate_input: dict[str, object],
    ) -> None: ...

    def mark_started(self, request_id: str) -> None: ...

    def mark_finished(
        self,
        request_id: str,
        *,
        status: RequestStatus,
        prediction_id: str | None = None,
        logs: list[str] | None = None,
        error: str | None = None,
    ) -> None: ...

    def add_result(
        self,
        request_id: str,
        *,
        sequence: int,
        image: StoredImage,
        elapsed_seconds: float | None = None,
        logs: list[str] | None = None,
        error: str | None = None,
    ) -> None: ...


@dataclass(frozen=True)
class SQLiteGenerationLog:
    path: Path

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            _prepare_schema(connection)
            connection.executescript(SCHEMA)
            connection.execute(
                """
                INSERT INTO schema_version (id, version)
                VALUES (1, ?)
                ON CONFLICT (id) DO UPDATE SET version = excluded.version
                """,
                (SCHEMA_VERSION,),
            )

    def create_request(
        self,
        record: GenerationRequest,
        *,
        model_alias: str,
        model: str,
        replicate_input: dict[str, object],
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO generation_requests (
                    id,
                    sent_at,
                    model_alias,
                    model,
                    prompt,
                    request_sent_json,
                    parameters_json,
                    source_image_filenames_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.request_id,
                    record.created_at.isoformat(),
                    model_alias,
                    model,
                    record.prompt,
                    _json(replicate_input),
                    _json(record.parameters),
                    _json(record.source_images),
                ),
            )
            connection.execute(
                """
                INSERT INTO generation_results (
                    request_id,
                    status,
                    logs_json
                )
                VALUES (?, ?, ?)
                """,
                (record.request_id, "queued", _json([])),
            )

    def mark_started(self, request_id: str) -> None:
        now = _now()
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE generation_results
                SET started_at = ?, status = ?
                WHERE request_id = ?
                """,
                (now, "running", request_id),
            )

    def mark_finished(
        self,
        request_id: str,
        *,
        status: RequestStatus,
        prediction_id: str | None = None,
        logs: list[str] | None = None,
        error: str | None = None,
    ) -> None:
        now = _now()
        with self._connect() as connection:
            sent_at, started_at = _request_times(connection, request_id)
            elapsed_start = started_at or sent_at
            elapsed_seconds = _elapsed_seconds(elapsed_start, now)
            connection.execute(
                """
                UPDATE generation_results
                SET completed_at = ?,
                    status = ?,
                    prediction_id = COALESCE(?, prediction_id),
                    logs_json = ?,
                    error = ?,
                    elapsed_seconds = ?
                WHERE request_id = ?
                """,
                (
                    now,
                    status,
                    prediction_id,
                    _json(logs or []),
                    error,
                    elapsed_seconds,
                    request_id,
                ),
            )

    def add_result(
        self,
        request_id: str,
        *,
        sequence: int,
        image: StoredImage,
        elapsed_seconds: float | None = None,
        logs: list[str] | None = None,
        error: str | None = None,
    ) -> None:
        del elapsed_seconds, logs, error
        with self._connect() as connection:
            result_id = _result_id(connection, request_id)
            connection.execute(
                """
                INSERT INTO generation_assets (
                    result_id,
                    request_id,
                    sequence,
                    filename,
                    source_url,
                    content_type,
                    size_bytes,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result_id,
                    request_id,
                    sequence,
                    image.path.name,
                    image.source_url,
                    image.content_type,
                    image.size_bytes,
                    image.created_at,
                ),
            )

    def get_request(self, request_id: str) -> dict[str, object] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM generation_requests WHERE id = ?",
                (request_id,),
            ).fetchone()
        return dict(row) if row is not None else None

    def get_result(self, request_id: str) -> dict[str, object] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM generation_results WHERE request_id = ?",
                (request_id,),
            ).fetchone()
        return dict(row) if row is not None else None

    def list_assets(self, request_id: str) -> list[dict[str, object]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM generation_assets
                WHERE request_id = ?
                ORDER BY sequence
                """,
                (request_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection


SCHEMA_VERSION = 2

SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_version (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    version INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS generation_requests (
    id TEXT PRIMARY KEY,
    sent_at TEXT NOT NULL,
    model_alias TEXT NOT NULL,
    model TEXT NOT NULL,
    prompt TEXT NOT NULL,
    request_sent_json TEXT NOT NULL,
    parameters_json TEXT NOT NULL,
    source_image_filenames_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS generation_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id TEXT NOT NULL UNIQUE REFERENCES generation_requests(id),
    started_at TEXT,
    completed_at TEXT,
    status TEXT NOT NULL,
    prediction_id TEXT,
    logs_json TEXT NOT NULL,
    error TEXT,
    elapsed_seconds REAL
);

CREATE TABLE IF NOT EXISTS generation_assets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    result_id INTEGER NOT NULL REFERENCES generation_results(id),
    request_id TEXT NOT NULL REFERENCES generation_requests(id),
    sequence INTEGER NOT NULL,
    filename TEXT NOT NULL,
    source_url TEXT NOT NULL,
    content_type TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (request_id, sequence)
);

CREATE INDEX IF NOT EXISTS generation_requests_sent_at_idx
ON generation_requests(sent_at);

CREATE INDEX IF NOT EXISTS generation_results_status_idx
ON generation_results(status);

CREATE INDEX IF NOT EXISTS generation_assets_request_id_sequence_idx
ON generation_assets(request_id, sequence);
"""

APPLICATION_TABLES = (
    "generation_assets",
    "generation_results",
    "generation_requests",
    "schema_version",
)


def _prepare_schema(connection: sqlite3.Connection) -> None:
    version = _schema_version(connection)
    if version == SCHEMA_VERSION:
        return
    if version == 1:
        _migrate_schema_v1_to_v2(connection)
        return
    if version is not None:
        msg = f"Unsupported generation log schema version: {version}."
        raise RuntimeError(msg)
    if _has_unversioned_lab_schema(connection):
        _drop_application_tables(connection)


def _schema_version(connection: sqlite3.Connection) -> int | None:
    if not _table_exists(connection, "schema_version"):
        return None
    row = connection.execute(
        "SELECT version FROM schema_version WHERE id = 1"
    ).fetchone()
    if row is None:
        return None
    return int(row["version"])


def _has_unversioned_lab_schema(connection: sqlite3.Connection) -> bool:
    names = {
        row["name"]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
    }
    return any(table in names for table in APPLICATION_TABLES)


def _drop_application_tables(connection: sqlite3.Connection) -> None:
    for table in APPLICATION_TABLES:
        connection.execute(f"DROP TABLE IF EXISTS {table}")


def _migrate_schema_v1_to_v2(connection: sqlite3.Connection) -> None:
    columns = _table_columns(connection, "generation_requests")
    if "prompt" not in columns:
        connection.execute(
            "ALTER TABLE generation_requests ADD COLUMN prompt TEXT NOT NULL DEFAULT ''"
        )
    connection.execute(
        """
        INSERT INTO schema_version (id, version)
        VALUES (1, ?)
        ON CONFLICT (id) DO UPDATE SET version = excluded.version
        """,
        (SCHEMA_VERSION,),
    )


def _table_columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {row["name"] for row in connection.execute(f"PRAGMA table_info({table})")}


def _table_exists(connection: sqlite3.Connection, table: str) -> bool:
    row = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table,),
    ).fetchone()
    return row is not None


def _json(value: object) -> str:
    return json.dumps(value, sort_keys=True)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _request_times(
    connection: sqlite3.Connection,
    request_id: str,
) -> tuple[str | None, str | None]:
    row = connection.execute(
        """
        SELECT generation_requests.sent_at, generation_results.started_at
        FROM generation_requests
        LEFT JOIN generation_results
            ON generation_results.request_id = generation_requests.id
        WHERE generation_requests.id = ?
        """,
        (request_id,),
    ).fetchone()
    if row is None:
        return None, None
    return row["sent_at"], row["started_at"]


def _result_id(connection: sqlite3.Connection, request_id: str) -> int:
    row = connection.execute(
        "SELECT id FROM generation_results WHERE request_id = ?",
        (request_id,),
    ).fetchone()
    if row is None:
        msg = f"Generation result row does not exist for request: {request_id}."
        raise RuntimeError(msg)
    return int(row["id"])


def _elapsed_seconds(start: str | None, end: str) -> float | None:
    if start is None:
        return None
    return (datetime.fromisoformat(end) - datetime.fromisoformat(start)).total_seconds()
