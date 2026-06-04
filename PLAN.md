`# Mask Editor Implementation Plan

Source scenario: [SCENARIO.md](SCENARIO.md)

Decision captured from the open questions: implement the first mask editor with native Canvas 2D and no new JavaScript paint dependency.

## Ticket 1: Add Gallery Mask Actions

Status: Completed.

Goal: Let users start mask creation from an eligible gallery image.

Scope:

- Add a mask action button to each supported non-GIF gallery image.
- Include the source image filename and image URL in the button or gallery item data already used by the browser UI.
- Do not expose mask actions for unsupported files.
- Keep existing open, download, metadata, Immich, and delete actions unchanged.

Acceptance criteria:

- Gallery cards for supported images show a mask action.
- Activating the action opens a mask editor overlay without page navigation.
- Existing gallery actions still work.

Test focus:

- Workspace/gallery route renders mask controls for supported images.
- GIF or unsupported files do not receive mask controls.

## Ticket 2: Build the Mask Editor Overlay Shell

Goal: Provide the modal-style editing surface above the current workspace.

Scope:

- Add a hidden overlay element to the workspace template.
- Add open and close behavior in `static/app.js`.
- Show the selected source image inside the overlay at a usable responsive size.
- Dismiss without saving when the user closes the overlay.
- Keep keyboard and touch targets usable on mobile and desktop.

Acceptance criteria:

- Opening the mask action shows the selected image in an overlay.
- Closing the overlay returns to the current workspace without changing gallery files.
- Reopening for a different image shows that image, not stale state from the previous one.

Test focus:

- Server-rendered workspace includes the overlay shell and required data attributes.
- JavaScript behavior should be validated manually in the browser for layout and interaction.

## Ticket 3: Implement Native Canvas Mask Painting

Goal: Let users paint a visible mask over the selected image.

Scope:

- Use native Canvas 2D for the source-image display and mask layer.
- Paint a semi-transparent red glow where the mask is applied.
- Track mask intensity separately from the visible image so export can produce grayscale mask data.
- Support pointer input for mouse, pen, and touch.
- Prevent painting outside the image bounds.

Acceptance criteria:

- Painted areas show a red glow while the underlying image remains visible.
- Unpainted areas remain visually unchanged.
- The mask state survives redraws and responsive resizing while the overlay is open.

Test focus:

- Add focused JavaScript/manual validation notes for pointer painting behavior.
- Keep server tests unaffected; this ticket is primarily browser behavior.

## Ticket 4: Add Brush Controls

Goal: Give users control over mask stroke size and edge falloff.

Scope:

- Add a brush size control.
- Add a brush falloff control for center-to-edge opacity behavior.
- Apply changed control values to future strokes without clearing existing mask data.
- Choose conservative default values that work on touch devices and desktop.

Acceptance criteria:

- Brush size changes affect the painted stroke diameter.
- Falloff changes affect how quickly mask intensity fades from center to edge.
- Existing painted mask areas remain after changing either control.

Test focus:

- Manual browser validation for small, medium, and large brush sizes.
- Manual browser validation that falloff changes visible and exported mask gradients.

## Ticket 5: Add Invert Mask

Goal: Let users swap masked and unmasked areas before saving.

Scope:

- Add an invert mask button to the overlay.
- Invert the internal mask data, not only the red visual overlay.
- Redraw the overlay after inversion.
- Allow repeated inversion.

Acceptance criteria:

- Clicking invert once turns unpainted areas into masked areas and painted areas into unmasked areas.
- Clicking invert twice returns to the previous mask state.
- Saving after inversion exports the inverted mask.

Test focus:

- Unit-test mask data inversion if mask data handling is factored into a small pure helper.
- Manual browser validation for visual inversion.

## Ticket 6: Add Server-Side Mask Save Route

Goal: Persist provider-ready mask PNG files safely under the gallery image directory.

Scope:

- Add a CSRF-protected route for saving mask PNG data for a gallery image.
- Validate the source image filename with the same safety rules as gallery image routes.
- Reject path traversal, leading-dot names, unsupported source extensions, and non-image payloads.
- Decode and validate the submitted mask image server-side.
- Require the mask dimensions to match the selected source image dimensions.
- Save as `<source-stem>-mask.png` in the gallery image directory.
- Do not mutate the source image.

Acceptance criteria:

- Saving creates a PNG named with the source stem plus `-mask.png`.
- Invalid filenames and path traversal are rejected.
- Mismatched mask dimensions are rejected.
- The original gallery image is unchanged.

Test focus:

- Route success path writes the expected mask filename.
- Route rejects unsafe source filenames.
- Route rejects missing source images.
- Route rejects invalid or mismatched mask payloads.
- Route requires CSRF.

## Ticket 7: Export 8-Bit Black-and-White PNG Masks

Goal: Convert the painted mask data into a provider-ready PNG.

Scope:

- Export a PNG with the same pixel dimensions as the source image.
- Write black for unpainted pixels.
- Write white for fully painted pixels.
- Preserve falloff as grayscale values when the brush creates soft edges.
- Ensure the saved file is an 8-bit grayscale-compatible PNG.

Acceptance criteria:

- Fully unpainted mask exports black.
- Fully painted areas export white.
- Soft brush edges export intermediate grayscale values.
- Exported mask dimensions match the source image exactly.

Test focus:

- Unit-test mask data conversion if implemented in a pure helper.
- Server-side image tests verify saved mode/dimensions and representative pixel values.

## Ticket 8: Refresh Gallery After Mask Save

Goal: Make the saved mask immediately available in the gallery.

Scope:

- After a successful save, close or reset the overlay according to the simplest usable behavior.
- Refresh the gallery list so the new `-mask.png` appears.
- Show a success message with the saved filename.
- Show actionable error messages for failed saves.

Acceptance criteria:

- Saved masks appear in the gallery without a full page reload.
- The user sees whether save succeeded or failed.
- Existing gallery selection/edit behavior still works after refresh.

Test focus:

- API route returns enough JSON for the browser to refresh and message correctly.
- Manual browser validation for save, gallery refresh, and error display.

## Ticket 9: Document Mask Workflow

Goal: Explain the new mask creation workflow to users.

Scope:

- Update README user workflow with mask creation steps.
- Mention that masks are saved next to gallery images as `-mask.png`.
- Mention that masks are 8-bit black-and-white PNGs suitable for models that accept masks.
- Keep contributor implementation notes out of README.

Acceptance criteria:

- README describes how to open, paint, invert, and save a mask.
- README documents where the saved mask file appears.

Test focus:

- Documentation-only; no test changes required.
