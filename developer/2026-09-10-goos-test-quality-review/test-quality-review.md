# GOOS Test Quality Review

Date: 2026-09-10

Reviewed source revision: `55712c12d033366e89de174bdb493d4e2bca89e8`.
All source line references below refer to that revision.
This assessment is the pre-ticket baseline; the implemented outcome is recorded
in the ticket implementation log below.

## Verdict

The suite is strong at behavior and architectural boundaries, but only
moderately refactor-resilient as a whole.

Most Python tests are not shallow forwarding tests. HTTP tests enter through
Flask, domain tests call public module APIs, persistence tests use real temporary
files or SQLite, and provider tests replace actual network clients at the
external protocol boundary. Those tests should survive internal refactoring
when the public behavior or provider protocol does not change.

The main weakness is composition. The generation route, real worker, provider
selection, browser workspace, and browser feature modules are mostly verified
in separate slices. A small number of interaction-only tests prove that one
object hands values to another, but there are too few walking-skeleton tests to
prove that the assembled application delivers the behavior. Three helpers also
derive expected values from the same registry data consumed by production code,
which can let contract drift pass unnoticed.

| Quality                      | Assessment | Reason                                                                                                                        |
|------------------------------|------------|-------------------------------------------------------------------------------------------------------------------------------|
| Observable behavior          | Strong     | Route, domain, image, persistence, and browser DOM outcomes dominate the suite.                                               |
| Boundary/seam discipline     | Strong     | Network, clock, executor, and provider seams are replaced without real provider calls.                                        |
| Refactoring resilience       | Mixed      | Raw HTML assertions, a private helper import, and callback choreography couple some tests to structure.                       |
| Outside-in walking skeletons | Weak       | Backend generation and browser workflows are mostly tested as separately composed layers.                                     |
| Oracle independence          | Mixed      | Most expected values are explicit; three important default/payload expectations are derived from production registry objects. |
| Failure localization         | Mixed      | Many focused tests exist, but several large tests assert multiple independent behaviors.                                      |

## Baseline and method

- 528 Python tests passed in 4.08 seconds with `uv run pytest`.
- 102 browser tests in 14 files passed with `npm run js:check`; lint and the
  production bundle build also passed.
- The suite contains 14,802 lines across Python and browser test files.
- The review traced test entry points, fakes, monkeypatches, callback spies,
  filesystem/SQLite verification, and application composition. A scan found 130
  call-inspection or call-assertion lines across 15 files; these were reviewed in
  context rather than treated as automatically bad.

This is a qualitative review of representative tests and their composition,
supported by suite-wide searches and execution. Refactoring survival is a
prediction: no mutation campaign, actual refactoring experiment, live provider
contract verification, or real-browser visual check was performed. Passing test
counts measure the baseline, not assertion quality. Priorities rank review work,
not demonstrated production defects.

The review uses these GOOS/TDD criteria:

1. Start from behavior meaningful to a caller or user.
2. Exercise the behavior through a stable interface.
3. Replace slow or uncontrolled external boundaries, not arbitrary internal
   implementation.
4. Keep expectations on collaborator protocols only when that protocol is an
   intentional seam.
5. Prefer tests that remain unchanged when internal structure changes without a
   behavioral change.
6. Maintain at least one thin end-to-end path through the assembled system.

