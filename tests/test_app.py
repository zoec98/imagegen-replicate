import json
import os
from urllib.parse import parse_qs, urlparse

from imagegen.app import create_app
from imagegen.app_version import app_checksum


def extract_csrf_token(response):
    marker = b'<meta name="csrf-token" content="'
    start = response.data.index(marker) + len(marker)
    end = response.data.index(b'"', start)
    return response.data[start:end].decode("utf-8")


def extract_app_checksum(response):
    marker = b'<meta name="app-build" content="'
    start = response.data.index(marker) + len(marker)
    end = response.data.index(b'"', start)
    return response.data[start:end].decode("utf-8")


def extract_attribute(response, marker):
    start = response.data.index(marker) + len(marker)
    end = response.data.index(b'"', start)
    return response.data[start:end].decode("utf-8")


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


def test_index_renders_prompt_form(app_factory):
    client = app_factory().test_client()

    response = client.get("/")
    checksum = extract_app_checksum(response)

    assert response.status_code == 200
    assert b'name="csrf-token"' in response.data
    assert b'name="app-build"' in response.data
    assert len(checksum) == 16
    assert b'<form\n        class="prompt-form"' in response.data
    assert b'action="/generate"' not in response.data
    assert b'data-api-generate-url="/api/generate"' in response.data
    assert b'data-api-images-url="/api/images"' in response.data
    assert b'data-api-app-version-url="/api/app-version"' in response.data
    assert b'data-poll-seconds="1.0"' in response.data
    assert b'class="messages" aria-live="polite"' in response.data
    assert b'name="prompt"' in response.data
    assert b'name="size"' in response.data
    assert b'name="aspect_ratio"' in response.data
    assert b'name="max_images"' in response.data
    assert b"disable_safety_checker" not in response.data
    assert b"Generate" in response.data


def test_index_static_asset_urls_are_cache_busted(app_factory):
    client = app_factory().test_client()

    response = client.get("/")
    checksum = extract_app_checksum(response)
    css_url = extract_attribute(response, b'<link rel="stylesheet" href="')
    js_url = extract_attribute(response, b'<script defer src="')

    assert urlparse(css_url).path == "/static/app.css"
    assert urlparse(js_url).path == "/static/app.js"
    assert parse_qs(urlparse(css_url).query) == {"v": [checksum]}
    assert parse_qs(urlparse(js_url).query) == {"v": [checksum]}


def test_api_app_version_matches_rendered_checksum(app_factory):
    client = app_factory().test_client()
    index = client.get("/")
    checksum = extract_app_checksum(index)

    response = client.get("/api/app-version")

    assert response.status_code == 200
    assert response.json == {"app_checksum": checksum}


def test_index_lists_existing_images(tmp_path, app_factory):
    (tmp_path / "first.png").write_bytes(b"not really an image")
    (tmp_path / "animated.gif").write_bytes(b"gif")
    (tmp_path / "ignore.txt").write_text("ignore", encoding="utf-8")
    client = app_factory().test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert b"first.png" in response.data
    assert b'href="/images/first.png"' in response.data
    assert b"animated.gif" not in response.data
    assert b"ignore.txt" not in response.data


def test_image_route_serves_stored_file(tmp_path, app_factory):
    (tmp_path / "sample.png").write_bytes(b"image-bytes")
    client = app_factory().test_client()

    response = client.get("/images/sample.png")

    assert response.status_code == 200
    assert response.data == b"image-bytes"


def test_image_route_uses_env_relative_output_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    output_dir = tmp_path / "data" / "images"
    output_dir.mkdir(parents=True)
    (output_dir / "sample.png").write_bytes(b"image-bytes")
    (tmp_path / ".env").write_text(
        "IMAGEGEN_OUTPUT_DIR=data/images\n"
        "IMAGEGEN_MODEL=seedream45\n"
        "IMAGEGEN_FLASK_SECRET_KEY=test-secret\n",
        encoding="utf-8",
    )
    app = create_app({"TESTING": True, "IMAGEGEN_ENV_PATH": tmp_path / ".env"})

    response = app.test_client().get("/images/sample.png")

    assert response.status_code == 200
    assert response.data == b"image-bytes"


def test_image_route_blocks_unsafe_paths(app_factory):
    client = app_factory().test_client()

    response = client.get("/images/../pyproject.toml")

    assert response.status_code == 404


def test_image_route_blocks_gif_files(tmp_path, app_factory):
    (tmp_path / "animated.gif").write_bytes(b"gif")
    client = app_factory().test_client()

    response = client.get("/images/animated.gif")

    assert response.status_code == 404


