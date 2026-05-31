# Implementation Plan

This plan is derived from `SCENARIO.md`. The work is grouped by topic:

- image-generation-provider: Stories 1, 2, and 3.
- gallery download improvements: Stories 4, 5, and 6.

Those two groups cover the current scenario. Provider work owns provider
selection, provider-specific registries, schema tooling, and pricing metadata.
Gallery work owns stored image metadata, clean exports, and download controls.

## Image Generation Provider

### Ticket 1: Provider-Aware Configuration

#### Scope

- Add `FAL_KEY` or the provider key name chosen by the fal.ai client library to
  `.env` generation and `env.example`.
- Represent enabled providers from available API keys.
- Keep Replicate enabled only when `REPLICATE_API_TOKEN` is configured.
- Keep fal.ai enabled only when the fal.ai key is configured.
- Provide a clear UI/server message when no generation provider is configured.
- Preserve tests without real provider API calls.

#### Acceptance Criteria

- Missing API keys are allowed at startup.
- Providers without API keys are not offered for generation.
- The app reports a clear error if no provider can be used.
- Existing Replicate-only tests continue to pass with a fake/no-op worker.
- `env.example` documents both provider keys.

#### Suggested Tests

- Config loads with no provider keys.
- Config reports Replicate enabled when `REPLICATE_API_TOKEN` is set.
- Config reports fal.ai enabled when the fal.ai key is set.
- Index rendering shows only enabled providers.

### Ticket 2: Provider-Aware Model Registry Shape

#### Scope

- Introduce provider identity in model metadata.
- Either split registries by provider or add provider filtering to a single
  registry.
- Keep provider-specific model keys, versions, schemas, pricing, capabilities,
  parameter names, defaults, limits, and output metadata distinct.
- Add a pricing source field for registry pricing metadata:
  - `provider_api`;
  - `static`;
  - `unknown`.
- Keep current Replicate models represented as Replicate provider entries.

#### Acceptance Criteria

- Model aliases are unique within a provider.
- The UI/API can list models for one provider without leaking models from
  another provider.
- Existing Replicate model behavior remains unchanged for current models.
- Pricing can be displayed with its source, or omitted clearly when unknown.

#### Suggested Tests

- Registry filters models by provider.
- Duplicate aliases across different providers are handled intentionally.
- Replicate entries preserve existing pricing as `static`.
- Unknown pricing is represented explicitly rather than guessed.

### Ticket 3: Provider Selector UI

#### Scope

- Add a provider selector to the top-left of the generation controls, directly
  left of the model selector.
- Changing provider refreshes the model selector options.
- Keep model-specific parameter controls synced with the selected provider and
  model.
- Do not offer providers that are disabled by missing API keys.
- Preserve server-rendered behavior and progressive JavaScript style.

#### Acceptance Criteria

- Provider is the first generation choice in the UI.
- Changing provider changes available model options.
- Disabled providers are not selectable.
- Submitting an unsupported provider is rejected server-side.
- The browser can disable generation when no provider is available, but server
  validation remains authoritative.

#### Suggested Tests

- Index includes provider selector before model selector when providers exist.
- Provider/model registry JSON is provider-aware.
- API rejects unsupported provider values.
- API rejects a provider that is not configured.

### Ticket 4: Provider-Aware Request Validation And Persistence

#### Scope

- Include selected provider in generation request payloads.
- Validate provider and model together server-side.
- Use provider-specific model metadata for parameter validation.
- Store provider identity in request store state, SQLite request history, and
  embedded image metadata.
- Preserve annotated prompt behavior: stored app metadata keeps annotated
  prompts; provider calls receive stripped prompt text.

#### Acceptance Criteria

- Request state includes provider.
- SQLite request rows include provider.
- Embedded metadata includes provider and provider model identity.
- Existing Replicate requests continue to use Replicate request construction.
- Provider/model mismatches are rejected before worker jobs are created.

#### Suggested Tests

- Generate API accepts configured provider/model combinations.
- Generate API rejects unknown provider.
- Generate API rejects model alias not available for selected provider.
- Generation log persists provider.
- Embedded metadata contains provider.

