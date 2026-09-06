"""Contract tests for the non-generating Wiro schema command."""

from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts" / "get_schema_wiro.py"
SPEC = importlib.util.spec_from_file_location("get_schema_wiro", SCRIPT)
assert SPEC and SPEC.loader
schema = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(schema)


def test_schema_command_requests_detail_only_and_reports_inputs(capsys):
    calls = []

    def fake_request(url, *, headers, payload):
        calls.append((url, headers, payload))
        return {
            "result": True,
            "errors": [],
            "tool": [
                {
                    "title": "Seedream 5 Pro Uncensored",
                    "computingtime": "60 seconds",
                    "categories": ["text-to-image", "image-to-image"],
                    "parameters": [
                        {
                            "name": "inputImage",
                            "type": "file",
                            "maxFiles": 10,
                        },
                        {
                            "name": "resolution",
                            "type": "select",
                            "required": True,
                            "default": "1k",
                            "options": ["1k", "2k"],
                        },
                    ],
                    "output": {
                        "type": "image",
                        "urls": ["https://cdn.example/out.png"],
                    },
                    "dynamicprice": '[{"price":0.045,"priceMethod":"cpr"}]',
                }
            ],
        }

    result = schema.main(
        ["bytedance/seedream-v5-pro-uncensored"],
        environ={"WIRO_API_KEY": "do-not-print"},
        request=fake_request,
    )

    captured = capsys.readouterr()
    assert result == 0
    assert calls == [
        (
            schema.DETAIL_URL,
            {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "x-api-key": "do-not-print",
                "User-Agent": schema.USER_AGENT,
            },
            {
                "slugowner": "bytedance",
                "slugproject": "seedream-v5-pro-uncensored",
                "summary": False,
            },
        )
    ]
    assert "Tool Detail URL" in captured.out
    assert "Run URL" in captured.out
    assert "Text-to-image: yes" in captured.out
    assert "Image-to-image: yes" in captured.out
    assert "inputImage" in captured.out
    assert "maximum `10` source file(s)" in captured.out
    assert "resolution" in captured.out
    assert "https://cdn.example/out.png" in captured.out
    assert "0.045" in captured.out
    assert "do-not-print" not in captured.out
    assert "do-not-print" not in captured.err


def test_schema_command_rejects_missing_key_and_bad_model(capsys):
    assert schema.main(["bytedance/seedream-v5-pro"], environ={}) == 1
    missing_key = capsys.readouterr()
    assert "WIRO_API_KEY" in missing_key.err

    assert schema.main(["not-a-model"], environ={"WIRO_API_KEY": "key"}) == 1
    bad_model = capsys.readouterr()
    assert "owner/model" in bad_model.err


def test_schema_command_rejects_provider_error(capsys):
    def fake_request(url, *, headers, payload):
        return {"result": False, "errors": [{"message": "unknown model"}]}

    assert (
        schema.main(
            ["bytedance/missing"],
            environ={"WIRO_API_KEY": "key"},
            request=fake_request,
        )
        == 1
    )
    captured = capsys.readouterr()
    assert "rejected" in captured.err
    assert "unknown model" in captured.err


def test_schema_help_does_not_require_credentials(capsys):
    assert schema.main(["--help"], environ={}) == 0
    assert "usage: scripts/get_schema_wiro owner/model" in capsys.readouterr().out


def test_schema_command_loads_key_from_repo_dotenv(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("WIRO_API_KEY=from-dotenv\n", encoding="utf-8")
    calls = []

    def fake_request(url, *, headers, payload):
        calls.append(headers)
        return {"result": True, "tool": [{"title": "Seedream"}]}

    assert (
        schema.main(["bytedance/seedream-v5-pro-uncensored"], request=fake_request) == 0
    )
    assert calls[0]["x-api-key"] == "from-dotenv"
    assert "from-dotenv" not in capsys.readouterr().out


def test_schema_report_flattens_wiro_parameter_groups(capsys):
    schema.print_parameters(
        [
            {
                "title": "Input",
                "items": [
                    {
                        "id": "inputImage",
                        "type": "combinefileinput",
                        "maxinputlenght": 10,
                        "note": "Reference images",
                    },
                    {
                        "id": "resolution",
                        "type": "select",
                        "defaultvalue": "1k",
                        "options": [{"value": "1k", "text": "1k"}],
                    },
                ],
            }
        ]
    )

    output = capsys.readouterr().out
    assert "| inputImage | combinefileinput |" in output
    assert "maximum `10` source file(s)" in output
    assert "| resolution | select |" in output
    assert "1k" in output
