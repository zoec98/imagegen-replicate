"""CSRF session behavior tests.

Behaviors protected:
- CSRF tokens are created and reused in the user's session.
- CSRF sessions are bound to the client IP that loaded the page.
"""

from imagegen.security import (
    CSRF_CLIENT_IP_SESSION_KEY,
    CSRF_SESSION_KEY,
    ensure_csrf_token,
)


def test_ensure_csrf_token_creates_token_and_client_ip(app_factory):
    app = app_factory()
    with app.test_request_context("/", environ_base={"REMOTE_ADDR": "192.0.2.10"}):
        token = ensure_csrf_token()

        from flask import session

        assert token
        assert session[CSRF_SESSION_KEY] == token
        assert session[CSRF_CLIENT_IP_SESSION_KEY] == "192.0.2.10"


def test_ensure_csrf_token_reuses_existing_token(app_factory):
    app = app_factory()
    with app.test_request_context("/", environ_base={"REMOTE_ADDR": "192.0.2.10"}):
        from flask import session

        session[CSRF_SESSION_KEY] = "existing"
        session[CSRF_CLIENT_IP_SESSION_KEY] = "192.0.2.10"

        assert ensure_csrf_token() == "existing"
