# Wiro model parity research — tickets

These tickets implement the committed scope in `user-stories.md`. Research is
the first delivery and the decision gate for all registry implementation; no
model is added from name similarity or a guessed Wiro model reference.

## 1. Inventory matching Wiro models and contracts

Research Wiro's current offering for the 19 `Research` model families and
report alternate Wiro variants for the two `Already covered` Seedream
families. Write the evidence and conclusions to `research.md` in this epic
directory. Do not change the model registry in this ticket.

Behavior and evidence to establish:

- The research table preserves every row from `user-stories.md`. The seven
  `Skip` rows are marked excluded without querying or implementing them; the 19
  `Research` rows receive `available`, `unavailable`, `ambiguous`, or `blocked`
  status; the two `Already covered` rows report alternate variants only.
- Candidate endpoints are found through Wiro's current catalog or search, with
  the source and retrieval date recorded. A guessed `owner/model` or matching
  display name is not accepted as proof.
- Every candidate exact endpoint is verified with
  `scripts/get_schema_wiro owner/model`, which loads `WIRO_API_KEY` from the
  project `.env` and calls the non-generating Tool Detail API.
- Each available endpoint records its exact `owner/model`, display name,
  documentation and runtime URLs, normal or uncensored variant, text/edit
  capabilities, parameters, defaults, choices, bounds, fixed inputs,
  source-image limits, output shape, expected runtime, and provider-reported
  pricing.
- If normal and uncensored variants both exist, the uncensored endpoint is the
  implementation candidate and the normal endpoint is report-only. A normal
  endpoint is an implementation candidate when no uncensored variant exists.
- More or alternate versions are reported without automatically expanding
  implementation scope. Ambiguous matches explain what evidence is missing.
  Unavailable conclusions state which catalog/search evidence was checked so
  absence is not inferred only from a failed guessed reference.
- The report identifies the exact set of Wiro endpoints recommended for later
  implementation and notes any contract that the existing Wiro client or
  registry cannot represent.
- No Run endpoint or other billable generation is called. Credentials, API
  headers, private images, prompts, signed URLs, and raw sensitive response
  fields are not recorded.

Use the existing schema script as the repeatable contract boundary. Extend it
only if a confirmed candidate exposes relevant Tool Detail data that the
current safe report cannot represent; if code changes become necessary, cover
that observable report behavior with one failing test before the minimum fix.

Public artifact: `developer/2026-09-07-wiro-model-parity/research.md`.

Verification:

- Reconcile the report against all 28 inventory rows and the 19/7/2 interest
  counts.
- Re-run `scripts/get_schema_wiro` successfully for every endpoint marked
  available or already covered.
- Check the report for credentials, headers, signed URLs, local private paths,
  and unsupported claims.
- Run `git diff --check`. If the schema script changes, also run its focused
  tests, `uv run pytest`, and `uv run ruff check src tests`.

Commit `research.md` and any necessary schema-report improvement before the
decision gate below.

## Research decision

Ticket 1 is committed as `2b6e5de`. Its authenticated research recommends ten
exact endpoints. The following implementation tickets are a draft and require
approval and a tickets commit before Ticket 2 starts. No unavailable,
ambiguous, excluded, already-covered, or report-only endpoint receives a code
ticket.

All tickets use the contract in `research.md` and re-run
`scripts/get_schema_wiro` before editing the registry. Follow red-green-refactor:
write the smallest failing registry/client test, implement only that contract,
run focused tests, then run the full required checks before committing.
Complicated provider price matrices are displayed as the researched minimum-to-
maximum range for operator guidance; the provider account remains authoritative
for billing. Safety controls are fixed, hidden application policy: off where
available, `low` for GPT moderation, and the highest documented tolerance for
Flux.

## 2. Add Seedream 4.5 Uncensored

Add provider-scoped alias `wiro:seedream45-uncensored` for
`bytedance/seedream-v4-5-uncensored`. This is the smallest new contract because
it reuses the proven Seedream Lite parameter and source-plus-output shape.

- Expose the exact resolution, ratio, output-count, watermark, pricing, and
  14-source/15-total contract for text and edit modes.
- Keep watermark `false` by default and do not add a safety input that Tool
  Detail does not expose.
- Prove web/CLI discovery, validation, fake multipart editing, and persisted
  provider/model metadata without changing existing Seedream entries.
- Update the Wiro operator contract in `developer/provider-models.md`.

Commit after full Python tests and lint pass.

## 3. Add Z-Image Turbo

Add text-only alias `wiro:z-image-turbo` for
`tongyi-mai/z-image-turbo`.

- Represent the exact steps, scale, seed, resolution, ratio, runtime, and
  `$0.006` per-run price; preserve Wiro's text-valued numeric seed contract.
