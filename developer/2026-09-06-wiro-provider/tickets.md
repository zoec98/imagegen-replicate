# Wiro uncensored Seedream provider — tickets

These tickets implement the committed Wiro provider stories in behavior-first
order. Wiro remains unavailable from normal application configuration until its
registry contract and provider client are complete, so no intermediate commit
exposes a provider that cannot generate.

Implementation constraints shared by every ticket:

- Use only `WIRO_API_KEY`, sent as `x-api-key` to the fixed HTTPS Wiro API
  origin. Do not load or use `WIRO_API_SECRET`.
- Treat `Uncensored` as part of each exact model identity. Do not add a generic
  safety setting or weaken any application validation.
- Use the installed `httpx` dependency and existing provider, request,
  source-image, image-store, metadata, and generation-history boundaries.
- Automated tests use fake HTTP responses and local temporary files only. They
  must never submit or bill a real Wiro task.
- Add one failing behavior test at a time, make it pass with the smallest
  change, and commit each completed ticket before starting the next.

## 1. Add authenticated Wiro schema discovery

Provide `scripts/get_schema_wiro owner/model` as the repeatable maintainer
interface for inspecting a Wiro model without starting a generation.

Behavior to prove first:

- A valid `owner/model` and `WIRO_API_KEY` request Wiro's Tool Detail endpoint
  and never call a Run endpoint.
- The request authenticates with `x-api-key`; the key is absent from stdout,
  stderr, and failures.
- The report names the model, documentation/runtime URLs, availability,
  capabilities, inputs, requirements, defaults, choices, bounds, source-image
  cardinality, output information, expected runtime, and provider pricing when
  Wiro supplies them.
- The report explicitly summarizes text-to-image support, image-to-image
  support, and the source-image limit.
- Missing credentials, malformed model references, unknown models, network
  failures, and malformed provider responses exit non-zero with actionable
  messages.
- Sanitized fake responses for Pro and Lite reproduce the contracts in
  `schema-discovery.md`, including Lite's duplicate legacy auto values being
  reported without inventing a second user choice.

Keep the command self-contained and standard-library based unless a smaller
existing project helper already covers the behavior.

Public interface: `scripts/get_schema_wiro owner/model` and its Markdown-style
terminal report.

Likely touchpoints: `scripts/get_schema_wiro`, one focused test module, and
`AGENTS.md`'s script inventory.

Verification: exercise missing-key, invalid-model, Pro, Lite, and malformed
response cases with fakes, then run `uv run pytest` and
`uv run ruff check src tests`.

## 2. Register the two Wiro model contracts

Add provider-scoped registry data for exactly the two authenticated endpoints,
without enabling Wiro from environment configuration yet.

Behavior to prove first:

- Provider lookup recognizes `wiro` with display name `Wiro`.
- Wiro contains exactly `seedream5-pro-uncensored` and
  `seedream5-lite-uncensored`; each resolves only inside the Wiro provider and
  has a display name containing `Uncensored`.
- Both text and edit targets use their exact
  `bytedance/seedream-v5-*-uncensored` model identity and the fixed Wiro
  documentation/runtime origin.
- Pro exposes the authenticated `resolution`, `aspectRatio`, `outputFormat`,
  and string-valued `watermark` contract. Its edit target binds up to 10
  sources to `inputImage`.
- Lite exposes `resolution`, `aspectRatio`, `maxImages`, and string-valued
  `watermark`; the UI has one `auto` choice for each applicable field. Its edit
  target binds up to 14 sources to `inputImage`.
- Lite validates `maxImages` from 1 through 15, and validation rejects an edit
  when selected sources plus requested outputs exceed 15.
- Prompt and `inputImage` cannot be supplied through generic model parameters;
  the existing source-image boundary remains authoritative.
- Provider pricing records the authenticated Tool Detail values and identifies
  the provider API as their source.

Do not copy a Replicate or fal.ai Seedream registry entry: the Wiro contracts
and camel-case field names are provider-specific.