The [authors' chapter outline](https://growing-object-oriented-software.com/toc.html)
explicitly covers collaborating-object unit tests, mock objects, walking
skeletons, and test flexibility (chapters 2, 4, 8, and 24). GOOS does not imply
that every internal collaborator mock is a bad test. The local TDD skill's
preference for integration-style tests and boundary-only mocking is a stricter
project lens. Here an interaction test is a concern when it pins incidental
implementation or is the only evidence for an assembled behavior; a meaningful
peer protocol can legitimately be specified with expectations. Neither approach
promises unchanged tests when the interface under test itself changes.

## Strengths to preserve

### S1. Route tests are genuinely outside-in

The route suites create a Flask app, submit real HTTP requests, use CSRF tokens,
and verify returned state plus filesystem or SQLite effects. Examples include
generation submission in `tests/test_generation_api.py:20`, complete edited
image workflows in `tests/test_image_edit_routes.py:439`, URL import security in
`tests/test_image_import_routes.py:180`, and trash restoration in
`tests/test_trash_routes.py:77`.

These tests cross several internal functions without naming them. Route and
repository refactoring should leave most of them unchanged.

### S2. Domain and persistence tests use real controlled resources

Image editing, metadata embedding, gallery/trash behavior, palettes, request
state, and generation history are exercised through public functions with real
temporary images, directories, and SQLite databases. Representative examples
are `tests/test_image_edits.py:29`, `tests/test_metadata_embed.py:71`,
`tests/test_generation_log.py:16`, and `tests/test_palettes.py:22`.

This is stronger than mocking the filesystem or SQL layer and checking call
arguments. The assertions describe stored or returned behavior.

### S3. Provider call assertions sit on legitimate external seams

Exact provider endpoints, payload fields, multipart parts, polling requests, and
error translation are public compatibility contracts even though the tests
inspect fake-client calls. Good examples are the Replicate prediction protocol
in `tests/test_replicate_client.py:293`, fal.ai submission in
`tests/test_falai_client.py:86`, Wiro submission/polling in
`tests/test_wiro_client.py:59`, and `httpx.MockTransport` use in
`tests/test_image_store.py:400`.

These are not candidates for blanket conversion to broad outcome assertions.
Changing the internal adapter should be harmless; changing the provider wire
protocol should fail these tests.

### S4. Browser tests usually observe DOM behavior

Most browser tests click controls and assert visible state, text, accessibility
attributes, selected images, or rendered cards. Examples include source-image
selection in `tests/js/source-images.test.js:25`, trash behavior in
`tests/js/trash.test.js:11`, metadata presentation in
`tests/js/metadata.test.js:101`, and gallery information behavior in
`tests/js/gallery.test.js:123`.

`fetch` and canvas are appropriate browser/platform seams. These tests are
substantially stronger than pure function-call wiring checks.

### S5. Test names and module headers mostly state behavior

Most Python test modules declare the protected behaviors, and most test names
describe outcomes such as rejection, persistence, restoration, or lifecycle
state rather than method names or call order. This makes the suite usable as a
specification and gives future TDD work useful domain vocabulary.

## Findings for review

### F1 — High: no backend generation walking skeleton

**Evidence**

- The shared app fixture supplies `NoopGenerationWorker` unless overridden
  (`tests/conftest.py:15` and `tests/conftest.py:43`).
- The route-level worker test only records the request passed to `start`
  (`tests/test_generation_api.py:431`).
- Worker lifecycle behavior is tested separately with injected providers
  (`tests/test_worker.py:45`).
- App construction of `ThreadedGenerationWorker` and
  `default_generation_providers()` at `src/imagegen/app.py:48` is never exercised
  by a generation request in tests.

**Why it matters**

Each layer can pass while the assembled route → worker → selected provider →
request/log result path is broken. The recording-worker test usefully verifies
dispatch at the worker interface, but does not establish completion.

**Refactoring survival**

The separate layer tests survive local refactors, but they do not protect
composition changes. Moving worker creation, changing the provider mapping, or
altering app configuration can break production while all relevant tests remain
green.

**Remedy story**

As a maintainer changing application composition, I want one deterministic
generation walking-skeleton test so that a valid HTTP request proves the
assembled route, worker, provider selection, request store, and generation log
still deliver a terminal result.

**Test-first acceptance examples**

- Start with one failing test that posts valid JSON to `/api/generate` through a
  real Flask app and crosses `run_generation_request` rather than stopping at a
  recording worker.
- Substitute only the external generation provider; make worker execution
  synchronous through an existing executor/worker seam so the test has no
  timing race.
- Observe the accepted response, terminal state through `/api/generation/<id>`,
  and durable result through the generation-log interface.
- Do not assert the internal sequence of store/log method calls, add an
  end-to-end framework, or make a real provider request.
- Explicitly injected providers cover route/worker orchestration but cannot
  verify the default adapter mapping. If that wiring is in the accepted scope,
  add a separate example retaining the real selected adapter and replacing its
  SDK/HTTP boundary. Do not claim that a fake provider proves default wiring or
  image persistence. Retain the existing Event-based threaded-worker test for
  concurrency behavior.

### F2 — High: browser feature tests do not use the assembled workspace contract

**Evidence**

- Browser modules build their own HTML strings, including the large duplicate
  workspace in `tests/js/workspace-fixture.js:1`.
- Only one browser test imports `frontend/main.js`, and it checks provider/model
  option switching (`tests/js/workspace.test.js:34`).
- The second workspace test calls `setupWorkspace` directly and only reads the
  selected model (`tests/js/workspace.test.js:56`).
- Feature tests then inject callbacks between gallery, metadata, generation,
  trash, upload, and editor modules instead of exercising their production
  wiring.

**Why it matters**

The handwritten DOM can drift from the Jinja template, and collaborating modules
can change contracts incompatibly while their isolated tests still pass. The
suite has good browser component behavior but a thin walking skeleton for the
actual workspace.

**Refactoring survival**

Feature-module tests will often need edits when module ownership changes even if
the browser behavior remains the same. Conversely, broken top-level wiring may
not fail them.

**Remedy story**

As a user of the generated workspace, I want one representative workflow tested
through the assembled browser entry point so that incompatible template hooks
or module wiring cannot leave individually passing components unusable together.

**Test-first acceptance examples**

- Start with one failing jsdom test initialized by `frontend/main.js`, using the
  real rendered workspace shape or a fixture mechanically produced from it.
- Exercise one representative workflow end to end in the browser layer: enable
  edit mode, select an existing source image, submit generation, advance fake
  time through running and successful responses, and observe the new gallery
  image, completion message, and enabled submit control.
- Fake browser boundaries only (`fetch`, timers, and canvas where required); do
  not inject callbacks between the production feature modules in this test.
- Keep focused module tests for complex DOM and image-editor behavior; add a
  second composed workflow only if the first cannot cover a distinct top-level
  wiring risk.
- Generate template fixtures during verification or check their freshness so
  template drift fails automatically. A handwritten fixture copied once does
  not close this gap. This jsdom test covers composition, not browser layout or
  real canvas rasterization.

### F3 — Medium: three test oracles copy defaults from production registry data

**Evidence**

- `tests/route_helpers.py:40` calculates expected API parameters by iterating the
  production model's parameters; it is used at
  `tests/test_generation_api.py:47` and `tests/test_generation_api.py:401`.
- `tests/test_validation.py:21` repeats the same algorithm and compares it with
  validation output at `tests/test_validation.py:45`.
- `tests/test_replicate_client.py:107` constructs the expected provider payload
  from the same target defaults and fixed inputs used by production code, then
  compares it at `tests/test_replicate_client.py:142`.

**Why it matters**

If a required default is accidentally changed or removed in the registry, both
the system and its expected value change together. These particular assertions
prove default propagation and internal consistency, not independent default
values. That propagation is useful behavior. Other explicit registry or provider
tests may already catch an individual changed value; no suite-wide surviving
mutation is claimed here.

**Refactoring survival**

They are coupled to the registry representation and may fail during a harmless
registry redesign. At the same time, they can survive an incorrect registry
content change that should fail.

**Remedy story**

As a maintainer changing model metadata, I want independent expected values for
representative defaults and provider requests so that an accidental registry
contract change fails a test instead of changing both the implementation and
its oracle.

**Test-first acceptance examples**

- Replace the generated Seedream 4.5 defaults expectation with an explicit
  expected parameter dictionary owned by the test.
- Keep registry-wide tests as independent invariants such as unique names,
  valid bounds, and fixed-input separation; do not calculate an expected payload
  with the same comprehension as production.
- Keep one explicit provider payload example per materially different wire shape
  rather than snapshotting every model.
- Demonstrate the value of the new oracle during the TDD change by temporarily
  changing or omitting one required default and confirming the new test fails.

### F4 — Medium: workspace rendering tests couple to raw markup and one private helper

**Evidence**

- `test_index_renders_prompt_form` contains dozens of byte-substring and relative
  ordering checks (`tests/test_workspace_routes.py:24`).
- Gallery rendering similarly asserts exact class fragments and attribute
  strings (`tests/test_workspace_routes.py:609`).
- The suite imports `_workspace_context`, an explicitly private route helper
  (`tests/test_workspace_routes.py:21`), and tests it directly at lines 184 and
  204.

**Why it matters**

Whitespace, attribute order, element restructuring, class renaming, or folding
the private helper into another implementation can fail tests without changing
the behavior. The first test also protects many independent concerns, so a
failure is less diagnostic.

**Refactoring survival**

Low for template refactors and route decomposition; high only when the current
HTML implementation remains structurally similar.

**Remedy story**

As a maintainer refactoring the workspace template and route internals, I want
rendering tests to describe semantic browser contracts so that harmless
whitespace, attribute-order, and helper-extraction changes do not break the
suite.

**Test-first acceptance examples**

- Split `test_index_renders_prompt_form` by observable concern before changing
  assertions, so each failure names one workspace capability.
- Parse the `/` response and assert intentional form controls, data hooks,
  accessibility attributes, and user-visible content semantically rather than
  as formatting-sensitive byte fragments.
- Replace both `_workspace_context` tests with requests through `/` that vary the
  configured model and observe the selected option in the response.
- Prove refactoring resilience by reformatting attribute order or whitespace and
  confirming the semantic tests remain green; do not add a new parser dependency
  if the standard library or installed jsdom tooling suffices.

### F5 — Medium: a small set of tests specify internal relay choreography

**Evidence**

- Gallery dispatch checks only that metadata and editor callbacks receive the
  current figure (`tests/js/gallery.test.js:92` and
  `tests/js/gallery.test.js:103`).
- Metadata loading checks that response data is relayed to `applyMetadata` and a
  message callback (`tests/js/metadata.test.js:45`).
- Worker provider-selection tests assert every argument passed to an injected
  generation function and then only assert `succeeded`
  (`tests/test_worker.py:256` and `tests/test_worker.py:296`).
- The scan found interaction assertions in only 15 of 55 test files; this is a
  concentrated smell, not a suite-wide pattern.

**Why it matters**

These examples answer “did these parameters reach this collaborator?” more than
“did the application deliver the behavior?” They make callback/module
boundaries costly to change and can pass even when no user-observable outcome is
completed.

**Refactoring survival**

Low if callback boundaries are merged, split, renamed, or replaced; reasonable
only if the callback is intentionally treated as a stable interface.

**Remedy story**

As a maintainer changing module boundaries, I want tests to assert completed
behavior rather than internal relay calls so that callbacks and worker/provider
adapters can be reorganized without rewriting otherwise valid specifications.

**Test-first acceptance examples**

- Classify each interaction expectation as a stable peer/external protocol or
  incidental internal relay before changing it. Preserve protocol assertions
  that protect a distinct responsibility, even for application-owned peers.
- Cover gallery metadata/edit dispatch and metadata application through the
  an additional composed browser example: click Load metadata and observe the
  prompt, selected model, and parameter controls; click Edit image and observe
  the editor opening for the selected image. F2's generation scenario alone
  cannot replace these tests. Remove relay-only examples only once their
  distinct responsibilities are covered.
- Cover worker model selection through the walking skeleton in F1 plus the
  provider wire-contract tests in S3. Before removing the existing selected-model
  or edit-source checks, retain the real adapter in an example that distinguishes
  the requested model from the configured default and observes source inputs at
  the SDK/HTTP seam. F1's fake provider alone cannot replace these checks.
- For any retained collaborator expectation, name the stable protocol in the
  test and assert the minimum interaction required by that protocol, not call
  order or unrelated arguments.

### F6 — Low: dead duplicated helpers remain in a route test module

**Evidence**

`tests/test_trash_routes.py:362-409` defines image-edit payload and request
helpers that have no callers in that module. Equivalent live helpers exist at
`tests/test_image_edit_routes.py:30-76`.

**Why it matters**

Dead test setup obscures the behaviors owned by the trash suite and can be
mistaken for coverage. It also creates two apparent places to update image-edit
test rules.

**Remedy story**

As a test reader, I want the trash route module to contain only setup used by its
trash behaviors so that helper definitions cannot be mistaken for test coverage
or create a second maintenance location for image-edit rules.

**Test-first acceptance examples**

- Delete the five unused image-edit helpers from `test_trash_routes.py` and
  remove imports used only by them.
- Keep the live helpers local to `test_image_edit_routes.py`; do not introduce a
  shared helper module for a single caller.
- Run the full Python suite and Ruff check to prove the deletion changes no
  behavior and leaves no unused imports.

## Refactoring survival by surface

| Surface | Likely survival | Notes |
| --- | --- | --- |
| Gallery, palettes, validation, annotations | High | Public functions and observable domain results. |
| Image storage/edit/export/metadata | High | Real files and decoded/embedded output verification. |
| SQLite generation history | High | Public persistence behavior; schema migrations are intentional contracts. |
| Flask JSON routes | High | HTTP status, payload, security, and persisted effects. |
| Provider clients | High for internal refactors | Exact wire-protocol assertions should change only with provider contracts. |
| Worker orchestration | Mixed | Lifecycle outcomes are strong; provider relay examples are structural. |
| CLI | Mixed to high | Parsing/output are public; `main` output tests patch internal CLI services intentionally. |
| Jinja workspace rendering | Low to mixed | Exact byte strings and a private helper import create avoidable coupling. |
| Browser feature modules | Mixed | DOM outcomes are strong; synthetic fixtures and callback expectations weaken composition confidence. |
| Full application composition | Low | No backend generation walking skeleton and only a minimal browser composition test. |

## Review decisions preserved in ticket conversion

1. Accept, reject, or revise F1 and choose the single backend behavior that will
   serve as the walking skeleton.
2. Accept, reject, or revise F2 and choose one representative composed browser
   workflow; avoid converting every component test into an end-to-end test.
3. Identify which defaults and provider payload fields in F3 are intentional
   stable contracts before making their expected values explicit.
4. Decide which workspace classes/data attributes in F4 are public browser hooks
   and which are replaceable markup.
5. For F5, name any callback interfaces the team wants to keep stable; only the
   remaining relay tests should be raised to observable workflows.
6. F6 can become a deletion-only cleanup ticket if accepted.

The decisions above were accepted and converted into the six tickets in
`tickets.md`. The ticket plan was committed before implementation; each ticket
was then implemented as a focused test-suite change with no production-code
changes.

## Merge-readiness verification

The final document review corrected the distinction between GOOS peer-protocol
tests and the local TDD skill's stricter mocking preference, bounded the claims
about derived oracles, and clarified which composed examples must exist before
deleting narrower tests. Existing correct behavior does not require an artificial
production change to obtain a failing test; use controlled fault injection to
check sensitivity when needed.

Verification on 2026-09-10: 531 Python tests passed, Ruff passed, and all 102
JavaScript tests plus ESLint and the bundle build passed. The generated bundle
was unchanged. `git diff --check` passed. Main at `4b974de` differs from the
audited source only by the package version bump; a read-only three-way merge
check found no conflicts. The implementation branch contains the two review
documents and test-only changes for all six approved tickets; it is ready for
review and merge into main.