- Prove discovery, rejection of edit mode and out-of-contract values, JSON
  request serialization through a fake transport, and metadata/history.
- Update the Wiro operator contract.

Commit after full Python tests and lint pass.

## 4. Add the HiDream Dev and Fast variants

Add `wiro:hidream-dev` and `wiro:hidream-fast` for the two exact HiDream
endpoints. Research proved a shared text-only schema; keep only the differing
step/flow-shift defaults, runtime, identity, and display name variant-specific.

- Represent prompt, negative prompt, steps, scale, flow shift, samples, seed,
  width, and height exactly.
- Do not invent a static price: Tool Detail supplied no dynamic price for
  either endpoint.
- Prove both entries independently discoverable, text-only, validated, and
  serialized while sharing only existing or genuinely duplicated helpers.
- Update the Wiro operator contract.

Commit after full Python tests and lint pass.

## 5. Add Grok Imagine Image

Add `wiro:grok-imagine` for `xai/grok-imagine-image`.

- Expose the exact sample count, ratio choices, resolution choices, one-source
  edit limit, runtime, and `$0.02` per-output price.
- Prove text JSON and single-source multipart requests with fake transports,
  including the scalar multipart source field expected for a one-file binding.
- Prove discovery, validation, history/metadata, and unchanged behavior for the
  report-only V2 endpoint.
- Update the Wiro operator contract.

Commit after full Python tests and lint pass.

## 6. Add Nano Banana 2 and Pro

Add `wiro:nano-banana-2` and `wiro:nano-banana-pro`. Research proved the same
prompt/source/safety shape, with variant-specific aspect ratios, resolutions,
and prices.

- Preserve each endpoint's exact case-sensitive choices and 14-source edit
  limit. Send fixed `safetySetting: "OFF"` and do not expose it as a form
  parameter.
- Display the provider-reported price ranges `$0.045–$0.151` for Nano Banana 2
  and `$0.14–$0.24` for Pro.
- Prove text and multipart edit serialization for both variants, registry/UI
  discovery, validation, and history/metadata.
- Update the Wiro operator contract.

Commit after full Python tests and lint pass.

## 7. Add Flux 2 Flex with exact dimension validation

Add `wiro:flux-2-flex` for `black-forest-labs/flux-2-flex`.

- First add only the minimum reusable numeric validation metadata needed to
  express nonzero multiples of 16 while retaining Wiro's special zero value;
  cover it with a failing server-validation test.
- Expose exact dimensions, seed, guidance, steps, format, eight-source edit
  limit, and runtime. Send fixed `safetyTolerance: 5`, the documented least
  restrictive value, without exposing it as a form parameter. Default format
  to JPEG under project policy while preserving both provider choices.
- Preserve the conditional `cp-pixel` Tool Detail contract as descriptive
  provider pricing; do not present it as a flat per-image price.
- Prove JSON and multipart requests, discovery, validation, and
  history/metadata. Update the operator contract.

Commit after full Python and JavaScript checks if registry serialization changes
browser-facing parameter behavior.

## 8. Add GPT Image 1.5 and GPT Image 2

Add `wiro:gpt-image-15` and `wiro:gpt-image-2`. Research proved a shared
multi-image edit and output-control shape, with independent size/ratio and
pricing matrices.

- Expose each ordinary non-safety parameter, default, choice, bound, and
  runtime exactly. Display the provider-reported price ranges
  `$0.009–$0.200` for GPT Image 1.5 and `$0.003–$0.712` for GPT Image 2, and
  default output format to JPEG under project policy.
- Send fixed `moderation: "low"`, Wiro's explicit low setting, and do not
  expose it as a form parameter.
- Bind up to 16 ordinary edit sources to `inputImage` and keep both endpoints'
  optional `inputImageMask` out of generic parameters. The current request/UI
  contract has no trusted second file-input channel; document mask-targeted GPT
  editing as unsupported rather than accepting a browser-submitted path or
  silently treating a mask as an ordinary source.
- Prove text JSON, ordinary multipart editing, discovery, validation,
  history/metadata, and rejection of `inputImage` or `inputImageMask` in generic
  parameters.
- Update the Wiro operator contract and explicitly state the mask limitation.

Commit after full Python and JavaScript checks if browser-facing parameter
behavior changes.

## Final verification

After Ticket 8, run:

```bash
uv run pytest
uv run ruff format src tests
uv run ruff check --fix src tests
npm run js:format
npm run js:check
git diff --check
```

Smoke-test the ten new selector entries only after the user separately chooses
whether to authorize paid provider calls. A registry implementation requires no
billable probe.
