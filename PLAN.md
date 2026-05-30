# Next Stage Implementation Plan

This plan covers the next set of infrastructure changes:

- Detect stale browser pages/static JavaScript.
- Remove GIF support.
- Move generated-image metadata from JSON sidecars into embedded image metadata.
- Add a SQLite generation log under `data/`.

The current app-like `/api/*` generation flow remains the baseline.

## Ticket 1: Static Page Freshness Check

### Scope

- Add an application static/build checksum generated from relevant UI assets:
  - `src/imagegen/templates/index.html`
  - `src/imagegen/static/app.js`
  - `src/imagegen/static/app.css`
- Embed the checksum in the rendered page head, for example:
  - `<meta name="app-build" content="...">`
- Expose the current checksum through a lightweight API route, for example:
  - `GET /api/app-version`
- Have `app.js` compare the page checksum with the server checksum:
  - On page load.
  - Before starting a generation request.
  - Optionally after a generation finishes.
- If the page is stale, show a clear message and disable Generate until reload.
- Keep this local and deterministic; do not depend on git state.

### Acceptance Criteria

- Rendered HTML contains the current app checksum.
- `/api/app-version` returns the same checksum for current assets.
- If the checksum differs, the UI marks itself stale and blocks new generation.
- Stale-page messaging is visible and actionable.
- Existing API CSRF rules are not weakened.

### Suggested Tests

- Unit test checksum generation changes when asset content changes.
- Route test for `GET /api/app-version`.
- Template test that the checksum meta tag is present.
- JS/browser manual check: simulate a mismatched checksum and confirm Generate is blocked.

### Notes

- This is not a substitute for browser cache headers, but it directly handles the development problem where a loaded tab is using old `app.js`.
- A later improvement can add cache-busted static URLs, for example `app.js?v=<checksum>`.

## Ticket 1b: Cache-Busted Static URLs

### Scope

- Render static asset URLs with the same application checksum used by Ticket 1:
  - `/static/app.css?v=<checksum>`
  - `/static/app.js?v=<checksum>`
- Keep the checksum deterministic and local to the current asset/template contents.
- Use `url_for("static", filename=..., v=app_checksum)` or an equivalent helper.
- Keep stale-page detection from Ticket 1. Cache busting makes new page loads fetch new assets; it does not detect already-loaded stale tabs by itself.

### Acceptance Criteria

- Rendered HTML includes `?v=<checksum>` on `app.css` and `app.js`.
- The query value matches the checksum exposed by `/api/app-version`.
- When relevant static/template content changes, the rendered static URLs change.
- Existing static asset serving still works in Flask development mode.

### Suggested Tests

- Template route test asserts cache-busted CSS and JS URLs.
- Unit test or route test confirms the query value equals the current app checksum.
- Manual browser check: after changing `app.js`, a reload fetches the new URL instead of reusing the old cached URL.

## Ticket 2: Remove GIF Support

### Scope

- Remove `.gif` from local gallery discovery.
- Remove `image/gif` from generated output extension mapping.
- Reject GIF downloads explicitly, even though `image/gif` starts with `image/`.
- Reject GIF source images for edit requests.
- Update tests and documentation.

### Acceptance Criteria

- GIF files in `data/images/` are not shown in the gallery.
- GIF output URLs are rejected by download validation.
- GIF source image filenames are rejected by source-image validation.
- `.png`, `.jpg`, `.jpeg`, and `.webp` remain supported.

### Suggested Tests

- Gallery discovery excludes `.gif`.
- Download helper rejects `image/gif`.
- Source image validation rejects `source.gif`.
- Existing supported extension tests continue to pass.

## Ticket 3: Embedded Metadata Writer And Provider

### Scope

