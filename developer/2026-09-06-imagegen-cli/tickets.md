# imagegen CLI — tickets

These tickets implement the committed CLI user stories in behavior-first order.
The first version is synchronous, text-to-image only, and calls the existing
application services directly rather than the Flask HTTP API.

## 1. Enforce provider-scoped model identities

Make provider model lookup accept either the stable alias or the display name
needed by the CLI, while preserving the existing provider boundary.

Behavior to prove first:

- A model resolves by its exact alias within the selected provider.
- A model resolves by its case-insensitive display name within the selected
  provider.
- A value belonging only to another provider is rejected.
- Unknown and ambiguous values produce actionable errors with valid choices.
- Selectable aliases are unique within each provider.
- Selectable display names are unique case-insensitively within each provider.

Document both uniqueness rules in `developer/provider-models.md` so future
registry entries preserve the lookup contract.

Public interface: the provider-scoped model registry lookup used by the web
application and CLI.

Likely touchpoints: `src/imagegen/model_registry.py`,
`tests/test_model_registry.py`, and `developer/provider-models.md`.

Verification: add failing registry behavior tests one at a time, implement the
smallest shared lookup change, then run `uv run pytest` and
`uv run ruff check src tests`.

## 2. Provide the imagegen entry point and global help

Make the existing packaged `imagegen` command start a testable CLI and expose
complete global help without loading runtime configuration.

Behavior to prove first:

- `imagegen --help` exits successfully and names the command `imagegen`.
- Help lists all selectable providers and groups their models by provider.
- Each model shows its alias and display name.
- Help identifies the generation options and explains the human/agent discovery
  sequence, matching rules, option spelling rules, boolean syntax, exit
  statuses, and stdout/stderr contract.
- Help includes short examples for direct prompts, prompt files,
  model-specific help, and quiet output.
- Asking for help does not require credentials, create or modify `.env`, create
  runtime directories, initialize SQLite, or submit generation work.

Keep help deterministic and generated from the registry where provider/model
content is concerned. Do not add `imagen`, `--llm`, or `--schema` entry points.

Public interface: the installed `imagegen` command and a callable CLI entry
point that accepts an argument list for tests.

Likely touchpoints: `src/imagegen/__init__.py`, one focused CLI module,
`pyproject.toml`, and a focused CLI test module.

Verification: invoke the public CLI entry point with `--help` in an isolated
working directory, then run `uv run pytest` and `uv run ruff check src tests`.

## 3. Generate model-specific help and parameter options

After provider/model selection, expose the selected text-to-image target's
user-configurable registry parameters through standard command-line options.

Behavior to prove first:

- `imagegen --provider PROVIDER --model MODEL --help` works with an alias or
  display name without loading runtime configuration.
- A registry parameter such as `image_size` accepts both `--image_size` and
  `--image-size`, storing the value under `image_size`.
- Select help shows choices and defaults.
- Integer and number help shows bounds and defaults.
- Boolean parameters accept positive and negative underscore forms and their
  hyphenated equivalents.
- Parameter descriptions come from the selected registry target.
- Prompt, source-image fields, and fixed provider inputs are not duplicated as
  generated model options.
- Normalized spellings that collide with reserved CLI options or another
  parameter fail clearly instead of silently overriding an option.

Use the registry as the only model-option schema and the Python standard
library parser already chosen for the CLI.

Public interface: model-specific CLI help and the parsed parameter mapping
passed to existing validation.

Likely touchpoints: the CLI module and its focused tests.

Verification: cover one select, one bounded numeric, and one boolean parameter
through public CLI parsing/help behavior, then run `uv run pytest` and
`uv run ruff check src tests`.

## 4. Validate direct and file-based prompts

Accept exactly one prompt source and feed the resulting prompt and parsed model
parameters through the application's existing generation validation.

Behavior to prove first:

- `--prompt TEXT` supplies a trimmed, non-empty prompt.
- `--file FILENAME` reads and trims a non-empty UTF-8 prompt.
- Supplying neither or both prompt options exits with status `2` before any
  provider request.
- Missing, unreadable, non-UTF-8, empty, and whitespace-only prompt files exit
  with status `2` and an actionable stderr message.
