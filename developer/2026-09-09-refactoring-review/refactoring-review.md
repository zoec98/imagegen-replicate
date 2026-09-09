# Refactoring Review

Date: 2026-09-09

Scope: current `src/imagegen`, editable frontend modules, templates, CSS, and
tests. `src/imagegen/static/app.js` and its sourcemap were excluded because they
are generated artifacts. This is a planning artifact and does not authorize
behavior changes.

Review method: repository inventory and line counts, Python AST function/class
spans, JavaScript syntax-tree function spans, normalized function similarity,
cross-reference searches for callers and duplicate concepts, current tests,
and comparison with the earlier refactoring audits.

Baseline verification: `uv run pytest` passes all 498 tests and
`uv run ruff check src tests` passes.

## Summary

No critical issues were found. One high-severity architectural duplication can
cause provider behavior to drift. Five medium-severity boundaries make changes
needlessly broad or hard to test. One low-severity test organization issue
slows navigation but does not affect runtime behavior.

The best first target is the legacy Replicate model path: removing it deletes
parallel request-building and compatibility code already superseded by the
provider-neutral registry. The large provider registry files are not findings;
they are mostly declarative, provider-specific contract data whose apparent
similarities do not imply identical upstream behavior.

## Severity rubric

- **High:** parallel sources of truth can produce inconsistent runtime behavior.
- **Medium:** the boundary materially raises regression risk or makes focused
  behavior difficult to test.
- **Low:** organization or repetition adds maintenance cost without a likely
  runtime defect.

## Findings

### High — Replicate has a second model architecture and request serializer

Evidence:

- `model_registry_base.py:64-93` defines the provider-neutral
  `GenerationTarget` and `ProviderModel`, while `model_registry_base.py:102-117`
  retains the overlapping `ReplicateModel` type.
- `model_registry.py:155-200` converts every `ReplicateModel` into a
  `ProviderModel`; fal.ai and Wiro already enter the registry in the latter
  shape directly.
- `replicate_client.py:129-174` implements `build_prediction_input`, while
  `provider_requests.py:14-61` implements the same defaults, fixed-input,
  custom-dimension, and source-image rules for the provider-neutral path. The
  normalized bodies are 86% similar.
- `validation.py:327-388` and `config.py:118-136` carry unions and branches only
  to accept both model shapes. `generation_provider.py:51-78` also rebuilds a
  Replicate-specific `AppConfig` instead of resolving the same target contract
  used by the other providers.

Why it matters: request construction and validation have two sources of truth.
A new constraint can be added to the provider-neutral path but omitted from
Replicate, or vice versa. The compatibility branches spread the cost through
otherwise provider-neutral modules.

Smallest remedy:

1. Express Replicate registry entries directly as `ProviderModel` and
   `GenerationTarget`, preserving the existing public aliases.
2. Make `AppConfig.model` a `ProviderModel` and pass a resolved target into the
   Replicate client, as the fal.ai and Wiro clients already do.
3. Use `build_provider_request` for Replicate, then delete
   `build_prediction_input`, `_source_image_input_value`, the conversion layer,
   `ReplicateModel`, and validation compatibility branches.
4. Delete the pass-through `_build_provider_request` in `api_routes.py:675-690`
   and call the shared function directly.

Behavior tests required first:

- Replicate text and edit requests preserve provider model id, fixed inputs,
  defaults, custom dimensions, and single-versus-multiple source binding.
- API and CLI generation logs preserve the provider-ready metadata payload.
- Existing provider/model alias resolution and configured default selection
  remain unchanged.
- The same contract tests cover Replicate, fal.ai, and Wiro targets without
  asserting their internal class types.

### Medium — `main.js` is both bootstrap and the workspace model/form controller

Evidence:

- `frontend/main.js:12-543` is one 532-line immediately invoked function.
- Besides wiring workflow modules, it owns provider/model selection, parameter
  state and rendering, pricing rendering, freshness checks, metadata replay,
  and global keyboard handling.
- `frontend/main.js:338-359` and `frontend/metadata.js:68-89` contain the same
  `modelForMetadata` implementation.
- `tests/js/workspace.test.js` has one behavior test, so custom-dimension state,
  metadata replay, pricing, stale-page handling, and parameter rendering can
  only be reached through the full module side effect.

Why it matters: a change to model parameters or metadata replay requires
constructing the whole workspace and all workflows. The duplicate metadata
lookup can drift between tooltip display and loading metadata into the form.

Smallest remedy: export one `setupWorkspace(root = document)` function and move
the cohesive model/form state into a `workspace.js` module. Export one
`modelForMetadata(registry, metadata)` helper from `metadata.js` (where the
concept already belongs) and use it for both tooltip and workspace replay.
Keep `main.js` as a short call to `setupWorkspace`; do not add a state framework.

