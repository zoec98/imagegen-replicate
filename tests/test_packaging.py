import tomllib
from pathlib import Path


def test_project_exposes_cli_and_web_console_scripts():
    project_file = Path(__file__).parents[1] / "pyproject.toml"
    metadata = tomllib.loads(project_file.read_text(encoding="utf-8"))

    assert metadata["project"]["scripts"] == {
        "imagegen": "imagegen.cli:main",
        "imagegen-web": "imagegen.web:main",
    }
