# Click Image Info Popover Tickets

Source stories: `development/2026-07-07-click-info-popover/user-stories.md`.

## TDD Approach

Implement this epic as vertical red-green-refactor slices. Each ticket starts
with one behavior-level failing test through the browser JavaScript public setup
path, then adds only the implementation needed to pass that behavior before
moving to the next ticket.

Prefer jsdom tests that exercise `setupGallery()` and `setupMetadata()` through
rendered gallery DOM and user events. Avoid tests that assert private helper
calls or internal state that users cannot observe.

## Ticket 1: Open Image Info On Click

Status: Complete.

### User Story

As a gallery user, I want clicking the image information button to open the
image information box, so that I can inspect image metadata without depending
on hover behavior.

### Red Test

Add one failing Vitest test proving that clicking `.gallery-info` opens the
image information box and fills it with the same metadata lines currently shown
by the tooltip: filename, model, dimensions, and prompt.

### Green Scope

- Change the image information interaction from hover-driven display to
  click-controlled display.
- Preserve the existing metadata fetch/cache behavior used by
  `refreshTooltip()`.
- Keep the existing server-rendered and JavaScript-rendered action markup
  compatible.
- Ensure the open box remains visible after pointer movement away from the
  `(i)` button.

### Acceptance Criteria

- Clicking `(i)` opens a visible information box.
- The box shows filename, resolved model display name, dimensions, and prompt.
- Missing metadata still shows the existing unavailable fallback text.
- Pointer hover is not required to keep the box visible.

### Verification

- Add failing Vitest test before implementation.
- `npm run js:check`

### Implementation Notes

- Added a gallery integration-style Vitest test that wires `setupGallery()` to
  `setupMetadata()` and verifies click-open metadata text.
- Added `.image-info-open` as the visible information-box state.
- Removed hover/focus metadata refresh listeners from the gallery behavior.
- Changed tooltip visibility CSS to depend on `.image-info-open` rather than
  `:hover`.

## Ticket 2: Toggle And Active State

Status: Complete.

### User Story

As a gallery user, I want the active `(i)` button to look highlighted and close
on a second click, so that I can tell which image information box is open and
dismiss it without a separate close control.

### Red Test

Add one failing Vitest test proving that the first click marks the info button
active and the second click closes the box and removes the active state.

### Green Scope

- Add an active class or attribute for an open info button.
- Style the active `(i)` button consistently with existing gallery action
  states, such as armed delete or uploaded Immich.
- Toggle the same box closed on a second click.
- Keep the state synchronized when the gallery refreshes.

### Acceptance Criteria

- First click opens the box and highlights the `(i)` button.
- Second click on the same `(i)` closes the box.
- Closing restores the normal button appearance.
- The active state is removed when its box closes.

### Verification

- Add failing Vitest test before implementation.
- `npm run js:check`

### Implementation Notes

- Added a repeated-click Vitest test for opening, active state, and closing.
- Added `.gallery-info-active` to the active `(i)` button while its box is
  open.
- A second click on the same `(i)` now closes the information box and removes
  the active state.

## Ticket 3: Only One Info Box Open

Status: Complete.

### User Story

As a gallery user, I want opening another image information box to close the
previous one, so that the gallery does not accumulate overlapping metadata
boxes.

### Red Test

Add one failing Vitest test with two gallery items proving that opening the
second item closes the first item and transfers the active state to the second
button.

### Green Scope

- Track the currently open info action at the gallery behavior boundary.
- Close any previously open information box before opening a new one.
- Avoid coupling tests to private variables; verify only DOM visibility and
  active state.

### Acceptance Criteria

- Opening image B closes image A's information box.
- Image A's `(i)` button returns to normal state.
- Image B's information box is visible and its `(i)` button is active.

### Verification

- Add failing Vitest test before implementation.
- `npm run js:check`

### Implementation Notes

- Added a two-image Vitest test proving a newly opened info box closes the
  previous one.
- Added a gallery-level `closeInfoBoxes()` helper that removes open and active
  state from other info controls before opening a new one.

## Ticket 4: Selectable Information Text

Status: Complete.

### User Story

As a gallery user, I want the text inside the information box to be selectable,
so that I can use normal browser copy behavior such as `Cmd-C`.

### Red Test

Add one failing Vitest or DOM-focused test proving that the open information
box exposes selectable text content and does not render controls that interfere
with prompt selection.

### Green Scope

- Ensure tooltip/popover CSS allows text selection inside the information box.
- Ensure clicking and dragging inside the information box does not close it.
- Preserve text content as normal DOM text, not canvas, SVG-only, or
  inaccessible title text.

### Acceptance Criteria

- Filename, model, dimensions, and prompt are normal selectable text.
- User selection inside the box does not close the box.
- Standard browser copy can operate on selected text.

### Verification

- Add failing Vitest test before implementation where jsdom can observe the
  behavior.
- Browser smoke test text selection in Safari or another browser where the
  hover bug reproduced.
- `npm run js:check`

### Implementation Notes

- Added a Vitest test that verifies opened info text is marked selectable and
  does not close during text interaction.
- Added `image-info-selectable` to server-rendered, gallery-rendered, and
  trash-rendered info boxes.
- Added CSS for normal text selection and text cursor inside info boxes.

## Ticket 5: Remove Clipboard Copy Button

Status: Planned.

### User Story

As a gallery user, I do not want a special copy prompt button in the
information box, so that the UI relies on normal selectable text behavior
instead of clipboard API permissions.

### Red Test

Add one failing Vitest test proving that an open information box with prompt
metadata does not render `.tooltip-copy-prompt` and does not require
`navigator.clipboard`.

### Green Scope

- Remove the copy prompt button from metadata rendering.
- Remove the `navigator.clipboard.writeText()` click path for this interaction.
- Remove copied-state UI styling and generated bundle output.
- Keep prompt text visible and selectable in the information box.

### Acceptance Criteria

- No copy prompt button appears when prompt metadata exists.
- The information interaction works when `navigator.clipboard` is unavailable.
- No copied confirmation state appears for prompt copying.

### Verification

- Add failing Vitest test before implementation.
- `npm run js:check`

## Ticket 6: Rebuild Assets And Run Full Checks

Status: Planned.

### User Story

As a maintainer, I want generated browser assets and project checks to match
the source changes, so that end users can run the Flask app without Node and
the change is safe to ship.

### Red Test

No new behavior test. This ticket is a final integration and verification pass
after tickets 1-5 are green.

### Green Scope

- Rebuild `src/imagegen/static/app.js` and `src/imagegen/static/app.js.map`.
- Remove obsolete CSS selectors for the copy prompt button if they are no
  longer used.
- Confirm no hover-only info behavior remains in CSS or JavaScript.
- Run required project checks.

### Acceptance Criteria

- Generated JavaScript matches frontend source.
- No stale copy-button CSS remains.
- Existing gallery behavior outside image info still works.
- The final diff contains source, generated asset, style, and test updates
  needed for the feature.

### Verification

- `npm run js:format`
- `npm run js:check`
- `uv run pytest`
- `uv run ruff check src tests`
