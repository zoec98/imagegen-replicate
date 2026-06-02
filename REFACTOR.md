# Refactoring Audit

Audit date: 2026-06-02.

Scope: `src/imagegen/*.py`. This pass documents responsibilities and proposed
refactorings only. It does not change implementation behavior.

## Cross-Cutting Findings

- JSON shaping for models and palettes is implemented in both `routes.py` and
  `api_routes.py`.
- Safe image filename validation is used by route handlers and source-image
  validation, but the behavior is split between `routes.py`,
  `source_images.py`, and `gallery.py`.
- Generation request submission is spread across API route handling,
  validation, provider-payload construction, request state, durable logging,
  and worker startup. The route currently coordinates all of those steps.
- Model metadata is correct to keep data-driven, but `model_registry.py` is now
  large enough that future model additions will make review harder.
- SQLite schema/migration details and the public generation-log repository live
  together in `generation_log.py`. This is acceptable now, but it is a natural
  split point if more migrations arrive.

## Module Audit

### `src/imagegen/__init__.py`

Intended responsibility: Expose package-level entry points only.

Functions/classes outside responsibility: none.

Duplication or scattered concepts: none.

Proposed refactorings: none.

Behavior tests needed first: none.

### `src/imagegen/app.py`

Intended responsibility: Build and configure the Flask application object, wire
app-scoped services, and register route modules.

Functions/classes outside responsibility: none.

Duplication or scattered concepts: service lookup/type checks are handled in
`api_routes.py`, while service creation happens here.

Proposed refactorings:

- Consider extracting app service accessors into a small `services.py` module if
  more route modules need typed access to configured services.

Behavior tests needed first:

- Creating an app initializes configured directories and durable log storage.
- Injected request store, generation log, worker, metadata provider, and app
  config are used by HTTP routes instead of default services.

### `src/imagegen/api_routes.py`

Intended responsibility: Register JSON API endpoints and translate
application/domain outcomes into browser-facing JSON responses.

Functions/classes outside responsibility:

- `_selected_model` performs request-model selection and error shaping.
- `_fragment_payload` performs palette payload validation.
- `_request_json`, `_gallery_image_json`, `_palette_json`, and
  `_palette_fragment_json` duplicate response-shaping concepts also needed by
  server-rendered routes.

Duplicated or scattered concepts:

- Palette JSON shaping duplicates `routes.py`.
- Gallery image response construction partly overlaps route/file-serving image
  safety behavior.
- Generation submission orchestration repeats provider-payload construction
  before the worker later builds the provider payload again for Replicate.

Proposed refactorings:

- Extract shared model/palette/gallery serializers into `response_models.py` or
  another small presentation-boundary module used by both HTML and JSON routes.
- Extract generation-submission orchestration from `api_generate` into a
  domain-level service, for example `GenerationSubmissionService.submit(payload)`.
- Move model selection into validation or the submission service so routes do
  less request interpretation.
- Keep API status-code mapping in `api_routes.py`; do not move HTTP concerns
  into domain services.

Behavior tests needed first:

- `POST /api/generate` accepts a valid default-model request and returns the
  queued request JSON with status `202`.
- `POST /api/generate` rejects unknown models, invalid parameters, invalid edit
  mode/source images, and invalid prompt annotations before creating a request.
- Accepted generation requests persist annotated prompts while storing a
  provider-ready payload without annotation syntax in SQLite.
- Palette CRUD endpoints preserve names, validation failures, conflict status,
  and CSRF requirements.
- `GET /api/images` returns newest-first gallery JSON with metadata URLs and
  Immich upload URLs only when configured.

### `src/imagegen/routes.py`

Intended responsibility: Register HTML/file-serving routes and shape
server-rendered workspace data.

Functions/classes outside responsibility:

- `_model_json`, `_pricing_json`, `_parameter_json`, `_custom_dimensions_json`,
  `_palette_json`, and `_palette_fragment_json` are presentation serializers
  shared conceptually with API routes.
- `safe_image_filename` is a reusable filename policy used outside ordinary HTML
  routes.

Duplicated or scattered concepts:

- Model and palette JSON shaping duplicates `api_routes.py`.
- Safe image filename checks overlap with `source_images.py` and gallery image
  extension rules.

Proposed refactorings:

- Move shared presentation serializers out of route modules.
- Move safe gallery filename validation to a dedicated image filename policy
  module or to `gallery.py`, then have routes and API routes call it.
- Keep route handlers responsible for `send_file`, `send_from_directory`,
  redirects, and `abort`.

Behavior tests needed first:

