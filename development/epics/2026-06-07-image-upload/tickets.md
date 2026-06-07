# Image Upload Tickets

Source story: `development/epics/image-upload/user-story.md`.

## Decisions Applied

- Store uploads and imports in the configured images directory.
- Always use a generated local filename for imported/uploaded images.
- Support single-file drag-and-drop uploads in the first implementation.
- Support Immich pagination only in the first implementation; no search or
  filtering yet.
- Preserve existing embedded image metadata unchanged when importing images.
- Keep `src/imagegen/static/app.js` as a single no-build file for this feature.

## Ticket 1: Create Image Import Storage Boundary

### Goal

Add a backend boundary for validating and storing imported image bytes without
trusting browser-submitted filenames, MIME types, URLs, or remote metadata.

### Scope

- Create a focused module such as `src/imagegen/image_imports.py`.
- Generate collision-resistant local image filenames instead of preserving
  remote or uploaded filenames.
- Validate image bytes with Pillow before writing them into the configured
  images directory.
- Restrict stored files to supported image formats used by the local gallery.
- Upload size limit of 100MiB.
- Write files only inside the configured images directory.
- Preserve embedded image metadata as-is; do not add source metadata in this
  first implementation.

### Acceptance Criteria

- Valid PNG, JPEG, and WebP image bytes can be stored and then appear in the
  local gallery.
- Invalid image bytes are rejected before storage.
- Unsupported formats are rejected before storage.
- Generated filenames are safe, unique, and collision-resistant.
- No caller can choose an output path or overwrite an existing image.
- Existing embedded metadata is not rewritten or stripped by the import helper.

### Verification

- Add focused unit tests for generated names, supported image validation,
  invalid image rejection, unsupported format rejection, collision handling, and
  output-directory confinement.
- `uv run pytest`
- `uv run ruff check src tests`

## Ticket 2: Add URL Image Import API

### Goal

Let the upload overlay import one image from an HTTP or HTTPS URL through a
CSRF-protected JSON API.

### Scope

- Add a POST API endpoint for URL imports.
- Accept a JSON payload containing a URL.
- Validate that the URL uses `http` or `https`.
- Fetch the remote content with timeouts and a bounded response size.
- Pass fetched bytes through the image import storage boundary.
- Return the imported image using the same gallery JSON shape used by
  `/api/images`.

### Acceptance Criteria

- HTTP and HTTPS image URLs can be imported.
- Non-HTTP schemes are rejected.
- Missing, malformed, unreachable, oversized, non-image, and unsupported image
  responses return actionable JSON errors.
- The endpoint requires CSRF protection.
- Provider credentials and sensitive local paths are not leaked in errors.
- Successful imports refresh the local gallery client-side using returned image
  data or the existing gallery refresh API.

### Verification

- Add route tests with mocked HTTP responses; do not make real network calls in
  tests.
- Cover success, invalid scheme, invalid payload, fetch failure, oversized
  response, non-image data, unsupported image format, and missing CSRF.
- `uv run pytest`
- `uv run ruff check src tests`

## Ticket 3: Add Local Drag-And-Drop Upload API

### Goal

Let the upload overlay accept a single dropped local image file and store it in
the configured images directory.

### Scope

- Add a CSRF-protected multipart upload API endpoint.
- Accept exactly one file in the first implementation.
- Reject empty uploads and multi-file uploads.
- Treat browser-submitted filenames and MIME types as advisory only.
- Pass uploaded bytes through the image import storage boundary.
- Return the imported image using the same gallery JSON shape used by
  `/api/images`.

### Acceptance Criteria

- A single valid dropped image file can be uploaded.
- Multiple files are rejected with a clear error.
- Non-image and unsupported image data are rejected even when the browser MIME
  type says `image/*`.
- The endpoint requires CSRF protection.
- Existing gallery images are not overwritten.
- Successful uploads refresh the local gallery client-side using returned image
  data or the existing gallery refresh API.

### Verification

- Add route tests for valid upload, no file, multiple files, invalid image data,
  unsupported image format, misleading MIME type, collision handling, and
  missing CSRF.
- `uv run pytest`
- `uv run ruff check src tests`

## Ticket 4: Extend Immich Client For Main Gallery Pagination

### Goal

Expose the Immich main gallery as a paginated source for imports without loading
tens of thousands of remote assets at once.

### Scope

- Add Immich client methods for listing main-gallery assets in batches of 20.
- Add Immich client support for downloading or streaming a selected asset for
  import.
- Keep Immich configuration and credentials behind the existing Immich client
  boundary.
- Do not add search or filtering in the first implementation.

### Acceptance Criteria

- The client can request the first page of 20 Immich assets.
- The client can request subsequent pages without loading the full gallery.
- Returned asset records contain only the fields needed by the upload overlay:
  stable asset id, thumbnail URL or thumbnail data route, display timestamp or
  label, dimensions if available, and import eligibility.
- Remote API failures preserve actionable details without leaking credentials.
- Unit tests do not call the real Immich service.

### Verification

- Add Immich client tests using mocked HTTP responses.
- Cover pagination parameters, empty page, API error, malformed response, and
  asset download.
- `uv run pytest`
- `uv run ruff check src tests`

## Ticket 5: Add Immich Browser And Import APIs

### Goal

Provide JSON endpoints that let the upload overlay page through Immich assets
and import a selected asset into the local images directory.

### Scope

- Add a GET API endpoint for paginated Immich main-gallery assets.
- Enforce a page size of 20.
- Add a CSRF-protected POST API endpoint for importing one Immich asset.
- Hide Immich endpoints or return a clear not-configured response when Immich is
  not configured.
- Pass downloaded Immich asset bytes through the image import storage boundary.
- Return imported images using the same gallery JSON shape used by `/api/images`.

