"""In-memory generation request state tracking.

This module owns local MVP request state for app-like generation flows. It
tracks lifecycle status, submitted prompt and parameters, Replicate identifiers,
downloaded image filenames, timestamps, and displayable error detail.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from threading import Lock
from typing import Literal


RequestStatus = Literal["queued", "running", "succeeded", "failed", "timeout"]
REQUEST_STATUSES: set[str] = {"queued", "running", "succeeded", "failed", "timeout"}


@dataclass
class GenerationRequest:
    request_id: str
    prompt: str
    parameters: dict[str, object]
    status: RequestStatus
    created_at: datetime
    updated_at: datetime
    error: str | None = None
    prediction_id: str | None = None
    output_urls: list[str] = field(default_factory=list)
    images: list[str] = field(default_factory=list)
    logs: list[str] = field(default_factory=list)

    def to_json(self) -> dict[str, object]:
        return {
            "request_id": self.request_id,
            "status": self.status,
            "prompt": self.prompt,
            "parameters": self.parameters,
            "error": self.error,
            "prediction_id": self.prediction_id,
            "output_urls": self.output_urls,
            "images": self.images,
            "logs": self.logs,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class RequestStore:
    """Thread-safe local request state store for one Flask process."""

    def __init__(self) -> None:
        self._requests: dict[str, GenerationRequest] = {}
        self._lock = Lock()

    def create(
        self, *, prompt: str, parameters: dict[str, object]
    ) -> GenerationRequest:
        now = datetime.now(UTC)
        request_record = GenerationRequest(
            request_id=uuid.uuid4().hex,
            prompt=prompt,
            parameters=dict(parameters),
            status="queued",
            created_at=now,
            updated_at=now,
        )
        with self._lock:
            self._requests[request_record.request_id] = request_record
        return request_record

    def get(self, request_id: str) -> GenerationRequest | None:
        with self._lock:
            return self._requests.get(request_id)

    def update(
        self,
        request_id: str,
        *,
        status: RequestStatus | None = None,
        error: str | None = None,
        prediction_id: str | None = None,
        output_urls: list[str] | None = None,
        images: list[str] | None = None,
        logs: list[str] | None = None,
    ) -> GenerationRequest | None:
        with self._lock:
            request_record = self._requests.get(request_id)
            if request_record is None:
                return None

            if status is not None:
                request_record.status = status
            if error is not None:
                request_record.error = error
            if prediction_id is not None:
                request_record.prediction_id = prediction_id
            if output_urls is not None:
                request_record.output_urls = list(output_urls)
            if images is not None:
                request_record.images = list(images)
            if logs is not None:
                request_record.logs = list(logs)
            request_record.updated_at = datetime.now(UTC)
            return request_record