def test_image_view_renders_full_image_page(tmp_path, app_factory):
    (tmp_path / "sample.png").write_bytes(b"image-bytes")
    client = app_factory().test_client()

    response = client.get("/images/sample.png/view")

    assert response.status_code == 302
    assert response.headers["Location"] == "/images/sample.png"


def test_image_metadata_route_serves_sidecar_json(tmp_path, app_factory):
    (tmp_path / "sample.png").write_bytes(b"image-bytes")
    metadata = {
        "content_type": "image/png",
        "created_at": "2026-05-29T12:00:00+00:00",
    }
    (tmp_path / "sample.png.json").write_text(
        json.dumps(metadata),
        encoding="utf-8",
    )
    client = app_factory().test_client()

    response = client.get("/images/sample.png/metadata")

    assert response.status_code == 200
    assert response.json == metadata


def test_image_metadata_route_404s_for_missing_sidecar(tmp_path, app_factory):
    (tmp_path / "sample.png").write_bytes(b"image-bytes")
    client = app_factory().test_client()

    response = client.get("/images/sample.png/metadata")

    assert response.status_code == 404


def test_api_generate_accepts_json_and_returns_request_id(app_factory):
    client = app_factory().test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    response = client.post(
        "/api/generate",
        json={
            "prompt": "a small red house",
            "parameters": {"size": "2K"},
        },
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 202
    assert response.json["request_id"]
    assert response.json["status_url"] == (
        f"/api/generation/{response.json['request_id']}"
    )
    assert response.json["poll_seconds"] == 1.0
    assert response.json["status"] == "queued"
    assert response.json["prompt"] == "a small red house"
    assert response.json["source_images"] == []
    assert response.json["parameters"] == {
        "aspect_ratio": "match_input_image",
        "max_images": 1,
        "sequential_image_generation": "disabled",
        "size": "2K",
    }
    assert response.json["images"] == []


def test_api_generate_starts_configured_worker(app_factory):
    class RecordingWorker:
        def __init__(self):
            self.records = []

        def start(self, request_record):
            self.records.append(request_record)

    worker = RecordingWorker()
    client = app_factory(IMAGEGEN_WORKER=worker).test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    response = client.post(
        "/api/generate",
        json={"prompt": "a small red house"},
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 202
    assert [record.request_id for record in worker.records] == [
        response.json["request_id"]
    ]


def test_api_generate_accepts_existing_source_images(tmp_path, app_factory):
    (tmp_path / "source.png").write_bytes(b"image")
    client = app_factory().test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    response = client.post(
        "/api/generate",
        json={
            "prompt": "edit this",
            "source_images": ["source.png"],
        },
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 202
    assert response.json["source_images"] == ["source.png"]


def test_api_generate_rejects_missing_source_image(app_factory):
    client = app_factory().test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    response = client.post(
        "/api/generate",
        json={
            "prompt": "edit this",
            "source_images": ["missing.png"],
        },
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 400
    assert response.json == {"error": "Source image not found: missing.png."}


def test_api_generate_rejects_gif_source_image(tmp_path, app_factory):
    (tmp_path / "source.gif").write_bytes(b"gif")
    client = app_factory().test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    response = client.post(
        "/api/generate",
        json={
            "prompt": "edit this",
            "source_images": ["source.gif"],
        },
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 400
    assert response.json == {"error": "Invalid source image filename: source.gif."}


def test_api_generate_rejects_blank_prompt(app_factory):
    client = app_factory().test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    response = client.post(
        "/api/generate",
        json={"prompt": "  "},
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 400
    assert response.json == {"error": "Prompt is required."}


def test_api_generate_rejects_non_object_parameters(app_factory):
    client = app_factory().test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    response = client.post(
        "/api/generate",
        json={"prompt": "a small red house", "parameters": ["size", "2K"]},
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 400
    assert response.json == {"error": "parameters must be an object."}


def test_api_generate_rejects_invalid_select_choice(app_factory):
    client = app_factory().test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    response = client.post(
        "/api/generate",
        json={
            "prompt": "a small red house",
            "parameters": {"size": "custom"},
        },
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 400
    assert response.json == {"error": "size must be one of: 2K, 4K."}


def test_api_generate_rejects_out_of_range_integer(app_factory):
    client = app_factory().test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    response = client.post(
        "/api/generate",
        json={
            "prompt": "a small red house",
            "parameters": {"max_images": 99},
        },
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 400
    assert response.json == {"error": "max_images must be at most 15."}


def test_api_generate_rejects_disable_safety_checker_override(app_factory):
    client = app_factory().test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    response = client.post(
        "/api/generate",
        json={
            "prompt": "a small red house",
            "parameters": {"disable_safety_checker": False},
        },
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 400
    assert response.json == {"error": "disable_safety_checker is fixed by the server."}


def test_api_generation_returns_known_request_status(app_factory):
    client = app_factory().test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)
    created = client.post(
        "/api/generate",
        json={"prompt": "a small red house"},
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    response = client.get(f"/api/generation/{created.json['request_id']}")

    assert response.status_code == 200
    assert response.json == created.json


def test_api_generation_unknown_request_id_returns_json_404(app_factory):
    client = app_factory().test_client()

    response = client.get("/api/generation/missing")

    assert response.status_code == 404
    assert response.json == {"error": "Generation request not found."}


def test_api_images_returns_gallery_json_newest_first(tmp_path, app_factory):
    older = tmp_path / "older.png"
    newer = tmp_path / "newer.jpg"
    gif = tmp_path / "animated.gif"
    ignored = tmp_path / "ignored.txt"
    older.write_bytes(b"older")
    newer.write_bytes(b"newer")
    gif.write_bytes(b"gif")
    ignored.write_text("ignored", encoding="utf-8")
    os.utime(older, (100, 100))
    os.utime(newer, (200, 200))
    os.utime(gif, (300, 300))
    client = app_factory().test_client()

    response = client.get("/api/images")

    assert response.status_code == 200
    assert response.json == {
        "images": [
            {
                "filename": "newer.jpg",
                "url": "/images/newer.jpg",
                "metadata_url": None,
                "content_type": None,
                "created_at": None,
            },
            {
                "filename": "older.png",
                "url": "/images/older.png",
                "metadata_url": None,
                "content_type": None,
                "created_at": None,
            },
        ]
    }


def test_api_images_returns_empty_gallery(app_factory):
    client = app_factory().test_client()

    response = client.get("/api/images")

    assert response.status_code == 200
    assert response.json == {"images": []}


def test_api_images_includes_sidecar_metadata(tmp_path, app_factory):
    (tmp_path / "sample.png").write_bytes(b"image-bytes")
    (tmp_path / "sample.png.json").write_text(
        json.dumps(
            {
                "content_type": "image/png",
                "created_at": "2026-05-29T12:00:00+00:00",
                "ignored": "not in gallery API",
            }
        ),
        encoding="utf-8",
    )
    client = app_factory().test_client()

    response = client.get("/api/images")

    assert response.status_code == 200
    assert response.json == {
        "images": [
            {
                "filename": "sample.png",
                "url": "/images/sample.png",
                "metadata_url": "/images/sample.png/metadata",
                "content_type": "image/png",
                "created_at": "2026-05-29T12:00:00+00:00",
            }
        ]
    }


def test_test_api_accepts_valid_csrf_json_request(app_factory):
    client = app_factory(IMAGEGEN_ENABLE_TEST_API=True).test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    response = client.post(
        "/api/_test",
        json={"ok": True},
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 200
    assert response.json == {"ok": True}


def test_test_api_rejects_missing_csrf_token(app_factory):
    client = app_factory(IMAGEGEN_ENABLE_TEST_API=True).test_client()
    client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})

    response = client.post(
        "/api/_test",
        json={"ok": True},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 403
    assert response.json == {"error": "Invalid CSRF token."}


def test_test_api_rejects_invalid_csrf_token(app_factory):
    client = app_factory(IMAGEGEN_ENABLE_TEST_API=True).test_client()
    client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})

    response = client.post(
        "/api/_test",
        json={"ok": True},
        headers={"X-CSRF-Token": "wrong"},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 403
    assert response.json == {"error": "Invalid CSRF token."}


def test_test_api_rejects_different_client_ip(app_factory):
    client = app_factory(IMAGEGEN_ENABLE_TEST_API=True).test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    response = client.post(
        "/api/_test",
        json={"ok": True},
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.11"},
    )

    assert response.status_code == 403
    assert response.json == {"error": "Client IP does not match this session."}


def test_test_api_rejects_non_json_request(app_factory):
    client = app_factory(IMAGEGEN_ENABLE_TEST_API=True).test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    response = client.post(
        "/api/_test",
        data={"ok": "true"},
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 415
    assert response.json == {"error": "API requests must use application/json."}


def test_api_response_does_not_emit_cors_headers(app_factory):
    client = app_factory(IMAGEGEN_ENABLE_TEST_API=True).test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    response = client.post(
        "/api/_test",
        json={"ok": True},
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert "Access-Control-Allow-Origin" not in response.headers
    assert "Access-Control-Allow-Credentials" not in response.headers
