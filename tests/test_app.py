from imagegen.app import create_app
from imagegen.config import AppConfig
from imagegen.model_registry import MODEL_REGISTRY


def make_app(tmp_path, **config):
    app_config = AppConfig(
        replicate_api_token="",
        output_dir=tmp_path,
        model_alias="seedream45",
        model=MODEL_REGISTRY["seedream45"],
        flask_secret_key="test-secret",
        replicate_poll_seconds=1.0,
        replicate_timeout_seconds=60.0,
    )
    return create_app(
        {
            "IMAGEGEN_APP_CONFIG": app_config,
            "IMAGEGEN_OUTPUT_DIR": tmp_path,
            "TESTING": True,
            **config,
        }
    )


def test_create_app_returns_flask_app(tmp_path):
    app = make_app(tmp_path)

    assert app.name == "imagegen.app"


def test_index_renders_prompt_form(tmp_path):
    client = make_app(tmp_path).test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert b'<form class="prompt-form"' in response.data
    assert b'name="prompt"' in response.data
    assert b'name="size"' in response.data
    assert b'name="aspect_ratio"' in response.data
    assert b'name="max_images"' in response.data
    assert b"disable_safety_checker" not in response.data
    assert b"Generate" in response.data


def test_index_lists_existing_images(tmp_path):
    (tmp_path / "first.png").write_bytes(b"not really an image")
    (tmp_path / "ignore.txt").write_text("ignore", encoding="utf-8")
    client = make_app(tmp_path).test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert b"first.png" in response.data
    assert b'href="/images/first.png"' in response.data
    assert b"ignore.txt" not in response.data


def test_generate_rejects_empty_prompt(tmp_path):
    client = make_app(tmp_path).test_client()

    response = client.post("/generate", data={"prompt": "   "}, follow_redirects=True)

    assert response.status_code == 200
    assert b"Prompt is required." in response.data


def test_generate_calls_injected_generator_and_redirects(tmp_path):
    calls = []

    def fake_generate(prompt, app_config):
        calls.append((prompt, app_config.model_alias))
        return type("Result", (), {"stored_images": [tmp_path / "out.png"]})()

    client = make_app(tmp_path, IMAGEGEN_GENERATE=fake_generate).test_client()

    response = client.post("/generate", data={"prompt": "a small red house"})

    assert response.status_code == 302
    assert response.headers["Location"] == "/"
    assert calls == [("a small red house", "seedream45")]


def test_generate_flashes_generator_errors(tmp_path):
    def fake_generate(prompt, app_config):
        raise RuntimeError("replicate failed")

    client = make_app(tmp_path, IMAGEGEN_GENERATE=fake_generate).test_client()

    response = client.post(
        "/generate",
        data={"prompt": "a small red house"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"replicate failed" in response.data


def test_image_route_serves_stored_file(tmp_path):
    (tmp_path / "sample.png").write_bytes(b"image-bytes")
    client = make_app(tmp_path).test_client()

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


def test_image_route_blocks_unsafe_paths(tmp_path):
    client = make_app(tmp_path).test_client()

    response = client.get("/images/../pyproject.toml")

    assert response.status_code == 404


def test_image_view_renders_full_image_page(tmp_path):
    (tmp_path / "sample.png").write_bytes(b"image-bytes")
    client = make_app(tmp_path).test_client()

    response = client.get("/images/sample.png/view")

    assert response.status_code == 302
    assert response.headers["Location"] == "/images/sample.png"
