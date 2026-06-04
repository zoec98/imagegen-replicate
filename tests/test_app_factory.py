"""Flask app factory and asset version tests.

Behaviors protected:
- App construction returns a configured Flask app with isolated data directories.
- App startup cleans stale temporary clean-export files.
- UI asset checksums change when rendered asset content changes.
"""

from imagegen.app_version import app_checksum


def test_app_checksum_changes_when_asset_content_changes(tmp_path):
    template = tmp_path / "index.html"
    script = tmp_path / "app.js"
    style = tmp_path / "app.css"
    template.write_text("<html></html>", encoding="utf-8")
    script.write_text("console.log('one');", encoding="utf-8")
    style.write_text("body { color: black; }", encoding="utf-8")

    first = app_checksum((template, script, style))

    script.write_text("console.log('two');", encoding="utf-8")

    assert app_checksum((template, script, style)) != first


def test_create_app_returns_flask_app(app_factory):
    app = app_factory()

    assert app.name == "imagegen.app"


def test_create_app_creates_derived_data_directories(app_config, app_factory):
    app_factory()

    assert app_config.data_dir.is_dir()
    assert app_config.output_dir.is_dir()
    assert app_config.fragment_root.is_dir()
    assert app_config.trash_dir.is_dir()
    assert app_config.tmp_dir.is_dir()


def test_create_app_cleans_temporary_exports(app_config, app_factory):
    app_config.tmp_dir.mkdir(parents=True)
    stale_export = app_config.tmp_dir / "sample-clean-old.png"
    stale_export.write_bytes(b"stale")

    app_factory()

    assert not stale_export.exists()
