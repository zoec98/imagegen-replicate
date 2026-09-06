# imagegen CLI user stories

## Epic

As a user of imagegen, I want an `imagegen` command-line interface that uses
the application's existing model registry, validation, generation providers,
image storage, metadata, and generation history so that I can generate images
from scripts without running or automating the web interface.

## Decisions

- The command is named `imagegen`.
- Run generation directly through the existing application service path. Do
  not submit requests to the Flask web interface.
- Run synchronously and wait for the generation to finish.
- Reuse existing registry lookup, request validation, provider clients, image
  persistence, embedded metadata, and SQLite generation history behavior.
- Support text-to-image generation only in this epic. Image-edit and source
  image options are separate future work.
- Require an explicit provider and model for generation.
- Accept model aliases and display names.
- Read configuration and credentials from the same project-root `.env` used by
  the web application.
- Use the Python standard library for CLI argument parsing. Do not add a CLI
  framework dependency.
- Make ordinary help sufficiently explicit for both human users and language
  model agents. Do not add a separate LLM help mode.

## Story 1: Discover providers and models

As a user, I want `imagegen --help` to list available providers and their
models so that I can discover valid generation targets without opening the web
interface.

### Acceptance criteria

- `imagegen --help` exits successfully without requiring provider credentials.
- Help does not create or modify `.env`, initialize runtime storage, or start a
  generation request.
- Help lists every selectable provider in the registry.
- Models are grouped by provider.
- Each model entry shows its alias and display name.
- The help output identifies `--provider`, `--model`, `--prompt`, `--file`, and
  `--quiet` as generation options.
- Help includes an automation and agent usage section that explains the
  discovery sequence:
  1. Run `imagegen --help` to discover providers and models.
  2. Run `imagegen --provider PROVIDER --model MODEL --help` to discover the
     selected model's parameters.
  3. Run generation with the discovered options.
- Help states the required arguments, mutually exclusive prompt inputs,
  alias/display-name matching rules, underscore/hyphen option equivalence,
  boolean option syntax, exit statuses, and stdout/stderr contract.
- Help includes short, copyable examples for direct prompts, prompt files,
  model-specific help, and quiet output.
- Help text is deterministic plain text that does not depend on whether the
  caller is a human or an agent.
- The command name shown in usage and errors is `imagegen`.

## Story 2: Resolve a provider model

As a user, I want to select a provider and identify a model by alias or display
name so that I can use either the stable scripting name or the human-readable
name shown by the application.

### Acceptance criteria

- Generation requires `--provider` with a registered provider id such as
  `replicate` or `falai`.
- Generation requires `--model` with either an alias or display name belonging
  to the selected provider.
- Aliases are matched exactly.
- Display names are matched case-insensitively within the selected provider.
- A model cannot be selected from a provider other than the provider given by
  `--provider`.
- Unknown and ambiguous values fail before generation with an actionable error
  that lists valid choices.
- Registry validation and tests require every selectable model alias to be
  unique within its provider.
- Registry validation and tests require every selectable model display name to
  be unique, case-insensitively, within its provider.
- Provider-model documentation states that future entries must preserve both
  uniqueness requirements.

## Story 3: Discover model-specific options

As a user, I want `imagegen --provider PROVIDER --model MODEL --help` to show
that model's parameters so that I can construct a valid command without
consulting provider documentation.

### Acceptance criteria

- Model help works when `MODEL` is an alias or display name.
- Model help does not require credentials, modify `.env`, initialize runtime
  storage, or start generation.
- Each applicable text-to-image registry parameter is exposed using its
  registry name, for example `image_size` becomes `--image_size`.
- Each parameter also accepts a spelling with interior underscores replaced by
  hyphens, for example `--image-size`.
- Both spellings map to the original registry parameter name.
- Parameter help is generated from registry descriptions, types, defaults,
  choices, and numeric minimum and maximum values.
- Select parameters list their accepted choices and default when present.
- Integer and number parameters show their bounds and default when present.
- Boolean parameters use paired positive and negative options, such as
  `--sync_mode` and `--no-sync_mode`; their hyphenated equivalents are also
  accepted.
