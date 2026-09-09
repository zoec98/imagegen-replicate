# Refactoring Review Tickets

Status: Approved by user on 2026-09-09.

Sources:

- `developer/2026-09-09-refactoring-review/user-stories.md`
- `developer/2026-09-09-refactoring-review/refactoring-review.md`

## Decisions applied

- Preserve every existing user-facing Replicate model alias and lookup
  behavior; only the underlying registry representation changes.
- Use `ProviderModel`, `GenerationTarget`, and `build_provider_request` as the
  existing shared provider contract. Do not add another provider abstraction.
- Give main gallery, trash, and upload/Immich cards one DOM, size, density,
  information, action-placement, and responsive layout contract. Current
  visual differences are not compatibility requirements.
- Keep route URLs, endpoint names, request/response payloads, CSRF behavior,
  metadata, and stored files unchanged.
- Preserve current uncommitted model-registry changes, including the GPT Image
  2.5 output-compression defaults; do not overwrite unrelated worktree edits.
- Add no runtime or development dependencies.
- Work one behavior at a time. For behavior changes, add one failing public-
  interface test and make it pass before adding the next. For mechanical
  refactors, start green, move one boundary, and immediately prove the same
  public behavior remains green.
- Complete and commit each approved ticket before starting the next.

## 1. Split the catch-all image route tests by behavior

### Goal

Make route coverage navigable before moving runtime route boundaries, without
rewriting or deleting coverage.

### Observable behavior

- Pytest collects the same 498 tests before and after the move.
- Existing route assertions, parametrization, fixtures, and test names remain
  unchanged.
- Local image serving/download/metadata tests remain in
  `test_image_routes.py`.
- Gallery listing, URL/file import, trash/delete, and crop/blur/mask route tests
  move into focused route test modules.
- Edited-image end-to-end workflows stay together rather than being reduced to
  domain unit tests.

### Public interface

No application interface changes. This ticket changes test file ownership only.

### Likely touchpoints

- `tests/test_image_routes.py`
- `tests/test_gallery_routes.py`
- `tests/test_image_import_routes.py`
- `tests/test_trash_routes.py`
- `tests/test_image_edit_routes.py`

### Verification

- Record the baseline collection count, move one behavior group at a time, and
  confirm its tests still pass before the next move.
- `uv run pytest`
- `uv run ruff check src tests`

## 2. Route Replicate generation through the shared target request contract

### Goal

Remove Replicate's parallel provider-request serializer while leaving registry
storage migration for the next ticket.

### Observable behavior

- The Replicate generation client accepts the resolved `ProviderModel` and
  `GenerationTarget` used by the other providers.
- Text generation submits the target's exact provider model id and the same
  prompt, defaults, validated overrides, and fixed inputs as today.
- Edit generation binds one source as one value and multiple sources as a list,
  according to the target's `SourceImageBinding`.
- Custom dimensions remove the scale parameter and retain width/height exactly
  as today.
- Provider submission receives opened streams, while metadata receives local
  source filenames; every opened stream closes on success and failure.
- Prompt annotations are stripped from the provider request but retained in
  stored metadata.
- API and CLI generation logs keep the existing provider-ready payload.

### Public interface

- `replicate_client.generate_image_urls` takes explicit `model` and `target`
  arguments, matching the provider-neutral runtime boundary.
- `build_provider_request` is the only provider-ready payload builder.
- Replicate prediction creation, polling, errors, and `GenerationResult` remain
  unchanged.

### TDD sequence

1. Add a failing Replicate client test that calls the client with a resolved
   model/target and proves the submitted and metadata source representations.
2. Make that path use `build_provider_request`.
3. Add custom-dimension and fixed-input cases one at a time.
4. Move existing `build_prediction_input` coverage to the shared public builder,
   then delete the duplicate builder and API-route pass-through wrapper.

### Likely touchpoints

- `src/imagegen/replicate_client.py`
- `src/imagegen/generation_provider.py`
- `src/imagegen/provider_requests.py`
- `src/imagegen/api_routes.py`
- `src/imagegen/cli.py`
- `tests/test_replicate_client.py`
- `tests/test_generation_api.py`
- provider request/CLI tests

