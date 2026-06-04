"""Route-level API security tests.

Behaviors protected:
- Mutating JSON API routes accept valid CSRF requests and reject missing or invalid tokens.
- API CSRF protection binds requests to the same client IP.
- API responses do not emit permissive CORS headers.
"""

from route_helpers import extract_csrf_token


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
