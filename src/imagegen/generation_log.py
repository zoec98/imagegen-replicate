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
            connection.executescript(SCHEMA)

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
                    created_at,
                    status,
                    model_alias,
                    model,
                    replicate_input_json,
                    prompt,
                    parameters_json,
                    source_image_filenames_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.request_id,
                    record.created_at.isoformat(),
                    record.status,
                    model_alias,
                    model,
                    _json(replicate_input),
                    record.prompt,
                    _json(record.parameters),
                    _json(record.source_images),
                ),
            )

    def mark_started(self, request_id: str) -> None:
        now = _now()
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE generation_requests
                SET status = ?, started_at = ?
                WHERE id = ?
                """,
                ("running", now, request_id),
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
            created_at, started_at = _request_times(connection, request_id)
            elapsed_start = started_at or created_at
            elapsed_seconds = _elapsed_seconds(elapsed_start, now)
            connection.execute(
                """
                UPDATE generation_requests
                SET status = ?,
                    completed_at = ?,
                    prediction_id = COALESCE(?, prediction_id),
                    logs_json = ?,
                    error = ?,
                    elapsed_seconds = ?
                WHERE id = ?
                """,
                (
                    status,
                    now,
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
        with self._connect() as connection:
            if elapsed_seconds is None:
                created_at, started_at = _request_times(connection, request_id)
                elapsed_seconds = _elapsed_seconds(
                    started_at or created_at,
                    image.created_at,
                )
            connection.execute(
                """
                INSERT INTO generation_results (
                    request_id,
                    sequence,
                    filename,
                    source_url,
                    content_type,
                    size_bytes,
                    created_at,
                    elapsed_seconds,
                    logs_json,
                    error
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    request_id,
                    sequence,
                    image.path.name,
                    image.source_url,
                    image.content_type,
                    image.size_bytes,
                    image.created_at,
                    elapsed_seconds,
                    _json(logs or []),
                    error,
                ),
            )

    def get_request(self, request_id: str) -> dict[str, object] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM generation_requests WHERE id = ?",
                (request_id,),
            ).fetchone()
        return dict(row) if row is not None else None

    def list_results(self, request_id: str) -> list[dict[str, object]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM generation_results
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


SCHEMA = """
CREATE TABLE IF NOT EXISTS generation_requests (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT,
    status TEXT NOT NULL,
    model_alias TEXT NOT NULL,
    model TEXT NOT NULL,
    replicate_input_json TEXT NOT NULL,
    prompt TEXT NOT NULL,
    parameters_json TEXT NOT NULL,
    source_image_filenames_json TEXT NOT NULL,
    prediction_id TEXT,
    logs_json TEXT,
    error TEXT,
    elapsed_seconds REAL
);

CREATE TABLE IF NOT EXISTS generation_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id TEXT NOT NULL REFERENCES generation_requests(id),
    sequence INTEGER NOT NULL,
    filename TEXT NOT NULL,
    source_url TEXT NOT NULL,
    content_type TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    elapsed_seconds REAL,
    logs_json TEXT,
    error TEXT
);
"""


def _json(value: object) -> str:
    return json.dumps(value, sort_keys=True)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _request_times(
    connection: sqlite3.Connection,
    request_id: str,
) -> tuple[str | None, str | None]:
    row = connection.execute(
        "SELECT created_at, started_at FROM generation_requests WHERE id = ?",
        (request_id,),
    ).fetchone()
    if row is None:
        return None, None
    return row["created_at"], row["started_at"]


def _elapsed_seconds(start: str | None, end: str) -> float | None:
    if start is None:
        return None
    return (datetime.fromisoformat(end) - datetime.fromisoformat(start)).total_seconds()
