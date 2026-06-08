# Gallery Cleanup Analysis

## Current State

The three visible gallery-like views are implemented with partially shared
pieces, but they do not share one layout contract.

### Main Generated Images Gallery

The main view is server-rendered in `src/imagegen/templates/index.html` and
re-rendered after API refreshes by `imageFigure()` in `src/imagegen/static/app.js`.
Both paths emit the same basic card shape:

- `.gallery` as the grid container.
- `.gallery-item` as the image card.
- an image link as the square media area.
- `.source-select` overlay for edit-source selection.
- `figcaption` containing `.gallery-actions`.
- icon-sized `.gallery-action` buttons and links.

The layout is mostly governed by the shared CSS around
`src/imagegen/static/app.css` lines 1046-1280:

- `.gallery` starts as one column.
- `.gallery-item a` owns the `aspect-ratio: 1 / 1` square.
- `.gallery-item img` uses `height: 100%`, `width: 100%`, and
  `object-fit: contain`.
- `.gallery-actions` is a flex ribbon.
- media queries switch `.gallery` to three columns at `48rem`, and to
  `repeat(auto-fill, minmax(16rem, 1fr))` at `78rem`.

This is the stable behavior the other views should copy: variable columns, a
stable square image area, and a fixed action ribbon underneath.

### Trash Gallery

The trash overlay is server-rendered only as an empty shell in
`src/imagegen/templates/index.html`; its cards are created by `trashFigure()` in
`src/imagegen/static/app.js` lines 1962-2012.

Trash cards intentionally reuse some main gallery classes:

- cards use `class="gallery-item trash-item"`;
- action buttons use `.gallery-actions`, `.gallery-action`, `.gallery-info`,
  and the shared info tooltip structure;
- image sizing inherits from `.gallery-item a` and `.gallery-item img`.

Trash then adds local CSS overrides at `src/imagegen/static/app.css` lines
678-701:

- `.trash-gallery` is a separate grid container;
- `.trash-item` becomes a grid with `grid-template-rows: minmax(0, 1fr) auto`;
- `.trash-item a` adds `min-height: 0`;
- `.trash-item figcaption` sets `min-height: 3rem`.

The likely instability comes from the combination of a scroll-limited overlay
grid, row sizing with `minmax(0, 1fr)`, and fixed caption height. When many
items are present, the card body can shrink while the caption remains stable.
The media area technically still has an aspect ratio rule, but the trash item
row model is fighting the simpler main-gallery card model.

Trash also inherits the same fixed breakpoint behavior as the main gallery:
`1fr`, then exactly three columns at `48rem`, then `auto-fill` only above
`78rem`. On iPad-sized widths this can leave the view stuck at three columns
instead of using the available pane width more fluidly.

### Upload / Immich Gallery

The upload overlay's Immich browser uses a separate implementation. Cards are
created by `immichAssetFigure()` in `src/imagegen/static/app.js` lines 609-660,
not by the main `imageFigure()` or trash `trashFigure()` path.

The DOM and CSS are distinct:

- `.upload-immich-gallery` is a separate grid container.
- `.upload-immich-item` is a separate card class, not `.gallery-item`.
- the image is a direct child of the figure, not wrapped by the shared square
  `.gallery-item a` media element.
- the footer uses custom metadata text plus `.upload-immich-import`, not
  `.gallery-actions`.
- CSS at `src/imagegen/static/app.css` lines 899-986 sets its own grid,
  row sizing, image sizing, footer sizing, and button styling.

The upload grid is already `repeat(auto-fill, minmax(10rem, 1fr))` on normal
widths, but switches to exactly two columns below `40rem`. Its card uses
`grid-template-rows: minmax(0, auto) 3.75rem`, and the image owns its own
`aspect-ratio`. This is close to the desired shape, but it is not the same
shape as the main gallery and can still behave differently under constrained
overlay height.

## Assessment

Yes, these views are implemented differently.

The main and trash views partially share card styles, but trash overrides the
card row model. The upload Immich view is a separate card and ribbon
implementation. The current CSS therefore has three gallery contracts:

- main gallery: `.gallery` plus `.gallery-item`;
- trash gallery: `.trash-gallery` plus `.gallery-item.trash-item`;
- upload Immich gallery: `.upload-immich-gallery` plus `.upload-immich-item`.

This makes the inconsistent resize behavior unsurprising. The markup and CSS do
not express one reusable "gallery grid with square media cell and fixed action
ribbon" component.

## Recommended Direction

Refactor toward one shared gallery/card contract, but keep the implementation
small and CSS-first.

Recommended shared structure:

