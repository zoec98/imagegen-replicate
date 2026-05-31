# Implementation Plan

This plan is derived from `SCENARIO.md`.

The scenario is covered by two workstreams:

- image-generation-provider: provider selection, provider-specific model
  registries, provider clients, schema helpers, and provider pricing metadata.
- gallery download improvements: metadata-rich stored images, clean exports,
  forced-download routes, and gallery controls.

## Decisions

- Use `FAL_KEY` for fal.ai credentials. Do not support `FAL_API_KEY` unless the
  fal.ai library later proves that name is required.
- Missing provider API keys are allowed at startup. Providers without keys are
  not offered for generation.
- Replicate is the first-load default provider when it is enabled. Otherwise,
  use the first enabled provider. If none are enabled, show a clear no-provider
  message.
- Model aliases are unique within a provider, not globally unique.
- Fully qualified model references use `provider:alias`, for example
  `replicate:seedream45`.
- Bare model aliases resolve inside the currently selected provider.
- Page initialization may fall back to the first model for the selected provider
  if a configured default alias is unavailable. Submitted API requests must
  reject invalid provider/model combinations instead of falling back.
- fal.ai text-to-image and edit endpoints that form one user-facing model are
  linked in the fal.ai registry. The model selector shows the text/non-edit
  entry; edit mode uses the linked edit endpoint when one exists.
- Replicate pricing remains registry metadata. fal.ai pricing is fetched only by
  `scripts/get_schema_falai`; no runtime or startup pricing refresh is included
  in this plan.
- `scripts/get_schema` is renamed to `scripts/get_schema_replicate`; no
  compatibility wrapper remains.
- Script helpers do not need automated tests.
- Use `AUTHOR` as the only author/copyright metadata setting. New `.env` files
  get `AUTHOR=Noname Changeme Nescio`.
- Copyright is synthesized from `AUTHOR` and the generation year stored in image
  metadata.
- Clean downloads use unique temporary files under `<data_dir>/tmp`, are not
  cached as gallery assets, and do not mutate stored gallery images.
- Clicking a gallery image opens/views it. The normal download icon forces
  download of the stored metadata-rich image. The clean download icon forces
  download of a stripped temporary image.

## Image Generation Provider

### Ticket 1: Provider Configuration And Availability

#### Scope

- Add `FAL_KEY` to `.env` generation and `env.example`.
- Extend configuration with provider availability:
  - Replicate is enabled when `REPLICATE_API_TOKEN` is set.
  - fal.ai is enabled when `FAL_KEY` is set.
- Compute the first-load provider:
  - Replicate when enabled;
  - otherwise the first enabled provider;
  - otherwise no selected provider.
- Make no-provider state explicit for routes/templates/API responses.

#### Acceptance Criteria

- The app starts with no provider keys.
- Providers without API keys are not offered for generation.
- The app can report that no generation provider is configured.
- `env.example` documents `REPLICATE_API_TOKEN` and `FAL_KEY`.

#### Suggested Tests

- Config loads with no provider keys.
- Config reports Replicate enabled from `REPLICATE_API_TOKEN`.
- Config reports fal.ai enabled from `FAL_KEY`.
- Provider defaulting prefers Replicate only when Replicate is enabled.
- Provider defaulting falls through to fal.ai when only `FAL_KEY` is set.

### Ticket 2: Provider Registry Foundation

#### Scope

- Split model registries by provider.
- Introduce provider identity in model metadata.
- Keep provider-specific model keys, versions, schema URLs, pricing,
  capabilities, parameters, defaults, limits, and output shapes distinct.
- Keep current Replicate models represented as Replicate provider entries.
- Keep pricing representation provider-aware:
  - Replicate entries keep static registry pricing.
  - fal.ai entries may use provider-API pricing when imported by helper script.
  - unknown pricing is represented explicitly.
- Add registry lookup helpers for:
  - enabled provider model lists;
  - fully qualified `provider:alias` references;
  - bare aliases scoped to a selected provider;
  - page-initialization fallback to first model for a provider.

#### Acceptance Criteria

- Model aliases are unique within a provider.
- Duplicate aliases across providers are allowed.
- Provider model lists do not leak models from other providers.
- Existing Replicate registry behavior is preserved through provider-aware
  helpers.
- Unknown pricing is explicit and never guessed.

#### Suggested Tests

- Registry filters by provider.
- Fully qualified model references resolve to the exact provider/model.
- Bare aliases resolve only within the selected provider.
- Initialization fallback chooses the first model for the provider.
- Bad provider/model references are distinguishable from missing defaults.

