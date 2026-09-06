from imagegen import main


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

    exit_code = main(
        ["--provider", "falai", "--model", "Seedream 4.5", "--help"]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "--image_size" in captured.out
    assert "--image-size" in captured.out
    assert "auto_2K" in captured.out
    assert not (tmp_path / ".env").exists()


def test_model_help_does_not_expose_source_image_parameter(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)

    exit_code = main(
        ["--provider", "replicate", "--model", "seedream45", "--help"]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "--image_input" not in captured.out


def test_model_help_exposes_boolean_positive_and_negative_options(
    tmp_path,
    monkeypatch,
    capsys,
):
    monkeypatch.chdir(tmp_path)

    exit_code = main(
        ["--provider", "falai", "--model", "nano-banana-2", "--help"]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "--limit_generations" in captured.out
    assert "--no-limit_generations" in captured.out
    assert "--limit-generations" in captured.out
    assert "--no-limit-generations" in captured.out


def test_model_help_does_not_expose_fixed_provider_inputs(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)

    exit_code = main(["--provider", "falai", "--model", "flux-2", "--help"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "--sync_mode" not in captured.out
    assert "--sync-mode" not in captured.out
