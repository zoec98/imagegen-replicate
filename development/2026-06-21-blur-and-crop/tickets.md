# Blur And Crop Tickets

Source stories: `development/2026-06-21-blur-and-crop/user-stories.md`.

## Decisions Applied

- Keep the existing pencil icon, but treat it as `Edit image`.
- Extend the existing mask editor into a mode-aware image editor with `Crop`,
  `Blur`, and `Mask` modes.
- Preserve embedded source metadata exactly as-is for crop and blur outputs.
  Do not add operation history metadata.
- Save crop and blur results as new uniquely named gallery images.
- Do not overwrite the original source image.
- Do not expose crop coordinate entry or coordinate readouts.
- Require crop rectangles to map to at least 10 by 10 natural-image pixels.
- Use existing red painted markup for blur selection. Do not implement true
  blur preview in the first version.
- Use a blur radius slider from 0 to 50 px, accepting floating-point values.
- Keep blur brush size as a mask creation detail only; do not send it as a
  server operation parameter.
- Keep blur falloff defaulted to 0 percent in blur mode, but allow users to
  raise falloff for soft blur edges.
- Add two new backend endpoints for crop and blur. Keep the existing mask
  endpoint for mask mode.
- Reuse existing filename, path, output-directory, and gallery boundaries where
  possible.

## Ticket 1: Confirm Image Editing Boundaries

Status: Complete.

Result: `development/2026-06-21-blur-and-crop/boundary-audit.md`.

### Goal

Identify the existing server-side boundaries that crop and blur should reuse
before adding new endpoints.

### Scope

- Locate the current source-image filename validation used by generation and
  mask workflows.
- Locate gallery output-directory confinement and unique filename generation.
- Locate embedded metadata read/write helpers.
- Locate CSRF handling used by mutating gallery or mask routes.
- Document which helpers will be reused by crop and blur.
- Document any small helper extraction needed before endpoint work.

### Acceptance Criteria

- The implementation path for validating source image filenames is known.
- The implementation path for writing new gallery images safely is known.
- The implementation path for preserving embedded metadata is known.
- Crop and blur endpoint tickets can reference concrete helpers or boundaries.
- Any missing boundary is recorded as part of this epic before implementation.

### Verification

- Documentation-only ticket unless helper extraction is required.
- If code changes are required: `uv run pytest`
- If code changes are required: `uv run ruff check src tests`

### Implementation Notes

- Reuse `imagegen.source_images.validate_source_image_filename()` and
  `source_image_path()` for source image validation and path resolution.
- Reuse `imagegen.security.require_api_csrf` for crop and blur JSON endpoints.
- Reuse `api_routes._gallery_image_by_filename()` and
  `api_routes._gallery_image_json()` for successful edited-image responses.
- Add a new local edit helper module for crop/blur output writing; existing
  provider download, import, trash, and mask writers do not exactly match the
  metadata-preserving edited-image contract.
- Extract reusable mask payload decoding from `mask_store.py` before blur so
  blur can validate the same mask payload shape without writing a mask file.

## Ticket 2: Add Backend Crop Operation

Status: Complete.

### Goal

Add a server-side crop endpoint that creates a new gallery image from a
validated rectangle without modifying the source image.

### Scope

- Add a crop API endpoint protected by CSRF.
- Accept a source image identifier and crop rectangle payload.
- Validate source filename using the existing safe boundary.
- Validate crop rectangle shape, numeric values, bounds, and minimum natural
  image size.
- Map the operation to natural image pixels on the server-provided image.
- Save the cropped image under the configured images directory with a
  collision-safe generated filename.
- Preserve embedded source metadata exactly as-is when present.
- Do not add operation history or new metadata when source metadata is absent.
- Return a JSON response compatible with gallery refresh behavior.
- Add focused route and image-operation tests.

### Acceptance Criteria

- Valid crop requests produce a new gallery image.
- Source images are never overwritten.
- Out-of-bounds, empty, negative, malformed, non-numeric, and too-small crop
  rectangles are rejected.
- Unsafe source filenames are rejected.
- Existing embedded metadata is preserved exactly as-is.
- Sources without embedded metadata do not receive operation metadata.
- Crop failures return actionable JSON errors.

### Verification

- Add failing tests before implementation.
- `uv run pytest`
- `uv run ruff check src tests`

### Implementation Notes

- Added `imagegen.image_edits.crop_image()` as the backend crop operation.
- Added `POST /api/images/<path:filename>/crop` as a CSRF-protected JSON API.
- Crop outputs use server-generated `source-crop-<uuid>` filenames and preserve
  the source file extension.
