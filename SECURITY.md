# Security Report

This document describes the security model for `imagegen`, the threats it is
intended to address, and the controls expected to remain in place as the app is
developed.

## Deployment Assumptions

`imagegen` is a local Flask application. The expected deployment is one of:

- Bound to `127.0.0.1:5002` and used from the same machine.
- Bound to `0.0.0.0:5002` for use from trusted devices on a household LAN, such
  as an iPad.
- Optionally placed behind a TLS reverse proxy for browser transport security.

The app has no user principal, login flow, roles, tenants, or per-user data
isolation. Anyone who can reach the running web service should be treated as the
same operator. The intended operational pattern is to start the app on demand,
use it, and stop it afterward.

This app is not designed to be exposed directly to the public internet.

## Assets

The primary assets are:

- Provider API credentials, including `REPLICATE_API_TOKEN`, `FAL_KEY`, and
  optional Immich credentials.
- Generated and uploaded local image files under `IMAGEGEN_DATA_DIR`.
- Embedded image metadata, including prompts, model settings, source image
  references, author, and copyright information.
- Prompt palette fragments under `IMAGEGEN_DATA_DIR/fragments`.
- Durable generation history in SQLite under `IMAGEGEN_DATA_DIR`.
- The currently running browser session, including its CSRF token.

## Trust Boundaries

The main trust boundaries are:

- Browser to Flask HTTP requests.
- Flask route code to local filesystem paths.
- Flask route code to embedded image metadata loaded from PNG, JPEG, or WebP
  files.
- Flask worker/provider wrappers to external generation providers.
- Optional Flask route code to Immich.
- Optional reverse proxy to Flask.

Data crossing any of these boundaries should be treated as untrusted unless it
was just produced by the current server-side code path.

## Security Goals

The app aims to provide these protections:

- Mutating requests should only be accepted from the browser session that loaded
  the currently running app instance.
- Cross-site request forgery should not be able to create generations, edit
  palettes, delete images, or upload images to Immich.
- Filesystem paths and filenames received from the browser or from embedded
  metadata must not escape configured app directories.
- Browser-rendered content from prompts, filenames, palette fragments, provider
  errors, and metadata must not execute script.
- Metadata loaded from image files must be treated as untrusted input,
  especially source image filenames and provider/model parameters.
- Clean downloads must not mutate the stored gallery image and must not be
  written into the gallery output directory.

## Current Controls

### Request Origin and CSRF

Mutating JSON API routes are protected by `require_api_csrf` in
`src/imagegen/security.py`.

The rendered workspace obtains a random session CSRF token from `GET /`. A
mutating API request must:

- Use `Content-Type: application/json`.
- Include the `X-CSRF-Token` header matching the Flask session.
- Come from the same `request.remote_addr` recorded when the token was created.

The app also removes permissive CORS headers from responses.

This is a local-app guard, not authentication. It prevents ordinary cross-site
form posts and blind cross-origin writes from a different website. It does not
protect against a malicious user or compromised device that can directly browse
the app, read the page, and use the issued token.

Reverse proxies must preserve a stable client address as seen by Flask. If all
proxied requests appear to come from the proxy address, the same-client-IP check
binds the token to the proxy rather than to the end device.

### No User Isolation

There is intentionally no account model. All clients with network access to the
running app share the same authority over:

- Generating images.
- Reading gallery files and metadata.
- Loading metadata into the workspace.
- Creating, updating, and deleting prompt fragments inside existing palettes.
- Moving gallery images to trash.
- Uploading gallery images to Immich when configured.

For LAN use, network reachability is the access control boundary. Do not bind to
`0.0.0.0` on untrusted networks.

### Filesystem Path Handling

Image routes accept only safe basename-style image filenames. `safe_image_filename`
uses Werkzeug `secure_filename`, requires the sanitized name to match the
submitted name exactly, and allows only `.jpeg`, `.jpg`, `.png`, and `.webp`.

Palette access goes through `PaletteRepository`, which validates palette and
fragment names against a restricted name pattern and resolves paths under the
configured fragment root.

Gallery deletion moves files from the configured output directory to the
configured trash directory. It does not unlink directly from route code and does
not overwrite existing trash files.

These controls should remain mandatory for every route that accepts a filename,
palette name, or fragment name. New code should not join browser-provided or
metadata-provided strings into paths directly.

### XSS Handling

The app uses server-rendered Jinja templates and JSON API responses. Jinja
autoescaping and DOM APIs such as `textContent` should be used for untrusted
strings.

Treat these values as untrusted for browser rendering:

- Prompts and annotated prompts.
- Palette fragment content.
- Filenames.
- Provider errors.
- Embedded metadata fields.
- Model/provider parameters restored from metadata.
- Immich responses.

