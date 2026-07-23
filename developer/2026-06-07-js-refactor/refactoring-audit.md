# JavaScript Refactor Proposal - 2026-06-07

## Summary

`src/imagegen/static/app.js` is currently a single no-build browser script of
about 2,100 lines. That has kept runtime deployment simple, but it makes testing
and maintenance harder as workflows accumulate: provider/model switching,
palette editing, source image selection, mask editing, gallery actions, trash,
Immich upload, metadata loading, generation polling, and future image upload.

Recommended direction:

- Use **Vite** as the build system.
- Keep browser runtime dependencies at **zero** initially.
- Store maintainable source modules under `src/imagegen/frontend/`.
- Generate the browser target as `src/imagegen/static/app.js`, preserving the
  current Flask template contract.
- Use **Vitest + jsdom** for DOM-focused JavaScript tests.
- Use **ESLint** for correctness linting and **Prettier** for formatting.

This is intentionally conservative: it introduces a Node toolchain only for
development and tests, while keeping the Flask app's runtime static asset shape
unchanged.

## Current State

- No `package.json` exists.
- No JS build config exists.
- `index.html` loads `src/imagegen/static/app.js` as the production browser
  script.
- The app already cache-busts `app.js` with `app_checksum()`.
- Python tests currently protect key HTML data hooks, but browser behavior is
  mostly manual.

## Goals

- Split `app.js` into smaller files with explicit imports and exports.
- Make workflow code testable without a real Flask server.
- Keep generated runtime output compatible with the current Flask templates.
- Avoid adding frontend framework runtime dependencies unless a later feature
  clearly needs them.
- Keep the initial JavaScript toolchain understandable for maintainers who are
  not frontend specialists.

## Non-Goals

- Do not introduce React, Vue, Svelte, or another UI framework now.
- Do not convert the Flask-rendered workspace into a single-page app.
- Do not add TypeScript in the first step.
- Do not split CSS or introduce CSS modules in this proposal.
- Do not require Node at application runtime.

## Recommended Framework And Build System

Use **Vite with vanilla JavaScript**.

Why Vite:

- It is a mainstream modern build tool for browser JavaScript.
- It supports a vanilla JavaScript project without a UI framework.
- It can bundle ES modules into a single browser file.
- It integrates naturally with Vitest.
- It keeps the mental model small: source files in, static browser asset out.

Why not a full UI framework now:

- The app is server-rendered Flask with progressive browser behavior.
- Most existing complexity is workflow orchestration around DOM elements and API
  calls, not reusable component rendering.
- A UI framework would add runtime dependencies and a larger migration.
- Native DOM modules are enough to make the current code testable.

Recommended build output:

- Source entry: `src/imagegen/frontend/main.js`
- Generated target: `src/imagegen/static/app.js`
- Optional generated sourcemap: `src/imagegen/static/app.js.map`

The generated `app.js` should be treated as a build artifact. The source of
truth becomes `src/imagegen/frontend/`.

## Source Layout

Proposed layout:

```text
src/imagegen/
|-- frontend/
|   |-- main.js
|   |-- api.js
|   |-- dom.js
|   |-- state.js
|   |-- gallery.js
|   |-- generation.js
|   |-- immich.js
|   |-- mask-editor.js
|   |-- metadata.js
|   |-- palettes.js
|   |-- source-images.js
|   |-- trash.js
|   `-- image-upload.js
`-- static/
    |-- app.css
    |-- app.js
    `-- app.js.map