Public interface: provider/model discovery, generation-target resolution, and
registry-driven parameter validation.

Likely touchpoints: `src/imagegen/model_registry_base.py`,
`src/imagegen/model_registry.py`, one Wiro registry module,
`src/imagegen/generation_validation.py`, and registry/validation tests.

Verification: prove provider-scoped lookup, exact target/input shapes, edit
limits, and generic source-field rejection, then run `uv run pytest` and
`uv run ruff check src tests`.

## 3. Implement the Wiro asynchronous text-generation client

Implement the provider boundary for one text-to-image task from submission
through local persistence, while keeping it unconfigured in the application.

Behavior to prove first:

- A request strips prompt annotations, builds defaults and validated Wiro
  parameters through the shared request builder, and submits exactly once to
  `POST /v1/Run/{owner}/{model}`.
- Requests use only the fixed Wiro HTTPS origin and `x-api-key`; no callback,
  WebSocket, configurable base URL, or secret is used.
- A successful submission retains the returned task identifier and polls only
  that task through `POST /v1/Task/Detail` until Wiro's terminal post-process
  event.
- Success requires both the terminal success event and `pexit == "0"`.
- Output URL normalization accepts the documented Task Detail output shape,
  removes duplicates, and rejects a nominal success with no valid HTTPS image
  URL.
- Successful URLs pass to the existing image store with provider `wiro`, local
  alias, exact Wiro model, original annotated prompt, task identifier, and the
  provider-ready metadata input.
- Polling uses the existing configured poll interval and timeout, performs no
  automatic resubmission, and raises the shared provider timeout at the runtime
  adapter boundary.
- Authentication, validation, rate-limit, provider-policy, cancelled/failed
  task, timeout, malformed-response, and missing-output cases are distinct and
  actionable. When a task exists, the safe task identifier remains available
  on the failure without credentials, headers, or local paths.

Use fake HTTP transport and an injected clock/sleep in tests. Do not add an SDK,
callback server, retry framework, or a generic provider-client abstraction.

Public interface: the Wiro client generation function and its Wiro
request/timeout failures, matching the existing provider-client result shape.

Likely touchpoints: one `src/imagegen/wiro_client.py` module,
`src/imagegen/generation_provider.py`, and `tests/test_wiro_client.py`.

Verification: prove one submit across multi-poll success, every terminal
failure family, timeout, malformed data, URL normalization, and image-store
arguments, then run `uv run pytest` and `uv run ruff check src tests`.

## 4. Add Wiro source-image editing

Extend the completed Wiro client to send selected gallery sources through each
model's existing edit target without requiring public source URLs.

Behavior to prove first:

- A text-only request remains a normal non-multipart generation when no source
  is selected.
- An edit request opens only source paths supplied by the existing
  source-image resolver and sends them under Wiro's `inputImage` multipart
  field with the required repeated-field representation.
- Pro accepts at most 10 sources and Lite at most 14; Lite also enforces the
  combined source-plus-output limit of 15 before submission.
- Every opened stream is closed after success, provider failure, network
  failure, or timeout.
- The provider submission receives upload parts, while persisted metadata
  contains local source filenames and never absolute paths, remote upload URLs,
  credentials, or headers.
- `inputImage` from generic parameters cannot replace or add to the validated
  selected sources.
- Editing follows the same single-submit polling, terminal-state, output
  normalization, and image-store behavior as text generation.

Confirm the multipart field representation against Wiro's current API
documentation and record any contract correction in `schema-discovery.md`.

Public interface: the Wiro client called with `source_image_paths` and the
existing provider edit workflow.

Likely touchpoints: `src/imagegen/wiro_client.py`, its focused tests, and
`schema-discovery.md` only if live documentation resolves an ambiguity.

Verification: fake Pro and Lite multipart requests, boundary counts, combined
Lite counts, metadata filenames, stream closure on success/failure, and a
source-free request, then run `uv run pytest` and
`uv run ruff check src tests`.