- Crop reads existing embedded application metadata and writes the exact same
  metadata dictionary to the edited output when present.
- Sources without embedded application metadata produce cropped outputs without
  added operation metadata.
- Added operation-level tests in `tests/test_image_edits.py`.
- Added route-level tests in `tests/test_image_routes.py`.

## Ticket 3: Add Frontend Image Editor Mode Shell

Status: Complete.

### Goal

Convert the existing mask editor UI into a mode-aware image editor shell while
preserving current mask behavior.

### Scope

- Rename browser-facing labels and tooltips from mask-only wording to image
  editing wording where appropriate.
- Add an operation selector at the far left of the editor controls.
- Provide `Crop`, `Blur`, and `Mask` modes.
- Preserve current mask mode as the default-compatible behavior unless a better
  default is chosen during implementation.
- Update visible controls when modes change.
- Clear transient crop and paint selections when the editor closes.
- Keep existing mask endpoint usage unchanged in `Mask` mode.
- Add jsdom tests for mode switching and control visibility.

### Acceptance Criteria

- The pencil icon opens the editor overlay.
- The editor exposes `Crop`, `Blur`, and `Mask`.
- Switching modes does not close the editor.
- Mask mode still shows brush size and falloff controls.
- Mask mode does not show crop controls or blur radius controls.
- Existing mask save behavior remains compatible.
- Closing the editor clears transient editor state.

### Verification

- Add failing Vitest tests before implementation.
- `npm run js:check`
- `uv run pytest`
- `uv run ruff check src tests`
- Manual browser smoke test of opening, closing, and mask mode.

### Implementation Notes

- Kept the pencil icon but changed browser-facing labels/tooltips to
  `Edit image`.
- Added an operation selector with `Crop`, `Blur`, and `Mask` modes to the
  editor controls.
- Set `Crop` as the default mode per the ticket 3 addendum.
- Added mode-specific shell control groups for crop and blur without
  implementing crop drawing or blur submission yet.
- Mask mode still owns the existing brush size, falloff, invert, and save mask
  controls.
- Closing and reopening the editor resets transient mode state back to `Crop`.
- Added jsdom tests for mode switching, control visibility, close reset, and
  dynamic gallery labels.

## Ticket 4: Add Frontend Crop Interaction

Status: Complete.

### Goal

Allow users to draw a free crop rectangle over the displayed image and submit it
to the crop endpoint.

### Scope

- Add crop-mode pointer interaction for drawing a rectangle over the displayed
  image.
- Visually dim the non-selected image area while a crop rectangle exists.
- Disable the crop action until a valid displayed rectangle exists.
- Convert displayed image coordinates to natural image dimensions for the
  backend payload.
- Do not show coordinate entry or coordinate readouts.
- Submit crop payload through the existing API helper.
- Refresh the gallery after successful crop.
- Show actionable crop errors on failure.
- Add jsdom tests for crop control state, payload assembly, and success/error
  handling.

### Acceptance Criteria

- Crop mode uses rectangle selection, not brush painting.
- The crop rectangle can be drawn freely with pointer interaction.
- The area outside the crop rectangle is dimmed.
- The crop action is disabled until a valid rectangle exists.
- The browser sends natural image coordinates, not raw displayed coordinates.
- Coordinates are not displayed and cannot be manually entered.
- Successful crop refreshes the gallery and leaves the source unchanged.
- Crop errors are visible to the user.

### Verification

- Add failing Vitest tests before implementation.
- `npm run js:check`
- `uv run pytest`
- `uv run ruff check src tests`
- Manual browser validation of crop drawing, dimming, save, and gallery refresh.

### Implementation Notes

- Added crop save URLs to server-rendered and API-rendered gallery image data.
- Crop mode is now the default editor mode.
- Crop mode uses rectangle pointer interaction on the editor overlay canvas.
- The overlay canvas dims the non-selected region and outlines the crop
  rectangle.
- The crop action remains disabled until the natural-image crop rectangle is at
  least 10 by 10 pixels.
- Crop submissions send natural image coordinates to
  `POST /api/images/<filename>/crop` through the existing CSRF JSON helper.
- Successful crop closes the editor, refreshes the gallery, and reports the
  new image filename.
- Crop errors leave the editor open and show the backend error.
- Added jsdom tests for crop control state, crop payload assembly, success
  handling, and error handling.

## Ticket 5: Add Backend Blur Operation

Status: Complete.

### Goal

