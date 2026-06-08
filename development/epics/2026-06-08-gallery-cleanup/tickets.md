# Gallery Cleanup Tickets

## Goal

Merge the main gallery, trash gallery, and upload/Immich gallery around one
shared layout contract where it makes sense:

- variable column grid;
- fixed square media cell;
- image fit inside the square cell;
- fixed ribbon underneath;
- existing workflow-specific actions preserved.

Keep the work incremental. Do not process the broad JavaScript build-system
refactor before this gallery cleanup unless the gallery work unexpectedly grows
into broad `app.js` surgery.

## Ticket 1: Introduce Shared Gallery Layout CSS

### User Story

As a user browsing generated, trashed, or importable images, I want gallery
cards to resize consistently across desktop, iPad/tablet, and mobile widths so
images do not collapse while action ribbons remain usable.

### Scope

- Add shared CSS classes for the common card contract:
  `.image-gallery`, `.image-card`, `.image-card-media`, and
  `.image-card-ribbon`.
- Keep existing selector hooks during the first pass:
  `.gallery`, `.trash-gallery`, `.upload-immich-gallery`, `.gallery-item`,
  `.trash-item`, `.upload-immich-item`, `.gallery-actions`, `.trash-restore`,
  and `.upload-immich-import`.
- Make `.gallery`, `.trash-gallery`, and `.upload-immich-gallery` opt into the
  shared grid behavior.
- Make `.gallery-item`, `.trash-item`, and `.upload-immich-item` opt into the
  shared card behavior.
- Remove or neutralize the trash-specific row compression:
  `.trash-item { grid-template-rows: minmax(0, 1fr) auto; }` and
  `.trash-item a { min-height: 0; }`.
- Remove fixed intermediate column counts where they fight responsive behavior,
  especially exactly three columns at `48rem` and exactly two upload columns
  under `40rem`, unless browser verification proves a fixed count is still
  needed.

### Acceptance Criteria

- Main gallery and trash gallery use a responsive `auto-fill` or equivalent
  grid with a minimum card size close to `16rem`.
- Upload/Immich gallery uses the same layout contract with a denser minimum
  card size, close to `10rem`, unless product review decides otherwise.
- Each image card has a square media region whose size is driven by column
  width, not by viewport-height row compression.
- The action/footer ribbon sits below the media region and does not overlap the
  image.
- Existing click handlers and tests that rely on legacy classes continue to
  work.

### Verification

- `uv run pytest`
- `uv run ruff check src tests`
- Browser-check main, trash, and upload galleries at mobile, iPad/tablet, and
  desktop widths.

## Ticket 2: Update Server-Rendered Main Gallery Markup

### User Story

As a maintainer, I want the initial server-rendered main gallery and the
JavaScript-refreshed main gallery to emit the same card structure so visual
fixes do not drift between first load and refresh.

### Scope

- Update `src/imagegen/templates/index.html` main gallery markup to include the
  shared layout classes.
- Preserve existing main-gallery behavior hooks:
  `.gallery`, `.gallery-item`, `.source-select`, `.gallery-actions`,
  `.gallery-action`, `.gallery-info`, `.gallery-load`, `.gallery-download`,
  `.gallery-download-clean`, `.gallery-mask`, `.gallery-immich`, and
  `.gallery-delete`.
- Wrap or classify the square image link as the shared media element.
- Classify the `figcaption` or contained action area as the shared ribbon
  element.

### Acceptance Criteria

- The initial generated-images gallery uses the shared media/ribbon class
  structure.
- Existing data attributes for delete, mask, metadata, content type, and Immich
  upload remain intact.
- Source image selection still has the same DOM hooks and visual behavior.
- Empty-gallery rendering remains unchanged.

### Verification

- Python route/template tests continue to pass.
- Browser-check a fresh page load before any gallery refresh.

## Ticket 3: Refactor Main Gallery JavaScript Rendering To Match Markup

### User Story

As a user generating or deleting images, I want the refreshed gallery to look
and behave exactly like the initial gallery.

### Scope

- Update `imageFigure()` in `src/imagegen/static/app.js` to emit the shared
  layout classes used by the server-rendered markup.
- Keep all existing behavior and state:
  metadata load, downloads, clean download, mask creation, optional Immich
  upload, delete confirmation, source selection, tooltip refresh, and data
  attributes.
