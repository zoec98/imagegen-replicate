"""Application configuration and .env management."""

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
        name="IMAGEGEN_MODEL",
        default=DEFAULT_MODEL_ALIAS,
        comment=f"Default model alias. Options: {', '.join(sorted(MODEL_REGISTRY))}.",
    ),
    EnvSetting(
        name="IMAGEGEN_FLASK_SECRET_KEY",
        default="dev-secret-change-me",
        comment="Flask secret key for local development. Replace for shared deployments.",
    ),
)


@dataclass(frozen=True)
class AppConfig:
    replicate_api_token: str
    output_dir: Path
    model_alias: str
    model: ReplicateModel
    flask_secret_key: str


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

    env_file = ensure_env_file(env_path)
    load_dotenv(env_file, override=False)

    model_alias = os.getenv("IMAGEGEN_MODEL", DEFAULT_MODEL_ALIAS).strip()
    model = MODEL_REGISTRY.get(model_alias)
    if model is None:
        choices = ", ".join(sorted(MODEL_REGISTRY))
        msg = f"Unknown IMAGEGEN_MODEL {model_alias!r}. Expected one of: {choices}."
        raise ValueError(msg)

    return AppConfig(
        replicate_api_token=os.getenv("REPLICATE_API_TOKEN", "").strip(),
        output_dir=Path(os.getenv("IMAGEGEN_OUTPUT_DIR", "data/images")).expanduser(),
        model_alias=model_alias,
        model=model,
        flask_secret_key=os.getenv(
            "IMAGEGEN_FLASK_SECRET_KEY",
            "dev-secret-change-me",
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
