# Security Review: Current Application Boundaries

Date: 2026-09-09
Baseline revision: `99009efd81c192727a1527165e4d46ed63ff460e`
Review mode: repository-wide static security review
Planning status: ready for specialization workflow decomposition

## Outcome

The current application still fits its intended localhost or trusted-household-LAN threat model, but seven low-severity weaknesses should be addressed. Five have high-confidence static evidence and two have medium-confidence evidence. No vulnerability was found in the new command-line application's authorization or validation flow.

This document is an epic input, not an implementation ticket set. It states the current boundary, validated findings, recommended ordering, and observable acceptance criteria. Ticket decomposition should preserve the security properties below and keep each change independently testable.

## Scope and Method

The review used `developer/security-boundary.md` as the baseline and traced the current production entry points, HTTP routes, frontend request construction, provider adapters, outbound downloads, image parsing, filesystem repositories, metadata, SQLite history, optional Immich integration, and developer schema helpers.

Reviewed artifacts included `SECURITY.md`, `developer/security-boundary.md`, `pyproject.toml`, `README.md`, `src/imagegen/`, `scripts/`, and representative security tests. Generated frontend bundles, dependency internals, private runtime data, binary documentation assets, Git internals, and historical epic documents were excluded. This was static analysis: no vulnerability-triggering requests, live provider calls, external-service calls, or deployment verification were performed.

## Baseline Corrections

The baseline should be updated before or alongside remediation:

- `scripts/run-dev*` no longer exist. The supported web launcher is the installed `imagegen-web` entry point implemented by `src/imagegen/web.py`.
- The installed `imagegen` CLI in `src/imagegen/cli.py` is a second production entry point.
- The CLI does not open a listener or weaken the web session/CSRF boundary. Its caller already has the invoking OS user's filesystem and environment authority.
- The CLI does share provider credentials and billable generation authority, image storage, embedded metadata, SQLite history, and stdout/stderr disclosure with the web application. It therefore belongs in the documented trust model as a trusted local-shell boundary.
- Wiro credentials and provider behavior are missing from the current boundary document.
- State-changing requests are not exclusively JSON: upload endpoints use CSRF-protected multipart requests.
- `env.example` should be checked against the current Wiro and timeout configuration so deployment guidance matches runtime behavior.

## Security Properties to Preserve

- Default web binding remains loopback-only; trusted-LAN exposure is explicit.
- Every web mutation remains protected by the same-instance session, client-address, and CSRF controls.
- Browser, provider, and Immich filenames or metadata never escape configured storage roots.
- Provider credentials are sent only to fixed, intended provider hosts.
- Provider fixed safety inputs cannot be overridden by callers.
- Prompt annotations are stripped before provider submission.
- CLI and web generation use the same model enablement, parameter validation, fixed-input, provider, storage, metadata, and history boundaries.
- Tests make no real provider calls and runtime data remains outside the repository.

## Validated Findings

### SR-01: URL imports can reach private and loopback services

Severity: Low
Confidence: High
CWE: CWE-918
Primary evidence: `src/imagegen/image_imports.py:68-92`

`validate_import_url()` checks only the HTTP(S) scheme and presence of a hostname. `fetch_import_url()` follows redirects without rejecting loopback, private, link-local, reserved, or otherwise unsafe resolved addresses. A directly connected operator-equivalent client can make the Flask host probe internal services and can recover a response when it decodes as a supported image.

Recommendation: introduce one outbound destination policy, apply it to the initial URL and every redirect, reject unsafe IPv4 and IPv6 address classes and mixed DNS answers, and prevent DNS rebinding. Reuse the same policy for provider-controlled image downloads where applicable.

Observable acceptance criteria:

- URL import rejects IPv4 and IPv6 loopback, private, link-local, multicast, unspecified, and reserved destinations.
- A public URL that redirects to an unsafe destination is rejected before the second connection.
- DNS answers containing an unsafe address are rejected, including mixed safe/unsafe answers.
- Ordinary public HTTP(S) image imports continue to work under the selected scheme policy.

