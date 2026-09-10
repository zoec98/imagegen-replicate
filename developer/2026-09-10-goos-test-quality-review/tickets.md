# GOOS Test Quality Tickets

Status: implemented
Sources: [user-stories.md](user-stories.md),
[test-quality-review.md](test-quality-review.md)

These tickets convert the six review findings into implementation-sized,
behavior-focused changes. They are ordered so later deletion of interaction
tests happens only after replacement coverage exists.

The plan was approved before implementation. Each ticket below is complete;
the commits are recorded in the implementation log at the end of this file.

For behavior that already works, establish a green baseline and demonstrate a
new test's sensitivity with a temporary controlled fault. Restore the fault
before committing. Do not change correct production behavior merely to create a
red phase. Test-only refactoring and dead-code deletion remain green throughout.

## Ticket 1: Remove dead trash-test helpers

Finding: F6

Goal: make the trash route suite describe only trash behavior and remove setup
that can be mistaken for image-edit coverage.

Public behavior:

- Trash route behavior and coverage remain unchanged.
- Image-edit test helpers remain local to the image-edit route suite where they
  are used.

Test boundary:

- Delete the unused image payload, crop, blur, and mask-limit helpers from
  `tests/test_trash_routes.py`.
- Remove imports and constants used only by those helpers.
- Do not extract a shared helper for the single remaining caller.

Done when:

- `tests/test_trash_routes.py` contains no uncalled image-edit helpers.
- The full Python suite and Ruff check pass without changing production code.

## Ticket 2: Make representative default oracles independent

Finding: F3

Goal: ensure an unintended model-default or provider-payload change fails a
test instead of changing both production output and the expected value.

Public behavior:

- A Seedream 4.5 request without optional overrides produces the explicitly
  approved API parameter defaults.
- The corresponding Replicate request contains the explicitly approved provider
  defaults and fixed inputs.
- Registry-wide shape checks continue to enforce generic invariants without
  duplicating the production default-building algorithm.

Test boundary:

- Replace `expected_response_parameters()` and
  `expected_default_parameters()` use for the representative Seedream 4.5
  examples with literal expected values owned by the tests.
- Replace `expected_default_inputs()` in the representative Replicate payload
  example with an explicit wire payload.
- Keep dynamic registry invariant tests for uniqueness, valid bounds, choices,
  and fixed-input separation.
- Temporarily alter or omit one asserted default to demonstrate that each new
  oracle fails, then restore it.

Done when:

- The three representative assertions no longer calculate their expected
  values from `ProviderModel` or `GenerationTarget` objects.
- Helpers with no remaining callers are deleted.
- The full Python suite and Ruff check pass.

## Ticket 3: Test workspace rendering through semantic HTTP behavior

Finding: F4

Goal: let harmless template formatting and route-helper refactoring proceed
without weakening the browser contract checked at `/`.

Public behavior:

- The workspace response contains the required form controls, intentional data
  hooks, accessibility attributes, selected provider/model, and user-visible
  state.
- Configuring an available start model selects it in the rendered workspace.
- Configuring an unavailable start model falls back to an available model.
- Reordering whitespace or HTML attributes does not change these results.

Test boundary:

- Exercise rendering through the Flask test client at `/`.
- Replace direct `_workspace_context` tests with configured HTTP examples.
- Split the broad prompt-form example into tests named for distinct observable
  workspace capabilities.
- Parse only the elements needed by each behavior using the standard library or
  an already installed test dependency. Do not add a parser dependency solely
  for these assertions.
- Preserve exact string checks only where the literal text or URL is itself a
  public contract.

Done when:

- No test imports `_workspace_context`.
- Semantic assertions survive an attribute-order and whitespace-only template
  edit.
- The full Python suite and Ruff check pass.

## Ticket 4: Add a backend generation walking skeleton

Finding: F1

Goal: prove that the assembled HTTP generation path reaches a terminal result
through the real worker orchestration while external generation remains fake.

Public behavior:

- A valid CSRF-protected `POST /api/generate` is accepted and returns a pollable
  request identifier.
- The selected provider receives the request through the worker.
- `GET /api/generation/<id>` exposes the terminal successful state, provider
  identifier, output URL, stored image name, and logs.
- The generation-log interface exposes the same completed lifecycle and asset
  result.
- Default provider composition maps Replicate, fal.ai, and Wiro to their
  intended adapters.

Test boundary:

- Use the real Flask route, `RequestStore`, `ThreadedGenerationWorker`,
  `run_generation_request`, and `SQLiteGenerationLog`.
- Make execution deterministic through an immediate executor or equivalently
  small application-composition seam.
- Replace generation at the `GenerationProvider` protocol for the walking
  skeleton; do not mock store or log method calls.
- Add a separate focused composition example for the default provider mapping.
  If adapter selection must be proven through the route, retain the real adapter
  and fake its SDK/HTTP boundary.
