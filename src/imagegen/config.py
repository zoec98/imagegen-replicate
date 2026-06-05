"""Application configuration and .env management.

This module owns local `.env` file creation/update and conversion of environment
variables into the typed AppConfig used by the Flask app and service wrappers.
"""

from __future__ import annotations

import os
import secrets
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from imagegen.model_registry import (
    DEFAULT_MODEL_ALIAS,
    MODEL_REGISTRY,
    ProviderId,
    ReplicateModel,
)


FLASK_SECRET_SETTING = "IMAGEGEN_FLASK_SECRET_KEY"
INSECURE_FLASK_SECRET_KEY = "dev-secret-change-me"
FLASK_SECRET_BYTES = 32


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
        name="FAL_KEY",
        default="",
        comment="fal.ai API key. Leave empty until you are ready to call fal.ai.",
    ),
    EnvSetting(
        name="IMAGEGEN_DATA_DIR",
        default="data",
        comment="Directory where runtime data, images, palettes, trash, and SQLite live.",
    ),
    EnvSetting(
        name="TRASHCAN_HOLD_LIMIT_DAYS",
        default="7",
        comment="Days to keep trash before automatic purge. Use 0 to disable.",
    ),
    EnvSetting(
        name="AUTHOR",
        default="Noname Changeme Nescio",
        comment="Author name embedded in generated image metadata.",
    ),
    EnvSetting(
        name="IMMICH_URL",
        default="",
        comment="Optional Immich server URL for uploading gallery images.",
    ),
    EnvSetting(
        name="IMMICH_GALLERY_ID",
        default="",
        comment="Optional Immich album id to attach uploaded images to.",
    ),
    EnvSetting(
        name="IMMICH_API_KEY",
        default="",
        comment=(
            "Optional Immich API key. Required permissions: asset.upload and "
            "albumAsset.create."
        ),
    ),
    EnvSetting(
        name="IMAGEGEN_MODEL",
        default=DEFAULT_MODEL_ALIAS,
        comment=f"Default model alias. Options: {', '.join(sorted(MODEL_REGISTRY))}.",
    ),
    EnvSetting(
        name=FLASK_SECRET_SETTING,
        default="",
        comment="Flask secret key for browser sessions. Generated automatically by setup.",
    ),
    EnvSetting(
        name="IMAGEGEN_REPLICATE_POLL_SECONDS",
        default="1.0",
        comment="Seconds between Replicate prediction polling requests.",
    ),
    EnvSetting(
        name="IMAGEGEN_REPLICATE_TIMEOUT_SECONDS",
        default="180.0",
        comment="Maximum seconds to wait for a Replicate prediction before timing out.",
    ),
)

DEPRECATED_ENV_SETTING_NAMES = {
    "IMAGEGEN_OUTPUT_DIR",
    "IMAGEGEN_DB_PATH",
    "IMAGEGEN_FRAGMENT_ROOT",
}


