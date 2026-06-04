# Security Remediation Plan

Source: `AUDIT.md`, generated 2026-06-04.

## Ticket 1: Require a Strong Flask Secret for LAN/Shared Use

Priority: P1

Finding: `AUDIT-001`

Problem: `IMAGEGEN_FLASK_SECRET_KEY` defaults to the committed value
`dev-secret-change-me`. Because Flask sessions are signed with this key, the
default weakens the CSRF/session write guard.

Scope:

- Generate a random secret when `.env` is created or updated and the setting is
  empty/default or contains the legacy secret `dev-secret-change-me`.
- Warn if `--secure-network` is used and the configured secret is still the
  insecure default or empty.
- Keep tests able to inject deterministic secrets through app config.
- Update `README.md`, `SECURITY.md`, and `env.example` if the user-facing setup
  flow changes.

Acceptance Criteria:

- A new `.env` gets a non-default random `IMAGEGEN_FLASK_SECRET_KEY`.
- Existing non-default secrets are preserved.
- LAN startup with `scripts/run-dev.sh --secure-network` and
  `scripts\run-dev.cmd --secure-network` warns with a clear message when the
  secret is the default.
- Local `127.0.0.1` startup remains possible without extra manual steps.
- No generated secret is committed to the repository.

Tests:

- Config test for generated random secret on new `.env`.
- Config test that an existing explicit secret is preserved.
- Script-level or focused subprocess test for `--secure-network` refusing the
  default secret, if practical.
- Run `uv run pytest`.
- Run `uv run ruff check src tests`.

## Ticket 3: Restrict Remote Image Download Targets

Priority: P1

Finding: `AUDIT-005`

Problem: Provider output URLs are fetched with redirects enabled, but download
targets are not checked against private, loopback, link-local, multicast, or
metadata-service networks.

Scope:

- Add URL validation before provider image downloads.
- Require `https`.
- Resolve redirects to the ultimate target, then resolve hostnames.
- For the resolved hostnames, reject unsafe IP ranges:
  loopback, private, link-local, multicast, unspecified, and reserved where
  appropriate.
- Keep existing timeout, content-type, GIF rejection, and max-size controls.
- Ensure error messages do not leak credentials.

Acceptance Criteria:

- Safe public HTTPS image URLs can still be downloaded.
- URLs pointing at `127.0.0.1`, `localhost`, RFC1918 LAN IPs, link-local
  addresses, and cloud metadata IPs are rejected before content is fetched.
- Redirects to unsafe targets are rejected.
- Unsupported schemes such as `file:`, `ftp:`, and `data:` are rejected.
- Downloaded content must still pass content-type and size checks.

Tests:

- Unit tests for URL classification and rejected unsafe hosts.
- Fake HTTP client tests for redirect validation.
- Existing image store tests still pass.
- Run `uv run pytest`.
- Run `uv run ruff check src tests`.

## Ticket 4: Set Explicit Session Cookie Defaults

Priority: P2

Finding: `AUDIT-003`

Problem: Session cookie security attributes are not explicit in application
configuration.

Scope:

- Set `SESSION_COOKIE_HTTPONLY=True`.
- Set `SESSION_COOKIE_SAMESITE="Lax"`.
- Keep `SESSION_COOKIE_SECURE=False` so the app remains usable without TLS.

Acceptance Criteria:

- Session cookies are HttpOnly and SameSite=Lax by default.
- Plain HTTP local use continues to work.

Tests:

- Route/client test asserting default `Set-Cookie` includes HttpOnly and
  SameSite=Lax.
- Run `uv run pytest`.
- Run `uv run ruff check src tests`.

## Ticket 5: Add Browser Security Headers

Priority: P2

Finding: `AUDIT-004`

Problem: The app does not set a Content Security Policy or common browser
hardening headers.

Scope:

- Extend the existing response hardening hook or add a new one.
- Set `X-Content-Type-Options: nosniff`.
- Set `Referrer-Policy: no-referrer`.
- Set a frame policy, preferably through CSP `frame-ancestors 'none'`.
- Add a CSP compatible with the current app:
  `default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data: blob:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'`.
- Verify the CSP does not block local gallery images, static CSS, static JS, or
  JSON script tags.

Acceptance Criteria:

- Workspace and API responses include the hardening headers.
- The current UI still loads static CSS, static JS, gallery images, and JSON
  registry data.
- No inline JavaScript is introduced to satisfy the policy.
- CORS remains non-permissive.

Tests:

- Route test for security headers on `GET /`.
- Route test that CORS headers are still absent.
- Optional browser/manual check that the workspace loads under the CSP.
- Run `uv run pytest`.
- Run `uv run ruff check src tests`.

## Suggested Order

1. Ticket 1: Require a strong Flask secret for LAN/shared use.
3. Ticket 3: Restrict remote image download targets.
4. Ticket 4: Set explicit session cookie defaults.
5. Ticket 5: Add browser security headers.

## Completion Checklist

For each ticket:

- Add or update behavior tests before implementation where practical.
- Keep changes scoped to the finding being fixed.
- Update `README.md` and `SECURITY.md` when user-facing configuration changes.
- Run `uv run pytest`.
- Run `uv run ruff check src tests`.