- `GET /` renders the workspace with model registry data, palette data, gallery
  filenames, CSRF token, app checksum, and Immich availability.
- Image open, normal download, clean download, and metadata routes distinguish
  missing files, unsafe names, unsupported GIFs, attachment names, and clean
  metadata stripping.
- Static asset URLs remain cache-busted by the app checksum.

### `src/imagegen/model_registry.py`

Intended responsibility: Define model metadata, parameter schemas, defaults, and
the in-process model registry used by validation and request construction.

Functions/classes outside responsibility: none.

Duplicated or scattered concepts:

- Repeated prompt, source-image, pricing, aspect-ratio, output-format, and
  safety-filter parameter definitions across model entries.
- Schema-derived model data and registry dataclass types live in one large file.

Proposed refactorings:

- Split dataclass/type definitions from concrete model entries, for example
  `model_types.py` plus a data-only registry module.
- Consider helper builders for common parameters only where repeated behavior is
  genuinely identical; avoid hiding model-specific schema differences.
- Consider grouping large model constants by provider if the registry keeps
  growing.

Behavior tests needed first:

- The registry exposes the same aliases, display names, Replicate model keys,
  edit capability, source-image limits, fixed inputs, pricing, and ordered
  parameters for every configured model.
- Validation and `build_prediction_input` still consume each registry entry
  correctly, including custom dimensions and fixed safety-checker inputs.
- The index page and API generation endpoint expose/accept the same model
  choices after the split.

### `src/imagegen/validation.py`

Intended responsibility: Validate submitted generation payloads against model
metadata before requests are stored or workers are started.

Functions/classes outside responsibility: none.

Duplicated or scattered concepts:

- Source-image validation is delegated to `source_images.py`, but edit-mode
  policy lives here.
- Custom-dimension policy is interpreted here and again in
  `replicate_client.build_prediction_input`.

Proposed refactorings:

- Extract custom-dimension normalization into a small domain helper shared by
  validation and provider-payload construction if more custom-dimension models
  are added.
- Keep source-image existence checks behind `source_images.py`; keep request
  edit-mode semantics here or in a generation-submission service.

Behavior tests needed first:

- Valid text-to-image payloads receive defaults and reject fixed-input
  overrides, unknown parameters, prompt-in-parameters, source-image parameters,
  and invalid types/ranges.
- Edit requests require edit mode and existing source images, reject sources
  outside edit mode, and respect per-model source-image limits.
- Custom dimensions require width and height only when activated and remove the
  scale parameter from provider inputs.

### `src/imagegen/replicate_client.py`

Intended responsibility: Build Replicate prediction payloads, run/poll
predictions, normalize outputs, and hand successful outputs to storage.

Functions/classes outside responsibility:

- `build_prediction_input` is also used outside the Replicate runtime path to
  store reproducible request payloads before work starts.

Duplicated or scattered concepts:

- Provider-ready payload construction is called in both API request logging and
  actual Replicate generation.
- Custom-dimension behavior overlaps with validation.
- Source-image inputs are represented both as open files for Replicate and local
  filenames for metadata.

Proposed refactorings:

- Extract provider-payload construction into a boundary module such as
  `prediction_inputs.py` if additional providers or request logging needs grow.
- Keep the network client/polling code in `replicate_client.py`.
- Consider replacing `generate_image_urls` with a result name that reflects that
  images are downloaded and persisted, not only URL generation.

Behavior tests needed first:

- Provider payloads include defaults, user parameters, fixed inputs, stripped
  prompt text, source images under the model-specific source field, and custom
  dimension handling.
- Runtime generation opens source files only for the provider call, closes them
  on success and failure, polls until terminal status, and reports provider
  errors with actionable details.
- Stored image metadata receives the original annotated prompt and filename
  source-image references, not open file objects.

### `src/imagegen/image_store.py`

Intended responsibility: Download generated image outputs, enforce storage
safety checks, and persist metadata-rich gallery files.

Functions/classes outside responsibility: none.

Duplicated or scattered concepts:

- Supported image extensions overlap with `gallery.py`, `image_export.py`, and
  `source_images.py`.
- Filename creation uses model alias, prediction id, and sequence but does not
  currently use a random component despite the contributor policy asking for
  collision-resistant filenames.

Proposed refactorings:

- Centralize supported image type/extension policy if more image handling
  modules are added.
- Consider generating collision-resistant filenames independent of provider
  prediction ids before making gallery storage more concurrent.

Behavior tests needed first:

- Downloads reject non-image, GIF, and oversized responses; accepted JPEG/PNG/WebP
  responses are stored under the output directory.