Behavior tests required first:

- Provider changes retain or select the correct provider-scoped model.
- Parameter controls preserve values, omit blank seeds, and switch custom
  dimension controls correctly.
- Metadata replay selects provider/model, prompt, supported parameters, edit
  mode, and valid source images for both current and legacy metadata fields.
- A changed app checksum disables generation and shows the stale-page error.

### Medium — the image editor still has a mask-only boundary and one 647-line setup function

Evidence:

- `frontend/mask-editor.js:7-653` places nearly all state and behavior inside
  `setupMaskEditor` (647 lines).
- The function now owns three operations—crop, blur, and mask—as shown by its
  operation state and controls at `mask-editor.js:19-45`, but its module and
  public setup name still describe only masks.
- Geometry, canvas drawing, pointer interaction, image loading, request
  creation, and modal lifecycle are nested in the same closure.

Why it matters: crop or blur changes must reason about unrelated painting and
mask-save state. Pure geometry and payload behavior cannot be tested without a
large canvas/DOM fixture.

Smallest remedy: rename the module/setup to `image-editor` first. Extract only
the pure operation calculations and request-payload builders that can be tested
without DOM or canvas; keep the shared modal and canvas lifecycle together.
Split operation controllers only if the remaining setup still changes often.

Behavior tests required first:

- Opening, closing, and switching operations resets only the intended state.
- Pointer coordinates map correctly after canvas scaling.
- Crop rectangles clamp to the source and reject undersized selections.
- Blur and mask payloads preserve current radius, falloff, invert, and PNG
  behavior.
- Failed and successful saves preserve the current button/message behavior.

### Medium — all JSON workflows are registered inside one 415-line function

Evidence:

- `api_routes.py` is 809 lines and `register_api_routes` spans
  `api_routes.py:76-490`.
- That nested function registers generation, gallery listing, URL/file/Immich
  imports, trash, palettes, Immich upload, deletion, mask, crop, blur, and the
  test endpoint.
- The test suite already recognizes these domains in
  `test_generation_api.py`, `test_palette_api.py`, and `test_immich_routes.py`,
  while the runtime module does not.

Why it matters: unrelated route changes share a large import surface and one
lexical scope. Handlers are not directly importable for focused tests, and
merge conflicts are more likely as workflows grow.

Smallest remedy: keep Flask decorators and existing URLs, but split route
registration by the domains already proven by tests: generation, palettes,
Immich, and gallery/image lifecycle. Leave small response mappers with their
own route group; keep shared selection/request helpers in `api_routes.py` until
two groups actually need them.

Behavior tests required first:

- Existing URL, HTTP method, status, JSON, and CSRF behavior for every moved
  endpoint remains unchanged.
- `create_app` registers every route once with the same endpoint names used by
  `url_for`.
- Configured fake clients, repositories, worker, and generation log remain
  injectable through app config.

### Medium — image-card structure, sizing, and behavior diverge across three workflows

Evidence:

- `frontend/gallery.js:320-347` and `frontend/image-upload.js:484-511` contain
  identical 28-line `createImageMedia` functions.
- `frontend/trash.js:193-206` contains a reduced copy of the same helper.
- `createImageCardRibbon` is duplicated in `gallery.js:349-351` and
  `image-upload.js:513-515`; trash builds the same figcaption inline at
  `trash.js:174`.
- `createInfoAction` is also near-duplicated in `gallery.js:360-378` and
  `trash.js:208-230`, with different icon construction.
- `static/app.css` applies workflow-specific gallery sizing and density rules,
  so main gallery, upload/Immich, and trash cards differ despite representing
  the same interaction pattern.

Why it matters: accessibility, external-link safety, lazy loading, image error
behavior, sizing, and action placement can diverge among cards that should have
one product contract. The current density differences are incidental and do
not need compatibility preservation.

Smallest remedy: define one card DOM/CSS contract and use it in all three
workflows. Move `createImageCard`, `createImageMedia`,
`createImageCardRibbon`, and the shared information action into a small
`image-card.js` module; keep workflow-specific actions local. Replace
workflow-specific size and density overrides with the single shared layout.
Use the complete information icon and accessible tooltip behavior everywhere;
the reduced trash variant does not need to be preserved.

Behavior tests required first:

- Linked media retains `target="_blank"` and `rel="noopener"`.
- Optional loading/error behavior and alt text remain available.
- Gallery, trash, and Immich cards render the same media size, density,
  information action, caption structure, and action placement.
- Workflow-specific actions—select/edit/download/delete, restore, and
  import—remain available with their current accessible labels.
- Responsive checks confirm the one shared card contract at desktop, tablet,
  and mobile widths.

### Medium — local upload and Immich browsing share one oversized workflow closure