- Prefer `pyexiv2` as the first implementation candidate because it is backed by Exiv2 and is a better fit for the app's JPEG, PNG, and WebP support than `piexif`.
- Before committing the dependency, run a short local spike that verifies:
  - installation through `uv`;
  - write/read support for JPEG, PNG, and WebP files;
  - where the metadata is stored most cleanly, preferring XMP for structured application JSON and EXIF `UserComment` only if that works reliably across supported formats;
  - behavior when a file already has metadata;
  - document that project licensing accepts `pyexiv2`'s GPLv3 license;
  - native Exiv2 dependency behavior on the project's target developer platforms.
- If `pyexiv2` is rejected because of platform or format behavior, fall back to a narrower implementation:
  - `piexif` plus `Pillow` for JPEG/WebP where reliable;
  - `Pillow` `PngInfo` or another explicit PNG text chunk strategy for PNG;
  - a single project provider API hiding those format-specific details.
- Add `src/imagegen/metadata_embed.py` or `src/imagegen/exif.py`, based on the previously reviewed `set_exif_data()` strategy from the sibling image generation project.
- Store generated-image metadata in the image file instead of writing JSON sidecars.
- Specifically store the previous metadata `parameters` key in embedded metadata.
- Preserve or expose the current metadata provider boundary:
  - Replace `SidecarImageMetadataProvider` with an embedded-metadata-backed provider.
  - Keep route/gallery code using the provider interface.
- Decide the metadata tag contract before implementation:
  - Prefer a namespaced XMP field for structured app JSON if `pyexiv2` handles it cleanly across JPEG, PNG, and WebP.
  - Use `ExifIFD.UserComment` for JSON payloads only when it is reliable for the selected output formats.
  - Use standard date fields for creation time where practical.
  - Keep `ImageDescription` short and human-readable if used.
- Do not write new `<image-filename>.json` sidecars for newly generated images.
- Do not delete existing JSON sidecars in this ticket.
- Take care of charset encoding and decoding issues in the data.
- If `pyexiv2` is used from background worker code, serialize metadata read/write calls with a process-local lock because the library documents global-state thread-safety limits.

### Acceptance Criteria

- Generated JPEG, PNG, and WebP images have embedded metadata written after download, or unsupported formats fail explicitly before this ticket is accepted.
- The `parameters` payload can be read back through the provider API.
- New generated images do not create JSON sidecars.
- Existing gallery metadata access still works through the provider boundary.
- The selected dependency and metadata storage contract are documented in this plan or follow-up docs.
- If a supported output format cannot reliably store embedded metadata, the limitation is explicit and tested.

### Suggested Tests

- Unit test embedded metadata writer writes and reads a `parameters` JSON payload for JPEG, PNG, and WebP fixtures.
- Unit test metadata provider returns expected `created_at` and content type where available.
- Image persistence test verifies no JSON sidecar is written.
- Image persistence test verifies embedded parameters are written.
- Test unsupported embedded metadata format behavior.
- If using `pyexiv2`, include a small test or guard proving metadata operations are serialized through the project boundary.

### Open Decisions

- GPLv3 licensing is acceptable for this project, so `pyexiv2` remains the preferred dependency if the format and platform spike passes.
- Whether the canonical structured metadata field should be XMP or EXIF `UserComment`.
- Whether full metadata should be duplicated into embedded metadata or only the `parameters` key, now that SQLite will hold the full generation record.

## Ticket 4: SQLite Generation Log

### Scope

- Add a SQLite database under `data/`, for example:
  - `data/imagegen.sqlite3`
- Use the standard library `sqlite3` first. SQLAlchemy is likely overkill for the current two-table MVP, but can be adopted later if migrations and richer relations become painful.
- Add `src/imagegen/generation_log.py` as the database/repository boundary.
- Initialize schema at app startup.
- Log generation request lifecycle transitions and results.
- Do not update SQLite every polling interval or every second. Polling remains an in-memory/UI concern; the durable log is updated only when the request is accepted, starts, reaches a terminal state, or produces result/error records.
- Store enough request data to recreate the original Replicate request later:
  - selected model alias and model key;
  - full input payload sent to Replicate, including fixed inputs such as `disable_safety_checker`;
  - user-adjustable parameters as submitted and validated;
  - source image references as local filenames, not image bytes or copied database blobs.

