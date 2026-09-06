#!/usr/bin/env python3
"""Print a Wiro model contract without starting a model run."""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from dotenv import load_dotenv

DETAIL_URL = "https://api.wiro.ai/v1/Tool/Detail"
DOCS_ROOT = "https://wiro.ai/models"
USER_AGENT = "imagegen-schema-fetch/0.1"


class SchemaError(RuntimeError):
    """A safe, actionable schema-discovery failure."""


def main(
    argv: Sequence[str] | None = None,
    *,
    environ: Mapping[str, str] | None = None,
    request: Callable[..., dict[str, Any]] | None = None,
) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] in {"-h", "--help"}:
        print("usage: scripts/get_schema_wiro owner/model")
        print("       WIRO_API_KEY must contain an API-key-only Wiro project key.")
        return 0
    if len(args) != 1:
        print("usage: scripts/get_schema_wiro owner/model", file=sys.stderr)
        return 2

    try:
        owner, model = parse_model_ref(args[0])
        if environ is None:
            load_dotenv(_dotenv_path(), override=False)
        env = os.environ if environ is None else environ
        api_key = env.get("WIRO_API_KEY", "").strip()
        if not api_key:
            raise SchemaError("WIRO_API_KEY is required for Wiro schema discovery.")
        response = (request or request_json)(
            DETAIL_URL,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "User-Agent": USER_AGENT,
            },
            payload={
                "slugowner": owner,
                "slugproject": model,
                "summary": False,
            },
        )
        tool = extract_tool(response, args[0])
    except SchemaError as error:
        print(f"Wiro schema discovery failed: {error}", file=sys.stderr)
        return 1

    print_report(args[0], tool)
    return 0


def parse_model_ref(value: str) -> tuple[str, str]:
    parts = value.strip().split("/")
    if len(parts) != 2 or not all(parts):
        raise SchemaError(f"model must be in owner/model form, got: {value}")
    return parts[0], parts[1]


def request_json(
    url: str,
    *,
    headers: Mapping[str, str],
    payload: Mapping[str, object],
) -> dict[str, Any]:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=dict(headers),
        method="POST",
    )
    try:
        with urlopen(request, timeout=30) as response:
            raw = response.read().decode("utf-8")
    except HTTPError as error:
        detail = _http_error_detail(error)
        suffix = f": {detail}" if detail else ""
        raise SchemaError(
            f"HTTP {error.code} from Wiro Tool Detail{suffix}."
        ) from error
    except URLError as error:
        raise SchemaError(
            f"could not reach Wiro Tool Detail: {error.reason}"
        ) from error
    except OSError as error:
        raise SchemaError(
            f"could not read Wiro Tool Detail response: {error}"
        ) from error

    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError as error:
        raise SchemaError("Wiro Tool Detail returned malformed JSON.") from error
    if not isinstance(decoded, dict):
        raise SchemaError("Wiro Tool Detail returned a non-object response.")
    return decoded


def _dotenv_path() -> Path:
    """Find the caller's .env, falling back to the repository .env."""

    candidates = [Path.cwd() / ".env", Path(__file__).resolve().parents[1] / ".env"]
    for path in candidates:
        if not path.exists():
            continue
        return path
    return candidates[0]


def _http_error_detail(error: HTTPError) -> str:
    try:
        raw = error.read().decode("utf-8", errors="replace")
    except OSError:
        return ""
    if not raw:
        return ""
    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError:
        return "provider returned a non-JSON error body"
    if isinstance(decoded, dict):
        detail = decoded.get("errors") or decoded.get("error") or decoded.get("message")
        if detail:
            return _safe_text(detail)
    return "provider returned an error response"


def extract_tool(response: Mapping[str, Any], model_ref: str) -> Mapping[str, Any]:
    if response.get("result") is not True:
        detail = response.get("errors") or "the provider rejected the request"
        raise SchemaError(f"Wiro rejected {model_ref}: {_safe_text(detail)}")
    tools = response.get("tool")
    if not isinstance(tools, list) or not tools or not isinstance(tools[0], dict):
        raise SchemaError(f"Wiro returned no model detail for {model_ref}.")
    return tools[0]


def print_report(model_ref: str, tool: Mapping[str, Any]) -> None:
    owner, model = parse_model_ref(model_ref)
    print(f"# Wiro Schema: `{model_ref}`")
    print()
    print(f"- Model page: <{DOCS_ROOT}/{model_ref}>")
    print(f"- Tool Detail URL: <{DETAIL_URL}>")
    print(f"- Run URL: <https://api.wiro.ai/v1/Run/{owner}/{model}>")
    print(f"- Available: {_markdown(tool.get('result', True))}")
    for label, key in (
        ("Title", "title"),
        ("Description", "description"),
        ("Expected runtime", "computingtime"),
    ):
        if tool.get(key) not in (None, ""):
            print(f"- {label}: {_markdown(tool[key])}")

    categories = _as_list(tool.get("categories"))
    if categories:
        print(
            f"- Categories: {', '.join(f'`{_safe_text(item)}`' for item in categories)}"
        )
        print(
            f"- Text-to-image: {'yes' if _has_category(categories, 'text-to-image') else 'no'}"
        )
        print(
            f"- Image-to-image: {'yes' if _has_category(categories, 'image-to-image') else 'no'}"
        )

    print()
    print_parameters(tool.get("parameters"))
    print_outputs(tool)
    print_pricing(tool.get("dynamicprice"))


