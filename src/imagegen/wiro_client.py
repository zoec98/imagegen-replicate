"""Wiro asynchronous generation client."""

from __future__ import annotations

import mimetypes
import time
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any, BinaryIO, Protocol

import httpx

from imagegen.config import AppConfig
from imagegen.generation_types import GenerationResult
from imagegen.image_store import StoredImage, persist_generated_images
from imagegen.model_registry import GenerationTarget, ProviderModel
from imagegen.prompt_annotations import strip_prompt_annotations
from imagegen.provider_requests import build_provider_request

WIRO_API_ROOT = "https://api.wiro.ai/v1"
PersistImages = Callable[..., list[StoredImage]]


class WiroHTTPClient(Protocol):
    def post(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        json: Mapping[str, object] | None = None,
        data: object | None = None,
        files: object | None = None,
        timeout: float | None = None,
    ) -> object: ...


class WiroResponse(Protocol):
    status_code: int

    def json(self) -> object: ...


class WiroRequestError(RuntimeError):
    def __init__(self, message: str, *, task_id: str | None = None) -> None:
        super().__init__(message)
        self.task_id = task_id


class WiroRequestTimeout(TimeoutError):
    def __init__(self, message: str, *, task_id: str | None = None) -> None:
        super().__init__(message)
        self.task_id = task_id


def generate_image_urls(
    prompt: str,
    app_config: AppConfig,
    *,
    model: ProviderModel,
    target: GenerationTarget,
    parameters: dict[str, object] | None = None,
    source_image_paths: list[Path] | None = None,
    client: WiroHTTPClient | None = None,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
    persist_images: PersistImages = persist_generated_images,
    api_key: str | None = None,
) -> GenerationResult:
    key = (
        api_key if api_key is not None else getattr(app_config, "wiro_api_key", "")
    ).strip()
    if not key:
        raise WiroRequestError("Wiro API key is not configured.")
    source_paths = list(source_image_paths or [])
    source_binding = target.source_images
    if parameters and source_binding and source_binding.provider_field in parameters:
        raise WiroRequestError(
            f"Wiro {source_binding.provider_field} must come from selected source images."
        )
    if source_paths and source_binding is None:
        raise WiroRequestError("Wiro target does not accept source images.")
    if source_binding is not None:
        if len(source_paths) > source_binding.max_count:
            raise WiroRequestError(
                f"Wiro accepts at most {source_binding.max_count} source images."
            )
        if source_binding.max_total is not None:
            output_count = _output_count(target, parameters, source_binding)
            if len(source_paths) + output_count > source_binding.max_total:
                raise WiroRequestError(
                    f"Wiro source images plus outputs cannot exceed {source_binding.max_total}."
                )

    http_client = client or httpx.Client(timeout=30.0)
    close_client = client is None
    try:
        provider_prompt = strip_prompt_annotations(prompt)
        submission_input = build_provider_request(
            provider_prompt,
            model,
            target,
            parameters=parameters,
        )
        metadata_input = build_provider_request(
            provider_prompt,
            model,
            target,
            parameters=parameters,
            source_image_inputs=[path.name for path in source_paths],
        )
        if source_paths:
            task_id = _submit_multipart_task(
                http_client,
                target=target,
                payload=submission_input,
                source_image_paths=source_paths,
                api_key=key,
                timeout=app_config.replicate_timeout_seconds,
            )
        else:
            task_id = _submit_task(
                http_client,
                target=target,
                payload=submission_input,
                api_key=key,
                timeout=app_config.replicate_timeout_seconds,
            )
        task, logs = _wait_for_task(
            http_client,
            task_id=task_id,
            api_key=key,
            timeout_seconds=app_config.replicate_timeout_seconds,
            poll_seconds=app_config.replicate_poll_seconds,
            sleep=sleep,
            clock=clock,
        )
        output_urls = normalize_output_urls(task.get("outputs"))
        if not output_urls:
            raise WiroRequestError(
                f"Wiro task {task_id} succeeded but returned no valid HTTPS image URLs.",
                task_id=task_id,
            )
        stored_images = persist_images(
            output_urls,
            output_dir=Path(app_config.output_dir),
            model=model,
            provider="wiro",
            model_alias=model.alias,
            provider_model=target.provider_model,
            prompt=prompt,
            prediction_id=task_id,
            prediction_input=metadata_input,
            author=app_config.author,
        )
        return GenerationResult(
            prediction_id=task_id,
            output_urls=output_urls,
            stored_images=stored_images,
            logs=logs,
        )
    finally:
        if close_client and hasattr(http_client, "close"):
            http_client.close()


