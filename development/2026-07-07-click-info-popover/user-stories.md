# Click Image Info Popover

## Epic

Replace the image information hover tooltip with a click-controlled information
popover so users can reliably inspect and copy image metadata text with normal
text selection and keyboard copy.

## User Stories

### Open Image Information

As a gallery user,
I want clicking the image information button to open the image information box,
so that I can inspect image metadata without depending on hover behavior.

Acceptance criteria:

- Clicking the `(i)` image information button opens a visible information box.
- The information box contains the same information currently shown in the hover
  tooltip: filename, model, dimensions, and prompt or unavailable fallbacks.
- Opening the box loads metadata as the current hover behavior does.
- The box remains open when the pointer moves away from the `(i)` button.

### Show Active State

As a gallery user,
I want the active `(i)` button to look highlighted,
so that I can tell which image information box is open.

Acceptance criteria:

- When an image information box is open, its `(i)` button is visually active.
- The active treatment follows existing gallery action patterns, similar to the
  Immich uploaded state or armed delete state.
- The active state is removed when the information box closes.

### Close Image Information

As a gallery user,
I want clicking the active `(i)` button a second time to close the information
box,
so that I can dismiss metadata without needing a separate close control.

Acceptance criteria:

- A second click on the same active `(i)` button closes its information box.
- Closing the box restores the `(i)` button to its normal state.
- Opening another image information box closes any previously open image
  information box.

### Select And Copy Text

As a gallery user,
I want the text inside the information box to be selectable,
so that I can use normal browser copy behavior such as `Cmd-C`.

Acceptance criteria:

- The filename, model, dimensions, and prompt text can be selected with the
  pointer.
- Standard keyboard copy works on selected text.
- The information box does not close while selecting text inside it.
- The implementation does not use a dedicated copy prompt button.

### Remove Copy Prompt Button

As a gallery user,
I do not want a special copy prompt button in the information box,
so that the UI relies on normal selectable text behavior instead of clipboard
API permissions.

Acceptance criteria:

- The information box does not render a copy prompt button.
- No click handler calls `navigator.clipboard.writeText` for this interaction.
- The UI does not show copied-state text for prompt copying.

