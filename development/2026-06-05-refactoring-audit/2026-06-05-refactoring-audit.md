# Refactoring Audit - 2026-06-05

Scope: repository structure, `src/imagegen` responsibilities, obvious duplication,
and dead-code candidates. This is a planning artifact only; it does not
authorize behavior changes.

## Summary

The codebase is still coherent and mostly follows the expected application
shape. The main architectural pressure is that route modules and the browser
script have accumulated multiple workflows. The next refactors should preserve
current public behavior while extracting small boundaries for file naming,
workspace page assembly, mask upload handling, and trash/gallery presentation.

Dead-code scan did not find widespread unused Python code. Two concrete
candidates surfaced:

- `src/imagegen/routes.py:_model_json` appears unused after the provider-aware
  model registry split.
- `tests/route_helpers.py:extract_json_script` appears unused by current tests.

The scan used `rg`, line counts, Python AST name-reference heuristics, and a
JavaScript function reference count. Flask route handlers were ignored as
dead-code false positives because decorators and endpoint names are the public
use.

## Module Responsibilities

### `src/imagegen/routes.py`

Intended responsibility: server-rendered workspace route and non-JSON local
file serving routes.

Current mismatch:

- It also owns generic image filename validation via `safe_image_filename`.
  `src/imagegen/gallery.py` has another `safe_image_filename`, creating a
  duplicated security concept.
- It contains `_metadata_json`, which filters embedded metadata source images.
  That behavior is route-facing, but the core metadata filtering concept belongs
  closer to `metadata.py` or a metadata presentation helper.
- It contains `_model_json`, which appears dead.

Proposed refactors:

- Move safe image filename validation into one shared module, likely
  `gallery.py` or a small `filenames.py`, and import it from routes, API routes,
  metadata filtering, and gallery trash helpers.
- Delete `_model_json` after confirming no hidden template or dynamic use.
- Consider extracting workspace context assembly from `index()` into a pure
  helper that returns the template context. This would keep `index()` as a thin
  Flask adapter and make configured-start-model behavior easier to test without
  HTML coupling.

Behavior tests needed first:

- Image/trash/download routes reject traversal, leading-dot names, unsupported
  extensions, and missing files.
- Metadata route filters unsafe and missing `source_images` while preserving
  warnings.
- Workspace starts with the configured model alias when available and falls
  back safely when unavailable for the selected provider.

### `src/imagegen/api_routes.py`

Intended responsibility: JSON `/api/*` route surface and browser-facing JSON
response shaping.

Current mismatch:

- It owns mask PNG request size calculation, base64 decoding, PNG validation,
  and mask image conversion. That is a cohesive domain but not inherently API
  route behavior.
- It owns trash retention refresh orchestration through `_refresh_trash_count`.
  The behavior is currently small, but as trash grows it may belong in a trash
  repository/service.
- It imports `safe_image_filename` from `routes.py`, making the API route layer
  depend on the non-JSON route module for a security helper.

Proposed refactors:

- Extract mask upload validation into `mask_store.py` or `mask_editor.py` with a
  public function such as `decode_mask_payload(payload, source_path,
  content_length)`.
- Extract trash refresh/count behavior into the same place as trash filesystem
  operations, so API routes call a single boundary.
- Remove the `api_routes -> routes` dependency by sharing filename validation
  through a non-route helper.

Behavior tests needed first:

- Mask save rejects wrong content length, invalid base64, non-PNG data, size
  mismatch, missing source file, and unsafe filename.
- Trash refresh purges only old eligible images and reports counts.
- Mutating image/trash routes require CSRF.

### `src/imagegen/gallery.py`

Intended responsibility: filesystem-facing gallery and trash helpers for local
image files.

Current mismatch:

- It contains both gallery listing and trash mutation. That is acceptable for
  now, but trash has become a distinct user workflow.
- It duplicates `safe_image_filename` with `routes.py`.

Proposed refactors:

- Split to `gallery.py` and `trash.py` only if trash behavior grows further.
  For now, a smaller move is to keep trash helpers here but make filename
  validation single-source.
- Consider returning typed trash image records instead of raw `Path` from
  `list_trash_images` when UI/API shape grows.

Behavior tests needed first:

