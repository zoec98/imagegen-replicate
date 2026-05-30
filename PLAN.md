# Next Stage Implementation Plan

Several completed tickets have been removed.

## Implementation Order

4. Rework SQLite log.
8. Add edit mode toggle and gallery source image selection.
9. Submit edit requests with source images.
10. Add gallery image action controls.
11. Add optional Immich upload integration.
12. Update docs and guardrails.


## Ticket 4: Rework SQLite log.

### Scope

- Existing SQLite database under `data/`:
  - `data/imagegen.sqlite3`
- For these changes, the old database does not need preservation. There is only lab data in it.
- Implement the change inside `src/imagegen/generation_log.py`, keeping it as the database/repository boundary.
- Keep the public call sites roughly the same:
  - `/api/generate` creates the accepted request row.
  - `ThreadedGenerationWorker` marks start/terminal state and adds generated assets.
  - The in-memory `RequestStore` remains the active polling store.
- Initialize the SQLite schema at app startup.
- Main idea: split immutable request facts, prediction lifecycle state, and produced assets into separate durable records.
- We do not update SQLite every polling interval or every second. Polling remains an in-memory/UI concern; the durable log is updated only when the request is accepted, starts, reaches a terminal state, or produces result/error records.
- Store enough request data to recreate the original Replicate request later:
  - selected model alias and model key;
  - full input payload sent to Replicate, including fixed inputs such as `disable_safety_checker`;
  - user-adjustable parameters as submitted and validated;
  - source image references as local filenames, not image bytes or copied database blobs.
- Do not build a history UI in this ticket.
- Do not add migrations for preserving old lab data. If an existing local database is incompatible, the implementation may rebuild the known application tables after confirming this is the unversioned lab schema.

### Tables and Changes

Currently the schema is unversioned. Add a `schema_version` table with one row containing the integer schema version. This ticket should create version `1`.

Target request table:

```sqlite
CREATE TABLE generation_requests (
    id TEXT PRIMARY KEY,
    sent_at TEXT NOT NULL,
    model_alias TEXT NOT NULL,
    model TEXT NOT NULL,
    request_sent_json TEXT NOT NULL,
    parameters_json TEXT NOT NULL,
    source_image_filenames_json TEXT NOT NULL
);
```

Target lifecycle/result table. One accepted request should have at most one row here, because one app request maps to one Replicate prediction attempt.

```sqlite
CREATE TABLE generation_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id TEXT NOT NULL UNIQUE REFERENCES generation_requests(id),
    started_at TEXT,
    completed_at TEXT,
    status TEXT NOT NULL,
    prediction_id TEXT,
    logs_json TEXT NOT NULL,
    error TEXT,
    elapsed_seconds REAL
);
```

Target asset table. Store one row per generated local asset.

```sqlite
CREATE TABLE generation_assets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    result_id INTEGER NOT NULL REFERENCES generation_results(id),
    request_id TEXT NOT NULL REFERENCES generation_requests(id),
    sequence INTEGER NOT NULL,
    filename TEXT NOT NULL,
    source_url TEXT NOT NULL,
    content_type TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (request_id, sequence)
);
```

Indexes:

- `generation_requests(sent_at)`.
- `generation_results(status)`.
- `generation_assets(request_id, sequence)`.

Repository behavior:

- `create_request(...)` inserts into `generation_requests` and also creates an initial `generation_results` row with `status = 'queued'`, empty `logs_json`, and no prediction id.
- `mark_started(...)` updates only `generation_results.started_at` and `generation_results.status`.
- `mark_finished(...)` updates only `generation_results.completed_at`, `status`, `prediction_id`, `logs_json`, `error`, and `elapsed_seconds`.
- `add_result(...)` inserts into `generation_assets`; it should not duplicate logs or errors per asset.
- Existing debug/test helpers such as `get_request(...)` and `list_results(...)` may be updated or replaced with helpers that expose the new row shapes for tests.
- Keep JSON serialization deterministic with sorted keys.

### Acceptance Criteria

- App startup creates the versioned schema idempotently in a fresh database.
- An unversioned lab database is handled explicitly and does not leave mixed old/new tables behind.
- Accepted requests persist:
  - request id;
  - sent timestamp;
  - model alias and Replicate model key;
  - full request JSON sent to Replicate;
  - validated user parameters JSON;
  - source image filename JSON.
- Starting and finishing a request update the lifecycle/result row, not the immutable request row.
- Successful generation with multiple images creates one `generation_results` row and one `generation_assets` row per stored image.
- Failed and timed-out requests create/update the lifecycle/result row with actionable error details and no fake asset rows.
- The in-memory polling behavior remains unchanged.
- Existing tests that assert Replicate payload construction and worker lifecycle behavior continue to pass after updating expected database row shapes.

### Suggested Tests

- `SQLiteGenerationLog.initialize()` creates `schema_version`, `generation_requests`, `generation_results`, and `generation_assets`, and can be called twice.
- Initializing over the current unversioned lab schema rebuilds to the new versioned schema.
- `create_request(...)` persists recreatable request data and creates a queued lifecycle row.
- `mark_started(...)` updates only the lifecycle row with `running` and `started_at`.
- `mark_finished(..., status="succeeded", prediction_id=..., logs=...)` records terminal state, prediction id, logs, completion timestamp, and elapsed time.
- `mark_finished(..., status="failed" | "timeout", error=...)` records error details without inserting assets.
- `add_result(...)` inserts asset metadata into `generation_assets` with stable sequence ordering and without copying logs/errors per asset.
- Worker test verifies a successful multi-image result creates one terminal lifecycle update and multiple asset rows.
- API route/generation log test verifies the stored `request_sent_json` includes fixed model inputs such as `disable_safety_checker: true`.

### Notes

- Keep the in-memory `RequestStore` for active request polling.
- SQLite is the durable history/log. It will never replace the active request polling.
- A later ticket can add UI history views backed by the database.

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

## Known Risks

- SQLite writes from background worker threads need careful connection handling; use one connection per operation or per repository instance with thread-safe boundaries.
- Model-specific UI state can become stale when switching models; validation must remain server-authoritative.
- Gallery deletion is intentionally destructive and needs narrow filename validation plus CSRF protection.
- Immich API behavior may vary by deployed server version; keep the integration behind a small client boundary and mocked tests.