### Ticket 3: fal.ai Linked Text/Edit Registry Entries

#### Scope

- Extend fal.ai registry metadata so one user-facing model can link:
  - a selectable text-to-image endpoint;
  - an optional edit endpoint.
- Example linked endpoints:
  - `fal-ai/bytedance/seedream/v4.5/text-to-image`;
  - `fal-ai/bytedance/seedream/v4.5/edit`.
- Mark linked edit endpoints as request targets, not normal top-level selector
  options.
- Add registry helpers to resolve the effective endpoint for:
  - text-to-image mode;
  - edit mode.

#### Acceptance Criteria

- fal.ai text models are selectable.
- fal.ai linked edit endpoints are available to request construction.
- fal.ai edit endpoints are not duplicated as normal model selector choices.
- Edit-mode resolution fails clearly when a fal.ai model has no linked edit
  endpoint.

#### Suggested Tests

- fal.ai registry exposes only selectable text models for UI lists.
- fal.ai registry resolves a linked edit endpoint when edit mode is active.
- fal.ai registry rejects edit-mode resolution without a linked edit endpoint.

### Ticket 4: Provider Schema Helper Scripts

#### Scope

- Rename `scripts/get_schema` to `scripts/get_schema_replicate`.
- Do not keep a `scripts/get_schema` compatibility wrapper.
- Add `scripts/get_schema_falai`.
- Update README and AGENTS script references.

#### Replicate Helper

- Preserve existing Replicate schema extraction behavior.
- Usage remains `scripts/get_schema_replicate owner/model`.

#### fal.ai Helper

- Accept fal.ai endpoint IDs such as
  `fal-ai/bytedance/seedream/v4.5/text-to-image`.
- Fetch or print useful registry-authoring information from fal.ai docs/API
  pages such as
  `https://fal.ai/models/fal-ai/bytedance/seedream/v4.5/text-to-image/api`.
- Surface the endpoint ID used in the Python example:
  `fal_client.submit(<endpoint_id>, arguments=...)`.
- Surface schema information from the page's schema section.
- Fetch pricing from the documented fal.ai Platform API during helper execution
  when `FAL_KEY` is available.
- Missing `.env` or missing `FAL_KEY` prints a warning and leaves pricing
  undefined/unknown; this is not an error.

#### Acceptance Criteria

- `scripts/get_schema_replicate owner/model` works as the old helper did.
- `scripts/get_schema_falai fal-ai/bytedance/seedream/v4.5/text-to-image`
  fetches the corresponding fal.ai docs/API page.
- fal.ai helper output identifies the endpoint ID.
- fal.ai helper output includes enough schema information to create or update a
  registry entry.
- fal.ai pricing is included when available, and omitted with a warning when
  unavailable.
- Documentation no longer references the ambiguous generic helper.

#### Suggested Checks

- Manual check Replicate helper against a known model when network access is
  intentionally allowed.
- Manual check fal.ai helper against a known docs page when network access is
  intentionally allowed.
- Manual fal.ai helper check without `FAL_KEY` confirms pricing is undefined
  with a warning.

### Ticket 5: Provider Selector UI

#### Scope

- Add a provider selector to the top-left of the generation controls, directly
  left of the model selector.
- Render only enabled providers.
- Render no-provider state clearly when no provider keys are configured.
- Changing provider refreshes:
  - model selector options;
  - selected model fallback for page state;
  - model-specific parameter controls;
  - edit availability for the selected model.
- Preserve server-rendered markup with progressive JavaScript updates.

#### Acceptance Criteria

- Provider is the first generation choice in the UI.
- Disabled providers are not selectable.
- Changing provider changes available models.
- fal.ai edit endpoints are not shown as separate normal model choices.
- Browser-side generation can be disabled when no provider is available.

#### Suggested Tests

- Index renders provider selector before model selector when providers exist.
- Index omits disabled providers.
- Index renders clear no-provider state.
- Provider/model registry JSON is provider-aware.
- JavaScript syntax check passes after dynamic selector changes.

### Ticket 6: Provider-Aware Generate API

#### Scope

- Include provider in generation request payloads.
- Validate provider and model together server-side.
- Reject unsupported, disabled, or mismatched provider/model combinations.
- Use provider-specific model metadata for parameter validation.
- Resolve fal.ai edit requests to the linked edit endpoint when edit mode is
  active.
- Reject fal.ai edit mode when no linked edit endpoint exists.
- Preserve annotated prompt handling:
  - accepted app state keeps annotated prompt;
  - provider request receives stripped prompt.