Add a server-side blur endpoint that applies Gaussian blur only to painted mask
regions and writes a new gallery image.

### Scope

- Add a blur API endpoint protected by CSRF.
- Accept a source image identifier, mask payload, and blur radius.
- Validate source filename using the existing safe boundary.
- Validate blur radius as a floating-point value from 0 to 20.
- Validate mask payload type, dimensions, bounds, and non-empty content.
- Reject missing, malformed, empty, or unsafe masks.
- Apply Gaussian blur only to marked regions.
- Save the blurred image under the configured images directory with a
  collision-safe generated filename.
- Preserve embedded source metadata exactly as-is when present.
- Do not add operation history or new metadata when source metadata is absent.
- Return a JSON response compatible with gallery refresh behavior.
- Add focused route and image-operation tests.

### Acceptance Criteria

- Valid blur requests produce a new gallery image.
- Source images are never overwritten.
- Blur radius accepts floating-point values from 0 to 20.
- Blur radius values outside the accepted range are rejected.
- Brush size is not accepted as a server operation parameter.
- Missing, malformed, empty, wrong-sized, or unsafe masks are rejected.
- Gaussian blur is applied only to marked regions.
- Existing embedded metadata is preserved exactly as-is.
- Sources without embedded metadata do not receive operation metadata.
- Blur failures return actionable JSON errors.

### Verification

- Add failing tests before implementation.
- `uv run pytest`
- `uv run ruff check src tests`

### Implementation Notes

- Used the existing Pillow dependency and `PIL.ImageFilter.GaussianBlur`; no
  new dependency and no hand-rolled blur implementation were added.
- Added `imagegen.image_edits.blur_image()` as the backend blur operation.
- Added `POST /api/images/<path:filename>/blur` as a CSRF-protected JSON API.
- Refactored `mask_store.py` to expose reusable mask payload decoding while
  preserving existing mask-save behavior.
- Blur outputs use server-generated `source-blur-<uuid>` filenames and preserve
  the source file extension.
- Blur accepts floating-point radius values from 0 to 20.
- Blur rejects `brush_size`; brush size remains a frontend mask creation
  detail, not a server operation parameter.
- Blur rejects missing, malformed, wrong-sized, and empty masks.
- Blur reads existing embedded application metadata and writes the exact same
  metadata dictionary to the edited output when present.
- Sources without embedded application metadata produce blurred outputs without
  added operation metadata.
- Added operation-level tests in `tests/test_image_edits.py`.
- Added route-level tests in `tests/test_image_routes.py`.

## Ticket 6: Add Frontend Blur Interaction

Status: Complete.

### Goal

Allow users to paint blur regions, select a Gaussian blur radius, and submit the
mask to the blur endpoint.

### Scope

- Add blur mode using the existing painted red markup behavior.
- Keep brush size controls available in blur mode.
- Show falloff controls in blur mode.
- Keep blur falloff defaulted to 0 percent.
- Add a blur radius slider labeled with `px`.
- Configure the blur radius range as 0 to 50 with floating-point values.
- Send mask payload plus blur radius through the existing API helper.
- Do not send brush size as a blur operation parameter.
- Do not implement true blur preview.
- Refresh the gallery after successful blur.
- Show actionable blur errors on failure.
- Add jsdom tests for control visibility, radius payload, mask payload, and
  success/error handling.

### Acceptance Criteria

- Blur mode uses brush painting.
- Brush size can be adjusted for mask creation.
- Falloff controls are available for soft blur edges.
- Blur radius is visible, uses a `px` metric, and accepts values from 0 to 50.
- The browser sends the painted mask or alpha mask plus blur radius.
- The browser does not send brush size as a blur operation parameter.
- The visible preview remains the existing red painted markup.
- Successful blur refreshes the gallery and leaves the source unchanged.
- Blur errors are visible to the user.

### Verification

- Add failing Vitest tests before implementation.
- `npm run js:check`
- `uv run pytest`
- `uv run ruff check src tests`
- Manual browser validation of blur painting, radius selection, save, and
  gallery refresh.

### Implementation Notes

- Added blur save URLs to server-rendered and API-rendered gallery image data.
- Blur mode uses the existing red painted overlay, brush-size control, and
  falloff control.
- Blur mode falloff defaults to 0 percent and can be raised for soft blur edges.
- Added a blur radius slider from 0 to 50 px with floating-point step support.
- Blur submissions send only `mask_png` and `blur_radius` to
  `POST /api/images/<filename>/blur`; brush size is not sent.