```

Initial module boundaries should follow user workflows, not abstract utility
categories. Shared utilities should stay small and obvious:

- `api.js`: `fetch` wrappers, CSRF header handling, JSON error handling.
- `dom.js`: selectors, event helpers, element creation helpers.
- `state.js`: shared browser state that cannot stay local to one workflow.
- `main.js`: bootstraps the page and wires workflow modules together.

Workflow modules should export small setup functions such as:

```js
export function setupTrash(root, services) {}
export function setupGallery(root, services) {}
export function setupMaskEditor(root, services) {}
```

The `services` object should carry shared dependencies such as API helpers,
gallery refresh, message rendering, and current CSRF token. This makes modules
testable without importing globals directly.

## Build Configuration

Add a root `package.json` with scripts:

```json
{
  "private": true,
  "type": "module",
  "scripts": {
    "js:build": "vite build",
    "js:test": "vitest run",
    "js:lint": "eslint src/imagegen/frontend tests/js",
    "js:format": "prettier --write src/imagegen/frontend tests/js",
    "js:check": "npm run js:lint && npm run js:test && npm run js:build"
  },
  "devDependencies": {
    "@eslint/js": "...",
    "eslint": "...",
    "jsdom": "...",
    "prettier": "...",
    "vite": "...",
    "vitest": "..."
  }
}
```

Add `vite.config.js`:

```js
import { defineConfig } from "vite";

export default defineConfig({
  build: {
    emptyOutDir: false,
    minify: false,
    outDir: "src/imagegen/static",
    rollupOptions: {
      input: "src/imagegen/frontend/main.js",
      output: {
        entryFileNames: "app.js",
        format: "iife",
        sourcemap: true
      }
    }
  },
  test: {
    environment: "jsdom",
    globals: false
  }
});
```

Notes:

- `format: "iife"` keeps the generated asset usable as a plain script tag.
- `minify: false` keeps local diffs and debugging readable.
- `emptyOutDir: false` prevents Vite from deleting `app.css` or other static
  Flask assets.
- The template can keep loading `/static/app.js` exactly as it does today.

## Test Framework Recommendation

Use **Vitest with jsdom**.

Why Vitest:

- It is fast and pairs naturally with Vite.
- It supports ES module imports directly.
- It provides Jest-like test ergonomics without adding Jest.
- It can run DOM tests through jsdom.

Why jsdom:

- Most current browser behavior is DOM event handling and `fetch` orchestration.
- jsdom is fast enough for unit-style workflow tests.
- It avoids running a full browser for every small behavior.

What to test in Vitest:

- DOM event wiring.
- State transitions.
- API wrapper behavior with mocked `fetch`.
- Rendering small gallery/trash/upload fragments.
- Form payload construction.
- Error and loading states.

What not to test only in Vitest:

- Canvas-heavy mask editing behavior.
- Real image rendering.
- File input behavior that differs meaningfully across browsers.
- Full Flask template integration.

For those, keep Python route/render tests and add occasional Playwright/manual
browser validation if the workflow is risky.

Proposed test layout:

```text
tests/
`-- js/
    |-- api.test.js
    |-- gallery.test.js
    |-- image-upload.test.js
    |-- mask-editor.test.js
    |-- palettes.test.js
    `-- trash.test.js