def _submit_task(
    client: WiroHTTPClient,
    *,
    target: GenerationTarget,
    payload: dict[str, object],
    api_key: str,
    timeout: float,
) -> str:
    response = _post_json(
        client,
        f"{WIRO_API_ROOT}/Run/{target.provider_model}",
        api_key=api_key,
        payload=payload,
        timeout=timeout,
        operation="run",
    )
    return _task_id_from_response(response)


def _submit_multipart_task(
    client: WiroHTTPClient,
    *,
    target: GenerationTarget,
    payload: dict[str, object],
    source_image_paths: list[Path],
    api_key: str,
    timeout: float,
) -> str:
    source_field = target.source_images.provider_field  # validated by caller
    opened_files: list[BinaryIO] = []
    try:
        try:
            opened_files = [path.open("rb") for path in source_image_paths]
        except OSError as error:
            raise WiroRequestError(
                f"Wiro source image could not be opened: {error}."
            ) from error
        files = [
            (
                source_field,
                (
                    path.name,
                    opened_file,
                    mimetypes.guess_type(path.name)[0] or "application/octet-stream",
                ),
            )
            for path, opened_file in zip(source_image_paths, opened_files, strict=True)
        ]
        response = _post_form(
            client,
            f"{WIRO_API_ROOT}/Run/{target.provider_model}",
            api_key=api_key,
            data={name: _form_value(value) for name, value in payload.items()},
            files=files,
            timeout=timeout,
            operation="run",
        )
    finally:
        for opened_file in opened_files:
            opened_file.close()
    return _task_id_from_response(response)


def _task_id_from_response(response: Mapping[str, Any]) -> str:
    if response.get("result") is not True:
        raise WiroRequestError(
            f"Wiro rejected the generation request: {_error_text(response)}."
        )
    task_id = response.get("taskid")
    if not isinstance(task_id, str) or not task_id.strip():
        raise WiroRequestError("Wiro Run response did not include a task id.")
    return task_id


def _output_count(
    target: GenerationTarget,
    parameters: dict[str, object] | None,
    source_binding,
) -> int:
    parameter_name = source_binding.output_count_parameter
    if parameter_name is None:
        return 0
    value = next(
        (
            parameter.default
            for parameter in target.parameters
            if parameter.name == parameter_name
        ),
        0,
    )
    if parameters and parameter_name in parameters:
        value = parameters[parameter_name]
    if isinstance(value, bool) or not isinstance(value, int):
        raise WiroRequestError(f"Wiro {parameter_name} must be an integer.")
    return value