- Successful blur closes the editor, refreshes the gallery, and reports the
  new image filename.
- Blur errors leave the editor open and show the backend error.
- Added jsdom tests for blur control visibility, radius labels, payload
  assembly, success handling, and error handling.

## Ticket 7: Preserve Gallery Integration For Edited Images

Status: Complete.

### Goal

Ensure crop and blur outputs behave like normal generated gallery images across
existing gallery workflows.

### Scope

- Confirm edited images appear in the gallery after crop and blur saves.
- Confirm edited images can be selected as source images where edit mode is
  supported.
- Confirm edited images can be downloaded through the existing clean download
  workflow.
- Confirm edited images can be deleted, trashed, restored, and inspected for
  metadata.
- Add or extend backend and JavaScript tests where existing coverage does not
  already prove these workflows.
- Avoid adding special gallery cases for crop or blur outputs unless required.

### Acceptance Criteria

- Cropped images appear as normal gallery entries.
- Blurred images appear as normal gallery entries.
- Edited image filenames are server-generated and safe.
- Edited images use existing gallery metadata loading.
- Edited images use existing delete, trash, restore, and download behavior.
- No browser-submitted output filename is trusted.

### Verification

- Add failing tests for any uncovered integration behavior before
  implementation.
- `npm run js:check`
- `uv run pytest`
- `uv run ruff check src tests`
- Manual browser validation of gallery integration for one crop output and one
  blur output.

### Implementation Notes

- No production gallery special-casing was needed; crop and blur outputs already
  use the same generated filename, output directory, gallery listing, metadata,
  download, delete, trash, restore, and source-image validation boundaries as
  normal gallery images.
- Added route integration coverage proving cropped outputs appear in `/api/images`
  with metadata, support metadata inspection, support clean download without
  stripping metadata from the stored gallery file, and can be deleted and
  restored through the existing trash workflow.
- Added route integration coverage proving blurred outputs appear in the gallery
  and can be reused as edit-mode source images in `/api/generate`.
- Added route coverage proving crop and blur ignore browser-submitted output
  filenames and use server-generated safe names.
- Manual browser validation remains in Ticket 8.

## Ticket 8: Manual Browser Validation And Epic Closeout

Status: Complete.

### Goal

Manually validate the in-browser behavior that jsdom tests cannot prove well
without adding Playwright.

### Scope

- Start the Flask development server.
- Validate opening the image editor from a gallery pencil icon.
- Validate mode switching among `Crop`, `Blur`, and `Mask`.
- Validate crop rectangle drawing and dimming.
- Validate crop save and output image result.
- Validate blur painting with red markup.
- Validate blur radius selection and output image result.
- Validate existing mask save behavior still works.
- Validate closing the editor clears transient selections.
- Record any browser-only issues discovered.
- Mark follow-up tickets if visual or interaction issues remain.

### Acceptance Criteria

- Manual browser validation notes are recorded in this epic.
- Crop interaction works with pointer input in a real browser.
- Blur painting works with pointer input in a real browser.
- Mask mode remains usable in a real browser.
- Generated crop and blur outputs are inspectable in the gallery.
- Any unresolved issue has a ticket or explicit decision.

### Verification

- `scripts/run-dev.sh --dev`
- Manual browser validation checklist recorded in this epic.
- `npm run js:check`
- `uv run pytest`
- `uv run ruff check src tests`

### Validation Notes

- Manual browser validation was completed by the user for the crop, blur, and
  mask editor workflows.
- The blur output appeared weaker than expected compared with other image
  programs. The current implementation does not intentionally mix source pixels
  into fully painted blur areas: the frontend exports fully painted blur mask
  pixels as grayscale `255`, and the backend composites the fully blurred image
  over the source image with that mask. The red editor overlay uses a lower
  alpha only for visual markup.
- Default editor values were adjusted after validation:
  - Brush radius defaults to `50 px`.
  - Falloff defaults to `0%`.
  - Gaussian blur radius defaults to `20 px`.
  - Gaussian blur radius accepts values from `0` to `50 px`.
- Crop and Blur action buttons were aligned as mode actions and styled like the
  primary Save Mask button when active.
- Follow-up browser validation found that CSS component display rules overrode
  the `hidden` attribute for the Falloff controls in Blur mode. Added explicit
  hidden-state CSS for editor controls and kept the Blur slider/action group on
  one aligned row at desktop widths.
- Follow-up decision: Falloff is now intentionally enabled in Blur mode. Existing
  grayscale mask export and backend compositing already support soft blur edges;
  the default remains `0%`.