- `.image-gallery` for any grid of image cards.
- `.image-card` for the repeated figure/card.
- `.image-card-media` for the fixed square image area.
- `.image-card-media img` with `object-fit: contain` by default.
- `.image-card-ribbon` for the footer/action ribbon.
- modifier classes only for behavior or small visual differences, for example
  `.image-gallery-main`, `.image-gallery-trash`, `.image-gallery-immich`,
  `.image-card-selected`, or `.image-card-thumbnail-error`.

Recommended grid behavior:

- Use `grid-template-columns: repeat(auto-fill, minmax(min(16rem, 100%), 1fr))`
  or a close variant for the main and trash views.
- Use a smaller minimum only where the product intentionally wants denser
  external-source browsing, for example `minmax(min(10rem, 100%), 1fr)` for
  Immich upload.
- Remove fixed intermediate column counts such as exactly three columns at
  `48rem` and exactly two upload columns under `40rem` unless testing proves
  they are needed.
- Keep the square media area outside any `1fr` row compression pattern. The
  card should be normal block/grid flow: square media first, ribbon second.
- Keep overlay scroll on the gallery container or pane, but do not make each
  card consume a fractional row height from the viewport.

Recommended DOM changes:

- Keep existing behavior hooks where tests or event handlers depend on them:
  `.gallery-item`, `.trash-item`, `.upload-immich-item`, `.gallery-actions`,
  `.trash-restore`, `.upload-immich-import`, and data attributes can remain as
  compatibility classes during the first pass.
- Add shared classes alongside existing classes, rather than renaming all
  selectors in one step.
- Extract tiny DOM helpers inside the current `app.js` before introducing a
  build system:
  `createImageCard()`, `createImageMedia()`, `createActionRibbon()`, and
  `createInfoAction()`.
- Let `imageFigure()`, `trashFigure()`, and `immichAssetFigure()` compose those
  helpers with different action sets.

Recommended CSS changes:

- Introduce shared card/grid/media/ribbon rules near the existing gallery CSS.
- Make `.gallery`, `.trash-gallery`, and `.upload-immich-gallery` opt into the
  shared grid rules.
- Make `.gallery-item`, `.trash-item`, and `.upload-immich-item` opt into the
  shared card rules.
- Delete or neutralize the unstable trash row overrides:
  `.trash-item { grid-template-rows: minmax(0, 1fr) auto; }` and
  `.trash-item a { min-height: 0; }`.
- Convert the upload image element to use a shared media wrapper, or at least
  apply the same media contract to its direct image until the DOM helper exists.

## Suggested Tickets

1. Add shared gallery CSS and migrate class usage without removing existing
   behavior hooks.
2. Refactor `imageFigure()`, `trashFigure()`, and `immichAssetFigure()` to share
   card/media/info/action helpers inside `app.js`.
3. Update server-rendered main gallery markup to include the shared classes so
   initial render and API refresh render the same card contract.
4. Add or update focused tests for expected markup hooks in main gallery, trash
   API rendering path, and Immich upload rendering path where practical.
5. Browser-check desktop, iPad/tablet width, and mobile width with enough items
   to force scrolling in trash and upload overlays.

## JS Refactor Recommendation

Do not process `development/refactors/2026-06-07-js-refactor.md` before fixing
the gallery layout.

That proposal is directionally useful, but it is a larger toolchain and source
layout change: Vite, Vitest, jsdom, ESLint, Prettier, a new `package.json`, and
module extraction. The gallery problem is narrower and mostly caused by CSS and
small DOM construction differences. Fixing the gallery first reduces user-facing
layout pain without coupling it to build-system churn.

The better sequence is:

1. Fix the gallery layout with small shared CSS and local DOM helper extraction
   in the current no-build `app.js`.
2. Verify the three gallery variants in the browser.
3. Then process the JavaScript refactor as its own epic, using the new shared
   gallery helper shape as one of the first modules to extract.

Only reverse that order if the gallery fix expands into broad `app.js` surgery.
At the current observed scope, it should not.

## Risks And Gaps

- The upload Immich gallery has different product needs than local generated
  images: it shows external assets with size/date metadata and an import action.
  It should share the card geometry, not necessarily every visual detail.
- The main gallery is both server-rendered and JavaScript-rendered after
  refresh. Any shared class migration must update both paths.
- Tooltip behavior depends on `.image-info-wrap` and `.image-info-tooltip`; keep
  those selectors stable during the first pass.
- Source image selection depends on `.gallery-item` and `.source-select`; keep
  those selectors stable for the main gallery.
- Visual verification matters because this bug is layout-sensitive and may not
  be fully covered by Python route tests.
