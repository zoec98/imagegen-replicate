# Gallery Cleanup Audit

## Summary

The gallery cleanup epic unified the generated image gallery, trash gallery, and
Upload/Immich gallery around a shared card layout contract:

- responsive gallery grids;
- fixed square media cells;
- images contained or cropped according to the view's product need;
- fixed action/metadata ribbons underneath each image;
- existing workflow-specific behavior hooks preserved.

The implementation kept the current no-build JavaScript setup and did not
process the broader JavaScript toolchain refactor.

## Implemented Tickets

- Ticket 1: Added shared CSS layout rules for `.image-gallery`, `.image-card`,
  `.image-card-media`, and `.image-card-ribbon`; removed unstable fixed-column
  and row-compression behavior; kept Upload/Immich denser than the main gallery.
- Ticket 2: Updated the server-rendered main gallery markup to emit the shared
  class structure.
- Ticket 3: Updated JavaScript-rendered main gallery cards to match the
  server-rendered shared structure.
- Ticket 4: Updated trash gallery cards to use the shared card/media/ribbon
  structure while preserving restore behavior.
- Ticket 5: Updated Upload/Immich cards to use the shared structure while
  preserving the accepted denser tile size and thumbnail crop behavior.
- Ticket 6: Extracted minimal shared DOM helpers inside `app.js` without adding
  build tooling.
- Ticket 7: Added outside-in server-rendered markup assertions and documented
  the remaining JS-created DOM test gap.
- Ticket 8: Recorded visual verification and closeout notes.

## Verification

Automated checks run during the epic:

- `uv run pytest` passed with 376 tests.
- `uv run ruff check src tests` passed.

Browser verification:

- The user visually checked resizing behavior for all three galleries:
  main gallery, trash gallery, and Upload/Immich gallery.
- The user accepted the visual result for all three galleries.
- A double scrollbar can still appear in Upload at some sizes. The user marked
  that as good enough for this epic.

## Decisions

- Keep Upload/Immich thumbnail browsing denser than the main gallery by using a
  smaller tile minimum.
- Keep Upload/Immich thumbnails cropped with `object-fit: cover`; generated and
  trash images use contained image display.
- Keep the trash Restore action as a text button for now.
- Preserve legacy selectors as compatibility hooks while adding the shared class
  vocabulary.
- Defer JS DOM tests for `imageFigure()`, `trashFigure()`, and
  `immichAssetFigure()` until the broader JavaScript refactor introduces a DOM
  test environment such as Vitest/jsdom.