### Verification

- `uv run pytest`
- `uv run ruff check src tests`

## 3. Make the Replicate registry natively provider-neutral

### Goal

Delete the legacy `ReplicateModel` representation and its compatibility
branches after the runtime no longer needs them.

### Observable behavior

- Every currently selectable Replicate alias resolves under provider
  `replicate` with the same display name, provider model id, parameters,
  defaults, bounds, choices, pricing, edit capability, source limit, custom
  dimensions, and fixed inputs.
- Bare aliases continue to resolve when Replicate is selected, and
  `replicate:<alias>` continues to resolve explicitly.
- The configured default model and CLI model choices remain unchanged.
- `AppConfig.model` always exposes `ProviderModel`, regardless of selected
  provider.
- Browser registry JSON and legacy embedded metadata lookup remain compatible.
- Current GPT Image 2.5 output-compression defaults from the worktree are
  preserved.

### Public interface

- `MODEL_REGISTRY` keeps the same Replicate alias keys but contains
  `ProviderModel` values.
- `resolve_model`, `resolve_model_ref`, `resolve_generation_target`, provider
  listing, API model selection, and CLI selection keep their current contracts.
- `ReplicateModel` and the Replicate-to-provider conversion layer are removed.

### TDD sequence

1. Capture the existing Replicate alias/target contract through public registry
   lookup, including a text-only, multi-source edit, single-source edit, and
   custom-dimension model.
2. Convert registry entries while keeping those behavior tests green.
3. Narrow `AppConfig` and validation to the provider-neutral types.
4. Delete the compatibility type, converter, and branches only after all
   callers use the shared shape.

### Likely touchpoints

- `src/imagegen/model_registry_base.py`
- `src/imagegen/model_registry_replicate.py`
- `src/imagegen/model_registry.py`
- `src/imagegen/config.py`
- `src/imagegen/validation.py`
- `src/imagegen/routes.py`
- `src/imagegen/image_store.py`
- registry, configuration, validation, route, CLI, and provider tests

### Verification

- `uv run pytest`
- `uv run ruff check src tests`

## 4. Extract a testable workspace controller from `main.js`

### Goal

Keep the browser entry point as wiring while giving provider/model form state
and metadata replay one explicit, testable owner.

### Observable behavior

- Importing the production entry point still initializes one workspace when a
  prompt form exists and does nothing when it does not.
- Provider changes retain a valid prior model or select the provider's first
  model, reset source state, and render pricing and parameters.
- Parameter values survive rerenders, blank seeds are omitted, and custom
  dimensions show and submit the correct controls.
- Metadata replay selects provider/model, prompt, supported parameters, edit
  mode, and valid source images for provider-aware and legacy metadata.
- Tooltip display and metadata replay resolve models with the same lookup.
- A checksum mismatch disables generation and shows the current stale-page
  error.

### Public interface

- `setupWorkspace(root = document)` owns workspace state and workflow wiring.
- `main.js` invokes that setup and contains no model/form implementation.
- One shared `modelForMetadata(registry, metadata)` lookup serves tooltip and
  replay behavior.

### TDD sequence

1. Add one failing workspace test for metadata replay through
   `setupWorkspace`.
2. Export the setup boundary and move only enough state to pass it.
3. Add provider change, parameter/custom-dimension, and stale-page behaviors one
   at a time.
4. Replace the duplicate metadata lookup after both callers are covered.

### Likely touchpoints

- `src/imagegen/frontend/main.js`
- `src/imagegen/frontend/workspace.js`
- `src/imagegen/frontend/metadata.js`
- `tests/js/workspace.test.js`
- `tests/js/workspace-fixture.js`
- `tests/js/metadata.test.js`

### Verification

- `npm run js:format`
- `npm run js:check`
- `uv run pytest`
- `uv run ruff check src tests`

## 5. Rename the mask-only frontend boundary to image editor

### Goal

Make the module and setup interface describe the crop, blur, and mask workflow
they already own, without changing DOM hooks or behavior.

### Observable behavior