- Prompt is exposed through the top-level `--prompt` and `--file` options, not
  duplicated as a generated model parameter option.
- Source-image registry fields are not exposed as generic model parameters.
- Fixed provider inputs are not exposed as user-configurable options.
- Registry parameter names whose normalized option spellings collide with a
  reserved CLI option or another parameter fail with an actionable registry
  error rather than silently overriding an option.

## Story 4: Supply a prompt directly or from a file

As a user, I want to provide prompt text directly or read it from a file so
that both interactive commands and reusable prompt documents are convenient.

### Acceptance criteria

- `--prompt TEXT` supplies prompt text directly.
- `--file FILENAME` reads prompt text from a UTF-8 encoded file.
- `--prompt` and `--file` are mutually exclusive.
- Exactly one of `--prompt` and `--file` is required for generation.
- Leading and trailing whitespace is removed from direct and file-based prompt
  text, consistently with existing generation validation.
- An empty prompt or a file containing only whitespace is rejected before any
  provider request is made.
- A missing, unreadable, or non-UTF-8 prompt file produces an actionable error
  on stderr and a non-zero exit status.
- Existing prompt annotation validation and provider-side annotation stripping
  behavior is reused.

## Story 5: Generate through existing application services

As a user, I want CLI generations to behave like web-interface generations so
that results appear in the same gallery with the same metadata and history.

### Acceptance criteria

- The CLI validates submitted model parameters with the existing authoritative
  server-side model validation.
- Registry defaults, select choices, numeric bounds, conditional dimensions,
  fixed inputs, and provider-specific parameter behavior remain consistent with
  the web application.
- The CLI creates the same generation request and durable history records used
  by the web application.
- Generation runs synchronously through the existing generation worker/service
  path and existing provider implementation selected by `--provider`.
- The CLI does not start Flask, require a running web server, acquire a browser
  session, parse a CSRF token, or make an HTTP request to the local web API.
- Existing provider credentials, timeouts, and polling configuration are used.
- Generated images are persisted through the existing image store with the
  same embedded metadata and safety checks as web-generated images.
- Successfully generated images appear in the configured gallery.
- An unavailable credential, validation failure, provider failure, timeout,
  download failure, or persistence failure produces a non-zero exit status and
  an actionable error on stderr.
- CLI interruption and cancellation of an already-submitted upstream provider
  request are outside this epic.

## Story 6: Consume generation results

As a user, I want machine-readable result output so that shell scripts can use
the generated images reliably.

### Acceptance criteria

- Without `--quiet`, successful generation writes the full completed request
  result as JSON to stdout.
- The JSON reuses the application's existing completed request shape rather
  than introducing a second incompatible result schema.
- Result image entries use reusable paths relative to the project root, such
  as `outputs/images/example.jpg`.
- With `--quiet`, successful generation writes only generated image paths to
  stdout, one path per line.
- Quiet paths are relative to the project root and use the configured data and
  image directories.
- `--quiet` does not write progress, logs, headings, JSON, or explanatory text
  to stdout.
- Diagnostics and errors are written to stderr in both output modes.
- Success exits with status `0`.
- Argument and validation failures exit with status `2`.
- Generation and other runtime failures exit with status `1`.

## Documentation requirements

- Update end-user documentation with installation and representative
  `imagegen` examples.
- Document that commands are run from the project root, which is also the base
  for `.env` loading and relative result paths.
- Document direct prompts, prompt files, alias and quoted display-name model
  selection, model-specific help, boolean options, and quiet output.
- Keep CLI help and end-user documentation consistent about the discovery
  sequence and automation contract.
- Update provider-model documentation with the per-provider alias and
  case-insensitive display-name uniqueness requirements.

## Out of scope

- Image-edit generation or source-image arguments.
- Submitting CLI work through the Flask HTTP API.
- Detached/background CLI execution.
- Canceling an upstream generation after CLI interruption.
- A new CLI framework dependency.
- A separate `--llm` help gateway or LLM-specific help text.
- A machine-readable `--schema` command. Add one only when a concrete consumer
  needs programmatic registry introspection.
