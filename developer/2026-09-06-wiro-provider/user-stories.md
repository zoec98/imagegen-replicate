# Wiro uncensored Seedream provider

## Epic

As an img-replicate user, I want to generate and edit images through Wiro's
Seedream 5 Pro Uncensored and Seedream 5 Lite Uncensored endpoints so that I
can use the Wiro deployments that accept legitimate prompts rejected by the
existing Replicate and fal.ai deployments while retaining the application's
normal gallery, metadata, and generation-history behavior.

## Evidence

- Interactive smoke testing confirmed that Wiro's Seedream 5 Pro Uncensored
  endpoint accepted prompts previously rejected by Replicate and fal.ai.
- Wiro publicly lists
  [`bytedance/seedream-v5-pro-uncensored`](https://wiro.ai/models/bytedance/seedream-v5-pro-uncensored)
  and
  [`bytedance/seedream-v5-lite-uncensored`](https://wiro.ai/models/bytedance/seedream-v5-lite-uncensored)
  as text-to-image and image-to-image models.
- [Wiro's API documentation](https://wiro.ai/docs) exposes model metadata
  through `POST /v1/Tool/Detail` and generation through its asynchronous Run
  and Task APIs.
- The API-key-only project created for this epic issued both a
  `WIRO_API_KEY` and `WIRO_API_SECRET`, despite Wiro's public documentation
  describing API-key-only projects as requiring only the key.
- Authenticated model-detail requests using only `WIRO_API_KEY` succeeded for
  both uncensored models; `WIRO_API_SECRET` was not required.

## Decisions

- Add `wiro` as a third provider; do not replace Replicate or fal.ai.
- Initially register only the two uncensored Seedream 5 endpoints:
  `seedream5-pro-uncensored` and `seedream5-lite-uncensored`.
- Treat each uncensored deployment as a distinct provider model. Do not expose
  a generic safety switch or silently substitute a regular endpoint.
- Include both models; authenticated schema discovery confirmed that each is
  available to the configured Wiro project.
- Use the server-side Wiro project configured for API-key-only authentication
  and send only `WIRO_API_KEY` as `x-api-key`.
- Do not add `WIRO_API_SECRET` to application configuration for this epic.
- Use the already-installed `httpx` dependency. Do not add a Wiro SDK.
- Submit asynchronously and poll the existing task with Wiro's Task Detail API.
  Do not use WebSockets, callbacks, or automatic cross-provider failover.
- Keep registry entries static and reviewable. Schema discovery informs them
  but does not dynamically change application behavior at runtime.

## Story 1: Discover Wiro model contracts

As a maintainer, I want a `scripts/get_schema_wiro` command so that Wiro model
parameters, capabilities, pricing, and response shapes can be captured from
the provider instead of copied from marketing pages or inferred from another
provider's Seedream schema.

### Acceptance criteria

- The command accepts one model reference in `owner/model` form.
- The command reads `WIRO_API_KEY` without printing or persisting it.
- The command does not read or require `WIRO_API_SECRET`.
- The command calls Wiro's model-detail API and does not start a generation.
- Output identifies the requested model, provider documentation/runtime URLs,
  model availability, input parameters, required fields, defaults, choices,
  bounds, file cardinality, output shape, and provider-reported pricing when
  present.
- Output highlights evidence for text generation, image editing, and the
  maximum number of source images.
- Missing credentials, unknown models, malformed responses, and network errors
  fail with an actionable non-zero result.
- The command reproduces the authenticated discovery findings recorded in
  `schema-discovery.md`; any later difference is reported rather than guessed
  around.

## Story 2: Configure and discover Wiro

As a user, I want Wiro to appear alongside the existing providers when I
configure a Wiro key so that its supported models are discoverable in the web
interface and CLI.

### Acceptance criteria

- `WIRO_API_KEY` is supported by setup, `.env.example`, and configuration
  loading and is never exposed to the browser, logs, metadata, or errors.
- Wiro is enabled only when its API key is non-empty.
- When enabled, provider discovery shows `Wiro` and exactly the confirmed
  uncensored Seedream models in this epic.
- Each model has a unique Wiro-local alias and display name that clearly says
  `Uncensored`.
- Wiro-only configuration selects Wiro by default; existing default-provider
  behavior remains unchanged when Replicate or fal.ai is configured.
- Model parameters and edit capability come from Wiro-specific registry data,
  not copied from Replicate or fal.ai entries.

## Story 3: Generate images through Wiro

As a user, I want Wiro text-to-image requests to behave like requests through
the existing providers so that successful results enter the same gallery and
history without a Wiro-specific workflow.

### Acceptance criteria

- Requests use the exact Wiro endpoint associated with the selected uncensored
  model.
- Prompt annotations are validated and stripped before the prompt is sent.
- Wiro-specific parameters are validated server-side from registry metadata
  before submission.
- The provider submits one task, retains its task identifier, and polls that
  same task until success, failure, cancellation, or timeout without creating
  duplicate billable runs.
- Success requires Wiro's terminal success state and success exit value; a
  nominal HTTP success containing a failed task is not accepted.
- Returned image URLs are normalized and persisted through the existing image
  store, embedded metadata, gallery, and generation-history boundaries.
- Stored metadata identifies provider `wiro`, the selected local alias, the
  exact Wiro model reference, task identifier, prompt, and submitted inputs.

## Story 4: Edit images through Wiro

As a user, I want to edit gallery images with either uncensored Seedream 5
model so that Wiro can be used from the application's existing edit workflow.

### Acceptance criteria

- Edit mode is available only when authenticated schema discovery confirms the
  endpoint accepts source images.
- Existing source-image selection, count limits, filename validation, and local
  path containment remain authoritative.
- Source images are sent using the field names, multiplicity, and upload form
  documented by Wiro; users do not need to make local gallery files publicly
  accessible.
- Provider source-image fields cannot be injected through the generic
  parameters object.
- Submitted source filenames are recorded in local metadata, while remote
  upload URLs and credentials are not.
- Text-only generation remains valid when the Wiro schema makes source images
  optional.

## Story 5: Report Wiro outcomes safely

As a user, I want actionable Wiro status and error reporting so that I can
distinguish invalid input, provider rejection, task failure, timeout, and an
invalid output without exposing credentials.

### Acceptance criteria

- Authentication, validation, rate-limit, provider-policy, task, timeout, and
  malformed-response failures produce distinct actionable errors.
- Wiro task identifiers and safe provider details are retained for support and
  troubleshooting.
- API keys, authentication headers, local absolute paths, and remote upload
  credentials never appear in browser responses, logs, or embedded metadata.
- A successful task with no valid image URL fails explicitly.
- Output URLs continue through the existing HTTPS, redirect, address, content
  type, and size validation before any file is stored.
- Automated tests use fake HTTP responses and never call or bill Wiro.

## Story 6: Document and verify the provider

As an operator, I want setup and verification instructions so that I can
configure Wiro and confirm both uncensored models without exposing the key or
mistaking playground behavior for API behavior.

### Acceptance criteria

- End-user documentation explains creation of an API-key-only Wiro project,
  `WIRO_API_KEY` configuration, provider/model selection, and supported edit
  limits.
- Provider documentation records the schema command, model references, schema
  retrieval date, pricing source, and any account-specific availability found
  during discovery.
- Mocked automated tests cover provider discovery, request construction, task
  polling, success, failure, timeout, output normalization, and edit uploads.
- A manual paid smoke test covers text generation and one-image editing for
  both Pro and Lite after implementation.
- Full project checks required by `AGENTS.md` pass before the epic is complete.

## Out of scope

- Wiro's regular Seedream endpoints or other Wiro catalog models.
- Runtime model discovery or automatic registry updates.
- A user-configurable safety-filter toggle.
- HMAC/signature authentication.
- WebSocket progress, callbacks, and webhooks.
- Automatic retry that creates a second billable task.
- Automatic failover between Wiro, fal.ai, and Replicate.
- Provider-side moderation guarantees beyond the behavior of the selected Wiro
  endpoint and Wiro's current terms.
- Broad renaming of the existing legacy polling and timeout settings.