- Stored files embed metadata containing model, prompt, parameters, source URL,
  author, copyright, creation time, content type, and size.
- Multiple outputs from one prediction produce distinct files and ordered
  metadata.

### `src/imagegen/gallery.py`

Intended responsibility: List and move locally stored gallery images while
keeping Flask response handling outside this module.

Functions/classes outside responsibility: none.

Duplicated or scattered concepts:

- Image extension policy overlaps with source-image validation and export
  support.
- Trash collision handling is local to gallery deletion; route code only sees a
  move operation.

Proposed refactorings:

- Move shared image extension/filename validation into a small image policy
  helper if source uploads or gallery actions grow.

Behavior tests needed first:

- Gallery listing returns supported image files newest first, ignores
  unsupported files, and includes embedded metadata when present.
- Deletion moves images into the configured trash directory, creates the trash
  directory, rejects path traversal/missing files, and does not overwrite trash
  collisions.

### `src/imagegen/image_export.py`

Intended responsibility: Create temporary metadata-stripped image exports
without mutating stored gallery files.

Functions/classes outside responsibility: none.

Duplicated or scattered concepts:

- Supported export suffixes duplicate the gallery/source-image image extension
  concept.

Proposed refactorings:

- Reuse a central supported-image policy if one is introduced.

Behavior tests needed first:

- Clean exports for PNG, JPEG, and WebP strip app metadata and format metadata
  while leaving the stored gallery image unchanged.
- Clean exports are written under the configured temporary directory and do not
  appear in gallery listings.

### `src/imagegen/metadata_embed.py`

Intended responsibility: Read, write, and describe embedded generated-image
metadata for supported image formats.

Functions/classes outside responsibility:

- `human_description` is format-independent description policy, but it is
  tightly coupled to metadata embedding today.

Duplicated or scattered concepts:

- Human-readable metadata text and parseable payload are both assembled here,
  while copyright policy is in `metadata_policy.py`.

Proposed refactorings:

- Move `human_description` to metadata policy only if more metadata producers
  need it.
- Keep PNG/EXIF encoding details private in this module.

Behavior tests needed first:

- Metadata round-trips for PNG, JPEG, and WebP with parseable application
  payloads.
- Existing PNG text metadata is preserved except for app-owned keys.
- Human EXIF/PNG description fields are written for external tools.
- Unsupported or unreadable image files fail safely.

### `src/imagegen/metadata.py`

Intended responsibility: Provide the route/gallery-facing boundary for reading
generated-image metadata.

Functions/classes outside responsibility: none.

Duplication or scattered concepts: none significant.

Proposed refactorings: none.

Behavior tests needed first: existing provider tests are sufficient for the
current shape.

### `src/imagegen/metadata_policy.py`

Intended responsibility: Encapsulate policy-derived metadata values that are
not image-format specific.

Functions/classes outside responsibility: none.

Duplication or scattered concepts: human description policy lives in
`metadata_embed.py`.

Proposed refactorings:

- Move human description construction here only if it becomes shared outside
  embedded metadata writing.

Behavior tests needed first:

- Copyright synthesis uses the generation year and rejects missing author or
  invalid creation timestamps.
- Human descriptions remain stable if moved.

### `src/imagegen/config.py`

Intended responsibility: Manage environment defaults and convert runtime
configuration into `AppConfig`.

Functions/classes outside responsibility: none.

Duplicated or scattered concepts:

- Derived path configuration and service feature switches are both assembled in
  `load_config`.

Proposed refactorings:

- Extract path derivation or optional-service configuration only if additional
  services or storage roots are added.

Behavior tests needed first:

- `.env` creation preserves existing values, writes expected defaults, removes
  deprecated settings, and does not override existing process environment.
- Config loading derives data/output/fragment/trash/tmp paths and enables
  Immich only when all required settings are present.
- Unknown model aliases are rejected.

### `src/imagegen/palettes.py`

Intended responsibility: Validate, list, read, and mutate prompt palette
fragments under the configured fragment root.

Functions/classes outside responsibility: none.

Duplicated or scattered concepts: none significant.

Proposed refactorings:

- Keep as-is for now. Splitting validation helpers from repository IO would add
  indirection without reducing meaningful complexity yet.

Behavior tests needed first:

- Listing ignores invalid palettes/fragments/content, sorts valid entries, and
  treats a missing root as empty.
- Reads/writes/deletes validate names before filesystem access, reject traversal,
  normalize UI spaces, enforce content rules, and require existing palette
  directories.

### `src/imagegen/prompt_annotations.py`

