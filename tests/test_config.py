import os

import pytest

from imagegen.config import ensure_env_file, load_config, write_env_example
from imagegen.model_registry import MODEL_REGISTRY


def test_ensure_env_file_creates_expected_defaults(tmp_path):
    env_path = tmp_path / ".env"

    ensure_env_file(env_path)

    content = env_path.read_text(encoding="utf-8")
    assert "REPLICATE_API_TOKEN=" in content
    assert "IMAGEGEN_OUTPUT_DIR=data/images" in content
    assert "IMAGEGEN_MODEL=seedream45" in content
    assert "IMAGEGEN_FLASK_SECRET_KEY=dev-secret-change-me" in content
    assert "IMAGEGEN_REPLICATE_POLL_SECONDS=1.0" in content
    assert "IMAGEGEN_REPLICATE_TIMEOUT_SECONDS=60.0" in content


def test_ensure_env_file_preserves_existing_values(tmp_path):
    env_path = tmp_path / ".env"
    env_path.write_text(
        "REPLICATE_API_TOKEN=existing-token\n"
        "IMAGEGEN_OUTPUT_DIR=custom/images\n"
        "IMAGEGEN_MODEL=\n",
        encoding="utf-8",
    )

    ensure_env_file(env_path)

    content = env_path.read_text(encoding="utf-8")
    assert "REPLICATE_API_TOKEN=existing-token" in content
    assert "IMAGEGEN_OUTPUT_DIR=custom/images" in content
    assert "IMAGEGEN_MODEL=seedream45" in content
    assert "IMAGEGEN_FLASK_SECRET_KEY=dev-secret-change-me" in content
    assert "IMAGEGEN_REPLICATE_POLL_SECONDS=1.0" in content
    assert "IMAGEGEN_REPLICATE_TIMEOUT_SECONDS=60.0" in content


def test_write_env_example_uses_non_secret_defaults(tmp_path):
    example_path = tmp_path / ".env.example"

    write_env_example(example_path)

    content = example_path.read_text(encoding="utf-8")
    assert "REPLICATE_API_TOKEN=" in content
    assert "IMAGEGEN_MODEL=seedream45" in content


def test_load_config_reads_env_file(tmp_path, monkeypatch):
    monkeypatch.delenv("REPLICATE_API_TOKEN", raising=False)
    monkeypatch.delenv("IMAGEGEN_OUTPUT_DIR", raising=False)
    monkeypatch.delenv("IMAGEGEN_MODEL", raising=False)
    monkeypatch.delenv("IMAGEGEN_FLASK_SECRET_KEY", raising=False)
    monkeypatch.delenv("IMAGEGEN_REPLICATE_POLL_SECONDS", raising=False)
    monkeypatch.delenv("IMAGEGEN_REPLICATE_TIMEOUT_SECONDS", raising=False)
    env_path = tmp_path / ".env"
    env_path.write_text(
        "REPLICATE_API_TOKEN=test-token\n"
        "IMAGEGEN_OUTPUT_DIR=custom/images\n"
        "IMAGEGEN_MODEL=seedream45\n"
        "IMAGEGEN_FLASK_SECRET_KEY=test-secret\n"
        "IMAGEGEN_REPLICATE_POLL_SECONDS=2.5\n"
        "IMAGEGEN_REPLICATE_TIMEOUT_SECONDS=30\n",
        encoding="utf-8",
    )

    config = load_config(env_path)

    assert config.replicate_api_token == "test-token"
    assert config.output_dir == tmp_path / "custom/images"
    assert config.model_alias == "seedream45"
    assert config.model is MODEL_REGISTRY["seedream45"]
    assert config.flask_secret_key == "test-secret"
    assert config.replicate_poll_seconds == 2.5
    assert config.replicate_timeout_seconds == 30.0


def test_load_config_rejects_unknown_model(tmp_path, monkeypatch):
    monkeypatch.setenv("IMAGEGEN_MODEL", "unknown")
    env_path = tmp_path / ".env"

    with pytest.raises(ValueError, match="Unknown IMAGEGEN_MODEL"):
        load_config(env_path)


def test_load_config_does_not_override_existing_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("REPLICATE_API_TOKEN", "from-environment")
    env_path = tmp_path / ".env"
    env_path.write_text("REPLICATE_API_TOKEN=from-file\n", encoding="utf-8")

    config = load_config(env_path)

    assert config.replicate_api_token == "from-environment"
    assert os.environ["REPLICATE_API_TOKEN"] == "from-environment"