```

## Linting And Formatting

Use **ESLint** and **Prettier** as dev dependencies.

ESLint should catch likely bugs:

- accidental globals
- unused variables
- missing imports
- unreachable code
- suspicious equality or control flow

Prettier should own formatting:

- indentation
- wrapping
- quote style
- trailing commas

Keep their responsibilities separate. Do not spend project time arguing about
formatting rules; let Prettier make those decisions.

Initial ESLint config should use browser globals and modern JavaScript rules.
Avoid large plugin stacks until there is a concrete need.

## Dependency Policy

Runtime dependencies:

- None initially.
- Continue using browser-native APIs: DOM, `fetch`, `FormData`, `URL`,
  `AbortController`, and standard events.

Dev dependencies:

- `vite`
- `vitest`
- `jsdom`
- `eslint`
- `@eslint/js`
- `prettier`

Optional later dev dependencies:

- `@vitest/coverage-v8` if JavaScript coverage becomes useful.
- `playwright` if automated browser tests become necessary.

Avoid initially:

- React/Vue/Svelte and related plugin stacks.
- TypeScript and `typescript-eslint`.
- Babel.
- jQuery or DOM helper libraries.
- Runtime state management libraries.
- CSS-in-JS or component styling frameworks.

## Generated Files And Git Policy

Because this is a Python/Flask app that serves static files from the package, the
generated `src/imagegen/static/app.js` should probably stay committed.

Recommended policy:

- Commit `src/imagegen/frontend/**`.
- Commit `src/imagegen/static/app.js`.
- Commit `src/imagegen/static/app.js.map` only if the team wants easier browser
  debugging from packaged installs.
- Add a generated-file header to `app.js`:

```js
// Generated by `npm run js:build` from src/imagegen/frontend/main.js.
// Do not edit this file directly.
```

This keeps packaging simple: installing or running the Flask app does not
require Node. Developers only need Node when changing JavaScript source.

## Migration Plan

### Phase 1: Introduce Tooling Without Behavior Changes

- Add `package.json`, `package-lock.json`, `vite.config.js`,
  `eslint.config.js`, and `.prettierrc`.
- Move the current `app.js` into `src/imagegen/frontend/main.js`.
- Build it back to `src/imagegen/static/app.js`.
- Confirm the generated runtime behavior is unchanged.
- Add `npm run js:build`, `npm run js:test`, `npm run js:lint`, and
  `npm run js:check`.

Verification:

- `npm run js:check`
- `uv run pytest`
- `uv run ruff check src tests`
- Manual browser smoke test.

### Phase 2: Extract Shared Infrastructure

- Extract CSRF/fetch helpers into `api.js`.
- Extract selector and element helpers into `dom.js`.
- Extract gallery refresh and message rendering if they are shared.
- Add Vitest tests for pure helpers and API wrappers.

### Phase 3: Extract Workflow Modules

Suggested order:

1. `trash.js`
2. `palettes.js`
3. `gallery.js`
4. `metadata.js`
5. `source-images.js`
6. `generation.js`
7. `mask-editor.js`
8. `image-upload.js`

Start with workflows that are event-heavy but not canvas-heavy. Leave the mask
editor later because image/canvas behavior is harder to test in jsdom.

### Phase 4: Add Browser-Level Coverage Selectively

Only add Playwright or another real-browser tool if the jsdom tests and Flask
render tests do not catch enough regressions.

Good candidates:

- Overlay open/close flows.
- Drag-and-drop upload behavior.
- Mask editor canvas behavior.
- Gallery refresh after image mutation.

## Recommended Commands

Add these commands to the regular developer workflow after the toolchain exists:

```bash
npm install
npm run js:check
uv run pytest
uv run ruff check src tests
```

For JavaScript changes:

```bash
npm run js:format
npm run js:build
npm run js:test
```

The project can later add a wrapper script if we want one command to run both
Python and JavaScript checks.

## Risks And Mitigations

### Risk: Generated `app.js` Diffs Become Noisy

Mitigation:

- Keep `minify: false`.
- Use stable module structure.
- Commit generated output only after `npm run js:build`.

### Risk: Node Tooling Feels Heavy For A Python App

Mitigation:

- Keep Node as a dev-only requirement.
- Do not require Node to run the Flask app from an installed package.
- Keep the dependency list small.

### Risk: Tests Couple To Private Implementation Details

Mitigation:

- Test DOM behavior through events and visible state.
- Keep Flask route/render tests for server-provided data hooks.
- Avoid testing private helper names unless they are intentionally exported.

### Risk: Vite Deletes Static Assets

Mitigation:

- Configure `emptyOutDir: false`.
- Keep `app.css` outside the JS build pipeline for now.

## Open Decisions

- Should `app.js.map` be committed?
  - Recommendation: yes during the migration, because it helps debug generated
    code. Revisit once the build is stable.
- Should CI run `npm run js:check`?
  - Recommendation: yes once the JS toolchain lands.
- Should TypeScript be adopted?
  - Recommendation: not initially. Consider it only after modules are split and
    tests exist.
- Should Playwright be added immediately?
  - Recommendation: no. Start with Vitest + jsdom and add real-browser tests
    only for workflows that jsdom cannot represent well.

## References

- Vite: https://vite.dev/guide/
- Vitest: https://vitest.dev/
- Vitest DOM environments: https://vitest.dev/guide/environment
- ESLint: https://eslint.org/docs/latest/use/getting-started
- Prettier: https://prettier.io/docs/install

