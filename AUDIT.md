# Security Audit

Audit range: `48d4829bda75b5507fda5282bf874dbc37b3b56a..HEAD`

Audit basis:

- Project security model and requirements in `SECURITY.md`.
- Flask/Python and browser JavaScript security guidance from the local security best-practices skill.
- Changed files in the audit range, with focus on the new mask editor, mask-save route, gallery JSON/template additions, and tests.

## Executive Summary

No Critical or High severity issues were found in the audited changes.

The new mask-save route preserves the project’s core security controls: it is CSRF-protected, JSON-only, validates gallery filenames with `safe_image_filename`, keeps writes inside the configured image directory, rejects non-PNG mask payloads, validates dimensions against the source image, and stores masks as grayscale PNG files. The new browser code uses safe DOM APIs such as `textContent`, `createElement`, dataset properties, and `fetch` with the existing CSRF header.

One Medium issue was found during the audit and remediated: mask PNG upload handling originally lacked an explicit request/body/decoded-image size bound before base64 decode and Pillow image load. The route now derives dynamic limits from the source image dimensions, caps decoded payloads at 256 MiB, and rejects oversized request bodies, oversized base64 strings, and oversized decoded payloads before image decoding.

## Findings

### M-001: Mask-save route accepted unbounded base64 PNG payloads before image decode

- Rule ID: FLASK-FILE-RESOURCE-001 / SECURITY.md Trust Boundaries and Filesystem Path Handling
- Severity: Medium
- Status: Remediated
- Location: `src/imagegen/api_routes.py`, `api_save_mask`, `_mask_payload_limits`, `_validate_mask_request_size`, `_mask_png_payload`
- Original evidence:

```python
payload = request.get_json(silent=True) or {}
mask_image = _decode_mask_png(_mask_png_payload(payload))
...
return b64decode(value, validate=True)
...
with Image.open(BytesIO(mask_bytes)) as image:
    image.load()
```

The original route had no visible global Flask request body limit such as `MAX_CONTENT_LENGTH`, and no route-level check of `request.content_length`, base64 string length, decoded byte length, Pillow pixel count, or expected maximum dimensions before `b64decode(...)` and `image.load()`.

- Impact: Anyone who can reach the app, load the workspace, and obtain a valid CSRF token can submit very large JSON/base64 mask payloads or compressed PNGs that require excessive memory and CPU to decode. In the local/LAN threat model this is not a public internet remote attack, but it can still make the running app unavailable or consume disk when the payload passes validation.
- Fix implemented:
  - The route opens the source image first and derives limits from `width * height`.
  - The decoded payload allowance is `source_width * source_height * 4 + 1 MiB`, allowing for RGBA canvas-origin PNG data plus file overhead.
  - The decoded payload allowance is capped with `min(dynamic_cap, 256 MiB)`.
  - The base64/data-URL string allowance is derived from the decoded-byte allowance.
  - The JSON request body allowance is derived from the base64 allowance plus a small JSON overhead allowance.
  - `request.content_length`, `len(mask_png)`, and `len(decoded_bytes)` are checked before Pillow loads the submitted mask.
  - No 96 MiB ceiling is used.
- Mitigation: Keep the app bound to `127.0.0.1` unless LAN access is needed, stop it after use, and only use `--secure-network` on trusted networks as already documented in `SECURITY.md`.
- False positive notes: Pillow has its own decompression-bomb safeguards, but the application-level dynamic bounds now reject oversized payloads earlier and independently.

## Controls Verified

- CSRF: The new mutating route `POST /api/images/<filename>/mask` is decorated with `@require_api_csrf` at `src/imagegen/api_routes.py:226-228`. The shared guard requires JSON, `X-CSRF-Token`, and a matching client IP.
- Path traversal: The route passes the URL filename through `safe_image_filename` before building `source_path`, and writes the mask using `mask_filename(safe_name)`.
- Directory confinement: The saved mask path is derived from `app_config.output_dir / saved_name`; `saved_name` is generated from the already-safe source basename.
- Unsupported source files: Source filenames still use the existing safe image extension policy, which excludes GIFs.
- Payload type validation: The mask payload is accepted only as base64 PNG data, decoded with `validate=True`, and opened with Pillow while checking `image.format == "PNG"`.
- Payload size validation: The mask payload is bounded dynamically from source dimensions before JSON parsing, base64 decoding, and Pillow image loading.
- Dimension validation: The route compares the decoded mask dimensions to the source image dimensions before saving.
- Stored format: The route converts saved masks to grayscale mode `L`, matching the provider-ready mask requirement.
- XSS posture: New dynamic browser UI paths use `textContent`, `createElement`, `setAttribute` for non-event attributes, dataset values, and Jinja autoescaping. No new `innerHTML`, `insertAdjacentHTML`, `eval`, `new Function`, `document.write`, string event handlers, `postMessage`, or browser storage usage was found in the audited changed files.
- External navigation: Refreshed gallery links use server-generated local image URLs and preserve `target="_blank"` with `rel="noopener"`.

## Test Coverage Observed

The audited tests cover these security-relevant behaviors:

- Mask save requires CSRF.
- Unsafe source filenames are rejected.
- Missing source images are rejected.
- Invalid PNG payloads are rejected.
- Oversized request bodies are rejected.
- Oversized base64 mask strings are rejected.
- Oversized decoded mask payloads are rejected.
- Dimension mismatches are rejected.
- Saved masks are written as PNG, mode `L`, with expected black/gray/white pixel values.