- Introduce small local helper functions only where they remove duplication
  without forcing the larger Vite/module refactor.

### Acceptance Criteria

- Main-gallery cards created by `imageFigure()` match the shared media/ribbon
  structure used by `index.html`.
- The order of main-gallery actions remains:
  Info, Load Prompt/metadata, Download with metadata, Download clean, Mask,
  optional Immich upload, Trash.
- Refreshing the gallery after generation, deletion, restore, or import does
  not change card geometry.

### Verification

- `uv run pytest`
- Manual generation does not need a provider call; use existing gallery refresh
  paths or fixture data where possible.
- Browser-check gallery refresh after a delete-to-trash and restore round trip.

## Ticket 4: Migrate Trash Gallery Onto Shared Card Structure

### User Story

As a user managing the trashcan, I want trashed images to use the same stable
thumbnail geometry as the main gallery, even with many items or on iPad/tablet
widths.

### Scope

- Update `trashFigure()` in `src/imagegen/static/app.js` to add the shared card,
  media, and ribbon classes.
- Preserve trash-specific hooks:
  `.trash-item`, `.trash-restore`, restore URL data attributes, filename data
  attributes, and `.image-info-*` tooltip classes.
- Keep the trash action set intentionally smaller:
  Info, spacer/flexible area, Restore.
- Make the Restore control visually fit into the shared ribbon without causing
  the image area to shrink.
- Ensure the trash grid uses the shared responsive grid contract rather than
  fixed columns on tablet widths.

### Acceptance Criteria

- Trash cards have square media cells and fixed ribbons with many items.
- The number of trash columns responds to pane width, not only hard breakpoints.
- Restore still works and refreshes both trash and main gallery.
- Empty-trash state and empty-trash button behavior remain unchanged.

### Verification

- Existing trash API/route tests continue to pass.
- Browser-check trash overlay with enough items to require scrolling.
- Browser-check at tablet/iPad width where the bug was observed.

## Ticket 5: Migrate Upload/Immich Gallery Onto Shared Card Geometry

### User Story

As a user importing from Immich, I want the upload gallery to use the same stable
thumbnail geometry as the local galleries while keeping its size/date metadata
and import button.

### Scope

- Update `immichAssetFigure()` in `src/imagegen/static/app.js` to use or emulate
  the shared card/media/ribbon structure.
- Decide whether to wrap the thumbnail image in `.image-card-media` or apply
  the shared media contract to the existing direct image in a compatibility
  pass.
- Preserve upload-specific hooks:
  `.upload-immich-item`, `.upload-immich-metadata`, `.upload-immich-size`,
  `.upload-immich-date`, `.upload-immich-import`, asset ID data attributes, and
  thumbnail error state.
- Keep the upload action/metadata ribbon:
  Size/Date, Import into images directory.
- Retain a denser card minimum than the main gallery if that remains useful for
  browsing external assets.

### Acceptance Criteria

- Upload/Immich cards have square media cells and fixed ribbons.
- Image sizing is consistent and does not compress unexpectedly under overlay
  scroll constraints.
- Size/date text truncates or wraps cleanly without forcing layout shifts.
- Import buttons remain touch-friendly and do not overlap metadata text.
- Thumbnail error styling still applies.

### Verification

- Existing Immich import/upload tests continue to pass.
- Browser-check upload overlay at mobile, iPad/tablet, and desktop widths.
- Browser-check with a page of many Immich assets, including one failed
  thumbnail if practical.

## Ticket 6: Extract Minimal Shared DOM Helpers

### User Story

As a maintainer, I want the three JavaScript-rendered gallery card paths to
share obvious construction helpers so future action changes do not recreate the
same layout bug in one view.

### Scope

- Add small helpers inside the current no-build `src/imagegen/static/app.js`.
- Candidate helpers:
  `createImageCard()`, `createImageMedia()`, `createActionRibbon()`,
  `createInfoAction()`, and possibly `createSvgIcon()`.
- Use those helpers in `imageFigure()`, `trashFigure()`, and
  `immichAssetFigure()` where the structures are genuinely shared.
- Do not introduce Vite, modules, `package.json`, Vitest, ESLint, or Prettier
  as part of this ticket.

### Acceptance Criteria

