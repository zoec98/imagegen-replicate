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

## Post-research decision gate

After Ticket 1 is committed, revise this file from the recommended endpoint
set in `research.md`:

- Add one implementation ticket per independent Wiro model contract, or one
  tightly scoped ticket for variants only when the research proves their Wiro
  schemas and runtime behavior are shared.
- Order tickets so the smallest representative contract proves the existing
  Wiro registry/client path first. Do not create code tickets for unavailable,
  ambiguous, blocked, skipped, or report-only endpoints.
- Define each ticket through public behavior: provider-scoped discovery, exact
  schema-driven validation/defaults, text and edit support where documented,
  safe fake-transport generation, history/metadata compatibility, and operator
  documentation.
- Use `scripts/get_schema_wiro` output as the source contract for each registry
  implementation. Never copy Replicate or fal.ai parameters into a Wiro entry.
- Obtain approval for the revised ticket plan and commit it before model
  implementation starts. Any paid probe remains separately approval-gated.