Client code should not insert these values with `innerHTML`, `insertAdjacentHTML`,
or equivalent APIs. Server code should not mark these values safe for Jinja
rendering.

### Embedded Metadata

The stored gallery file is the canonical metadata-rich image. Metadata is read
through `EmbeddedImageMetadataProvider`, not through templates or ad hoc route
code.

Embedded metadata may come from files that were generated by this app, copied
from another machine, edited externally, or deliberately tampered with. It must
therefore be treated as untrusted input. In particular:

- `source_images` values may contain path traversal attempts, absolute paths,
  unsupported extensions, stale filenames, or non-string values.
- `parameters` may contain unsupported names, wrong types, excessive values, or
  provider-specific source image fields.
- `prompt`, `model`, `model_alias`, `provider`, `created_at`, and
  `content_type` may be absent, malformed, or misleading.

The metadata route filters source image references through `safe_image_filename`
and only returns source images that still exist in the gallery directory. Unsafe
or missing references are omitted and reported as warnings.

Loading metadata into the workspace must remain a convenience operation, not a
trust elevation. Any later generation submitted from loaded metadata still has
to pass the normal server-side generation validation.

### External Providers and Remote Data

Generation providers return remote URLs or file-like results. These outputs are
untrusted until downloaded and validated by the provider wrapper and image store
code. Downloads should keep using a single helper with timeouts, content-type
checks, size limits where practical, and collision-resistant local filenames.

Provider error messages are useful for debugging but must not leak credentials.
They should be logged and returned with actionable detail while avoiding API key
or token disclosure.

### Clean Downloads

Normal downloads serve the stored metadata-rich gallery file. Clean downloads
create a temporary metadata-stripped copy under the configured temporary
directory and serve that copy without mutating the gallery file.

Clean export files must not be written into the gallery output directory and
must not be listed as gallery images.

## Residual Risks

- A device on the household LAN that can open the app can control it.
- A browser extension or local malware with access to the page can read the CSRF
  token and act as the operator.
- A TLS proxy improves transport security but does not add application
  authentication unless separately configured.
- Binding to `0.0.0.0` exposes the app to every host that can reach that
  interface.
- Flask debug mode should not be exposed outside a trusted development LAN.
- Metadata parsing depends on Pillow's image parsing behavior. Malformed images
  should be expected and handled as untrusted files.

## Operational Recommendations

- Prefer `127.0.0.1:5002` unless LAN access is actively needed.
- When using `0.0.0.0:5002`, use it only on a trusted household LAN and stop the
  app when finished.
- Use a strong `IMAGEGEN_FLASK_SECRET_KEY` for any shared LAN or proxied setup.
- Keep `.env`, `IMAGEGEN_DATA_DIR`, generated images, uploaded source images,
  and SQLite data out of source control.
- Put a TLS reverse proxy in front when accessing the app over Wi-Fi or through
  any network where passive observation is a concern.
- Keep Flask debug mode disabled except during active local development. The
  provided start scripts enable debug mode only when `--dev` is specified.
- Do not expose the Flask development server directly to the internet.
- Restrict firewall access to trusted local subnets or devices when possible.

## Development Requirements

Future changes should preserve these rules:

- Every mutating route must require `require_api_csrf` or an equivalent
  same-instance write guard.
- Mutating API routes should stay JSON-only unless a replacement CSRF strategy
  is explicitly designed for forms or uploads.
- Do not add permissive CORS for authenticated or mutating routes.
- Do not add user-supplied filesystem paths. Accept stable local filenames and
  resolve them under configured app directories.
- Do not bypass `PaletteRepository` for palette reads or writes.
- Do not bypass `ImageMetadataProvider` for gallery metadata access from routes.
- Do not trust metadata-loaded source image references; revalidate them before
  display, selection, or generation.
- Do not send app annotation syntax to model providers.
- Do not use `innerHTML` for untrusted prompts, filenames, metadata, provider
  output, or palette content.
- Do not expose `disable_safety_checker` as a user-configurable control.
- Do not make tests call real image generation providers by default.

## Verification Checklist

Before changing route, gallery, palette, metadata, or provider behavior, verify:

- `uv run pytest`
- `uv run ruff check src tests`

Security-relevant test coverage should include:

- Missing, invalid, wrong-content-type, and wrong-client CSRF requests.
- Path traversal attempts against image, gallery, palette, clean download, and
  delete routes.
- Unsafe metadata source image references.
- XSS payload strings in prompts, palette fragments, filenames, provider errors,
  and metadata fields.
- Clean download behavior that strips metadata without mutating the stored
  gallery file.
