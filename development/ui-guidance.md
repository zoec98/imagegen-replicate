# UI And Browser JavaScript Guidance

This file is for contributor-facing UI implementation notes. End-user usage
belongs in `README.md`.

## JavaScript Source Layout

Browser JavaScript source lives in `src/imagegen/frontend/`.

- `main.js`: workspace bootstrap and cross-module wiring.
- `api.js`: shared `fetch`, JSON, and CSRF request helpers.
- `dom.js`: small DOM construction and attribute helpers.
- Workflow modules such as `gallery.js`, `metadata.js`, `trash.js`,
  `palettes.js`, `source-images.js`, `generation.js`, `mask-editor.js`, and
  `image-upload.js`: own one browser workflow each.

Keep module interfaces small. Prefer `setupX(root, services)` functions that
bind DOM events, read server-rendered data hooks, and receive cross-workflow
behavior through explicit service callbacks.

## Generated Browser Bundle

The Flask template serves `/static/app.js`, generated from
`src/imagegen/frontend/main.js` by Vite.

Do not edit these files directly:

- `src/imagegen/static/app.js`
- `src/imagegen/static/app.js.map`

Run `npm run js:build` or `npm run js:check` after changing frontend source.
Keep the generated bundle committed so running the Flask app does not require
Node.

## JavaScript Checks

Use these commands for browser JavaScript changes:

```bash
npm run js:format
npm run js:check
```

`npm run js:check` runs ESLint, Vitest with jsdom, and the Vite build.

Node is a development requirement only for JavaScript changes. Python-only work
and normal Flask app runtime do not require Node.

## Testing Expectations

Put DOM behavior tests under `tests/js/`. Prefer tests that exercise visible DOM
state, dispatched events, and mocked network boundaries through public module
setup functions.

Use jsdom for fast workflow coverage. Keep manual browser validation notes for
behavior jsdom cannot represent reliably, such as canvas drawing fidelity,
browser-specific file input behavior, or visual layout.
