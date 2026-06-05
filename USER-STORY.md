# User Stories

## Story: Open the Gallery Trashcan

As a user managing generated images, I want a trashcan button next to the palette controls so that I can see and manage images that were moved out of the gallery without leaving the workspace.

Acceptance criteria:

- A trashcan button is visible next to the palette controls.
- The button label shows the current number of files in the configured trash directory.
- Activating the button opens an overlay pane similar to the mask editor pane.
- The overlay can be dismissed without changing the trash contents.
- The normal generation form and gallery remain unchanged behind the overlay.

## Story: Browse Deleted Images

As a user reviewing deleted images, I want the trash overlay to show a scrollable image gallery so that I can inspect deleted files before restoring or permanently removing them.

Acceptance criteria:

- The trash overlay shows an `Empty trash` button at the top.
- Below the `Empty trash` button, the overlay shows a scrollable gallery view of trash images.
- The trash gallery reuses or shares the existing gallery presentation code where practical.
- Each trash image has a `Restore` button below it.
- Empty trash state is clear when there are no trash images.

## Story: Restore an Image from Trash

As a user who deleted an image by mistake, I want to restore a selected image from trash so that it becomes available in the main image gallery again.

Acceptance criteria:

- Pressing `Restore` on a trash item moves that file from the trash directory back to the images directory.
- Restored images appear in the main gallery after refresh without requiring a full page reload.
- The trash count updates after restore.
- Restore validates filenames server-side and does not allow path traversal or leading-dot names.
- If a restored filename would collide with an existing gallery image, the app must use a collision-safe behavior rather than overwriting the existing gallery image.
- `Restore` requires CSRF protection as it is a mutating operation.

## Story: Empty Trash

As a user cleaning up local storage, I want an `Empty trash` button at the top of the open trashcan gallery view so that I can permanently remove all files currently in the trash directory.

Acceptance criteria:

- Pressing `Empty trash` deletes all eligible files in the configured trash directory.
- The main gallery images directory is not affected.
- The trash gallery and trash count update after emptying.
- Empty trash requires CSRF protection.
- Empty trash keeps filesystem operations confined to the configured trash directory.

## Story: Automatically Purge Old Trash

As a user who does not want trash to grow forever, I want old trash files to be removed automatically so that local storage stays bounded.

Acceptance criteria:

- The retention period is configured by `TRASHCAN_HOLD_LIMIT_DAYS`.
- `TRASHCAN_HOLD_LIMIT_DAYS` is read from `.env`.
- The default retention period is 7 days.
- Files older than the configured number of days are permanently deleted whenever the main gallery refreshes.
- Automatic purge only deletes files inside the configured trash directory.
- Purging old trash updates the trash count exposed to the browser.
- Invalid retention configuration or the value `0` mean that no automatic purging occurs.
