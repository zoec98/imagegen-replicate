# Security Audit

Date: 2026-06-04

Scope: Flask/Python backend, vanilla browser JavaScript frontend, launch scripts,
and tests, audited against `SECURITY.md`.

## Executive Summary

No critical or high-severity vulnerabilities were found in the audited codebase.
The main security goals in `SECURITY.md` are mostly implemented:

- Mutating API routes use the shared CSRF and same-client-IP guard.
- Image and palette filesystem access is centralized behind validators.
- Browser rendering generally uses Jinja autoescaping, `tojson`, `textContent`,
  and DOM node construction rather than HTML injection.
- Metadata-loaded source image references are filtered before the browser sees
  them from the metadata route.
- Clean downloads are created under the configured temporary directory and do
  not mutate the stored gallery image.

The remaining issues are secure-default hardening gaps. The most important are
the predictable default Flask secret, missing host validation, no explicit
security headers/CSP, and outbound image download SSRF hardening.

## Findings

### AUDIT-001: Default Flask Secret Allows Forged Session Cookies

- Rule ID: FLASK-CONFIG-001
- Severity: Medium
- Location: `src/imagegen/config.py` `ENV_SETTINGS` lines 74-78,
  `load_config` lines 206-209; `src/imagegen/app.py` `create_app` line 30
- Evidence:

```python
EnvSetting(
    name="IMAGEGEN_FLASK_SECRET_KEY",
    default="dev-secret-change-me",
    comment="Flask secret key for local development. Replace for shared deployments.",
)
```

```python
flask_secret_key=os.getenv(
    "IMAGEGEN_FLASK_SECRET_KEY",
    "dev-secret-change-me",
),
```

```python
app.secret_key = app_config.flask_secret_key
```

- Impact: Flask's default session cookie is signed, not encrypted. With the
  committed default secret, an attacker who can reach the app can forge session
  contents, including `csrf_token` and `csrf_client_ip`, and satisfy the custom
  CSRF guard with a matching header. Because the app intentionally has no user
  identity, this does not bypass authentication, but it weakens the
  "currently running app instance" write guard described in `SECURITY.md`.
- Fix: Generate a random secret when creating `.env`, or fail closed when
  `IMAGEGEN_FLASK_SECRET_KEY` is empty or still equals `dev-secret-change-me`
  outside test/local explicit development. For `--secure-network`, the script or
  config loader should refuse the default secret.
- Mitigation: Document that `.env` must contain a random secret before LAN use.
  A suitable local-only fallback could be a generated secret stored in ignored
  runtime data rather than a committed literal.
- False positive notes: This is less severe than it would be in a multi-user app
  because any LAN client that can browse the app can already become the operator.
  It still violates secure-default expectations for signed session integrity.

### AUDIT-002: No Host Header Allowlist / DNS Rebinding Defense

- Rule ID: FLASK-CONFIG-002 / secure local app boundary
- Severity: Medium
- Location: `src/imagegen/app.py` `create_app` lines 29-36; `scripts/run-dev.sh`
  lines 6-27; `scripts/run-dev.cmd` lines 6-27
- Evidence:

```python
app = Flask(__name__)
app.secret_key = app_config.flask_secret_key
app.config.update(
    IMAGEGEN_APP_CONFIG=app_config,
    IMAGEGEN_METADATA_PROVIDER=EmbeddedImageMetadataProvider(),
)
```

```bash
host="127.0.0.1"
...
exec uv run flask --app imagegen.app run "${debug_args[@]}" --host "$host" --port 5002
```

No app configuration sets Flask `TRUSTED_HOSTS`, and there is no custom Host
header check.

- Impact: A DNS rebinding attack can make a victim browser treat the local app
  as same-origin with an attacker-controlled hostname after DNS changes. If the
  app accepts arbitrary Host headers, the attacker may be able to read `GET /`,
  obtain the CSRF token, and perform writes from the victim browser. This is
  especially relevant for the `127.0.0.1` local mode and the LAN mode exposed by
  `--secure-network`.
- Fix: Configure allowed hosts explicitly. For default local mode, allow
  `127.0.0.1:5002` and `localhost:5002`. For `--secure-network`, require an
  explicit `IMAGEGEN_TRUSTED_HOSTS` list or derive a narrow LAN host/IP list.
  Flask 3.1 supports `TRUSTED_HOSTS`.
- Mitigation: Keep using `127.0.0.1` by default, stop the app after use, and use
  firewall restrictions on LAN. These do not replace Host validation.
- False positive notes: If a TLS reverse proxy already enforces Host allowlists,
  this may be mitigated at the edge. That control is not visible in repository
  code and should be verified in runtime proxy configuration.