### Proposed Tables

`generation_requests`:

- `id`: local request id, primary key.
- `created_at`: request creation timestamp.
- `started_at`: worker start timestamp.
- `completed_at`: terminal timestamp.
- `status`: queued/running/succeeded/failed/timeout.
- `model_alias`.
- `model`.
- `replicate_input_json`: full input payload sent to Replicate, suitable for recreating the request.
- `prompt`.
- `parameters_json`.
- `source_image_filenames_json`: local source image filenames for edit requests, never source image bytes.
- `prediction_id`.
- `error`.
- `elapsed_seconds`.

`generation_results`:

- `id`: integer primary key.
- `request_id`: foreign key to `generation_requests.id`.
- `sequence`.
- `filename`.
- `source_url`.
- `content_type`.
- `size_bytes`.
- `created_at`.
- `elapsed_seconds`.
- `logs_json`.
- `error`.

### Acceptance Criteria

- Database file is created under `data/`.
- Schema initializes idempotently.
- A generation request row is inserted when `/api/generate` accepts a request.
- Request rows contain enough data to recreate the original Replicate request without reading UI state.
- Edit request source images are stored as local filename references only.
- Status, start time, completion time, elapsed time, prediction id, logs, and errors are updated on lifecycle transitions, not every poll/second.
- Result rows are written for each stored output image.
- Tests use temporary database paths and do not touch real `data/`.

### Suggested Tests

- Schema initialization creates both tables.
- Insert request and fetch it back.
- Insert an edit request and verify only source image filenames are persisted.
- Verify `replicate_input_json` matches the payload the Replicate wrapper receives, including fixed model inputs.
- Update status lifecycle and elapsed time.
- Verify repeated polling/status reads do not write database updates.
- Insert multiple result rows for one request.
- Failed and timeout requests persist error detail.
- Worker test verifies logger calls with a fake generation result.

### Notes

- Keep the in-memory `RequestStore` for active request polling in this stage.
- SQLite is the durable history/log. It does not need to replace active request state yet.
- A later ticket can add UI history views backed by the database.

## Ticket 5: Wire EXIF And SQLite Into Generation Flow

### Scope

- Update `image_store.py` so image persistence returns enough data for:
  - EXIF metadata writing.
  - SQLite result insertion.
- Update `worker.py` so request lifecycle events are logged to SQLite.
- Keep API status responses backed by `RequestStore`.
- Keep gallery refresh behavior unchanged from the user's perspective.

### Acceptance Criteria

- Successful generation writes image files, EXIF metadata, and database request/result rows.
- Failed generation writes a failed database request row with error details.
- Timeout generation writes a timeout database request row with elapsed time.
- Gallery still lists newest local image files and opens direct image links.
- No JSON sidecars are written for new images.

### Suggested Tests

- End-to-end fake worker/service test writes EXIF and database rows.
- Failure-path worker test writes database error state.
- Timeout-path worker test writes database timeout state.
- Regression test that `/api/images` still returns current image data.

## Ticket 6: Add Flux Flex Model Registry Entry

### Scope

- Add registry support for `flux-flex`.
- Use the schema from:
  - `https://replicate.com/black-forest-labs/flux-2-flex/api/schema`
- Run `scripts/get_schema black-forest-labs/flux-2-flex` before implementation and extract the registry-relevant input/output shape.
- Capture:
  - stable internal id, likely `flux-flex`;
  - display name;
  - Replicate model key `black-forest-labs/flux-2-flex`;
  - schema URL;
  - pinned version if the schema page exposes one unambiguously;
  - edit capability and source image fields if present;
  - fixed inputs;
  - parameter widgets, defaults, bounds, enums, required fields, and ordering.
