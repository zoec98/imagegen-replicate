# Image editor defaults — tickets

## 1. Order image editor operations

Update the user-visible **Edit Image** operation selector so its options are
ordered `Blur`, `Crop`, `Mask`.

Behavior to prove first:

- Opening the image editor exposes those three operation choices in that exact
  order.

Keep the existing initial operation and the operation-specific controls
unchanged; this ticket changes ordering only.

Likely touchpoints: `src/imagegen/templates/index.html`,
`tests/test_workspace_routes.py`, and `tests/js/mask-editor.test.js`.

Verification: add one behavior-focused failing assertion against the rendered
operation list, make the smallest template/fixture adjustment to pass it, then
run `npm run js:check` and `uv run pytest`.

## 2. Default blur radius from the selected image size

When an image finishes loading into the editor, initialize its Blur setting to
`min(max(max(naturalWidth, naturalHeight) / 50, 0), 50)` pixels.

Behavior to prove first:

- A non-square image uses its longer natural pixel dimension, rather than its
  displayed size, to initialize the blur label and submitted blur radius.
- An image whose calculated radius exceeds 50 initializes to 50.
- Opening another image recomputes the default, while an input change remains
  intact for the image currently being edited.

Keep the existing range bounds (`0` through `50`) and precision (`0.1`) intact.
Do not change the server-side blur validation or API payload shape.

Likely touchpoints: `src/imagegen/frontend/mask-editor.js` and
`tests/js/mask-editor.test.js`; regenerate the committed static bundle with
`npm run js:build`.

Verification: use the editor's public `open()` flow with fake images of known
natural dimensions. Add each failing behavior test one at a time, implement
only enough client-side initialization to pass it, then run `npm run js:check`
and `uv run pytest`.