- Opening a gallery image still opens the same editor with Blur, Crop, and Mask
  in the current order and with the current default operation.
- All existing editor controls, keyboard close behavior, messages, and save
  routes remain unchanged.
- The production bundle initializes the renamed editor once.

### Public interface

- `frontend/image-editor.js` exports `setupImageEditor(root, services)`.
- `main.js` imports the new interface.
- Existing `.mask-editor-*` DOM/CSS selectors and server route names remain
  unchanged in this ticket; renaming stable markup would add churn without
  improving the boundary.

### TDD sequence

This is a green refactor: run the existing editor tests, rename the module and
public setup, update imports/tests/guidance, then rerun the same behaviors.

### Likely touchpoints

- `src/imagegen/frontend/mask-editor.js`
- `src/imagegen/frontend/image-editor.js`
- `src/imagegen/frontend/main.js`
- `tests/js/mask-editor.test.js`
- `AGENTS.md`
- `developer/ui-guidance.md`

### Verification

- `npm run js:format`
- `npm run js:check`
- `uv run pytest`
- `uv run ruff check src tests`

## 6. Extract pure image-editor operation logic

### Goal

Reduce the editor setup closure by moving stable calculation and payload logic
behind small functions that do not require the whole DOM/canvas fixture.

### Observable behavior

- Pointer coordinates map from displayed canvas bounds to natural pixels.
- Crop rectangles normalize drag direction, clamp to source bounds, round as
  today, and enable crop only at the current minimum size.
- Brush size/falloff produces the same mask intensity and clamping.
- Invert and PNG export preserve black, white, gray, and opaque-alpha values.
- Crop, blur, and mask requests keep their current URL, JSON fields, CSRF,
  loading state, success refresh, and error recovery.
- Opening, closing, and switching operations reset only current intended state.

### Public interface

- `setupImageEditor(root, services)` remains the workflow interface.
- Focused geometry/mask helpers may be exported from one operation module when
  their inputs and outputs are stable values; DOM elements and mutable editor
  state do not cross that boundary.

### TDD sequence

1. Prove coordinate and crop behavior with value-based tests, then extract it.
2. Prove mask paint/invert/export values, then extract them.
3. Keep request and modal behavior covered through `setupImageEditor` while
   reducing the closure.
4. Stop when the remaining setup owns DOM lifecycle and event orchestration;
   do not create one controller class per operation.

### Likely touchpoints

- `src/imagegen/frontend/image-editor.js`
- one focused `src/imagegen/frontend/image-editor-operations.js` if needed
- `tests/js/image-editor.test.js`

### Verification

- `npm run js:format`
- `npm run js:check`
- `uv run pytest`
- `uv run ruff check src tests`

## 7. Extract Immich browsing from local image upload

### Goal

Let local URL/file/drop import and the independent Immich browser evolve
without sharing one 475-line closure.

### Observable behavior

- URL and file/drop imports work when Immich is absent or disabled.
- File batches remain sequential, continue after a failure, refresh once after
  any success, and report complete/partial failure as today.
- Opening the upload overlay loads Immich page 1 only when its endpoint exists.
- Immich previous, next, empty, thumbnail-error, import-success, and
  import-failure states remain unchanged.
- Local upload busy state and Immich paging state do not disable or overwrite
  one another.

### Public interface

- `setupImageUpload(root, services)` keeps its current interface for local
  import and overlay lifecycle.
- `setupImmichImport(root, services)` owns only the rendered Immich browser and
  receives status and gallery-refresh callbacks.

### TDD sequence

1. Add a failing test that initializes local upload without any Immich DOM and
   completes a local import.
2. Move Immich state/rendering/handlers behind its setup while keeping existing
   Immich tests green one page behavior at a time.
3. Prove independent busy states before deleting the old nested functions.

### Likely touchpoints

- `src/imagegen/frontend/image-upload.js`
- `src/imagegen/frontend/immich-import.js`
- `tests/js/image-upload.test.js`
- `tests/js/immich-import.test.js`
- `developer/ui-guidance.md`

### Verification

- `npm run js:format`
- `npm run js:check`
- `uv run pytest`
- `uv run ruff check src tests`