- Prompt annotation rules are identical to web generation behavior.
- Model defaults, choices, numeric bounds, conditional dimensions, unknown
  parameters, source-image exclusions, and fixed inputs remain governed by the
  existing validator.

Public interface: `--prompt`, `--file`, generated model options, and the
validated generation request handed to the generation service.

Likely touchpoints: the CLI module and its focused tests; change shared
validation only if the CLI exposes a genuine missing shared boundary.

Verification: use a temporary UTF-8 prompt file and public CLI parsing paths,
then run `uv run pytest` and `uv run ruff check src tests`.

## 5. Run generation synchronously through existing services

Connect a validated CLI request to the same request store, durable generation
history, worker/service path, provider clients, image persistence, and metadata
behavior used by the web application.

Behavior to prove first:

- Explicit `--provider` and `--model` selections create a normal generation
  request for that provider and model.
- The request and provider-ready input are written to the configured SQLite
  generation history.
- The existing generation service runs synchronously and returns only after the
  request reaches a terminal status.
- A successful request uses the existing provider implementation and stores
  gallery images through the existing image store with embedded metadata.
- The CLI reads the project-root `.env` and existing credential, timeout,
  polling, data-directory, and author configuration only after parsing and
  validation require generation.
- The CLI does not start Flask, require a running server, create a browser
  session, acquire CSRF state, or call the local HTTP API.
- Tests inject a fake provider and make no real provider or image-download
  network calls.

Public interface: a synchronous CLI generation operation whose completed state
uses the existing `GenerationRequest` result shape.

Likely touchpoints: the CLI module, existing generation service boundaries only
where necessary for safe injection, and focused CLI tests.

Verification: exercise success and provider failure with fakes through the
public CLI entry point, assert durable history and stored-result state, then run
`uv run pytest` and `uv run ruff check src tests`.

## 6. Emit reusable results and stable exit statuses

Turn terminal generation state into the agreed human- and script-consumable
stdout, stderr, and exit-status contract.

Behavior to prove first:

- A successful normal invocation emits the full completed request JSON to
  stdout and exits `0`.
- JSON image entries are reusable paths relative to the project root, such as
  `outputs/images/example.jpg`.
- A successful `--quiet` invocation emits only project-root-relative image
  paths, one per line, and exits `0`.
- Quiet stdout contains no headings, progress, logs, JSON, or explanations.
- Argument and validation failures write actionable errors to stderr and exit
  `2`.
- Provider, timeout, download, persistence, and other runtime failures write
  actionable errors to stderr and exit `1`.
- Runtime diagnostics never corrupt successful JSON or quiet stdout.

Preserve the existing completed request JSON shape apart from rendering its
image entries as reusable project-root-relative paths.

Public interface: stdout, stderr, JSON, quiet line output, and process exit
statuses from `imagegen`.

Likely touchpoints: the CLI module and its focused tests.

Verification: capture all three process streams/status cases through the public
CLI entry point, then run `uv run pytest` and `uv run ruff check src tests`.

## 7. Document and verify the complete CLI workflow

Document the shipped command and run the repository-wide checks before the epic
is considered complete.

Behavior to verify:

- `README.md` explains running from the project root, direct and file prompts,
  alias and quoted display-name selection, model-specific help, underscore and
  hyphen parameter spellings, boolean options, normal JSON output, quiet path
  output, and exit statuses.
- Help and README examples agree with the implemented command.
- `imagegen --help` and representative model help are readable by both humans
  and agents without external documentation.
- No `imagen`, `--llm`, `--schema`, image-edit, detached execution, HTTP CLI
  transport, or cancellation feature has been added.

Likely touchpoints: `README.md` and any CLI help text adjusted by verification.

Verification:

- `uv run pytest`
- `uv run ruff format src tests`
- `uv run ruff check --fix src tests`
- `imagegen --help`
- one representative Replicate model-help invocation
- one representative fal.ai model-help invocation

Browser JavaScript is outside this epic; do not run or change the JavaScript
build unless implementation unexpectedly changes browser JavaScript scope, in
which case return to this ticket plan for approval first.
