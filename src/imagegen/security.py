"""CSRF and same-client request guards for JSON API routes.

This module owns session-backed API request protection. It creates a token for
the rendered page, binds that token to the client IP observed on `GET /`, and
validates JSON mutating API requests before route handlers run.
"""

from __future__ import annotations

import secrets
from collections.abc import Callable
from functools import wraps
from typing import Any

from flask import Response, jsonify, request, session


CSRF_TOKEN_BYTES = 32
CSRF_SESSION_KEY = "csrf_token"
CSRF_CLIENT_IP_SESSION_KEY = "csrf_client_ip"
CSRF_HEADER = "X-CSRF-Token"
CONTENT_SECURITY_POLICY = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self'; "
    "img-src 'self' data: blob:; "
    "object-src 'none'; "
    "base-uri 'none'; "
    "frame-ancestors 'none'"
)


def ensure_csrf_token() -> str:
    token = session.get(CSRF_SESSION_KEY)
    if not isinstance(token, str) or not token:
        token = secrets.token_urlsafe(CSRF_TOKEN_BYTES)
        session[CSRF_SESSION_KEY] = token
        session[CSRF_CLIENT_IP_SESSION_KEY] = request.remote_addr
    elif session.get(CSRF_CLIENT_IP_SESSION_KEY) is None:
        session[CSRF_CLIENT_IP_SESSION_KEY] = request.remote_addr
    return token


def validate_api_request() -> tuple[dict[str, str], int] | None:
    if not request.is_json:
        return {"error": "API requests must use application/json."}, 415

    session_token = session.get(CSRF_SESSION_KEY)
    request_token = request.headers.get(CSRF_HEADER)
    if not session_token or request_token != session_token:
        return {"error": "Invalid CSRF token."}, 403

    session_ip = session.get(CSRF_CLIENT_IP_SESSION_KEY)
    if not session_ip or request.remote_addr != session_ip:
        return {"error": "Client IP does not match this session."}, 403

    return None


def require_api_csrf(handler: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(handler)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        error = validate_api_request()
        if error is not None:
            body, status = error
            return jsonify(body), status
        return handler(*args, **kwargs)

    return wrapper


def no_cors_response(response: Response) -> Response:
    response.headers.pop("Access-Control-Allow-Origin", None)
    response.headers.pop("Access-Control-Allow-Credentials", None)
    response.headers.setdefault("Content-Security-Policy", CONTENT_SECURITY_POLICY)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    return response