### SR-02: Request size limits apply after body materialization

Severity: Low
Confidence: High
CWE: CWE-400
Primary evidence: `src/imagegen/app.py:32-38`, `src/imagegen/image_api_routes.py:81-105`, `src/imagegen/image_api_routes.py:174-233`

Flask has no application-wide request-body ceiling. Multipart uploads call an unbounded `read()` before enforcing the image byte limit, while JSON edit and mask bodies are parsed before their semantic limits are applied. A directly connected client can consume excessive memory, parser CPU, or temporary-file storage before rejection.

Recommendation: configure a hard application request ceiling, retain smaller route-specific limits, and read uploaded files at most `max_bytes + 1` before rejecting them.

Observable acceptance criteria:

- Oversized multipart and JSON requests receive HTTP 413 before image parsing or route-level mutation work begins.
- Upload reads stop after the configured maximum plus one byte.
- Existing valid uploads, masks, and edits remain accepted.
- Limits are documented in one authoritative configuration location.

### SR-03: The web launcher permits debug mode on every interface

Severity: Low
Confidence: Medium
CWE: CWE-489
Primary evidence: `src/imagegen/web.py:13-32`

The replacement launcher accepts `--dev` and `--secure-network` together, producing Flask debug mode on `0.0.0.0`. That explicitly requested combination exposes development diagnostics to every reachable LAN host and may expose debugger capabilities depending on Werkzeug and deployment behavior.

Recommendation: make debug mode loopback-only and reject the combined flags with a clear error.

Observable acceptance criteria:

- `imagegen-web --dev --secure-network` fails before the server starts.
- `--dev` always binds to loopback.
- Non-debug `--secure-network` behavior remains available and clearly warns that every reachable client is operator-equivalent.
- Launcher tests cover all flag combinations.

### SR-04: Clean downloads accumulate temporary image copies

Severity: Low
Confidence: High
CWE: CWE-400
Primary evidence: `src/imagegen/routes.py:94-104`, `src/imagegen/image_export.py`

Each clean-download GET creates a new UUID-named full-size copy. Cleanup occurs at application startup rather than after the response, so repeated requests can fill the data filesystem during a long-running process.

Recommendation: delete each temporary export through the response lifecycle, or stream the cleaned representation without persistent temporary state. Keep startup cleanup only as crash recovery.

Observable acceptance criteria:

- A completed or failed clean download leaves no per-request export behind.
- Repeated downloads do not increase retained temporary-file count or disk usage.
- Startup cleanup still removes artifacts left by an interrupted process.
- Clean exports never appear in the gallery or alter the stored gallery image.

### SR-05: Imported images lack an application pixel-count ceiling

Severity: Low
Confidence: Medium
CWE: CWE-409
Primary evidence: `src/imagegen/image_imports.py:128-139`, `src/imagegen/image_edits.py:45-85`

Imports cap compressed bytes but call Pillow `Image.load()` without an application-defined width, height, or total-pixel limit. A highly compressed image can allocate a large raster during import and again during later editing. Pillow's built-in decompression-bomb protections reduce, but do not remove, this risk.

Recommendation: centralize a decoded-image dimension policy and apply it after `Image.open()` but before `Image.load()` across import, edit, metadata, mask, and export paths.

Observable acceptance criteria:

- Images above the selected width, height, or total-pixel ceiling are rejected before full raster decoding.
- The same policy applies to every application-owned image decode path.
- Valid images near the documented limit continue to import, edit, inspect, and export.
- Rejection produces an actionable error without retaining a partial gallery image.

### SR-06: Provider identifiers can overwrite gallery images

Severity: Low
Confidence: High
CWE: CWE-73
Primary evidence: `src/imagegen/image_store.py:143-146`

Provider-controlled prediction or task identifiers are interpolated into output filenames and written with overwrite semantics. Direct directory traversal was not established, but a hostile provider can reuse a known identifier and matching extension to replace an existing gallery image and its metadata.

Recommendation: generate collision-resistant local basenames and publish exclusively or atomically. Retain provider identifiers only as metadata and history fields.