Evidence:

- `frontend/image-upload.js:4-478` places URL import, multi-file/drop import,
  upload busy state, Immich paging, thumbnail error reporting, and Immich import
  in one 475-line `setupImageUpload` function.
- The two workflows share an overlay and status element but have independent
  transport and state; Immich alone accounts for page state and handlers at
  `image-upload.js:16-25` and `image-upload.js:111-274`.

Why it matters: local upload changes carry Immich setup/state in every test,
and Immich paging changes can affect the shared busy/status behavior.

Smallest remedy: extract `setupImmichImport` with the existing DOM subtree,
status callback, CSRF token, and gallery-refresh callback. Keep URL, file, and
drop imports together because they are one local-upload workflow and share
busy state.

Behavior tests required first:

- URL and file/drop imports work when Immich is not configured or rendered.
- Immich first/next/previous/empty/error states remain unchanged.
- Import success refreshes the gallery once and preserves the current status.
- Local upload busy state does not disable or corrupt Immich page state.

### Low — `test_image_routes.py` is a catch-all test module

Evidence:

- `tests/test_image_routes.py` is 2,023 lines with 83 tests.
- It covers local file serving/download/metadata, gallery JSON, imports, trash,
  delete, mask, crop, and blur. Separate domain tests already exist for
  `image_imports`, `image_edits`, `mask_store`, and trash/gallery helpers.

Why it matters: finding route-level coverage and choosing the right fixture is
slower than necessary. This is organizational debt, not insufficient coverage.

Smallest remedy: move tests without rewriting them into files matching the
runtime route groups, such as `test_gallery_routes.py`,
`test_image_import_routes.py`, `test_trash_routes.py`, and
`test_image_edit_routes.py`. Keep end-to-end edited-image workflow tests in one
integration file. Do not deduplicate route tests against domain unit tests when
they protect distinct HTTP behavior.

Behavior tests required first: none beyond the move; the full suite must collect
the same test count and pass.

## Module responsibility assessment

| Module | Intended responsibility | Mismatch |
| --- | --- | --- |
| `model_registry_base.py` | Shared provider-neutral registry types | Retains the overlapping Replicate-only model type. |
| `model_registry.py` | Provider-aware registry facade and lookup | Converts a legacy provider registry into the common shape. |
| `replicate_client.py` | Replicate transport, polling, and result normalization | Reimplements shared provider request construction. |
| `provider_requests.py` | Shared provider-ready payload construction | Correct home; currently excludes Replicate. |
| `config.py` | Environment persistence and typed application configuration | Exposes a two-model-type union only for legacy Replicate. |
| `validation.py` | Authoritative untrusted generation-payload validation | Carries compatibility branches for both model shapes. |
| `frontend/main.js` | Browser entry point and workflow wiring | Owns the model/form controller and metadata replay. |
| `frontend/metadata.js` | Metadata loading and presentation | Duplicates model lookup with `main.js`. |
| `frontend/mask-editor.js` | Image-edit overlay | Name understates crop/blur scope; one closure owns all operations and infrastructure. |
| `frontend/image-upload.js` | Image import overlay | Owns both local upload and an independent Immich browser. |
| `frontend/gallery.js`, `trash.js`, `image-upload.js` | Workflow-specific card rendering | Repeat shared card primitives. |
| `api_routes.py` | JSON route surface | One registration function owns every API domain. |
| `tests/test_image_routes.py` | Image route behavior | Accumulated most image-related API domains. |

## Reviewed but intentionally left alone

- `model_registry_falai.py`, `model_registry_replicate.py`, and
  `model_registry_wiro.py` are large, but most lines are explicit upstream
  schema data. Do not introduce shared model-family builders across providers;
  similar names do not guarantee identical contracts. Split data files only
  when merge conflicts or ownership make that useful.
- `FalAIGenerationProvider` and `WiroGenerationProvider` are similar, but each
  is about 25 lines and translates provider-specific timeouts. A configurable
  generic provider class would save little and hide useful differences.
- `_validate_integer` and `_validate_number` are nearly identical, but keeping
  their parsing and precise error messages explicit is cheaper than a generic
  numeric parser.
- `generation_log.py`, `immich_client.py`, `config.py`, and `app.css` are large
  but cohesive. Line count alone is not a reason to split them.

## Suggested order

1. Split `test_image_routes.py` mechanically to make later coverage easier to
   navigate.
2. Unify Replicate on `ProviderModel`/`GenerationTarget` and delete the legacy
   request path.
3. Extract the workspace controller and shared metadata lookup from `main.js`.
4. Rename and reduce the image-editor setup boundary.
5. Split API registration along existing tested domains.
6. Deduplicate image-card primitives.
7. Extract Immich browsing only when the upload module is next changed.