def _wait_for_task(
    client: WiroHTTPClient,
    *,
    task_id: str,
    api_key: str,
    timeout_seconds: float,
    poll_seconds: float,
    sleep: Callable[[float], None],
    clock: Callable[[], float],
) -> tuple[dict[str, Any], str]:
    deadline = clock() + timeout_seconds
    last_logs = ""
    while True:
        response = _post_json(
            client,
            f"{WIRO_API_ROOT}/Task/Detail",
            api_key=api_key,
            payload={"taskid": task_id},
            timeout=timeout_seconds,
            operation=f"task {task_id}",
        )
        if response.get("result") is not True:
            raise WiroRequestError(
                f"Wiro task {task_id} status lookup failed: {_error_text(response)}.",
                task_id=task_id,
            )
        task = _task_from_response(response, task_id)
        debugoutput = task.get("debugoutput")
        if isinstance(debugoutput, str) and debugoutput:
            last_logs = debugoutput
        status = task.get("status")
        if status == "task_postprocess_end":
            pexit = task.get("pexit")
            if pexit != "0":
                raise WiroRequestError(
                    f"Wiro task {task_id} failed with pexit {pexit}.",
                    task_id=task_id,
                )
            return task, last_logs
        if status == "task_cancel":
            raise WiroRequestError(
                f"Wiro task {task_id} was cancelled.",
                task_id=task_id,
            )
        if clock() >= deadline:
            raise WiroRequestTimeout(
                f"Wiro task {task_id} timed out after {timeout_seconds:g}s.",
                task_id=task_id,
            )
        sleep(poll_seconds)


def _post_json(
    client: WiroHTTPClient,
    url: str,
    *,
    api_key: str,
    payload: dict[str, object],
    timeout: float,
    operation: str,
) -> dict[str, Any]:
    try:
        response = client.post(
            url,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "x-api-key": api_key,
            },
            json=payload,
            timeout=timeout,
        )
    except (httpx.HTTPError, OSError) as error:
        raise WiroRequestError(f"Wiro {operation} request failed: {error}.") from error
    return _decode_response(response, operation)


def _post_form(
    client: WiroHTTPClient,
    url: str,
    *,
    api_key: str,
    data: object,
    files: object,
    timeout: float,
    operation: str,
) -> dict[str, Any]:
    try:
        response = client.post(
            url,
            headers={
                "Accept": "application/json",
                "x-api-key": api_key,
            },
            data=data,
            files=files,
            timeout=timeout,
        )
    except (httpx.HTTPError, OSError) as error:
        raise WiroRequestError(f"Wiro {operation} request failed: {error}.") from error
    return _decode_response(response, operation)


def _decode_response(response: object, operation: str) -> dict[str, Any]:
    status_code = getattr(response, "status_code", None)
    if not isinstance(status_code, int):
        raise WiroRequestError(f"Wiro {operation} response had no HTTP status.")
    try:
        decoded = response.json()
    except (ValueError, TypeError) as error:
        raise WiroRequestError(
            f"Wiro {operation} response was not valid JSON."
        ) from error
    if not isinstance(decoded, dict):
        raise WiroRequestError(f"Wiro {operation} response was not a JSON object.")
    if status_code == 401 or status_code == 403:
        raise WiroRequestError(f"Wiro authentication failed during {operation}.")
    if status_code == 429:
        raise WiroRequestError(f"Wiro rate limit reached during {operation}.")
    if status_code >= 400:
        raise WiroRequestError(
            f"Wiro {operation} request failed with HTTP {status_code}: {_error_text(decoded)}."
        )
    return decoded


def _form_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _task_from_response(response: Mapping[str, Any], task_id: str) -> dict[str, Any]:
    tasks = response.get("tasklist")
    if not isinstance(tasks, list) or not tasks or not isinstance(tasks[0], dict):
        raise WiroRequestError(
            f"Wiro task {task_id} response did not include a task object.",
            task_id=task_id,
        )
    return tasks[0]


def normalize_output_urls(outputs: object) -> list[str]:
    if not isinstance(outputs, list):
        return []
    urls: list[str] = []
    for output in outputs:
        if not isinstance(output, dict):
            continue
        url = output.get("url")
        if not isinstance(url, str) or not url.startswith("https://"):
            continue
        if url not in urls:
            urls.append(url)
    return urls


def _error_text(response: Mapping[str, Any]) -> str:
    errors = response.get("errors")
    if isinstance(errors, list):
        messages = []
        for error in errors:
            if isinstance(error, dict) and isinstance(error.get("message"), str):
                messages.append(error["message"])
            elif isinstance(error, str):
                messages.append(error)
        if messages:
            return "; ".join(messages)
    if isinstance(errors, str):
        return errors
    return "provider returned an error"