- Keep `disable_safety_checker: true` as a fixed model input if the model exposes that parameter.
- Extend server-side validation to support model-specific parameters for both Seedream 4.5 and Flux Flex.

### Acceptance Criteria

- `flux-flex` is listed by the registry and can be selected by API payloads.
- Registry metadata is sufficient for the UI to render model-specific controls.
- Server validation rejects unsupported parameters for the selected model.
- Fixed model inputs are included in the final Replicate payload and are not user-editable.
- Tests do not call Replicate.

### Suggested Tests

- Registry test verifies the `flux-flex` model entry fields and schema URL.
- Validation tests cover required/default parameters for `flux-flex`.
- Payload construction test verifies fixed inputs and user parameters are merged correctly.
- Negative validation test rejects a Seedream-only parameter when `flux-flex` is selected, and vice versa.

## Ticket 7: Model Chooser Header And Model-Specific Controls

### Scope

- Replace the static headline currently showing the active model name with a model chooser dropdown.
- Populate the chooser from server-provided registry metadata.
- On model change:
  - update visible model name;
  - update model-specific parameter controls;
  - preserve the prompt text unless the user explicitly loads metadata from an image;
  - reset or validate parameters that do not apply to the newly selected model;
  - update edit-mode availability from model metadata.
- Keep the UI responsive on phone, tablet, and desktop widths.

### Acceptance Criteria

- The current model can be changed without reloading the page.
- The selected model is included in `/api/generate` payloads.
- Model-specific controls match the selected registry entry.
- Prompt content is preserved across model switches.
- Unsupported old parameter values are not silently submitted for the new model.

### Suggested Tests

- Route/template test exposes model registry metadata needed by the browser.
- API validation test accepts the selected model id and rejects unknown model ids.
- Browser/manual test switches between Seedream 4.5 and Flux Flex and verifies controls update.
- JavaScript unit-style test or browser check confirms prompt preservation on model switch.

## Ticket 8: Edit Mode Toggle And Source Image Selection

### Scope

- Add an `Edit` toggle button near the model controls.
- Disable and visually gray out the toggle when the selected model has no edit variant/capability.
- When edit mode is enabled:
  - allow gallery images to be selected and deselected as source images;
  - show a blue dot overlay in the top-right corner of each selected image;
  - show a selected-source-image counter next to the `Edit` toggle;
  - show a `Clear` button next to the counter that deselects all source images.
- When edit mode is disabled:
  - source image selection controls are inactive;
  - selected image state is either cleared or ignored according to a documented UI decision.
- Selection state should be local browser state until the user submits a generation request.
- Source images are represented by local gallery filenames, never image bytes in JSON payloads.

### Acceptance Criteria

- Models without edit capability show a disabled edit toggle.
- Models with edit capability allow edit mode to be enabled and disabled.
- Selected images have a clear blue top-right overlay indicator.
- The counter always matches the selected image count.
- `Clear` removes all selected-source-image state and updates overlays/counter.
- The UI remains touch-friendly and does not interfere with opening images in a new tab.

### Suggested Tests

- Template/API metadata test verifies edit capability is exposed to the browser.
- Browser/manual test verifies disabled and enabled edit toggle behavior per model.
- JavaScript test or browser check verifies select/deselect/counter/clear behavior.
- Validation test rejects source image filenames when the selected model is not edit-capable.

### Open Decisions

- Whether disabling edit mode clears selected images immediately or keeps them cached but ignored.
- Maximum number of source images per model should come from registry metadata where the schema exposes it.

## Ticket 9: Submit Edit Requests With Source Images

### Scope

- Extend the `/api/generate` browser payload to include:
  - selected model id;
  - edit mode flag;
  - selected source image filenames when edit mode is enabled.
- Server-side validation must enforce:
  - edit mode only for edit-capable models;
  - source image filenames refer to existing supported local gallery images;
  - selected source image count is within model limits;
  - source image parameters are mapped to the selected model's expected input field.
