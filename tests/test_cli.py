import json
from dataclasses import replace

import pytest

from imagegen import main
from imagegen.cli import (
    CliArgumentError,
    CliRequest,
    parse_cli_request,
    run_cli_generation,
)
from imagegen.generation_log import SQLiteGenerationLog
from imagegen.generation_types import GenerationResult
from imagegen.model_registry import resolve_model
from imagegen.request_store import RequestStore


def test_help_lists_providers_and_models_without_loading_configuration(
    tmp_path,
    monkeypatch,
    capsys,
):
    monkeypatch.chdir(tmp_path)

    exit_code = main(["--help"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "replicate" in captured.out
    assert "Seedream 4.5" in captured.out
    assert "falai" in captured.out
    assert "Bria Fibo" in captured.out
    assert not (tmp_path / ".env").exists()


def test_model_help_lists_registry_parameters_for_display_name(
    tmp_path,
    monkeypatch,
    capsys,
):
    monkeypatch.chdir(tmp_path)

    exit_code = main(["--provider", "falai", "--model", "Seedream 4.5", "--help"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "--image_size" in captured.out
    assert "--image-size" in captured.out
    assert "auto_2K" in captured.out
    assert not (tmp_path / ".env").exists()


def test_model_help_does_not_expose_source_image_parameter(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)

    exit_code = main(["--provider", "replicate", "--model", "seedream45", "--help"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "--image_input" not in captured.out


def test_model_help_exposes_boolean_positive_and_negative_options(
    tmp_path,
    monkeypatch,
    capsys,
):
    monkeypatch.chdir(tmp_path)

    exit_code = main(["--provider", "falai", "--model", "nano-banana-2", "--help"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "--limit_generations" in captured.out
    assert "--no-limit_generations" in captured.out
    assert "--limit-generations" in captured.out
    assert "--no-limit-generations" in captured.out


def test_model_help_does_not_expose_fixed_provider_inputs(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)

    exit_code = main(["--provider", "falai", "--model", "flux-2", "--help"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "--sync_mode" not in captured.out
    assert "--sync-mode" not in captured.out


def test_file_prompt_is_read_as_trimmed_utf8_before_generation(
    tmp_path,
    monkeypatch,
):
    prompt_file = tmp_path / "prompt.txt"
    prompt_file.write_text("\n  a red fox  \n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    request = parse_cli_request(
        ["--provider", "falai", "--model", "seedream45", "--file", str(prompt_file)]
    )

    assert isinstance(request, CliRequest)
    assert request.prompt == "a red fox"


def test_prompt_and_file_are_mutually_exclusive(tmp_path, monkeypatch, capsys):
    prompt_file = tmp_path / "prompt.txt"
    prompt_file.write_text("a red fox", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    exit_code = main(
        [
            "--provider",
            "falai",
            "--model",
            "seedream45",
            "--prompt",
            "a red fox",
            "--file",
            str(prompt_file),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "not allowed with argument" in captured.err


def test_model_parameter_aliases_are_normalized_and_typed():
    request = parse_cli_request(
        [
            "--provider",
            "falai",
            "--model",
            "seedream45",
            "--prompt",
            "a red fox",
            "--image-size",
            "square",
            "--num-images",
            "2",
        ]
    )

    assert isinstance(request, CliRequest)
    assert request.parameters["image_size"] == "square"
    assert request.parameters["num_images"] == 2


def test_cli_generation_runs_synchronously_through_existing_provider_service(
    app_config,
):
    request = parse_cli_request(
        [
            "--provider",
            "replicate",
            "--model",
            "seedream45",
            "--prompt",
            "a red fox",
        ]
    )
    assert isinstance(request, CliRequest)

    class FakeProvider:
        def generate(self, request_record, config):
            assert request_record.prompt == "a red fox"
            assert request_record.model_alias == "seedream45"
            return GenerationResult(
                prediction_id="prediction-1",
                output_urls=["https://example.test/fox.png"],
                stored_images=[],
                logs="",
            )

    record = run_cli_generation(
        request,
        app_config=app_config,
        providers={"replicate": FakeProvider()},
    )

    assert record.status == "succeeded"
    assert record.prediction_id == "prediction-1"
    assert record.output_urls == ["https://example.test/fox.png"]
    log = SQLiteGenerationLog(app_config.generation_log_path)
    assert log.get_request(record.request_id)["model_alias"] == "seedream45"
    assert log.get_result(record.request_id)["status"] == "succeeded"


def test_cli_generation_runs_wiro_when_wiro_is_enabled(app_config):
    model = resolve_model("wiro", "seedream5-lite-uncensored")
    config = replace(
        app_config,
        wiro_api_key="wiro-key",
        enabled_providers=("wiro",),
        selected_provider="wiro",
        model_alias=model.alias,
        model=model,
    )
    request = parse_cli_request(
        [
            "--provider",
            "wiro",
            "--model",
            model.alias,
            "--prompt",
            "a red fox",
        ]
    )
    assert isinstance(request, CliRequest)

    class FakeProvider:
        def generate(self, request_record, provider_config):
            assert provider_config.wiro_api_key == "wiro-key"
            assert request_record.provider == "wiro"
            assert request_record.model_alias == model.alias
            return GenerationResult(
                prediction_id="wiro-task-1",
                output_urls=["https://example.test/fox.jpg"],
                stored_images=[],
                logs="",
            )

    record = run_cli_generation(
        request,
        app_config=config,
        providers={"wiro": FakeProvider()},
    )

    assert record.status == "succeeded"
    assert record.prediction_id == "wiro-task-1"


def test_cli_generation_reuses_existing_parameter_validation(app_config):
    request = parse_cli_request(
        [
            "--provider",
            "replicate",
            "--model",
            "flux-flex",
            "--prompt",
            "a red fox",
            "--guidance",
            "999",
        ]
    )
    assert isinstance(request, CliRequest)

    with pytest.raises(CliArgumentError, match="guidance must be at most"):
        run_cli_generation(request, app_config=app_config, providers={})


def test_cli_generation_returns_failed_terminal_request(app_config):
    request = parse_cli_request(
        [
            "--provider",
            "replicate",
            "--model",
            "seedream45",
            "--prompt",
            "a red fox",
        ]
    )
    assert isinstance(request, CliRequest)

    class FailingProvider:
        def generate(self, request_record, config):
            raise RuntimeError("provider is unavailable")

    record = run_cli_generation(
        request,
        app_config=app_config,
        providers={"replicate": FailingProvider()},
    )

    assert record.status == "failed"
    assert record.error == "provider is unavailable"


def test_successful_json_output_contains_project_relative_image_paths(
    tmp_path,
    monkeypatch,
    capsys,
    app_config,
):
    monkeypatch.chdir(tmp_path)
    config = replace(app_config, data_dir=tmp_path / "outputs")
    store = RequestStore()
    record = store.create(
        provider="replicate",
        model_alias="seedream45",
        prompt="a red fox",
        parameters={},
    )
    store.update(
        record.request_id,
        status="succeeded",
        prediction_id="prediction-1",
        output_urls=["https://example.test/fox.png"],
        images=["seedream45-prediction-1-01.png"],
    )
    monkeypatch.setattr("imagegen.cli.load_config", lambda: config)
    monkeypatch.setattr("imagegen.cli.run_cli_generation", lambda request, **_: record)

    exit_code = main(
        [
            "--provider",
            "replicate",
            "--model",
            "seedream45",
            "--prompt",
            "a red fox",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert json.loads(captured.out)["images"] == [
        "outputs/images/seedream45-prediction-1-01.png"
    ]
    assert captured.err == ""


def test_quiet_output_contains_only_project_relative_image_paths(
    tmp_path,
    monkeypatch,
    capsys,
    app_config,
):
    monkeypatch.chdir(tmp_path)
    config = replace(app_config, data_dir=tmp_path / "outputs")
    store = RequestStore()
    record = store.create(
        provider="replicate",
        model_alias="seedream45",
        prompt="a red fox",
        parameters={},
    )
    store.update(
        record.request_id,
        status="succeeded",
        images=["one.png", "two.jpg"],
    )
    monkeypatch.setattr("imagegen.cli.load_config", lambda: config)
    monkeypatch.setattr("imagegen.cli.run_cli_generation", lambda request, **_: record)

    exit_code = main(
        [
            "--provider",
            "replicate",
            "--model",
            "seedream45",
            "--prompt",
            "a red fox",
            "--quiet",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out == "outputs/images/one.png\noutputs/images/two.jpg\n"
    assert captured.err == ""


def test_failed_generation_writes_error_to_stderr_and_returns_one(
    tmp_path,
    monkeypatch,
    capsys,
    app_config,
):
    monkeypatch.chdir(tmp_path)
    config = replace(app_config, data_dir=tmp_path / "outputs")
    record = RequestStore().create(
        provider="replicate",
        model_alias="seedream45",
        prompt="a red fox",
        parameters={},
    )
    record.error = "provider is unavailable"
    record.status = "failed"
    monkeypatch.setattr("imagegen.cli.load_config", lambda: config)
    monkeypatch.setattr("imagegen.cli.run_cli_generation", lambda request, **_: record)

    exit_code = main(
        [
            "--provider",
            "replicate",
            "--model",
            "seedream45",
            "--prompt",
            "a red fox",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert captured.err == "provider is unavailable\n"
