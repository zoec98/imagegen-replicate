# Blur And Crop User Stories

## Story

As a user, I want to edit existing gallery images so that I can create cropped,
blurred, or mask-derived versions without overwriting the original image.

The editor is opened from the existing pencil icon on a gallery image. The
pencil action should be treated as `Edit image`, not only `Create mask`.

## Decisions

- Use a new image-editor workflow that reuses the existing mask editor overlay
  where practical.
- Keep the pencil icon, but update labels/tooltips toward `Edit image`.
- Add an operation selector at the far left of the editor controls with three
  modes: `Crop`, `Blur`, and `Mask`.
- Preserve existing embedded metadata exactly as-is when creating edited images.
  Do not add operation history metadata.
- Save crop and blur results as new uniquely named gallery images.
- Do not overwrite the source image.
- Keep the existing mask-generation behavior available as `Mask` mode.
- Add two new backend endpoints for crop and blur. The existing mask endpoint
  remains the mask-mode backend.
- Reuse existing server-side filename/path validation boundaries where possible,
  and add focused validation for crop and blur payloads.
- Do not show coordinate entry or coordinate readouts for crop.
- Do not attempt blur preview in the first version. Keep the existing red
  painted markup as the preview of affected regions; the blurred output is
  visible after processing.

## Primary Workflow

1. The user opens the workspace gallery.
2. The user clicks the pencil icon on an existing image.
3. The image editor overlay opens with an operation selector.
4. The user chooses `Crop`, `Blur`, or `Mask`.
5. The visible editor controls adapt to the selected operation.
6. The user marks the image and clicks the operation-specific action button.
7. The server writes a new uniquely named image for crop or blur operations.
8. The gallery refreshes and shows the newly edited image.
9. The original image remains unchanged.

## Story 1: Open Image Editor

As a user, I want the pencil icon on a gallery image to open an image editor so
that I can choose what kind of edit to perform.

### Acceptance Criteria

- The existing pencil icon remains available on gallery images.
- The pencil icon opens the existing editor overlay shell.
- The icon label and tooltip describe image editing rather than only masking.
- The editor has an operation selector at the far left of the controls.
- The selector offers `Crop`, `Blur`, and `Mask`.
- Switching operations updates visible controls without closing the editor.
- Closing the editor clears transient crop and paint selections.

## Story 2: Crop Image

As a user, I want to draw a rectangle over an image and crop to that rectangle
so that I can save the selected region as a new gallery image.

### User Behavior

1. The user opens the image editor.
2. The user selects `Crop`.
3. The user draws a free rectangle over the displayed image.
4. The area outside the selected crop rectangle is visually dimmed.
5. The user clicks `Crop`.
6. The cropped image is saved as a new uniquely named gallery image.

### Acceptance Criteria

- Crop mode uses rectangle selection, not brush painting.
- The rectangle is drawn freely with pointer interaction.
- The non-selected part of the image is dimmed while a crop rectangle exists.
- The crop action is disabled until a valid rectangle exists.
- Crop coordinates are mapped from displayed image coordinates to natural image
  dimensions.
- Coordinates are not shown and cannot be entered manually.
- The minimum accepted crop size is 10 by 10 pixels after mapping to natural
  image dimensions.
- The server rejects out-of-bounds, empty, negative, malformed, or too-small
  crop rectangles.
- The server preserves existing embedded metadata exactly as-is when writing the
  cropped image.
- The original image is not modified.
- The gallery refreshes after a successful crop.
- Crop failures show actionable errors.

## Story 3: Blur Painted Regions

As a user, I want to paint regions of an image and blur only those regions so
that I can create a privacy-preserving edited copy.

### User Behavior

1. The user opens the image editor.
2. The user selects `Blur`.
3. The user paints regions over the image.
4. The painted regions use the existing red markup style.
5. The user chooses a Gaussian blur radius in pixels.
6. The user clicks `Blur`.
7. The blurred image is saved as a new uniquely named gallery image.

### Acceptance Criteria

- Blur mode uses brush painting like mask mode.
- Brush size can be adjusted.
- Brush falloff is fixed at 0 percent in blur mode.
- The falloff slider is hidden in blur mode.
- A blur radius slider is shown in blur mode.
- The blur radius slider uses a `px` metric.
- The blur radius range is 0 to 20.
- The blur radius accepts floating-point values.
- The browser sends the painted mask or alpha mask plus the blur radius to the
  backend.
- Brush size affects only mask creation; it is not sent as a blur operation
  parameter.
- The first version does not need a true blur preview.
- The server applies Gaussian blur only to marked regions.
- The server validates blur radius, source filename, and mask payload.
- The server rejects masks that are missing, malformed, empty, or unsafe to
  apply.
- The server preserves existing embedded metadata exactly as-is when writing the
  blurred image.
- The original image is not modified.
- The gallery refreshes after a successful blur.
- Blur failures show actionable errors.

## Story 4: Keep Existing Mask Workflow

As a user, I want the existing mask-generation workflow to remain available so
that the new editor does not remove current image-edit preparation behavior.

### Acceptance Criteria

- `Mask` mode preserves the current mask editor behavior.
- Mask mode still shows brush size and falloff controls.
- Mask mode does not show crop controls.
- Mask mode does not show blur radius controls.
- Existing mask save behavior and endpoint usage remain compatible.
- Existing mask tests continue to pass.

## Story 5: Preserve Gallery And Metadata Expectations

As a user, I want edited images to behave like normal gallery images so that I
can use them in existing workflows.

### Acceptance Criteria

- Cropped and blurred images appear in the local gallery after save.
- New edited images use unique safe filenames.
- Edited image filenames are generated by the server; browser-submitted
  filenames are not trusted.
- Existing embedded metadata is preserved exactly as-is when present.
- If the source image has no embedded metadata, the edited output also has no
  added operation metadata.
- Edited images can be selected as source images for generation where the
  selected model supports edit mode.
- Edited images can be downloaded, deleted, trashed, restored, and loaded for
  metadata using existing gallery workflows.

## Backend Requirements

- Add a crop API endpoint.
- Add a blur API endpoint.
- Keep the existing mask endpoint for mask mode.
- Require CSRF protection for crop and blur requests.
- Reuse existing output-directory confinement and safe filename validation
  boundaries where possible.
- Validate all browser-submitted filenames, dimensions, crop rectangles, masks,
  and blur radius values server-side.
- Store crop and blur outputs under the configured images directory.
- Use collision-safe generated filenames.
- Preserve source embedded metadata exactly as-is.

## Frontend Requirements

- Extend the existing editor overlay into a mode-aware image editor.
- Keep operation-specific controls stable and clear.
- Do not show in-app instructional prose beyond normal labels and controls.
- Use the existing red overlay markup for painted blur regions.
- Use a dimming effect outside the crop rectangle when crop selection exists.
- Keep jsdom tests focused on DOM state, control visibility, payload assembly,
  and action dispatch.
- Manually validate crop rectangle interaction, dimming appearance, blur brush
  interaction, and saved image results in a browser.

## Open Implementation Notes

- Investigate whether the crop dimming effect should be implemented with canvas
  overlay drawing or CSS-backed overlay elements.
- Confirm the existing safe filename and output-directory validation helpers
  before adding crop and blur endpoints.
- Decide ticket breakdown before implementation. A likely order is editor mode
  shell, crop backend, crop UI, blur backend, blur UI, then manual validation.