## 8. Give every image workflow one shared card DOM contract

### Goal

Remove copied card helpers and render main, trash, and Immich cards with the
same structural and accessible primitives.

### Observable behavior

- Every card uses the same figure, media, image, caption, information action,
  tooltip, and action-container structure.
- Linked media always uses `target="_blank"` and `rel="noopener"`.
- Alt text, optional lazy loading, and thumbnail error callbacks remain
  available.
- The complete information icon and tooltip behavior appear in main, trash,
  and Immich cards.
- Main actions (select/edit/download/delete), trash restore, and Immich import
  retain their current labels and effects.
- Dynamic cards and server-rendered initial gallery cards expose the same
  shared contract.

### Public interface

- One `image-card.js` module exports the minimal card construction primitives.
- Workflow modules supply their content and actions rather than cloning shared
  DOM construction.
- Existing event delegation continues to use workflow-specific classes.

### TDD sequence

1. Add a failing DOM-contract assertion shared by main, trash, and Immich card
   tests.
2. Implement the shared figure/media/caption primitives and migrate one
   workflow at a time.
3. Add the shared information action, then remove the copied helpers.
4. Align the server-rendered card markup after dynamic cards pass.

### Likely touchpoints

- `src/imagegen/frontend/image-card.js`
- `src/imagegen/frontend/gallery.js`
- `src/imagegen/frontend/trash.js`
- `src/imagegen/frontend/immich-import.js`
- `src/imagegen/templates/index.html`
- card workflow JS tests
- `tests/test_workspace_routes.py`

### Verification

- `npm run js:format`
- `npm run js:check`
- `uv run pytest`
- `uv run ruff check src tests`

## 9. Unify image-card size, density, and responsive layout

### Goal

Replace workflow-specific card sizing with one visual contract across main,
trash, and upload/Immich galleries.

### Observable behavior

- The three galleries use the same minimum card width, grid gap, media aspect
  ratio, caption height, information placement, and action placement.
- Upload/Immich and trash no longer override density with smaller cards.
- Images keep a single agreed fit behavior; no workflow-specific crop/contain
  difference remains.
- Galleries remain usable without horizontal overflow at desktop, tablet, and
  mobile widths.
- Overlay scrolling remains usable without nested scrollbars caused by the old
  dense-card overrides.

### Public interface

- Shared `.image-gallery`, `.image-card`, `.image-card-media`, and
  `.image-card-ribbon` classes define layout.
- Workflow-specific classes remain hooks for actions and state, not sizing.

### TDD and visual sequence

1. Add render/DOM assertions that all galleries use the shared layout classes.
2. Remove one workflow-specific CSS override at a time.
3. Manually verify main, trash, and upload/Immich galleries at representative
   desktop, tablet, and mobile widths, including empty and many-card states.

### Likely touchpoints

- `src/imagegen/static/app.css`
- `src/imagegen/templates/index.html`
- frontend card renderers
- route and JS card tests
- an epic visual verification note

### Verification

- `npm run js:check`
- `uv run pytest`
- `uv run ruff check src tests`
- Manual responsive verification recorded in the epic directory

## 10. Extract generation API route registration

### Goal

Move generation submission/status and their private response/selection helpers
behind one focused route module while preserving the Flask surface.

### Observable behavior

- `/api/generate` and `/api/generation/<request_id>` retain methods, endpoint
  names, statuses, JSON, validation, CSRF, worker start, and durable logging.
- Provider/model/edit selection and unknown/disabled provider errors remain
  unchanged.
- Configured request store, worker, and generation log fakes remain injectable.
- `url_for("api_generation_status", ...)` continues to resolve.

### Public interface

- A focused registration function accepts the Flask app and registers only the
  generation API endpoints.
- `register_api_routes(app)` remains the application-factory entry point and
  delegates to the focused registration function.

### TDD sequence

Start with the full generation API tests green, move submission and status as
one route group, run those tests, then run the full suite before deleting the
old definitions.

### Likely touchpoints

- `src/imagegen/api_routes.py`
- `src/imagegen/generation_api_routes.py`
- `tests/test_generation_api.py`
- `src/imagegen/app.py`