- The Replicate payload should include source images only for edit requests.
- SQLite logging should store source image filenames and the final Replicate input payload.

### Acceptance Criteria

- Text-to-image requests still work without source images.
- Edit requests send selected local source images to Replicate through the existing source image upload/file handling path.
- Invalid source filenames are rejected before worker start.
- Non-edit-capable models cannot receive source images.
- The generation log can later recreate the same request using the stored model id, parameters, prompt, and source image filenames.

### Suggested Tests

- API route test accepts a valid edit request with source image filenames.
- API route test rejects edit requests for non-edit-capable models.
- API route test rejects missing, unsupported, or path-traversal source image filenames.
- Replicate client test verifies source files are mapped to the model's source image input field.
- Generation log test verifies edit source filenames and final input payload are persisted.

## Ticket 10: Gallery Image Actions And Metadata Load

### Scope

- Decorate each gallery image placeholder/card with compact SVG icon buttons:
  - image type indicator for `png`, `jpg`, or `webp`;
  - folder icon button: load image metadata into the current workspace;
  - red trashcan icon button: delete image from the local gallery.
- Leave room for optional integration icons, such as the Immich upload cloud added in Ticket 11.
- The image type indicator is informational and not destructive.
- The load action reads embedded metadata through the metadata provider:
  - replace the current prompt with the image metadata prompt;
  - replace current model/settings with the image metadata parameters where supported;
  - surface a clear error if metadata is missing or incompatible with the current registry.
- The delete action calls a protected API route that unlinks the image file.
- Deleting should also remove associated metadata sidecars only for legacy files if sidecars still exist.
- Deletion must not allow path traversal or deleting outside the configured image directory.
- Refresh the gallery after deletion without reloading the page.

### Acceptance Criteria

- Gallery cards show file type, load, and delete controls without text overlap at mobile/tablet/desktop widths.
- Load metadata replaces prompt and settings with values read from the selected image metadata.
- Load metadata handles missing/incompatible metadata with a visible error and preserves current prompt/settings.
- Delete requires a CSRF-protected API request and removes only the selected local image file.
- Deleted images disappear from the gallery after successful deletion.
- Delete failures are visible and do not remove the card optimistically unless confirmed by the server.

### Suggested Tests

- Metadata route/provider test returns enough data to populate prompt/model/settings.
- API route test deletes a valid image under the configured image directory.
- API route test rejects path traversal and missing filenames.
- API route test rejects deletion without CSRF protection.
- Browser/manual test verifies icon placement, load behavior, delete behavior, and responsive layout.

### Open Decisions

- Whether delete should require a confirmation gesture in the MVP.
- Whether loading metadata should also restore edit-mode source image selections when those source image filenames still exist locally.

## Ticket 11: Optional Immich Upload Integration

### Scope

- Add optional `.env` configuration:
  - `IMMICH_URL`
  - `IMMICH_GALLERY_ID`
  - `IMMICH_API_KEY`
- Treat the integration as disabled unless all required Immich values are present.
- Add an Immich client boundary, for example `src/imagegen/immich_client.py`.
- Use `httpx` for Immich API calls.
- Verify the current Immich API shape during implementation before coding endpoint details.
- When Immich config is present, render a cloud icon button on gallery image cards.
- Hitting the cloud icon uploads the selected local image file to Immich.
- If `IMMICH_GALLERY_ID` maps to an Immich album/gallery concept, attach the uploaded asset to that target after upload.
- Handle duplicate upload responses as a successful "already present" state, not as an error.
- Keep the API route CSRF-protected and validate that the requested filename stays inside the configured image directory.
- Do not expose the Immich API key to browser JavaScript.
- Surface per-image upload state in the UI:
  - uploading;
  - uploaded;
  - already present;
  - failed.

### Acceptance Criteria

