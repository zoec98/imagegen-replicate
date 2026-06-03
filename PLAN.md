# Implementation Plan

This plan is derived from `SCENARIO.md`.

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