### Verification

- `uv run pytest`
- `uv run ruff check src tests`

## 11. Extract palette API route registration

### Goal

Give palette JSON mapping and fragment CRUD routes the palette boundary already
used by their repository and tests.

### Observable behavior

- Palette list/read/create/update/delete URLs, endpoint names, JSON, statuses,
  conflict/not-found errors, and CSRF requirements remain unchanged.
- PaletteRepository remains the only filesystem boundary and is configured
  from the app's fragment root.
- `url_for` and frontend palette requests continue to resolve existing endpoint
  names.

### Public interface

- One focused registration function owns palette endpoints and JSON mappers.
- `register_api_routes(app)` delegates to it.

### TDD sequence

Run palette API tests green, move one CRUD behavior at a time with the same
tests, then delete the old route/helper definitions.

### Likely touchpoints

- `src/imagegen/api_routes.py`
- `src/imagegen/palette_api_routes.py`
- `tests/test_palette_api.py`

### Verification

- `uv run pytest`
- `uv run ruff check src tests`

## 12. Extract Immich API route registration

### Goal

Keep Immich configuration, client acquisition, gallery proxy/import, and local
upload routes together and out of the generic API module.

### Observable behavior

- Asset listing, thumbnail proxy, asset import, and gallery-image upload retain
  methods, endpoint names, pagination, JSON/status behavior, and CSRF rules.
- Missing configuration remains 404; upstream gallery/download/upload failures
  retain their safe 502 responses.
- Configured fake clients remain injectable without satisfying unrelated client
  methods.
- Credentials and upstream details remain absent from browser responses.
- Existing `url_for` calls for thumbnail and upload endpoints still resolve.

### Public interface

- One focused registration function owns Immich API endpoints and response
  mappers.
- `register_api_routes(app)` delegates to it.

### TDD sequence

Run Immich route tests green, move listing/thumbnail first, then import/upload,
checking each public endpoint before deleting old helpers.

### Likely touchpoints

- `src/imagegen/api_routes.py`
- `src/imagegen/immich_api_routes.py`
- `tests/test_immich_routes.py`

### Verification

- `uv run pytest`
- `uv run ruff check src tests`

## 13. Extract local image lifecycle API route registration

### Goal

Finish the API split by grouping local gallery listing/import, trash, delete,
crop, blur, and mask routes around the existing image/trash domain boundaries.

### Observable behavior

- Gallery JSON remains newest-first with metadata, action URLs, current image
  count, and refreshed trash count.
- URL and multipart imports retain size/type/redirect validation, single-file
  API semantics, collision-safe names, metadata behavior, statuses, and CSRF.
- Trash list/restore/empty/delete retain safe filename validation, collision
  behavior, retention refresh, counts, statuses, and CSRF.
- Crop, blur, and mask retain payload validation, metadata preservation, output
  naming, action URLs, statuses, and CSRF.
- Configured image-import HTTP and metadata providers remain injectable.
- Every existing endpoint name referenced by templates, frontend data
  attributes, and `url_for` remains unchanged.

### Public interface

- One local-image registration function owns these API endpoints and their
  browser-facing image/trash JSON mapping.
- Existing `image_store`, `image_imports`, `image_edits`, `mask_store`,
  `gallery`, and `trash` modules remain the domain boundaries; the route module
  does not absorb their logic.
- `register_api_routes(app)` becomes a short coordinator for app-version/test
  routes and the four focused registration functions.

### TDD sequence

Use the focused route files from Ticket 1. Move gallery/listing first, then
imports, trash/delete, and editor operations one behavior group at a time.
Run the relevant route file after every move and the full suite before deleting
the old definitions.

### Likely touchpoints

- `src/imagegen/api_routes.py`
- `src/imagegen/image_api_routes.py`
- focused image/gallery/import/trash/edit route tests
- `src/imagegen/app.py`
- `AGENTS.md`

### Verification

- `uv run pytest`
- `uv run ruff check src tests`

## Implementation gate

This approved plan is committed before Ticket 1. Complete and commit each
ticket in order using its stated checks.
