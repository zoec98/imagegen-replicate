"""Palette API route tests.

Behaviors protected:
- Palette read endpoints expose validated fragment data without CSRF.
- Palette write endpoints require CSRF and preserve CRUD validation behavior.
- Invalid palette and fragment names do not reach unsafe filesystem paths.
"""

from route_helpers import extract_csrf_token

def test_api_palettes_lists_palette_data(app_config, app_factory):
    style = app_config.fragment_root / "style"
    style.mkdir(parents=True)
    (style / "photo.txt").write_text("photo", encoding="utf-8")
    client = app_factory().test_client()

    response = client.get("/api/palettes")

    assert response.status_code == 200
    assert response.json == {
        "palettes": [
            {
                "name": "style",
                "display_name": "style",
                "fragments": [
                    {
                        "name": "photo",
                        "display_name": "photo",
                        "content": "photo",
                    }
                ],
            }
        ]
    }

def test_api_palette_fragment_reads_without_csrf(app_config, app_factory):
    style = app_config.fragment_root / "style"
    style.mkdir(parents=True)
    (style / "photo.txt").write_text("photo", encoding="utf-8")
    client = app_factory().test_client()

    response = client.get("/api/palettes/style/fragments/photo")

    assert response.status_code == 200
    assert response.json == {
        "fragment": {
            "name": "photo",
            "display_name": "photo",
            "content": "photo",
        }
    }

def test_api_palette_fragment_rejects_invalid_read_name(app_factory):
    client = app_factory().test_client()

    response = client.get("/api/palettes/1bad/fragments/photo")

    assert response.status_code == 400
    assert "Invalid palette name" in response.json["error"]

def test_api_palette_fragment_crud(app_config, app_factory):
    style = app_config.fragment_root / "style"
    style.mkdir(parents=True)
    client = app_factory().test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    create = client.post(
        "/api/palettes/style/fragments",
        json={"name": "comic lawrence", "content": "ink style"},
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )
    assert create.status_code == 201
    assert create.json["fragment"]["name"] == "comic_lawrence"

    update = client.put(
        "/api/palettes/style/fragments/comic_lawrence",
        json={"content": "new ink style"},
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )
    assert update.status_code == 200
    assert update.json["fragment"]["content"] == "new ink style"
    assert (style / "comic_lawrence.txt").read_text(encoding="utf-8") == "new ink style"

    delete = client.delete(
        "/api/palettes/style/fragments/comic_lawrence",
        json={},
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )
    assert delete.status_code == 200
    assert delete.json == {"deleted": "comic_lawrence"}
    assert not (style / "comic_lawrence.txt").exists()

def test_api_create_palette_fragment_requires_csrf(app_config, app_factory):
    (app_config.fragment_root / "style").mkdir(parents=True)
    client = app_factory().test_client()

    response = client.post(
        "/api/palettes/style/fragments",
        json={"name": "photo", "content": "photo"},
    )

    assert response.status_code == 403

def test_api_create_palette_fragment_rejects_missing_palette(app_factory):
    client = app_factory().test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    response = client.post(
        "/api/palettes/style/fragments",
        json={"name": "photo", "content": "photo"},
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 404
    assert response.json == {"error": "Palette not found: style."}

def test_api_create_palette_fragment_rejects_conflict(app_config, app_factory):
    style = app_config.fragment_root / "style"
    style.mkdir(parents=True)
    (style / "photo.txt").write_text("photo", encoding="utf-8")
    client = app_factory().test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    response = client.post(
        "/api/palettes/style/fragments",
        json={"name": "photo", "content": "new"},
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 409
    assert "already exists" in response.json["error"]

def test_api_update_palette_fragment_rejects_invalid_content(
    app_config,
    app_factory,
):
    style = app_config.fragment_root / "style"
    style.mkdir(parents=True)
    (style / "photo.txt").write_text("photo", encoding="utf-8")
    client = app_factory().test_client()
    index = client.get("/", environ_base={"REMOTE_ADDR": "192.0.2.10"})
    token = extract_csrf_token(index)

    response = client.put(
        "/api/palettes/style/fragments/photo",
        json={"content": "bad: content"},
        headers={"X-CSRF-Token": token},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )

    assert response.status_code == 400
    assert "may not contain" in response.json["error"]

