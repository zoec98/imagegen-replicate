# App-Like MVP Implementation Plan

This plan moves the MVP from full-page form submissions toward a single-page Flask UI backed by `/api/*` routes. The page should normally not reload during generation. Prompt text, selected model parameters, and gallery state should remain visible while backend work runs.

## Ticket 1: CSRF And API Request Guard

### Scope

- Add a small security module for API route protection.
- On `GET /`, create or reuse a per-session CSRF token.
- Store the client IP from `request.remote_addr` in the session when the token is created.
- Embed the CSRF token into the page, for example as a `<meta name="csrf-token">`.
- Protect mutating `/api/*` routes with:
  - `Content-Type: application/json`.
  - `X-CSRF-Token` matching the session token.
  - `request.remote_addr` matching the session client IP.
- Do not enable CORS.

### Acceptance Criteria

- The rendered page contains a CSRF token.
- Mutating `/api/*` requests without the token are rejected.
- Mutating `/api/*` requests with a mismatched token are rejected.
- Mutating `/api/*` requests from a different client IP are rejected.
- Mutating `/api/*` requests with non-JSON content are rejected.
- Valid same-session JSON API requests with the token are accepted.

### Suggested Tests

- Unit tests for token creation and reuse.
- Route tests for missing token, invalid token, wrong IP, wrong content type, and valid request.
- Confirm no CORS headers are emitted for API responses.

## Ticket 2: API Route Skeleton

### Scope

- Split UI routes and API routes cleanly.
- Keep `GET /` as the browser workspace page.
- Add `/api/*` routes under a dedicated module, for example `api_routes.py`.
- Initial API routes:
  - `POST /api/generate`
  - `GET /api/generation/<request_id>`
  - `GET /api/images`
- Keep direct image serving at `GET /images/<filename>`.

### Acceptance Criteria

- `app.py` remains an app factory and registration point only.
- Browser UI route registration remains separate from API route registration.
- `/api/generate` accepts JSON and returns JSON.
- `/api/generation/<request_id>` returns JSON status for known requests.
- `/api/images` returns JSON gallery data sorted newest first.
- Existing direct image URLs keep working.

### Suggested Tests

- Route registration tests for all API endpoints.
- JSON response shape tests for `/api/images`.
- Unknown request id returns 404 JSON.
- Existing `/images/<filename>` tests continue to pass.

## Ticket 3: Request State Store

### Scope

- Add a lightweight local request state store.
- Track generation request id, prompt, parameters, status, errors, prediction id, output URLs, stored image filenames, timestamps, and logs where available.
- Keep the implementation local and simple for the MVP.
- Prefer an in-memory store for the first pass, with clear boundaries so it can later move to SQLite or files.

### Acceptance Criteria

- A request can be created with prompt and model parameters.
- A request can transition through `queued`, `running`, `succeeded`, `failed`, and `timeout`.
- Request state can be fetched by id.
- Completed requests include stored image filenames when available.
- Failed requests preserve error detail without leaking credentials.

### Suggested Tests

- Unit tests for create/get/update request lifecycle.
- Unknown request id returns `None` or a controlled not-found result.
- Status transitions preserve prompt and parameters.
- Error state stores a user-displayable message.

## Ticket 4: Background Generation Worker

### Scope

- Move Replicate generation out of the HTTP request/response cycle.
- `/api/generate` should enqueue or start a background task and return quickly with a local request id.
- The background task should:
  - Build the Replicate payload.
  - Create the prediction with `predictions.create(model=<model-key>, input=<payload>)`.
  - Poll `predictions.get(prediction.id)`.
  - Respect `IMAGEGEN_REPLICATE_POLL_SECONDS`.
  - Respect `IMAGEGEN_REPLICATE_TIMEOUT_SECONDS`.
  - Persist generated images and sidecar metadata.
  - Update request state throughout.
- No webhooks.
- No automatic retry.

### Acceptance Criteria

- `POST /api/generate` responds quickly with a local request id.
- The browser can poll `/api/generation/<request_id>` while work continues.
- The request eventually reaches a terminal state.
- Successful requests include downloaded image records.
- Failed or timed-out requests surface a clear error.
- Prompt and selected parameters remain available in request state.

### Suggested Tests

- Fake worker/generator tests that avoid real Replicate calls.
- API test that `/api/generate` returns a request id without blocking on a fake long task.
- Polling endpoint returns running status before completion.
- Polling endpoint returns succeeded status with stored images.
- Timeout path sets `timeout` state.

## Ticket 5: Parameter Parsing And Validation

### Scope

- Parse model-specific parameters from API JSON.
- Validate against model registry metadata.
- Keep `disable_safety_checker: true` in fixed inputs, never in user-submitted parameters.
- Preserve prompt and submitted parameters in request state.
- For Seedream 4.5 MVP, support:
  - `prompt`
  - `size`
  - `aspect_ratio`
  - `sequential_image_generation`
  - `max_images`