### Ticket 5: Provider Client Boundary

#### Scope

- Extract or generalize the current Replicate generation path behind a provider
  client boundary.
- Keep Replicate request construction in a Replicate-specific client.
- Add a fal.ai client wrapper with fakeable request/response behavior.
- Normalize successful provider responses into the app's stored-image pipeline.
- Normalize provider errors without hiding actionable provider details.

#### Acceptance Criteria

- Worker code calls a provider-neutral generation interface.
- Replicate behavior remains covered by existing tests.
- fal.ai client behavior is covered with fakes/mocks and no network calls.
- Downloaded output images still flow through the same safe image persistence
  and metadata embedding boundary.

#### Suggested Tests

- Worker dispatches to the selected provider client.
- Replicate client tests continue to pass.
- fal.ai client builds expected request payloads.
- fal.ai client handles failed provider responses with useful errors.

### Ticket 6: Replicate Schema Helper Rename

#### Scope

- Rename `scripts/get_schema` to `scripts/get_schema_replicate`.
- Update README and AGENTS references.
- Either remove `scripts/get_schema` or replace it with a compatibility message
  that points to provider-specific helpers.
- Preserve existing Replicate schema extraction behavior.

#### Acceptance Criteria

- `scripts/get_schema_replicate owner/model` works as the old Replicate helper
  did.
- Documentation no longer directs maintainers to the ambiguous generic helper.
- The old helper name does not silently fetch Replicate schemas for all
  provider work.

#### Suggested Tests

- If script tests are added, use fixture HTML rather than live replicate.com.
- Manual check: run the helper against a known model only when network access is
  intentionally allowed.

### Ticket 7: fal.ai Schema And Pricing Helper

#### Scope

- Add `scripts/get_schema_falai`.
- Fetch or print useful fal.ai model schema information for registry authoring.
- Fetch fal.ai pricing from the documented Platform API when available.
- Mark fetched fal.ai pricing with source `provider_api`.
- Represent missing fal.ai pricing as `unknown`.
- Do not make live network calls from normal unit tests.

#### Acceptance Criteria

- `scripts/get_schema_falai fal-ai/example-model` has a clear usage path.
- fal.ai pricing can be obtained from
  `/v1/models/pricing?endpoint_id=<endpoint_id>` when credentials allow it.
- Output includes enough information to create or update a fal.ai registry
  entry.
- Failure modes are explicit when credentials, endpoint IDs, or pricing data are
  unavailable.

#### Suggested Tests

- Unit-test fal.ai schema/pricing parsing with fixture JSON.
- Unit-test missing pricing as `unknown`.
- Unit-test provider API pricing as `provider_api`.

## Gallery Download Improvements

### Ticket 8: Author And Copyright Configuration

#### Scope

- Add `.env` settings for exported/stored image author and copyright metadata.
- Decide whether copyright is configured directly or derived from author and
  generation year.
- Keep missing values explicit: either fail clearly when required for metadata
  writing or omit with clear UI/server status.
- Update `env.example`, README, and AGENTS.

#### Acceptance Criteria

- Config exposes author metadata.
- Config exposes copyright metadata or enough information to derive it.
- Documentation explains how these values are used.
- Missing required metadata does not produce misleading synthetic metadata.

#### Suggested Tests

- Config loads author/copyright values.
- Config handles absent values as documented.
- Copyright derivation uses the generation year when that approach is chosen.

### Ticket 9: Store Synthetic Metadata On Generated Images

#### Scope

- Extend existing embedded metadata writing so stored generated images include:
  - current app prompt/application metadata;
  - human-readable prompt/display data;
  - generation timestamp;
  - author;
  - copyright;
  - application/software identity.
- Use Python/Pillow metadata handling; do not shell out to `exiftool`.
- For JPEG and WebP, write supported EXIF fields.
- For PNG, write equivalent text metadata.
- Preserve the application JSON metadata payload needed for gallery reload.

#### Acceptance Criteria

- Stored generated images are the canonical metadata-rich images.
- Existing prompt and app metadata continue to round-trip.
- JPEG/WebP files include author/copyright where supported.
- PNG files include equivalent text fields.
- No fake full camera metadata is added.

