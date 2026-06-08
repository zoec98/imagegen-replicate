# Gallery Cleanup Test Notes

## Ticket 7 Coverage

Added outside-in coverage to the existing workspace render test for the
server-rendered main gallery shared layout contract:

- `.gallery.image-gallery`
- `.gallery-item.image-card`
- `.image-card-media`
- `.image-card-ribbon`

This protects the initial page render without coupling tests to visual pixel
layout.

## Remaining Gap

The JavaScript-created cards from `imageFigure()`, `trashFigure()`, and
`immichAssetFigure()` are not directly inspected by Python tests. The existing
Python tests already cover the API payloads and server-rendered hooks those
functions consume, but they do not execute browser DOM construction.

Do not add a one-off JavaScript test toolchain for this cleanup. Cover these
functions with DOM tests when the broader JavaScript refactor introduces
Vitest/jsdom or equivalent browser-side test support.