- With no Immich config, no cloud upload buttons are rendered and no Immich API calls are possible.
- With complete Immich config, gallery cards render a cloud icon upload button.
- Upload calls are sent from the Flask backend, not directly from browser JavaScript to Immich.
- Successful uploads show a successful state in the UI.
- Duplicate/already-present responses show an "already present" state and do not produce an error toast.
- Failed uploads show actionable error text without leaking the API key.
- Filename validation prevents uploading arbitrary files outside the image directory.

### Suggested Tests

- Config test verifies Immich is disabled unless all required values are set.
- Template/API images test verifies the cloud action is exposed only when Immich is configured.
- Immich client tests use mocked `httpx` responses for success, duplicate/already-present, and failure.
- API route test verifies upload requires CSRF protection.
- API route test rejects path traversal and missing filenames.
- API route test verifies duplicate/already-present responses return a non-error status payload.
- Browser/manual test verifies cloud icon state transitions and responsive layout.

### Open Decisions

- Exact Immich API endpoints and duplicate response shape must be confirmed against the deployed Immich version during implementation.
- Whether `IMMICH_GALLERY_ID` should be named `IMMICH_ALBUM_ID` if the API uses album terminology.
- Whether uploaded-state should be persisted in SQLite or remain a per-session UI status for the first iteration.

## Ticket 12: Documentation And Guardrails

### Scope

- Update `README.md`:
  - Explain stale-page detection and reload behavior.
  - Remove references to JSON sidecars for new images.
  - Document SQLite log location.
  - Document optional Immich configuration and upload behavior.
- Update `AGENTS.md`:
  - GIF is unsupported.
  - Metadata is stored in EXIF for new images.
  - Durable generation logs live in SQLite under `data/`.
  - Route/gallery code must use provider/repository boundaries instead of reading EXIF or SQLite directly.
  - New models must be added from schema-derived registry metadata.
  - Source image references are stored as filenames, not image bytes.
  - Gallery deletion must stay inside the configured image directory.
  - Immich API keys stay server-side and must never be exposed to browser JavaScript.
- Update `.env.example` only if new configuration values are introduced.

### Acceptance Criteria

- Docs match the implemented behavior.
- No docs imply GIF support.
- No docs imply new JSON sidecars are written.
- Developer guardrails describe EXIF and SQLite boundaries.
- End-user documentation covers model selection, edit mode source selection, metadata load, and image deletion.
- End-user documentation covers optional Immich upload configuration and duplicate-upload behavior.

### Suggested Tests

- Documentation review.
- Full local checks:

```bash
uv run ruff format src tests
uv run ruff check --fix src tests
uv run pytest
```

## Implementation Order

1. Static page freshness check.
2. Remove GIF support.
3. Spike and select embedded metadata dependency, then add metadata read/write boundary.
4. Add SQLite generation log boundary.
5. Wire EXIF and SQLite into image persistence and worker lifecycle.
6. Add Flux Flex registry entry.
7. Add model chooser and model-specific controls.
8. Add edit mode toggle and gallery source image selection.
9. Submit edit requests with source images.
10. Add gallery image action controls.
11. Add optional Immich upload integration.
12. Update docs and guardrails.

## Known Risks

- Embedded metadata support varies by image format and library. `pyexiv2` likely has the best JPEG/PNG/WebP fit, and its GPLv3 license is acceptable here, but native Exiv2 dependencies and documented thread-safety limits still need handling.
- Removing GIF support may hide existing local GIF files if any are present.
- SQLite writes from background worker threads need careful connection handling; use one connection per operation or per repository instance with thread-safe boundaries.
- Stale-page detection must not create noisy false positives during normal use.
- Model-specific UI state can become stale when switching models; validation must remain server-authoritative.
- Gallery deletion is intentionally destructive and needs narrow filename validation plus CSRF protection.
- Immich API behavior may vary by deployed server version; keep the integration behind a small client boundary and mocked tests.
