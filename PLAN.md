# Trashcan Implementation Plan

Source stories: [USER-STORY.md](USER-STORY.md)

## Ticket 1: Add Trash Repository Helpers

Status: Completed.

Goal: Centralize safe filesystem operations for trash listing, counting, restoring, emptying, and purging.

Scope:

- Add helper functions or a small repository for the configured trash directory.
- List only supported local image files.
- Count eligible trash files for the UI label.
- Restore files from trash to the images directory.
- Empty eligible trash files without touching the images directory.
- Purge files older than a caller-provided retention cutoff.
- Reuse existing image filename safety rules where possible.
- Use collision-safe restore behavior instead of overwriting active gallery files.

Acceptance criteria:

- Trash listing and counting ignore unsupported files.
- Restore rejects unsafe filenames, path traversal, leading-dot names, and unsupported extensions.
- Restore never overwrites an existing gallery image.
- Empty trash deletes only eligible files inside the configured trash directory.
- Purge deletes only eligible old files inside the configured trash directory.

Test focus:

- Repository/domain tests for count, list, restore, collision handling, empty, purge, and unsafe filenames.

## Ticket 2: Add Trash Retention Configuration

Status: Completed.

Goal: Make automatic trash retention configurable through `.env`.

Scope:

- Add `TRASHCAN_HOLD_LIMIT_DAYS` to configuration and `.env` generation.
- Default to 7 days.
- Treat invalid values and `0` as disabling automatic purging.
- Expose the parsed value through `AppConfig`.

Acceptance criteria:

- New `.env` files include `TRASHCAN_HOLD_LIMIT_DAYS=7`.
- Missing values use 7 days.
- Invalid values disable automatic purge.
- `0` disables automatic purge.

Test focus:

- Config tests for default, valid custom value, invalid value, and `0`.

## Ticket 3: Purge Old Trash on Gallery Refresh

Status: Completed.

Goal: Automatically delete old trash files whenever the main gallery refreshes.

Scope:

- Run trash purge from the gallery refresh path before returning gallery data.
- Use `TRASHCAN_HOLD_LIMIT_DAYS` to compute the cutoff.
- Skip purge when retention is disabled.
- Include current trash count in the gallery API response.

Acceptance criteria:

- `GET /api/images` purges old trash when retention is enabled.
- Files newer than the retention limit remain in trash.
- Purge does not affect active gallery images.
- API response includes the updated trash count.

Test focus:

- API tests for purge-on-refresh, disabled purge, image-directory safety, and returned count.

## Ticket 4: Add Trash API Routes

Status: Completed.

Goal: Provide JSON endpoints for trash browsing, restore, and empty operations.

Scope:

- Add `GET /api/trash` or equivalent to list trash images and current trash count.
- Add CSRF-protected restore route for a selected trash image.
- Add CSRF-protected empty-trash route.
- Return enough JSON for the browser to update the trash overlay, trash count, and main gallery.
- Keep all filesystem operations confined to configured directories.

Acceptance criteria:

- Trash list returns eligible image files and their display URLs.
- Restore moves one safe trash file back into the images directory.
- Restore returns the restored filename and updated counts.
- Empty trash removes all eligible trash files and returns updated counts.
- Mutating trash routes require CSRF.
- Unsafe filenames and missing files return clear errors.

Test focus:

- Route tests for list, restore success, restore collision handling, restore unsafe/missing names, empty success, empty directory safety, and CSRF.

## Ticket 5: Render Trashcan Button and Overlay Shell

Status: Completed.

Goal: Add the visible trashcan entry point and modal-style trash overlay.

Scope:

- Add a trashcan button next to the palette controls.
- Show the current trash count in the button label.
- Add a hidden overlay pane similar to the mask editor pane.
- Add an `Empty trash` button at the top of the overlay.
- Add an empty-state area and a scrollable trash gallery container.
- Keep the normal generation form and gallery unchanged behind the overlay.

Acceptance criteria:

- The workspace renders a trashcan button next to palette controls.
- The button label includes the trash count.
- The hidden overlay shell is present in the rendered page.
- The overlay contains `Empty trash` and a scrollable trash gallery region.

Test focus:

- Workspace route tests for button, count label data, overlay shell, empty button, and trash gallery container.

## Ticket 6: Implement Trash Overlay Browser Behavior

Status: Completed.

Goal: Let users open, browse, and close the trash overlay without page navigation.

Scope:

- Wire the trashcan button to open the overlay.
- Fetch trash contents when the overlay opens.
- Render trash gallery cards using shared or reusable gallery presentation code where practical.
- Show a clear empty state when trash is empty.
- Close the overlay without changing trash contents.

Acceptance criteria:

- Opening the trashcan shows current trash images.
- Closing the overlay leaves the workspace state intact.
- Trash count and trash gallery state can be refreshed without full page reload.
- Existing main gallery behavior still works.

Test focus:

- Manual browser validation for overlay open/close, trash list rendering, empty state, and unchanged main gallery behavior.

## Ticket 7: Implement Restore from Trash in the Browser

Status: Completed.

Goal: Let users restore individual trash images from the trash overlay.

Scope:

- Add a `Restore` button to each trash gallery item.
- POST restore requests with CSRF.
- Refresh the main gallery after successful restore.
- Refresh the trash gallery and trash count after successful restore.
- Show actionable errors for failed restores.

Acceptance criteria:

- Pressing `Restore` moves the selected image back to the main gallery.
- The restored image appears in the main gallery without a full page reload.
- The trash item disappears from the trash overlay.
- The trash count updates.
- Failed restore keeps the overlay open and shows an error.

Test focus:

- Manual browser validation for restore success, count update, gallery refresh, and error handling.

## Ticket 8: Implement Empty Trash in the Browser

Status: Completed.

Goal: Let users permanently clear trash from the overlay.

Scope:

- Wire the `Empty trash` button to the empty-trash API with CSRF.
- Refresh the trash gallery and trash count after success.
- Preserve the main gallery.
- Show actionable errors for failed empty-trash operations.

Acceptance criteria:

- Pressing `Empty trash` removes all eligible trash images.
- The trash overlay shows the empty state afterward.
- The trashcan label count updates.
- Main gallery images remain unchanged.

Test focus:

- Manual browser validation for empty-trash success, empty state, count update, and gallery safety.

## Ticket 9: Document Trashcan Workflow

Status: Completed.

Goal: Explain trash management to users.

Scope:

- Update README with trashcan button behavior.
- Document restore and empty-trash workflows.
- Document `TRASHCAN_HOLD_LIMIT_DAYS`, default 7 days.
- Document that invalid values and `0` disable automatic purging.
- Keep contributor implementation details out of README.

Acceptance criteria:

- README explains where deleted images go.
- README explains how to restore and empty trash.
- README explains automatic purge timing and configuration.

Test focus:

- Documentation-only; no test changes required.