- Leave source image upload and `image_input` for a later ticket.

### Acceptance Criteria

- Valid submitted parameters are used in the Replicate payload.
- Missing optional parameters fall back to registry defaults.
- Invalid select choices are rejected.
- Invalid integer bounds are rejected.
- `disable_safety_checker` submitted by the browser is ignored or rejected and is always set to `true` by fixed inputs.
- Prompt has no artificial length limit, but blank prompt is rejected.

### Suggested Tests

- Unit tests for valid payload construction.
- Tests for default fallback.
- Tests for invalid select choice and out-of-range `max_images`.
- Test that user-supplied `disable_safety_checker: false` cannot disable the fixed `true` value.
- API validation tests for JSON error responses.

## Ticket 6: Browser-Side Generate Flow

### Scope

- Add client-side JavaScript for app-like form submission.
- Prevent the normal form reload.
- Read prompt and parameter controls from the page.
- Send `POST /api/generate` with JSON and `X-CSRF-Token`.
- Disable the Generate button during an active request.
- Change button text or state to show generation is running.
- Preserve the textarea and selected controls while the request is active and after it completes.
- Show persistent status/error messages on the page.

### Acceptance Criteria

- Pressing Generate does not reload the page.
- Prompt content remains in the textarea after submission.
- Parameter control values remain selected after submission.
- Generate button is disabled while one request is active.
- Double-submit is prevented.
- Missing/blank prompt shows an error without reload.
- API errors are shown without reload.

### Suggested Tests

- Browser or DOM-level test that submit prevents default navigation.
- Route-level tests for JSON validation.
- Manual browser verification on desktop and mobile widths.
- Test or manual check that button disables and re-enables.

## Ticket 7: Browser Polling And Progress Display

### Scope

- Poll `/api/generation/<request_id>` from the browser while a request is running.
- Poll interval should use the configured server value exposed to the page or a server-provided hint.
- Display status such as `queued`, `running`, `succeeded`, `failed`, or `timeout`.
- If Replicate logs/progress are available, show a concise progress message.
- Stop polling at terminal states.
- Refresh the gallery when generation succeeds.

### Acceptance Criteria

- Browser polls only while at least one request is active.
- Polling stops on terminal status.
- Running status is visible to the user.
- Failed and timeout states are visible to the user.
- Gallery updates after success without full page reload.
- Prompt and parameter values remain unchanged after gallery refresh.

### Suggested Tests

- JS/unit test or browser test for polling lifecycle if practical.
- API tests for status response shape.
- Manual browser verification with fake slow generation.
- Manual browser verification with a real Replicate request.

## Ticket 8: Gallery API And Client Refresh

### Scope

- Return gallery data from `/api/images`.
- Include filename, direct image URL, metadata URL if exposed later, content type if known, and creation time if available.
- Update the client gallery without reloading the page.
- Keep direct image links opening the image file in a new tab for easy downloads.
- Keep square gallery slots with contained natural-aspect images.

### Acceptance Criteria

- `/api/images` returns newest-first image data.
- Gallery refresh renders all current images.
- Gallery image links point directly to `/images/<filename>`.
- Captions show filenames.
- Empty gallery state is shown when no images exist.

### Suggested Tests

- API test for empty gallery.
- API test for newest-first ordering.
- API test excludes metadata JSON and non-image files.
- Browser/manual test for direct link opening.

## Ticket 9: Image Upload Preparation For Edit-Capable Models

### Scope

- Prepare the architecture for source images without fully implementing image-edit UI if out of MVP scope.
- Keep `edit_capable` in model metadata.
- Decide upload storage location under the same local storage root as generated outputs.
- Add a future-safe API shape for source images, but do not expose incomplete controls.

### Acceptance Criteria

- Model metadata clearly identifies edit-capable models.
- Upload and output storage roots can share a parent.
- No broken image-edit controls appear in the MVP UI.
- Future `image_input` support has an obvious route/module boundary.

### Suggested Tests

- Existing model registry tests for `edit_capable`.
- No UI controls for source upload until implemented.
- Documentation notes the planned upload boundary.

## Ticket 10: Documentation And Developer Guardrails

### Scope

- Update `README.md` for the app-like generate flow.
- Update `AGENTS.md` with API route rules:
  - Mutating `/api/*` routes require CSRF.
  - Mutating `/api/*` routes require JSON.
  - Mutating `/api/*` routes require same session client IP.
  - Do not enable CORS.
  - Do not expose `disable_safety_checker`.
- Document direct image links and local metadata sidecars.
- Keep `scripts/get_schema` as the schema inspection helper.

### Acceptance Criteria

- README describes install, run, and normal usage accurately.
- AGENTS contains clear backend/API security guardrails.
- PLAN stays current with implementation decisions.
- No docs imply page reload is required for generation.

### Suggested Tests

- Documentation review.
- Run `uv run pytest`.
- Run `uv run ruff format src tests`.
- Run `uv run ruff check --fix src tests`.