### Acceptance Criteria

- Immich gallery listing returns one batch of at most 20 assets per request.
- The client can request next and previous batches using an opaque cursor or
  explicit page token supported by the Immich client implementation.
- Importing an Immich asset stores a generated local filename in the configured
  images directory.
- Importing preserves the downloaded image metadata unchanged.
- Listing and import endpoints do not expose Immich credentials.
- Import requires CSRF protection.

### Verification

- Add route tests for configured and unconfigured Immich states.
- Cover first page, next page, empty result, API failure, successful import,
  invalid asset id, unsupported downloaded data, and missing CSRF.
- `uv run pytest`
- `uv run ruff check src tests`

## Ticket 6: Render Upload Button And Overlay Shell

### Goal

Add the upload entry point and overlay markup to the workspace without wiring
all interactions yet.

### Scope

- Add an upload button between the trash control and palette controls.
- Add upload overlay markup to `index.html`.
- Include a URL field with a `Load` button.
- Include a drag-and-drop target labeled for image uploads.
- Include an Immich browser region that renders only when Immich is configured.
- Add route data attributes for the new upload and Immich APIs.

### Acceptance Criteria

- The upload button appears between trash and palettes.
- The overlay can be opened and closed by browser code.
- The URL field and `Load` button are present.
- The drop target exists and communicates single-image upload behavior.
- The Immich browser shell is absent or disabled when Immich is not configured.
- Existing trash, palette, gallery, and mask UI hooks remain unchanged.

### Verification

- Add workspace render tests for button placement, overlay shell, data
  attributes, Immich configured/unconfigured states, and critical CSS/JS hooks.
- `uv run pytest`
- `uv run ruff check src tests`

## Ticket 7: Implement Upload Overlay Browser Behavior

### Goal

Wire the upload overlay interactions in the single no-build `app.js` file.

### Scope

- Open and close the upload overlay from the upload button.
- Submit URL imports with the `Load` button.
- Accept one dropped file with browser MIME type `image/*`.
- Reject multi-file drops in the browser before calling the API.
- Show progress, success, empty, and error states in the overlay.
- Refresh the local gallery after successful URL, drop, or Immich imports.

### Acceptance Criteria

- URL imports call the URL import API and surface API errors.
- Drag-and-drop uploads call the multipart upload API for one image file.
- Multi-file drops are rejected with a clear client-side message.
- Non-image browser MIME types are rejected client-side while the server still
  performs authoritative validation.
- Successful imports appear in the local gallery without a full page reload.
- Existing gallery selection, mask, trash, palette, and generation workflows
  continue to work.

### Verification

- Add or update route/render tests for required data hooks.
- Manually validate URL import, single-file drop, multi-file rejection, invalid
  file rejection, overlay open/close, and gallery refresh.
- `uv run pytest`
- `uv run ruff check src tests`

## Ticket 8: Implement Immich Overlay Pagination UI

### Goal

Let users browse Immich main-gallery assets in batches of 20 and import a
selected image from the upload overlay.

### Scope

- Load the first Immich batch when the upload overlay opens and Immich is
  configured.
- Render Immich assets in a gallery-like view.
- Add next/previous pagination controls.
- Import one selected Immich asset through the Immich import API.
- Show loading, empty, success, and error states.
- Do not implement search or filtering.

### Acceptance Criteria

- The overlay requests at most 20 Immich assets at a time.
- Next and previous controls fetch only the requested batch.
- The UI does not attempt to load the full Immich gallery.
- Importing an Immich image refreshes the local gallery.
- Immich browser controls are hidden or disabled when Immich is not configured.
- Pagination state remains coherent after API errors and empty pages.

### Verification

- Add or update render tests for Immich browser hooks and pagination controls.
- Manually validate first page, next page, previous page, empty result, API
  error, successful import, and unconfigured Immich state.
- `uv run pytest`
- `uv run ruff check src tests`

## Ticket 9: Style Upload Overlay And Responsive States

### Goal

Make the upload overlay fit the existing workspace UI and remain usable across
desktop, tablet, and mobile widths.

### Scope

- Add CSS for the upload button, overlay, URL row, drop target, Immich browser,
  pagination controls, and status messages.
- Keep styling in `src/imagegen/static/app.css`.
- Match existing gallery/trash overlay conventions without nesting cards inside
  cards.
- Ensure long URLs, filenames, labels, and errors do not overflow their
  containers.

### Acceptance Criteria

- The upload overlay is visually consistent with the existing workspace.
- The URL field and `Load` button remain usable on mobile.
- The drop target has clear idle, drag-over, invalid, loading, and error states.
- Immich pagination controls do not shift layout as batches load.
- Text and controls do not overlap at desktop, tablet, or mobile widths.

### Verification

- Manual responsive validation at desktop, tablet, and mobile widths.
- Validate overlay open/close and import states after CSS changes.
- `uv run pytest`
- `uv run ruff check src tests`

## Ticket 10: Document Image Upload Configuration And Use

### Goal

Update user-facing documentation so users know how URL uploads, local uploads,
and Immich imports work.

### Scope

- Update `README.md` with image upload usage.
- Document Immich configuration requirements for the upload overlay browser.
- Explain that imported files receive generated local filenames.
- Explain that initial drag-and-drop support accepts one file at a time.
- Explain that Immich browsing is paginated and does not include search or
  filtering yet.

### Acceptance Criteria

- README stays end-user focused.
- Internal implementation notes remain in `development/`.
- Documentation does not promise unsupported bulk upload, search, filtering, or
  metadata rewriting behavior.

### Verification

- Documentation review.
- `uv run pytest`
- `uv run ruff check src tests`