#### Acceptance Criteria

- Generate API accepts valid enabled provider/model combinations.
- Generate API rejects unknown providers.
- Generate API rejects disabled providers.
- Generate API rejects model aliases not available for the selected provider.
- fal.ai edit requests use the linked edit endpoint.
- Provider/model mismatches are rejected before request state or worker jobs are
  created.

#### Suggested Tests

- Valid Replicate request still succeeds.
- Unknown provider is rejected.
- Disabled provider is rejected.
- Wrong-provider model alias is rejected.
- fal.ai edit mode maps to linked edit endpoint.
- fal.ai edit mode without linked edit endpoint is rejected.

### Ticket 7: Provider Persistence

#### Scope

- Store provider identity in request store state.
- Store provider identity in SQLite request history.
- Store provider and provider model identity in embedded image metadata.
- For fal.ai edit requests, preserve:
  - user-facing selected model identity;
  - effective provider endpoint used for the request.
- Add or migrate SQLite schema as needed.

#### Acceptance Criteria

- Request status JSON includes provider.
- SQLite request rows include provider.
- Embedded metadata includes provider.
- Embedded metadata can identify the effective provider endpoint.
- Existing Replicate request history remains readable after migration.

#### Suggested Tests

- Request store records provider.
- Generation log persists provider.
- Embedded metadata includes provider and effective endpoint.
- Schema migration preserves existing rows.

### Ticket 8: Provider Client Boundary

#### Scope

- Extract the current Replicate generation path behind a provider-neutral
  generation interface.
- Keep Replicate request construction in a Replicate-specific client/module.
- Keep worker code provider-neutral.
- Normalize provider success into the existing stored-image pipeline.
- Normalize provider errors without hiding actionable provider detail.

#### Acceptance Criteria

- Worker dispatches through a provider-neutral interface.
- Existing Replicate generation behavior remains unchanged.
- Existing Replicate tests continue to pass.
- Stored image persistence remains shared across providers.

#### Suggested Tests

- Worker dispatches to Replicate through the provider interface.
- Replicate client request construction remains covered.
- Provider errors are propagated with useful messages.

### Ticket 9: fal.ai Provider Client

#### Scope

- Add a fal.ai client wrapper.
- Build submissions with `fal_client.submit(<endpoint_id>, arguments=...)`.
- Use the effective endpoint resolved by provider/model validation.
- Preserve returned fal.ai `request_id` as the provider request identifier.
- Poll or fetch fal.ai results according to the fal.ai client flow.
- Normalize output image URLs into the existing image persistence pipeline.
- Keep tests fake/mocked; no real fal.ai calls in automated tests.

#### Acceptance Criteria

- fal.ai text-to-image requests submit to the text endpoint.
- fal.ai edit requests submit to the linked edit endpoint.
- fal.ai result URLs are downloaded through the existing safe image persistence
  path.
- fal.ai errors keep actionable provider detail.
- No automated test calls fal.ai.

#### Suggested Tests

- fal.ai client builds expected text-to-image submission.
- fal.ai client builds expected edit submission.
- fal.ai client preserves provider request ID.
- fal.ai client normalizes successful image outputs.
- fal.ai client reports provider failures clearly.

## Gallery Download Improvements

### Ticket 10: Author And Copyright Configuration

#### Scope

- Add `AUTHOR` to `.env` generation and `env.example`.
- Fill new `.env` files with `AUTHOR=Noname Changeme Nescio`.
- Expose author metadata through typed application config.
- Add a helper to synthesize copyright from:
  - stored generation timestamp year;
  - `AUTHOR`.
- Update README and AGENTS with the metadata policy.

#### Acceptance Criteria

- Config exposes `AUTHOR`.
- New `.env` files contain the placeholder `AUTHOR` value.
- Copyright is derived from image metadata's generation year, not wall-clock
  current year.
- Documentation explains that `AUTHOR` drives stored metadata.

#### Suggested Tests

- Config loads `AUTHOR`.
- New `.env` files contain `AUTHOR=Noname Changeme Nescio`.
- Copyright derivation uses the generation year from image metadata.

### Ticket 11: Store Synthetic Metadata On Generated Images

#### Scope

- Extend embedded metadata writing so stored generated images include:
  - existing application JSON metadata;
  - prompt/display description;
  - generation timestamp;
  - author;
  - synthesized copyright;
  - application/software identity.
