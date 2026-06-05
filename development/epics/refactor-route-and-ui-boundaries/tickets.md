# Refactor Route and UI Boundaries Tickets

Source audit: `development/refactors/2026-06-05-refactoring-audit.md`.

## Decisions Applied

- Extract trash behavior into a new `src/imagegen/trash.py` module.
- Keep `src/imagegen/static/app.js` as a single no-build file for now.
- Do not migrate or reorganize legacy root planning files. They are ephemeral
  and will be cleaned up separately.

## Ticket 1: Delete Obvious Dead Helpers

### Goal

Remove private helpers that the audit found to be unused so later refactors have
less stale surface area to preserve.

### Scope

- Delete `src/imagegen/routes.py:_model_json`.
- Delete `tests/route_helpers.py:extract_json_script`.
- Confirm no remaining references exist.

### Acceptance Criteria

- `rg "_model_json"` finds no live references.
- `rg "extract_json_script"` finds no live references.
- Existing route and registry tests still pass.

### Verification

- `uv run pytest`
- `uv run ruff check src tests`

## Ticket 2: Consolidate Image Filename Validation

### Goal

Make image filename validation a single shared security boundary instead of
duplicating `safe_image_filename` across route and gallery code.

### Scope

- Move image filename validation into one non-route module.
- Prefer an existing domain module if it remains cohesive; otherwise create a
  small helper such as `src/imagegen/filenames.py`.
- Update routes, API routes, gallery, trash, metadata filtering, download, and
  mutation paths to use the shared helper.
- Remove duplicate implementations.

### Acceptance Criteria

- Image, trash, download, metadata, and API mutation routes reject path
  traversal, leading-dot names, unsupported extensions, directory separators,
  and missing files where applicable.
- There is only one implementation of image filename validation.
- API routes no longer import filename validation from `routes.py`.

### Verification

- Add or update behavior tests for unsafe filenames across image, trash,
  download, and metadata routes.
- `uv run pytest`
- `uv run ruff check src tests`

## Ticket 3: Extract Trash Filesystem Behavior Into `trash.py`

### Goal

Separate trashcan workflow logic from gallery listing so routes and API code use
a dedicated trash boundary.

### Scope

- Create `src/imagegen/trash.py`.
- Move trash-specific filesystem operations out of `src/imagegen/gallery.py`.
- Move trash retention refresh/count orchestration out of API route helpers
  where appropriate.
- Keep gallery listing behavior in `gallery.py`.
- Preserve current trash behavior: move deleted images to the configured trash
  directory, restore with collision handling, count trash images, list trash
  images, empty trash, and purge old eligible entries.

### Acceptance Criteria

- Gallery deletion remains constrained to the configured output directory.
- Deleted images are moved to the configured trash directory, not unlinked from
  routes.
- Restore behavior keeps existing collision semantics.
- Trash counts and list output remain unchanged at the route/API boundary.
- Mutating trash routes keep CSRF protection.

### Verification

- Keep or add domain tests for list, count, restore, collision, empty, and purge
  behavior.
- Add route/API tests for unsafe filenames and CSRF where gaps exist.
- `uv run pytest`
- `uv run ruff check src tests`

## Ticket 4: Extract Mask Payload Validation

### Goal

Move mask PNG upload validation and conversion out of `api_routes.py` into a
focused domain helper.

### Scope

- Create a focused module such as `src/imagegen/mask_store.py` or
  `src/imagegen/mask_editor.py`.
- Move content-length checks, base64 decoding, PNG validation, source-size
  comparison, and image conversion into the new module.
- Keep API route code responsible only for request parsing, invoking the helper,
  and shaping JSON responses.

### Acceptance Criteria

- Mask save rejects wrong content length, invalid base64, non-PNG data, source
  size mismatch, missing source file, and unsafe filenames.
- API error responses preserve current behavior and actionable messages without
  leaking sensitive local details.
- Provider-facing code never receives prompt annotation syntax or unsafe
  browser-submitted filenames as a side effect of this refactor.

### Verification

- Add focused unit tests for the mask helper.
- Keep or add API route tests for mask-save failure modes.
- `uv run pytest`
- `uv run ruff check src tests`

## Ticket 5: Extract Workspace Context Assembly

### Goal

Make `routes.index` a thin Flask adapter by moving workspace template context
assembly into a pure helper.

### Scope

- Extract provider/model/palette/source-image context assembly from
  `src/imagegen/routes.py:index`.