@dataclass(frozen=True)
class AppConfig:
    replicate_api_token: str
    fal_key: str
    enabled_providers: tuple[ProviderId, ...]
    selected_provider: ProviderId | None
    data_dir: Path
    author: str
    immich_url: str
    immich_gallery_id: str
    immich_api_key: str
    model_alias: str
    model: ReplicateModel
    flask_secret_key: str
    replicate_poll_seconds: float
    replicate_timeout_seconds: float
    trashcan_hold_limit_days: int | None

    @property
    def has_generation_provider(self) -> bool:
        return self.selected_provider is not None

    @property
    def output_dir(self) -> Path:
        return self.data_dir / "images"

    @property
    def fragment_root(self) -> Path:
        return self.data_dir / "fragments"

    @property
    def trash_dir(self) -> Path:
        return self.data_dir / "trash"

    @property
    def tmp_dir(self) -> Path:
        return self.data_dir / "tmp"

    @property
    def generation_log_path(self) -> Path:
        return self.data_dir / "imagegen.sqlite3"

    @property
    def immich_enabled(self) -> bool:
        return bool(
            self.immich_url.strip()
            and self.immich_gallery_id.strip()
            and self.immich_api_key.strip()
        )


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
        "\n".join(_setting_lines(ENV_SETTINGS, generate_secrets=False)) + "\n",
        encoding="utf-8",
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

    data_dir = Path(os.getenv("IMAGEGEN_DATA_DIR", "data")).expanduser()
    if not data_dir.is_absolute():
        data_dir = env_file.parent / data_dir

    replicate_api_token = os.getenv("REPLICATE_API_TOKEN", "").strip()
    fal_key = os.getenv("FAL_KEY", "").strip()
    enabled_providers = _enabled_providers(
        replicate_api_token=replicate_api_token,
        fal_key=fal_key,
    )

    return AppConfig(
        replicate_api_token=replicate_api_token,
        fal_key=fal_key,
        enabled_providers=enabled_providers,
        selected_provider=_selected_provider(enabled_providers),
        data_dir=data_dir,
        author=os.getenv("AUTHOR", "Noname Changeme Nescio").strip(),
        immich_url=os.getenv("IMMICH_URL", "").strip().rstrip("/"),
        immich_gallery_id=os.getenv("IMMICH_GALLERY_ID", "").strip(),
        immich_api_key=os.getenv("IMMICH_API_KEY", "").strip(),
        model_alias=model_alias,
        model=model,
        flask_secret_key=os.getenv(
            FLASK_SECRET_SETTING,
            "",
        ),
        replicate_poll_seconds=_float_env("IMAGEGEN_REPLICATE_POLL_SECONDS", 1.0),
        replicate_timeout_seconds=_float_env(
            "IMAGEGEN_REPLICATE_TIMEOUT_SECONDS",
            60.0,
        ),
        trashcan_hold_limit_days=_optional_positive_int_env(
            "TRASHCAN_HOLD_LIMIT_DAYS",
            7,
        ),
    )


def _with_required_settings(existing_lines: list[str]) -> list[str]:
    lines = _without_deprecated_settings(existing_lines)

    for setting in ENV_SETTINGS:
        index = _find_setting_line(lines, setting.name)
        if index is None:
            if lines and lines[-1] != "":
                lines.append("")
            lines.extend(_setting_lines((setting,)))
            continue

        current_value = lines[index].split("=", 1)[1].strip()
        if current_value and not _is_insecure_flask_secret(setting, current_value):
            continue

        lines[index] = f"{setting.name}={_setting_value(setting)}"
        comment = f"# {setting.comment}"
        previous_line = lines[index - 1] if index > 0 else ""
        if previous_line != comment:
            lines.insert(index, comment)

    return lines


def _without_deprecated_settings(existing_lines: list[str]) -> list[str]:
    lines: list[str] = []
    skip_next_blank = False
    for line in existing_lines:
        key = _line_key(line)
        if key in DEPRECATED_ENV_SETTING_NAMES:
            if lines and lines[-1].startswith("# "):
                lines.pop()
            skip_next_blank = True
            continue
        if skip_next_blank and not line.strip():
            skip_next_blank = False
            continue
        skip_next_blank = False
        lines.append(line)
    return lines


def _setting_lines(
    settings: tuple[EnvSetting, ...],
    *,
    generate_secrets: bool = True,
) -> list[str]:
    lines: list[str] = []
    for setting in settings:
        lines.extend(
            (
                f"# {setting.comment}",
                f"{setting.name}={_setting_value(setting, generate=generate_secrets)}",
            )
        )
    return lines


def _setting_value(setting: EnvSetting, *, generate: bool = True) -> str:
    if generate and setting.name == FLASK_SECRET_SETTING:
        return secrets.token_urlsafe(FLASK_SECRET_BYTES)
    return setting.default


def _is_insecure_flask_secret(setting: EnvSetting, value: str) -> bool:
    return setting.name == FLASK_SECRET_SETTING and value == INSECURE_FLASK_SECRET_KEY


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


def _optional_positive_int_env(name: str, default: int) -> int | None:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    try:
        parsed = int(value)
    except ValueError:
        return None
    if parsed <= 0:
        return None
    return parsed


def _enabled_providers(
    *,
    replicate_api_token: str,
    fal_key: str,
) -> tuple[ProviderId, ...]:
    providers: list[ProviderId] = []
    if replicate_api_token:
        providers.append("replicate")
    if fal_key:
        providers.append("falai")
    return tuple(providers)


def _selected_provider(
    enabled_providers: tuple[ProviderId, ...],
) -> ProviderId | None:
    if "replicate" in enabled_providers:
        return "replicate"
    if enabled_providers:
        return enabled_providers[0]
    return None