- Use Python/Pillow metadata handling; do not shell out to `exiftool`.
- For JPEG and WebP, write supported EXIF fields.
- For PNG, write equivalent text metadata.
- Preserve app metadata needed for gallery reload.
- Do not add fake camera metadata such as make, model, aperture, focal length,
  ISO, or exposure.

#### Acceptance Criteria

- Stored generated images are the canonical metadata-rich images.
- Existing prompt/model/parameter metadata continues to round-trip.
- JPEG/WebP files include author and synthesized copyright where supported.
- PNG files include equivalent text fields.
- Gallery metadata loading still works from stored files.

#### Suggested Tests

- JPEG metadata includes author, copyright, prompt description, and app payload.
- WebP metadata includes author, copyright, prompt description, and app payload.
- PNG text metadata includes author, copyright, prompt description, and app
  payload.
- Metadata provider can still load prompt/model/parameters from stored files.

### Ticket 12: Clean Image Export Service

#### Scope

- Add a Python helper that creates a metadata-stripped copy of a stored gallery
  image.
- Use unique temporary files under `<data_dir>/tmp`.
- Create `<data_dir>/tmp` at startup.
- Do not cache clean exports as gallery assets.
- Do not mutate the stored gallery image.
- Remove application JSON metadata and normal EXIF/text metadata where
  supported.
- Preserve image pixels and format.
- Clean temporary files opportunistically, for example on startup and/or after
  response handling where practical.
- Reject unsupported formats instead of converting silently.

#### Acceptance Criteria

- Clean PNG/JPEG/WebP exports contain no application metadata payload.
- Clean exports contain no prompt, author, or copyright metadata.
- Stored source image remains unchanged.
- Clean exports are created under `<data_dir>/tmp`.
- Clean exports do not appear in the gallery.
- Unsupported formats return clear errors.

#### Suggested Tests

- Clean JPEG export strips EXIF and app metadata.
- Clean WebP export strips EXIF and app metadata.
- Clean PNG export strips text chunks and app metadata.
- Source file metadata remains intact after clean export.
- Clean temporary files are not listed as gallery images.

### Ticket 13: Download Routes

#### Scope

- Add a route for forced download of the stored metadata-rich image.
- Add a route for forced download of a clean export.
- Keep existing image open/view route unchanged.
- Validate filenames with existing safe filename checks.
- Serve source files only from the configured output directory.
- Serve clean files only from app-created temporary export paths.
- Generate clear download filenames:
  - normal download may keep `sample.jpg`;
  - clean download may use `sample-clean.jpg`.

#### Acceptance Criteria

- Clicking the gallery image still opens/views the stored image.
- Normal download returns the stored image with attachment headers.
- Clean download returns a stripped export with attachment headers.
- Clean download does not rewrite the stored image.
- Unsafe filenames are rejected.
- Missing files return not found.

#### Suggested Tests

- Normal download returns the original image.
- Normal download uses attachment response headers.
- Clean download returns a metadata-stripped file.
- Clean download uses attachment response headers.
- Clean download filename includes `-clean`.
- Path traversal is rejected.
- Missing image is rejected.

### Ticket 14: Gallery Download Controls And Icons

#### Scope

- Add explicit normal download and clean download controls to each gallery item.
- Normal download uses a cloud-with-down-arrow icon.
- Clean download uses the same cloud-with-down-arrow icon with a small sparkle
  overlay offset to the right.
- Do not use disk icons for these actions.
- Keep current gallery actions compact and touch-friendly.
- Keep trash spacing and two-step delete behavior intact.
- Implement controls in both server-rendered gallery markup and JavaScript
  gallery refresh rendering.

#### Acceptance Criteria

- Users can distinguish normal metadata-rich download from clean download.
- Buttons have accessible labels.
- Icons render consistently in initial page load and refreshed gallery items.
- Text does not overlap at mobile/tablet/desktop widths.

#### Suggested Tests

- Route/render tests verify action markup and accessible labels.
- JavaScript syntax check passes.
- Browser visual testing is manual/user-authorized only.

### Ticket 15: Gallery Download Documentation

#### Scope

- Update README and AGENTS for:
  - stored images as metadata-rich canonical files;
  - `AUTHOR` metadata setting;
  - synthesized copyright behavior;
  - clean download behavior;
  - normal download versus open/view;
  - no `exiftool` shell dependency.

#### Acceptance Criteria

- User docs explain which download contains metadata.
- User docs explain which download strips metadata.
- Contributor docs mention Python metadata handling and no shell `exiftool`.
- Docs stay consistent with `SCENARIO.md`.

#### Suggested Tests

- Documentation-only unless docs tooling is introduced.