Intended responsibility: Parse app-specific prompt annotations and produce
provider-ready prompt text.

Functions/classes outside responsibility: none.

Duplicated or scattered concepts:

- Annotation palette-name validation reuses palette naming rules, which is
  appropriate because annotation syntax names palettes.

Proposed refactorings: none.

Behavior tests needed first:

- Plain prompts remain valid.
- Single and multiple annotations parse correctly.
- Provider prompt stripping removes app syntax and preserves annotation content.
- Invalid, nested, unterminated, or malformed annotations are rejected before
  request creation.

### `src/imagegen/request_store.py`

Intended responsibility: Track in-process generation request lifecycle state for
HTTP polling.

Functions/classes outside responsibility:

- `GenerationRequest.to_json` is response shaping inside the state object.

Duplicated or scattered concepts:

- Request JSON appears here and in `_request_json` in `api_routes.py`.

Proposed refactorings:

- Move request response shaping out of `GenerationRequest` if API response
  models are extracted.
- Keep thread-safe lifecycle mutation in this module.

Behavior tests needed first:

- Creating a request records queued status, timestamps, prompt, parameters,
  model alias, and source-image filenames.
- Status transitions preserve submission data and record output URLs, image
  filenames, prediction ids, logs, and displayable errors.
- API polling returns the same lifecycle fields after any serializer move.

### `src/imagegen/security.py`

Intended responsibility: Provide session-backed CSRF and same-client guards for
mutating JSON API requests.

Functions/classes outside responsibility: none.

Duplication or scattered concepts: none significant.

Proposed refactorings: none.

Behavior tests needed first:

- Rendered pages create/reuse a CSRF token bound to the first client IP.
- Mutating JSON API requests reject missing/invalid tokens, non-JSON bodies, and
  client-IP changes.
- API responses do not emit permissive CORS headers.

### `src/imagegen/source_images.py`

Intended responsibility: Validate source-image filenames and resolve them to
local app-controlled paths for image-edit requests.

Functions/classes outside responsibility: none.

Duplicated or scattered concepts:

- Safe filename and supported extension checks overlap with `routes.py` and
  `gallery.py`.

Proposed refactorings:

- Reuse a central gallery/source image filename validator if image upload or
  source-selection behavior grows.

Behavior tests needed first:

- Source-image validation accepts only existing supported image files inside the
  configured output directory.
- It rejects traversal, GIFs, missing files, non-arrays, unsupported models, and
  requests exceeding model source-image limits.

### `src/imagegen/worker.py`

Intended responsibility: Orchestrate asynchronous generation work and translate
generation outcomes into request-store and generation-log updates.

Functions/classes outside responsibility: none.

Duplicated or scattered concepts:

- The worker reconstructs model-specific app config from request state, while
  API submission separately selected and logged the model.

Proposed refactorings:

- If a generation-submission service is introduced, consider passing a richer
  queued work item that already contains model metadata and provider payload.
- Keep thread-pool ownership and lifecycle result mapping here.

Behavior tests needed first:

- Successful, failed, and timed-out generation runs update request state and
  durable log lifecycle fields.
- Multiple stored assets are persisted in order.
- Requests use their selected model rather than the app default model.
- `ThreadedGenerationWorker.start` returns before generation completes.

### `src/imagegen/immich_client.py`

Intended responsibility: Encapsulate Immich HTTP upload and album-attachment
behavior behind a small service client.

Functions/classes outside responsibility: none.

Duplicated or scattered concepts: none significant.

Proposed refactorings:

- Keep as-is. It already forms a clean external-service boundary.

Behavior tests needed first:

- Upload sends the expected asset metadata and then attaches the asset to the
  configured album.
- Duplicate upload/album responses map to success where appropriate.
- Upload and album failures return sanitized errors without leaking API keys.

### `src/imagegen/app_version.py`

Intended responsibility: Calculate deterministic cache/version identifiers for
browser-facing UI assets.

Functions/classes outside responsibility: none.

Duplication or scattered concepts: none.

Proposed refactorings: none.

Behavior tests needed first:

- Checksums are stable for identical file content and change when included UI
  asset content changes.

## Recommended Order

1. Extract shared presentation serializers for model, palette, gallery, and
   request JSON.
2. Extract shared safe image filename / supported image policy.
3. Extract generation submission orchestration from `api_generate`.
4. Split model registry type definitions from model data only after tests cover
   every registry entry's externally visible metadata.
5. Split SQLite schema/migrations from `SQLiteGenerationLog` only when another
   schema version or query surface makes it worthwhile.
