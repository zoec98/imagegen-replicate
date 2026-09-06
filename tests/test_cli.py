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
