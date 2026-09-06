from imagegen import main
from imagegen.cli import CliRequest, parse_cli_request


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