### AUDIT-003: Session Cookie Security Attributes Are Not Explicit

- Rule ID: FLASK-SESS-001
- Severity: Low
- Location: `src/imagegen/app.py` `create_app` lines 29-36
- Evidence:

```python
app = Flask(__name__)
app.secret_key = app_config.flask_secret_key
app.config.update(
    IMAGEGEN_APP_CONFIG=app_config,
    IMAGEGEN_METADATA_PROVIDER=EmbeddedImageMetadataProvider(),
)
```

The app does not explicitly configure `SESSION_COOKIE_HTTPONLY`,
`SESSION_COOKIE_SAMESITE`, or conditional `SESSION_COOKIE_SECURE`.

- Impact: The CSRF token and client-IP binding are stored in Flask's session.
  Flask defaults are not documented in this project, and future framework
  changes or config overrides could weaken cookie behavior. SameSite is a useful
  defense-in-depth layer for the custom CSRF design; Secure is appropriate when
  a TLS proxy is in front.
- Fix: Set explicit cookie defaults in `create_app` or config loading:
  `SESSION_COOKIE_HTTPONLY=True`, `SESSION_COOKIE_SAMESITE="Lax"`, and
  `SESSION_COOKIE_SECURE=True` only when a TLS/proxy configuration flag says the
  browser accesses the app over HTTPS.
- Mitigation: Keep the existing JSON-only custom-header CSRF requirement. Avoid
  setting `Secure` unconditionally because plain HTTP local use would stop
  session cookies from working.
- False positive notes: Flask currently defaults session cookies to HttpOnly,
  but making this explicit keeps the app's security posture self-documenting.

### AUDIT-004: No Content Security Policy or Browser Security Headers

- Rule ID: JS-XSS-001 defense-in-depth / frontend CSP baseline
- Severity: Low
- Location: `src/imagegen/app.py` line 52; `src/imagegen/security.py` lines
  63-66; `src/imagegen/templates/index.html` lines 6-12
- Evidence:

```python
app.after_request(no_cors_response)
```

```python
def no_cors_response(response: Response) -> Response:
    response.headers.pop("Access-Control-Allow-Origin", None)
    response.headers.pop("Access-Control-Allow-Credentials", None)
    return response
```

```html
<meta name="csrf-token" content="{{ csrf_token }}">
<meta name="app-build" content="{{ app_checksum }}">
<link rel="stylesheet" href="{{ url_for('static', filename='app.css', v=app_checksum) }}">
<script id="model-registry-data" type="application/json">{{ model_registry | tojson }}</script>
<script id="palette-data" type="application/json">{{ palettes | tojson }}</script>
<script defer src="{{ url_for('static', filename='app.js', v=app_checksum) }}"></script>
```

No CSP, `X-Content-Type-Options`, `Referrer-Policy`, or frame policy is set by
the app.

- Impact: The current frontend avoids obvious DOM XSS sinks, but prompts,
  palette fragments, provider errors, filenames, and embedded metadata are all
  untrusted. If a future change introduces an HTML injection sink, the absence
  of CSP increases the blast radius. Lack of `X-Content-Type-Options: nosniff`
  also leaves more room for browser content sniffing edge cases.
- Fix: Add a response hardening hook that sets at least:
  `Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data: blob:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'`,
  `X-Content-Type-Options: nosniff`, and `Referrer-Policy: no-referrer`.
  Adjust `img-src` only if the UI intentionally loads non-local images.
- Mitigation: Continue using `textContent`, DOM node construction, and Jinja
  autoescaping. Add regression tests that XSS payload strings remain escaped.
- False positive notes: A reverse proxy could set these headers. That is not
  visible in repository code.

### AUDIT-005: Remote Image Download Does Not Restrict Destination Networks

- Rule ID: SSRF / untrusted outbound URL handling
- Severity: Medium
- Location: `src/imagegen/image_store.py` `persist_generated_images` lines 63-68,
  `download_image` lines 106-123; `src/imagegen/falai_client.py`
  `_looks_like_url` lines 189-190
- Evidence:

```python
http_client = client or httpx.Client(timeout=30.0, follow_redirects=True)
```

```python
response = client.get(url)
response.raise_for_status()
...
if not content_type.startswith("image/"):
    msg = f"Expected image content from {url}, got {content_type or 'unknown'}."
    raise ImageDownloadError(msg)
```

```python
def _looks_like_url(value: str) -> bool:
    return value.startswith(("http://", "https://"))
```