Observable acceptance criteria:

- Repeated or adversarial provider identifiers never select an existing gallery pathname.
- A collision cannot overwrite an existing gallery file.
- Provider identifiers remain available in embedded metadata and generation history.
- Partial downloads are not published as completed gallery images.

### SR-07: Provider output collections are unbounded

Severity: Low
Confidence: High
CWE: CWE-770
Primary evidence: `src/imagegen/image_store.py:74-95`, `src/imagegen/replicate_client.py:153-163`, `src/imagegen/wiro_client.py:405-417`

Provider response normalizers accept arbitrarily many output URLs, and the shared persistence layer downloads every URL with only per-image limits. A hostile or malfunctioning provider can monopolize the single worker and consume unbounded cumulative network and disk resources.

Recommendation: carry the validated requested output count into persistence, impose a small hard maximum and cumulative byte/work budget, and remove partial results when the budget is exceeded.

Observable acceptance criteria:

- More output URLs than requested or permitted are rejected before extra downloads begin.
- Cumulative bytes and work are bounded for one generation, in addition to existing per-image limits.
- Budget failure cleans up partial files and records an actionable provider error without credential leakage.
- Replicate, fal.ai, and Wiro use the same persistence invariant.

## Hardening Recommendations Without a Validated Finding

- Bound Immich JSON and image response bodies. The current buffering is unbounded, but this review did not establish a practical attacker below the trust level of the configured Immich service.
- Bound provider log and error strings before persisting or returning them while preserving actionable details. Upstream limits and realistic attacker control were not established, so this remains defense in depth.
- Keep deployment prerequisites explicit: firewall/LAN trust, reverse-proxy TLS and client-address preservation, OS permissions on dotenv and data directories, provider/Immich account scope, and terminal or CI log retention.

## No-Issue Conclusions

- The CLI introduces no remote listener and no separate web authentication bypass. It reuses server-side generation validation and should remain a trusted local-shell interface.
- No executable DOM XSS sink was found in editable frontend modules.
- State-changing web routes consistently use the JSON or multipart CSRF guards. These guards prevent blind cross-origin mutation; they are not user authentication.
- No browser-only filesystem root escape, SQL injection, caller-selected provider credential destination, fixed-safety-input override, schema-script command injection, or committed credential was found.

## Recommended Epic Order

1. Update `developer/security-boundary.md` and deployment examples so all later tickets use the current launcher, CLI, Wiro, and multipart model.
2. Establish shared resource and destination invariants: outbound address policy, transport request ceiling, decoded-image ceiling, output-count/cumulative budget, and collision-safe local naming.
3. Apply those invariants at the narrow shared boundaries and add focused regression tests.
4. Fix clean-export lifecycle and enforce the launcher flag interlock.
5. Add the two defense-in-depth bounds only after the validated findings, unless deployment evidence raises their priority.

The specialization workflow should split implementation by independently observable behavior, keep documentation changes close to the affected boundary, and avoid a broad security-framework abstraction. Shared helpers are justified only where multiple concrete entry points need the same invariant.

## Definition of Done

- All seven findings have a passing regression test and their acceptance criteria are satisfied.
- `developer/security-boundary.md`, `SECURITY.md` where necessary, `README.md`, and `env.example` agree with the implemented launch and trust model.
- Full Python checks pass: `uv run pytest` and `uv run ruff check src tests`.
- JavaScript checks run only if browser JavaScript changes: `npm run js:check`.
- No test performs a live provider, Immich, or arbitrary network call.
- A follow-up security review confirms the remediations without expanding the supported deployment to an untrusted public network.

## Review Record

Canonical Codex Security scan ID: `29d68bb1-ad44-4827-9e42-e8407064068d`
Canonical report: `/private/var/folders/dn/vtkw12w17qv7cqw5yj6lmgjh0000gn/T/codex-security-scans-TqCuWH/img-replicate-security-review/99009efd81c192727a1527165e4d46ed63ff460e_20260909T124055Z_nmpe3wdn/report.md`