#### Suggested Tests

- JPEG synthetic metadata includes author, copyright, description/prompt, and
  application metadata.
- WebP synthetic metadata includes author, copyright, description/prompt, and
  application metadata.
- PNG text metadata includes author, copyright, description/prompt, and
  application metadata.
- Existing metadata provider can still load prompt/model/parameters from the
  stored file.

### Ticket 10: Clean Image Export Service

#### Scope

- Add a Python service/helper that creates a metadata-stripped copy of a stored
  gallery image.
- Do not mutate the stored gallery image.
- Remove application JSON metadata and normal EXIF/text metadata where supported.
- Preserve image pixels and format.
- Reject unsupported formats instead of converting silently.

#### Acceptance Criteria

- Clean export for PNG/JPEG/WebP contains no application metadata payload.
- Clean export contains no prompt, author, or copyright metadata.
- Stored source image remains unchanged.
- Unsupported formats return clear errors.

#### Suggested Tests

- Clean JPEG export strips EXIF and app metadata.
- Clean WebP export strips EXIF and app metadata.
- Clean PNG export strips text chunks and app metadata.
- Source file metadata remains intact after clean export.

### Ticket 11: Download Routes

#### Scope

- Add a route for normal stored-image download.
- Add a route for clean download.
- Keep existing image view/open behavior unchanged.
- Validate filenames with existing safe filename checks.
- Serve files only from the configured output directory.
- Generate clear download filenames:
  - normal download may keep `sample.jpg`;
  - clean download may use `sample-clean.jpg`.

#### Acceptance Criteria

- Normal download returns the stored metadata-rich image.
- Clean download returns a stripped export without rewriting the stored image.
- Unsafe filenames are rejected.
- Missing files return not found.
- Route tests do not require browser automation.

#### Suggested Tests

- Normal download returns the original image bytes/metadata.
- Clean download returns a metadata-stripped file.
- Clean download filename includes `-clean`.
- Path traversal is rejected.
- Missing image is rejected.

### Ticket 12: Gallery Download Controls And Icons

#### Scope

- Add explicit normal download and clean download controls to each gallery item.
- Normal download uses a cloud-with-down-arrow icon.
- Clean download uses the same cloud-with-down-arrow icon with a small sparkle
  overlay offset to the right.
- Do not use disk icons for these actions.
- Keep current gallery actions compact and touch-friendly.
- Keep trash spacing and two-step delete behavior intact.

#### Acceptance Criteria

- Users can distinguish normal metadata-rich download from clean download.
- Buttons have accessible labels.
- Icons render consistently in server-rendered gallery and refreshed gallery
  JavaScript.
- Text does not overlap at mobile/tablet/desktop widths.

#### Suggested Tests

- Route/render tests verify action markup and accessible labels.
- JavaScript syntax check passes.
- Browser visual testing is manual/user-authorized only.

### Ticket 13: Gallery Download Documentation

#### Scope

- Update README and AGENTS for:
  - stored images as metadata-rich canonical files;
  - author/copyright metadata settings;
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

## Open Questions

- Should fal.ai use environment variable `FAL_KEY`, `FAL_API_KEY`, or both with
  one canonical internal config name?
- If both Replicate and fal.ai keys are present, which provider should be
  selected by default on first page load?
- Should provider/model aliases be globally unique, or unique only within each
  provider?
- Should `scripts/get_schema` be removed entirely, or kept as a compatibility
  wrapper that prints an error pointing to `scripts/get_schema_replicate` and
  `scripts/get_schema_falai`?
- Should fal.ai pricing be fetched during schema-helper use only, or should the
  app have a runtime/cache refresh path for pricing?
- Should author/copyright metadata be required for generation, or should missing
  values allow generation while omitting those fields?
- What exact `.env` names should be used for author and copyright metadata?
- Should copyright be configured literally, derived from author plus generation
  year, or support both?
- For clean download, should the app stream an in-memory stripped image, write a
  temporary file under the data directory, or cache clean exports?
- Should normal download be a separate button from opening the image in a new
  tab, or is the existing image link sufficient once the clean button exists?