- Impact: `SECURITY.md` correctly treats provider outputs as untrusted remote
  URLs. The downloader enforces timeout, content type, and size, but it does not
  block loopback, RFC1918, link-local, or metadata-service addresses, and it
  follows redirects. A compromised provider response, provider-side bug, or
  unexpected model output shape could cause the local app to make requests to
  internal LAN services. The image content-type check limits data capture but
  does not prevent the outbound request itself.
- Fix: Validate final download targets before fetching and after redirects.
  Permit only `https` unless there is a documented provider need for `http`.
  Resolve hostnames and reject loopback, private, link-local, multicast, and
  unspecified addresses. Consider disabling automatic redirects and validating
  each `Location` target before following it.
- Mitigation: Keep provider API keys scoped, run the app on a trusted LAN, and
  rely on existing content-type/size limits until network-target validation is
  added.
- False positive notes: Replicate/fal.ai normally return provider/CDN URLs, so
  this is a defense against malicious or compromised upstream data rather than a
  normal user-controlled URL path.

## Positive Findings

### CSRF and Same-Client Guard

All state-changing app routes found in `src/imagegen/api_routes.py` are decorated
with `@require_api_csrf`: generation creation, palette create/update/delete,
Immich upload, gallery delete, and the test API. The guard requires JSON, a
matching `X-CSRF-Token`, and the same `request.remote_addr` recorded when the
workspace token was created (`src/imagegen/security.py` lines 35-48).

Tests cover valid CSRF, missing token, invalid token, wrong client IP,
non-JSON requests, and absence of permissive CORS headers
(`tests/test_security_routes.py` lines 12-102).

### Path Traversal Controls

Image route filenames go through `safe_image_filename`, which requires
Werkzeug's sanitized name to exactly match the submitted name and allows only
`.jpeg`, `.jpg`, `.png`, and `.webp` (`src/imagegen/routes.py` lines 161-165).
The same helper is reused for metadata source-image filtering and mutating image
API routes.

Palette filesystem access goes through `PaletteRepository`, which validates
names with `^[A-Za-z][A-Za-z0-9_-]*$` and resolves paths under the configured
fragment root (`src/imagegen/palettes.py` lines 10-13, 61-64, 142-156).

Tests cover image path traversal and delete path traversal
(`tests/test_image_routes.py` lines 51-56 and 400-417).

### XSS Controls

The initial page uses Jinja autoescaping and `tojson` for JSON script data
(`src/imagegen/templates/index.html` lines 10-11). The frontend scan found no
uses of `innerHTML`, `outerHTML`, `insertAdjacentHTML`, `document.write`,
`eval`, or string event-handler attributes. Untrusted strings are generally
inserted with `textContent` or as ordinary attributes through DOM APIs, for
example status messages (`src/imagegen/static/app.js` lines 105-116), metadata
tooltips (`src/imagegen/static/app.js` lines 1017-1029), and gallery item
construction (`src/imagegen/static/app.js` lines 1054-1167).

### Metadata Handling

Embedded metadata is read through `EmbeddedImageMetadataProvider`
(`src/imagegen/metadata.py` lines 57-67). The metadata route filters
`source_images` values through `safe_image_filename` and only returns existing
gallery files, adding warnings for unsafe or missing entries
(`src/imagegen/routes.py` lines 168-202). Later generation submission still
passes server-side validation before a job is created
(`src/imagegen/validation.py` lines 40-80).

### Clean Download Behavior

Clean downloads validate the requested gallery filename, create the stripped
copy under `app_config.tmp_dir`, and serve that temporary file as an attachment
(`src/imagegen/routes.py` lines 130-147; `src/imagegen/image_export.py` lines
19-37). Tests verify that clean exports strip metadata without mutating the
stored gallery file.

### Launch Script Defaults

The start scripts now default to `127.0.0.1`, set `FLASK_DEBUG=0`, and require
explicit flags for LAN binding and debug mode (`scripts/run-dev.sh` lines 6-27;
`scripts/run-dev.cmd` lines 6-27). This matches the local-first deployment
assumption in `SECURITY.md`.

## Recommended Remediation Order

1. Fix `AUDIT-001`: make the Flask secret random/required for LAN use.
2. Fix `AUDIT-002`: add Host header allowlisting.
3. Fix `AUDIT-005`: add outbound URL network-target validation before
   downloading provider images.
4. Fix `AUDIT-003` and `AUDIT-004`: set explicit session cookie attributes and
   browser security headers.
5. Add regression tests for the new defaults and header behavior.

## Verification Performed

This was a static audit using repository source inspection and targeted `rg`
queries. I did not run the test suite as part of writing this report because no
runtime behavior was changed.
