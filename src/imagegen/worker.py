"""Background generation worker orchestration.

This module owns starting generation work outside the HTTP request/response
cycle and translating Replicate wrapper outcomes into request-store lifecycle
updates. The default worker uses a small thread pool; tests can inject a fake
worker through Flask config.
"""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Protocol

from imagegen.config import AppConfig
from imagegen.replicate_client import (
    ReplicatePredictionTimeout,
    ReplicateResult,
    generate_image_urls,
)
from imagegen.request_store import GenerationRequest, RequestStore


GenerateImage = Callable[..., ReplicateResult]


class GenerationWorker(Protocol):
    def start(self, request_record: GenerationRequest) -> None: ...


class ThreadedGenerationWorker:
    def __init__(
        self,
        *,
        store: RequestStore,
        app_config: AppConfig,
        generate: GenerateImage = generate_image_urls,
        executor: ThreadPoolExecutor | None = None,
    ) -> None:
        self._store = store
        self._app_config = app_config
        self._generate = generate
        self._executor = executor or ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="imagegen-worker",
        )

    def start(self, request_record: GenerationRequest) -> None:
        self._executor.submit(
            run_generation_request,
            self._store,
            request_record,
            self._app_config,
            self._generate,
        )


def run_generation_request(
    store: RequestStore,
    request_record: GenerationRequest,
    app_config: AppConfig,
    generate: GenerateImage = generate_image_urls,
) -> None:
    store.update(request_record.request_id, status="running")
    try:
        result = generate(
            request_record.prompt,
            app_config,
            parameters=request_record.parameters,
        )
    except ReplicatePredictionTimeout as error:
        store.update(request_record.request_id, status="timeout", error=str(error))
        return
    except Exception as error:
        store.update(request_record.request_id, status="failed", error=str(error))
        return

    store.update(
        request_record.request_id,
        status="succeeded",
        prediction_id=result.prediction_id,
        output_urls=result.output_urls,
        images=[_stored_image_filename(image) for image in result.stored_images],
        logs=result.logs.splitlines() if result.logs else [],
    )


def _stored_image_filename(image: object) -> str:
    path = getattr(image, "path", image)
    return Path(path).name