## 5. Enable Wiro across configuration and generation workflows

Expose the now-complete provider through the existing web and CLI workflows
when, and only when, `WIRO_API_KEY` is configured.

Behavior to prove first:

- `.env` creation, `.env.example`, and configuration loading support
  `WIRO_API_KEY`; the secret value is never serialized to browser state,
  metadata, history, or error output.
- An empty key leaves Wiro disabled. A Wiro-only configuration enables and
  selects Wiro; Replicate remains preferred when configured, followed by the
  existing fal.ai priority, so current mixed-provider defaults do not change.
- Provider/model discovery shows the two Wiro models only when Wiro is enabled,
  and both are selectable through the existing web and CLI interfaces.
- The default provider map dispatches Wiro requests to the Wiro client and
  translates Wiro timeout failures into the shared timeout result.
- API provider validation, generation history, embedded metadata lookup, and
  source-image metadata recognize `wiro` without changing legacy Replicate or
  fal.ai records.
- A fake text request and a fake one-image edit travel through the public
  generation API/worker path, reach a terminal result, and store the exact
  provider/model/task/input metadata required by the stories.
- Failed and timed-out tasks retain their Wiro task identifier in durable
  generation state when submission produced one, while browser-visible errors
  remain safe plain text.
- Returned URLs continue through the existing image-store HTTPS, redirect,
  address, content-type, and size validation; the Wiro integration does not
  bypass or duplicate it.

Reuse the existing legacy poll and timeout settings for this epic. Do not add
Wiro-specific timing settings or rename the existing settings.

Public interface: application configuration, provider/model discovery, the
generation API, synchronous CLI generation, durable history, and embedded
metadata.

Likely touchpoints: `src/imagegen/config.py`, `src/imagegen/api_routes.py`,
`src/imagegen/generation_provider.py`, `src/imagegen/worker.py`,
`src/imagegen/generation_log.py`, `src/imagegen/metadata.py`, templates that
name configured credentials, and their existing focused tests.

Verification: cover Wiro-only and mixed configuration, web/CLI discovery,
successful text/edit generations, safe failures with task identifiers, and
legacy-provider regression behavior, then run `uv run pytest` and
`uv run ruff check src tests`.

## 6. Document and smoke-test both endpoints

Complete operator documentation and verify the real API only after all mocked
behavior is green.

Behavior to verify:

- `README.md` explains creating an API-key-only Wiro project, setting only
  `WIRO_API_KEY`, choosing Wiro and either uncensored model, and the Pro/Lite
  edit limits.
- `developer/provider-models.md` records the schema command, exact model
  references, retrieval date, pricing source, provider-specific fields, and
  the absence of a generic safety flag.
- `schema-discovery.md` records the observed terminal state, `pexit`, output
  object, error envelope, and multipart representation verified during
  implementation.
- A deliberate paid smoke test performs text generation and one-image editing
  once on Pro and once on Lite. It records safe task/result facts and cost
  observations without prompts, private images, credentials, headers, signed
  URLs, or absolute paths.
- Playground success is not presented as API verification, and documentation
  does not promise that `Uncensored` removes account, legal, or provider-policy
  constraints.

Public interface: setup/usage documentation and a concise manual smoke-test
record under this epic directory.

Likely touchpoints: `README.md`, `developer/provider-models.md`,
`developer/2026-09-06-wiro-provider/schema-discovery.md`, and a smoke-test note
in this epic directory.

Verification:

- `uv run pytest`
- `uv run ruff format src tests`
- `uv run ruff check --fix src tests`
- `npm run js:check` only if implementation changed browser JavaScript
- Run `scripts/get_schema_wiro` for both registered models
- Perform the four explicitly approved paid smoke requests and inspect their
  stored gallery/history metadata

Do not begin the paid smoke test without confirming its four billable requests
with the user at implementation time.