- Keep rendering, session, request, and redirect behavior in the route layer.
- Preserve configured-start-model behavior and provider fallback behavior.

### Acceptance Criteria

- Workspace starts with the configured model alias when it is available.
- Workspace falls back safely when the configured model is unavailable for the
  selected provider.
- Template context contains the same model registry, palette, source image, and
  route data hooks as before.

### Verification

- Add or update tests for configured-start-model and fallback behavior without
  relying only on brittle HTML assertions.
- Keep render tests for critical data attributes used by browser workflows.
- `uv run pytest`
- `uv run ruff check src tests`

## Ticket 6: Define JavaScript Tooling Recommendation Before Splitting `app.js`

### Goal

Keep `app.js` as a single no-build file for now, but define what tooling would
be needed before any future split or module migration.

### Scope

- Document recommendations for:
  - JS build framework, if the no-build file becomes unmaintainable.
  - JS testing framework for DOM event behavior.
  - JS linting/formatting/type-checking or other lightweight tooling.
- Evaluate options against the current Flask/static setup, local development
  cost, CI cost, and ability to test DOM behavior instead of private functions.
- Do not split `app.js` in this ticket.

### Recommended Direction

- Build framework: keep no-build until there is a concrete need; if splitting
  becomes necessary, prefer native ES modules first, then Vite only if bundling,
  dependency management, or browser compatibility demands it.
- Testing framework: prefer Vitest with jsdom for fast DOM event tests if a
  Node-based test layer is introduced.
- Browser validation: keep Playwright or equivalent browser-level checks for
  workflows that depend on real rendering, canvas/image behavior, file inputs,
  or Flask-rendered data attributes.
- Other tooling: use Prettier for formatting and ESLint for browser JavaScript
  linting only once the project accepts a Node toolchain.

### Acceptance Criteria

- A decision or notes artifact exists under this epic describing the recommended
  JS path and trigger points for adopting each tool.
- `app.js` remains a single no-build file.
- Any future split ticket depends on this recommendation and on UI validation
  coverage.

### Verification

- Documentation review only.

## Ticket 7: Add UI Render Hooks Before Any Browser Script Refactor

### Goal

Protect the current server-rendered contract before reorganizing UI code.

### Scope

- Add route/render tests for critical IDs, classes, and data attributes used by
  provider/model switching, palettes, source image selection, mask editor,
  gallery actions, trash overlay, Immich upload, metadata loading, generation
  polling, and parameter rendering.
- Keep tests behavior-oriented and avoid coupling to private JavaScript
  function names.

### Acceptance Criteria

- Tests fail if a required workflow hook is removed or renamed.
- Tests do not require a JS build step.
- Manual browser validation checkpoints are documented for workflows that cannot
  be covered by route/render tests.

### Verification

- `uv run pytest`
- `uv run ruff check src tests`

## Ticket 8: Organize CSS Without Changing Asset Strategy

### Goal

Reduce CSS maintenance cost while preserving the current static asset strategy.

### Scope

- Keep `src/imagegen/static/app.css` as a single file unless a separate asset
  strategy has already been approved.
- Group selectors by domain with clear section comments: base/forms, palette,
  mask editor, gallery, trash overlay, image view, and responsive layout.
- Keep intentionally shared gallery/trash selectors visible and documented by
  adjacency.

### Acceptance Criteria

- No visual behavior changes are intended.
- Trash-specific selectors are adjacent to trash UI styles.
- Shared gallery/trash styling remains explicit rather than accidental.

### Verification

- Manual responsive validation at desktop, tablet, and mobile widths.
- `uv run pytest`
- `uv run ruff check src tests`

## Ticket 9: Defer Provider Registry Structure Changes

### Goal

Avoid churn in the large provider registry modules until there is a concrete
maintenance or correctness problem.

### Scope

- Keep `model_registry_falai.py` and `model_registry_replicate.py` as
  data-driven Python modules for now.
- Add validation before changing storage format if manual data entry drift
  becomes a recurring problem.
- Do not introduce generated registry files without a separate decision.

### Acceptance Criteria

- Existing provider-specific registry behavior remains unchanged.
- Any future registry restructuring ticket identifies the drift, import-time,
  or reviewability problem it solves.

### Verification

- Provider-specific registry tests for alias resolution, edit target linkage,
  fixed inputs, selectable models, and custom dimensions.
- `uv run pytest`
- `uv run ruff check src tests`