- Retain the existing Event-based worker test for asynchronous behavior.

Done when:

- Breaking route-to-worker dispatch, worker-to-provider selection, terminal
  request updates, or durable result logging fails a focused test.
- No test makes a live provider or arbitrary network request.
- The full Python suite and Ruff check pass.

Depends on: Ticket 2 supplies independent representative request expectations.

## Ticket 5: Add an assembled browser generation workflow

Finding: F2

Goal: prove that the rendered workspace hooks and production JavaScript modules
fit together for one complete user workflow.

Public behavior:

- Starting from the rendered workspace, a user enables edit mode and selects an
  existing gallery image as a source.
- Submitting a prompt sends the selected provider, model, edit state, source
  image, and parameters to the generation API.
- Running and successful poll responses update visible status, restore the
  submit control, and render the returned gallery image.

Test boundary:

- Initialize the workflow through `frontend/main.js`; do not inject callbacks
  between production feature modules.
- Use the real rendered workspace shape, or a generated fixture whose freshness
  against the Jinja template is checked automatically.
- Fake `fetch` and time only at browser/platform boundaries.
- Advance fake time deterministically through accepted, running, and successful
  responses.
- Keep focused module and canvas tests for their distinct behavior. This jsdom
  workflow does not replace real-browser layout or rasterization checks.

Done when:

- A missing template hook or incompatible workspace, source-image, generation,
  or gallery module contract fails the composed test.
- A stale generated workspace fixture fails verification.
- `npm run js:check` passes and the committed production bundle is current.

Depends on: Ticket 3 identifies the intentional rendered workspace contract.

## Ticket 6: Replace incidental relay assertions with completed behavior

Finding: F5

Goal: preserve tests for meaningful peer protocols while removing assertions
that only pin replaceable callback and adapter structure.

Public behavior:

- Loading metadata from a gallery image updates the prompt, selected model, and
  parameter controls and reports success or compatibility warnings.
- Choosing Edit image opens the editor for that gallery image.
- A request for a model other than the configured default reaches the correct
  provider adapter with the selected model and source images.
- External provider wire protocols remain covered by their existing adapter
  contract tests.

Test boundary:

- Classify each cited interaction in F5 as a stable peer/external protocol or an
  incidental relay and record the decision in the affected test name or module
  behavior header.
- Add one composed browser metadata/edit example initialized through the
  workspace before removing the gallery and metadata relay-only examples.
- Use the backend walking skeleton with a non-default model and edit source; if
  it uses a fake `GenerationProvider`, retain a focused real-adapter example that
  observes model and source translation at the SDK/HTTP seam.
- Keep the minimum expectation that specifies each retained peer protocol.
  Avoid asserting unrelated arguments or call order.
- Delete a relay-only test only when its distinct observable responsibility is
  protected by replacement coverage.

Done when:

- The cited gallery, metadata, and worker tests either specify a named stable
  protocol or have been replaced by completed behavior tests.
- Reorganizing internal callbacks without changing browser behavior does not
  require rewriting the composed specifications.
- The full Python suite, Ruff check, and `npm run js:check` pass.

Depends on: Tickets 4 and 5 establish replacement composition coverage.

## Epic completion

- Each approved ticket is implemented in order and committed independently.
- Each behavior change follows one failing test to one minimum passing change;
  existing-behavior tests use a temporary controlled fault to prove sensitivity.
- Pure test refactors and dead-code deletion retain a green baseline.
- `uv run pytest` and `uv run ruff check src tests` pass after every ticket.
- `npm run js:check` passes after Tickets 5 and 6 and after any other browser
  JavaScript change.
- Tests make no live provider, Immich, DNS, or arbitrary network calls.
- The review documents remain the rationale; this file records the approved
  implementation order and behavior boundaries.

## Implementation log

| Ticket | Commit(s) | Verification |
|--------|-----------|--------------|
| 1 | `6e66ee9` | Dead helper cleanup; focused Python tests and Ruff passed. |
| 2 | `5d8d7da` | Independent representative oracles; focused Python tests and Ruff passed. |
| 3 | `082e1f5` | Semantic workspace HTTP tests; focused Python tests and Ruff passed. |
| 4 | `7c9ac94` | Backend route-to-worker walking skeleton and provider composition; Python tests and Ruff passed. |
| 5 | `d850f1f`, `e8590ad` | Composed browser generation, polling, and gallery refresh; `npm run js:check` passed. |
| 6 | `f331a5e` | Relay-test removal plus metadata/editor workflows; `npm run js:check` passed. |

Final verification: `uv run pytest` passed 531 tests, `uv run ruff check src tests`
passed, and `npm run js:check` passed 102 JavaScript tests, ESLint, and the
bundle build. No production source code was changed by this epic.