- Shared layout DOM is built in one place for JavaScript-rendered cards.
- Workflow-specific actions remain clear at the call sites.
- The helper extraction does not change behavior beyond the intended layout
  class/structure changes.
- The helper shape is suitable for later extraction into a `gallery.js` module
  if the broader JavaScript refactor proceeds.

### Verification

- `uv run pytest`
- `uv run ruff check src tests`
- Browser smoke test for gallery refresh, trash restore, and Immich import.

## Ticket 7: Add Focused Markup And Behavior Coverage

### User Story

As a maintainer, I want tests to protect the shared gallery contract enough that
future changes do not silently split the three views again.

### Scope

- Add or update Python tests for server-rendered main-gallery markup where
  existing test patterns support it.
- Add or update tests around API-rendered data hooks that JavaScript relies on,
  especially trash and Immich asset payloads.
- If the current Python test stack cannot reasonably inspect JavaScript-created
  DOM, document that limitation in the test or epic notes rather than adding a
  heavy JS toolchain in this ticket.
- Do not add the JS build/test tooling from
  `development/refactors/2026-06-07-js-refactor.md` just for this cleanup.

### Acceptance Criteria

- Tests protect the server-rendered main gallery's shared classes and required
  behavior hooks.
- Existing trash and Immich tests still prove required URLs/data are available
  to JavaScript rendering.
- Any remaining test gap for JavaScript-created DOM is explicitly noted.

### Verification

- `uv run pytest`
- `uv run ruff check src tests`

## Ticket 8: Browser Verification And Follow-Up Audit

### User Story

As a user on touch and desktop devices, I want the merged gallery layout to be
visibly stable in the workflows where the bug was reported.

### Scope

- Run the Flask development server with `scripts/run-dev.sh`.
- Verify the main gallery, trash overlay, and upload overlay in the browser.
- Check representative widths:
  mobile, iPad/tablet, desktop, and wide desktop.
- Check many-item states for trash and upload where scrolling is required.
- Record the outcome and any follow-up tickets in this epic directory.

### Acceptance Criteria

- Main gallery remains stable and does not regress.
- Trash gallery uses variable columns and fixed square media cells with a fixed
  ribbon underneath.
- Upload/Immich gallery uses variable columns and fixed square media cells with
  a fixed ribbon underneath.
- No text overlaps controls or escapes ribbons at the tested widths.
- Any remaining product tradeoffs are captured as follow-up notes or tickets.

### Verification

- `uv run pytest`
- `uv run ruff check src tests`
- `scripts/run-dev.sh`
- Browser screenshots or written notes for tested widths.

## Open Questions, Decisions, And Recommendations

### Open Questions

- Should the upload/Immich gallery use `object-fit: contain` like the generated
  image gallery, or `object-fit: cover` for denser external-source browsing?
- Should upload/Immich keep a smaller minimum card width than local generated
  and trash galleries?
- Should the trash Restore button remain a text button, or should it become an
  icon-sized gallery action to match the main ribbon more closely?
- Should the main gallery's middle breakpoint of exactly three columns be
  removed immediately, or should the first pass only change trash and upload?
- Is there a preferred iPad/tablet target width that should be treated as the
  canonical manual verification size?

### Necessary Decisions

- Adopt a shared gallery class vocabulary:
  `.image-gallery`, `.image-card`, `.image-card-media`, and
  `.image-card-ribbon`.
- Preserve legacy classes as compatibility hooks during the initial cleanup.
- Use responsive `auto-fill` grids instead of fixed intermediate column counts
  unless browser verification shows a specific fixed breakpoint is needed.
- Keep the gallery cleanup independent from the broad JavaScript toolchain
  refactor.
- Treat visual browser verification as required because the bug is
  layout-sensitive.

### Recommendations

- Start with Ticket 1 and Ticket 4 together if the immediate pain is trash
  compression; they are the smallest direct fix.
- Include Ticket 2 and Ticket 3 in the same short workstream so initial render
  and refresh render do not drift.
- Do Ticket 5 after the local gallery/trash contract is stable, because upload
  has legitimate product differences around external asset browsing.
- Do Ticket 6 only after the CSS/markup direction is proven in the browser.
- Defer `development/refactors/2026-06-07-js-refactor.md` until after these
  tickets land; use the final helper shape from this work as input to that
  larger refactor.