- Existing gallery helper tests for list/count/restore/collision/empty/purge
  should remain at the domain boundary.

### `src/imagegen/static/app.js`

Intended responsibility: progressive browser behavior for the server-rendered
workspace.

Current mismatch:

- It now owns many independent workflows in one 2k-line file: provider/model
  switching, palette editor, source image selection, mask editor, gallery
  actions, trash overlay, Immich upload, metadata loading, generation polling,
  and parameter rendering.
- Several functions are cohesive but large workflow islands rather than shared
  app behavior.

Proposed refactors:

- Extract small ES modules if the build-free static setup can support them, or
  split into plain files loaded in order:
  - `palette-ui.js`
  - `gallery-ui.js`
  - `mask-editor.js`
  - `trash-ui.js`
  - `generation-ui.js`
- Before splitting, preserve the same server-rendered selectors and route data
  attributes.

Behavior tests needed first:

- Existing manual browser validation remains required for UI interaction.
- Add at least minimal route/render tests that key data attributes exist for
  each workflow before splitting files.
- If a JS test harness is introduced later, test through DOM events rather than
  private functions.

### `src/imagegen/static/app.css`

Intended responsibility: workspace styling.

Current mismatch:

- It is nearly 1k lines and includes unrelated domains: prompt form, palettes,
  mask editor, gallery cards, trash overlay, image view, and responsive layout.
- Gallery and trash share class names intentionally, but this also couples
  unrelated states through CSS selectors.

Proposed refactors:

- Split by domain if the static asset strategy allows multiple CSS files:
  base/forms, gallery, mask editor, trash overlay, palettes.
- If keeping one CSS file, at least group sections with comments and keep
  trash-specific selectors adjacent to trash UI.

Behavior tests needed first:

- Manual responsive validation at desktop/tablet/mobile.
- Workspace render tests for critical class/data hooks should remain.

### `src/imagegen/model_registry_falai.py` and `src/imagegen/model_registry_replicate.py`

Intended responsibility: data-driven provider model registry entries.

Current mismatch:

- These modules are large by design because they are registry data. That is not
  a refactoring problem by itself.
- Manual data entry can still drift from schema extraction output.

Proposed refactors:

- Defer structural changes unless registry growth makes import time or review
  difficult.
- Consider generated registry fixtures or a validation script before changing
  storage format.

Behavior tests needed first:

- Provider-specific registry tests for alias resolution, edit target linkage,
  fixed inputs, selectable models, and custom dimensions.

## Dead-Code Candidates

### `src/imagegen/routes.py:_model_json`

Evidence:

- `rg "_model_json"` finds only the function definition.
- Provider-aware model JSON is built by `_provider_model_json`.

Risk:

- Low. It is private and not referenced by templates.

Suggested ticket:

- Delete `_model_json` and run the full test suite.

### `tests/route_helpers.py:extract_json_script`

Evidence:

- `rg "extract_json_script"` finds only the helper definition.
- Current route tests use `extract_model_registry` and `extract_palette_data`.

Risk:

- Low. It is a test helper only.

Suggested ticket:

- Delete `extract_json_script` and run the full test suite.

### Flask route handler names

Evidence:

- AST heuristics flag route handlers in `routes.py` and `api_routes.py`.

Conclusion:

- Not dead code. They are registered through decorators and referenced by
  Flask endpoint names and `url_for`.

### JavaScript functions

Evidence:

- A simple name-reference count found every declared function in `app.js`
  referenced at least twice.

Conclusion:

- No obvious dead JavaScript functions from this heuristic.

## Proposed Ticket Order

1. Delete obvious dead private/test helpers.
2. Consolidate safe image filename validation into one shared helper.
3. Extract mask payload validation out of `api_routes.py`.
4. Extract workspace context assembly out of `routes.index`.
5. Decide whether to split `app.js`; do not do this until the UI behavior has
   either manual validation checkpoints or a browser/DOM test plan.

## Open Questions

- Should trash become a separate `trash.py` repository now, or stay in
  `gallery.py` until more behavior appears?
- Should JavaScript remain a single no-build file, or is a small multi-file
  static module setup acceptable?
- Should root legacy planning files be migrated into `development/epics/` now,
  or left as historical artifacts until the next feature starts?
