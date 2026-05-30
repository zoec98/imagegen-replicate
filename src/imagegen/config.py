"""Application configuration and .env management.

This module owns local `.env` file creation/update and conversion of environment
variables into the typed AppConfig used by the Flask app and service wrappers.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from imagegen.model_registry import DEFAULT_MODEL_ALIAS, MODEL_REGISTRY, ReplicateModel


@dataclass(frozen=True)
class EnvSetting:
    name: str
    default: str
    comment: str


ENV_SETTINGS: tuple[EnvSetting, ...] = (
    EnvSetting(
        name="REPLICATE_API_TOKEN",
        default="",
        comment="Replicate API token. Leave empty until you are ready to call Replicate.",
    ),
    EnvSetting(
        name="IMAGEGEN_OUTPUT_DIR",
        default="data/images",
        comment="Directory where downloaded generated images and metadata are stored.",
    ),
    EnvSetting(
        name="IMAGEGEN_DB_PATH",
        default="data/imagegen.sqlite3",
        comment="SQLite database path for durable generation request history.",
    ),
    EnvSetting(
        name="IMAGEGEN_MODEL",
        default=DEFAULT_MODEL_ALIAS,
        comment=f"Default model alias. Options: {', '.join(sorted(MODEL_REGISTRY))}.",
    ),
    EnvSetting(
        name="IMAGEGEN_FLASK_SECRET_KEY",
        default="dev-secret-change-me",
        comment="Flask secret key for local development. Replace for shared deployments.",
    ),
    EnvSetting(
        name="IMAGEGEN_REPLICATE_POLL_SECONDS",
        default="1.0",
        comment="Seconds between Replicate prediction polling requests.",
    ),
    EnvSetting(
        name="IMAGEGEN_REPLICATE_TIMEOUT_SECONDS",
        default="60.0",
        comment="Maximum seconds to wait for a Replicate prediction before timing out.",
    ),
)


@dataclass(frozen=True)
class AppConfig:
    replicate_api_token: str
    output_dir: Path
    generation_log_path: Path
    model_alias: str
    model: ReplicateModel
    flask_secret_key: str
    replicate_poll_seconds: float
    replicate_timeout_seconds: float


def ensure_env_file(path: str | Path = ".env") -> Path:
    """Create or update a local .env file with all expected settings."""

    env_path = Path(path)
    existing_lines = (
        env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
    )
    lines = _with_required_settings(existing_lines)
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return env_path


def write_env_example(path: str | Path = ".env.example") -> Path:
    """Write a committed example env file with non-secret defaults."""

    example_path = Path(path)
    example_path.write_text(
        "\n".join(_setting_lines(ENV_SETTINGS)) + "\n", encoding="utf-8"
    )
    return example_path


def load_config(env_path: str | Path = ".env") -> AppConfig:
    """Ensure .env exists, load it, and return typed application config."""

    env_file = ensure_env_file(env_path).resolve()
    load_dotenv(env_file, override=False)

    model_alias = os.getenv("IMAGEGEN_MODEL", DEFAULT_MODEL_ALIAS).strip()
    model = MODEL_REGISTRY.get(model_alias)
    if model is None:
        choices = ", ".join(sorted(MODEL_REGISTRY))
        msg = f"Unknown IMAGEGEN_MODEL {model_alias!r}. Expected one of: {choices}."
        raise ValueError(msg)

    output_dir = Path(os.getenv("IMAGEGEN_OUTPUT_DIR", "data/images")).expanduser()
    if not output_dir.is_absolute():
        output_dir = env_file.parent / output_dir
    generation_log_path = Path(
        os.getenv("IMAGEGEN_DB_PATH", "data/imagegen.sqlite3")
    ).expanduser()
    if not generation_log_path.is_absolute():
        generation_log_path = env_file.parent / generation_log_path

    return AppConfig(
        replicate_api_token=os.getenv("REPLICATE_API_TOKEN", "").strip(),
        output_dir=output_dir,
        generation_log_path=generation_log_path,
        model_alias=model_alias,
        model=model,
        flask_secret_key=os.getenv(
            "IMAGEGEN_FLASK_SECRET_KEY",
            "dev-secret-change-me",
        ),
        replicate_poll_seconds=_float_env("IMAGEGEN_REPLICATE_POLL_SECONDS", 1.0),
        replicate_timeout_seconds=_float_env(
            "IMAGEGEN_REPLICATE_TIMEOUT_SECONDS",
            60.0,
        ),
    )


def _with_required_settings(existing_lines: list[str]) -> list[str]:
    lines = list(existing_lines)

    for setting in ENV_SETTINGS:
        index = _find_setting_line(lines, setting.name)
        if index is None:
            if lines and lines[-1] != "":
                lines.append("")
            lines.extend(_setting_lines((setting,)))
            continue

        current_value = lines[index].split("=", 1)[1].strip()
        if current_value:
            continue

        lines[index] = f"{setting.name}={setting.default}"
        comment = f"# {setting.comment}"
        previous_line = lines[index - 1] if index > 0 else ""
        if previous_line != comment:
            lines.insert(index, comment)

    return lines


def _setting_lines(settings: tuple[EnvSetting, ...]) -> list[str]:
    lines: list[str] = []
    for setting in settings:
        lines.extend((f"# {setting.comment}", f"{setting.name}={setting.default}"))
    return lines


def _line_key(line: str) -> str | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or "=" not in stripped:
        return None
    key = stripped.split("=", 1)[0].strip()
    return key or None


def _find_setting_line(lines: list[str], name: str) -> int | None:
    for index, line in enumerate(lines):
        if _line_key(line) == name:
            return index
    return None


def _float_env(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    try:
        parsed = float(value)
    except ValueError as error:
        msg = f"{name} must be a number."
        raise ValueError(msg) from error
    if parsed <= 0:
        msg = f"{name} must be greater than zero."
        raise ValueError(msg)
    return parsed