def print_parameters(raw: Any) -> None:
    parameters = decode_json(raw)
    entries = parameter_entries(parameters)
    print("## Inputs")
    print()
    if not entries:
        print("No structured input parameters were returned.")
        print()
        return
    print(
        "| Name | Type | Required | Default | Choices | Bounds | File limit | Description |"
    )
    print("| --- | --- | --- | --- | --- | --- | ---: | --- |")
    for entry in entries:
        name = first_value(
            entry, "name", "field", "fieldname", "parameter", "key", "id"
        )
        if not name:
            name = "(unnamed)"
        type_name = (
            first_value(entry, "type", "datatype", "inputtype", "dataType") or "unknown"
        )
        required = first_value(entry, "required", "isrequired", "mandatory")
        default = first_value(entry, "default", "defaultValue", "defaultvalue", "value")
        choices = choice_values(entry)
        minimum = first_value(entry, "minimum", "min", "minValue", "minvalue")
        maximum = first_value(entry, "maximum", "max", "maxValue", "maxvalue")
        file_limit = first_value(
            entry,
            "maxFiles",
            "max_files",
            "max_count",
            "maxCount",
            "maximumCount",
            "maxinputlenght",
            "max",
        )
        if file_limit is None and str(type_name).lower() in {
            "file",
            "image",
            "file[]",
            "image[]",
            "fileinput",
            "multifileinput",
            "combinefileinput",
        }:
            file_limit = maximum
        bounds = ""
        if minimum is not None or maximum is not None:
            bounds = f"{minimum if minimum is not None else ''}..{maximum if maximum is not None else ''}"
        description = first_value(entry, "description", "help", "note", "label") or ""
        cells = (
            name,
            type_name,
            _required_text(required),
            default,
            ", ".join(map(str, choices)),
            bounds,
            file_limit,
            description,
        )
        print("| " + " | ".join(_table_cell(value) for value in cells) + " |")
    print()
    source_limits = [entry for entry in entries if _looks_like_source(entry)]
    if source_limits:
        print("- Source-image inputs:")
        for entry in source_limits:
            name = (
                first_value(
                    entry, "name", "field", "fieldname", "parameter", "key", "id"
                )
                or "(unnamed)"
            )
            limit = first_value(
                entry,
                "maxFiles",
                "max_files",
                "max_count",
                "maxCount",
                "maximumCount",
                "maxinputlenght",
                "maximum",
                "max",
            )
            print(
                f"  - `{name}`: maximum `{limit}` source file(s)"
                if limit is not None
                else f"  - `{name}`: file input"
            )
        print()


def print_pricing(raw: Any) -> None:
    pricing = decode_json(raw)
    if pricing in (None, "", [], {}):
        return
    print("## Pricing")
    print()
    print("```json")
    print(json.dumps(pricing, indent=2, ensure_ascii=False, sort_keys=True))
    print("```")
    print()


def print_outputs(tool: Mapping[str, Any]) -> None:
    output = first_value(tool, "outputs", "output", "outputtype", "outputType")
    if output in (None, "", [], {}):
        return
    print("## Outputs")
    print()
    print("```json")
    print(json.dumps(decode_json(output), indent=2, ensure_ascii=False, sort_keys=True))
    print("```")
    print()


def parameter_entries(value: Any) -> list[Mapping[str, Any]]:
    value = decode_json(value)
    if isinstance(value, list):
        entries = []
        for item in value:
            if not isinstance(item, dict):
                continue
            nested = item.get("items")
            entries.extend(parameter_entries(nested) if nested is not None else [item])
        return entries
    if isinstance(value, dict):
        properties = value.get("properties")
        if isinstance(properties, dict):
            entries = []
            required = set(value.get("required", []))
            for name, definition in properties.items():
                if isinstance(definition, dict):
                    entry = dict(definition)
                    entry.setdefault("name", name)
                    if name in required:
                        entry.setdefault("required", True)
                    entries.append(entry)
            return entries
        for key in ("inputs", "parameters", "fields", "items"):
            nested = parameter_entries(value.get(key))
            if nested:
                return nested
        return [value]
    return []


def choice_values(entry: Mapping[str, Any]) -> list[Any]:
    value = first_value(entry, "choices", "options", "enum", "values")
    if not isinstance(value, list):
        return []
    result = []
    for item in value:
        if isinstance(item, dict):
            result.append(
                first_value(item, "value", "id", "name", "label", "text") or item
            )
        else:
            result.append(item)
    return result


def first_value(entry: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in entry and entry[key] not in (None, ""):
            return entry[key]
    return None


def _looks_like_source(entry: Mapping[str, Any]) -> bool:
    name = _safe_text(
        first_value(entry, "name", "field", "fieldname", "parameter", "key", "id")
    )
    type_name = _safe_text(
        first_value(entry, "type", "datatype", "inputtype", "dataType")
    )
    return "image" in name.lower() or type_name.lower() in {
        "file",
        "image",
        "file[]",
        "image[]",
        "fileinput",
        "multifileinput",
        "combinefileinput",
    }


def decode_json(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def _has_category(categories: list[Any], expected: str) -> bool:
    return expected in {_safe_text(item).lower() for item in categories}


def _as_list(value: Any) -> list[Any]:
    value = decode_json(value)
    if isinstance(value, list):
        return value
    return []


def _required_text(value: Any) -> str:
    if value is True or str(value).lower() in {"1", "true", "yes", "required"}:
        return "yes"
    return "no"


def _safe_text(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def _markdown(value: Any) -> str:
    return _safe_text(value).replace("|", "\\|").replace("\n", " ")


def _table_cell(value: Any) -> str:
    if value is None:
        return ""
    return _markdown(value)


if __name__ == "__main__":
    raise SystemExit(main())
