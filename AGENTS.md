# AGENTS.md

This file is the entry point for developers and coding agents working on
`imagegen`. End-user setup and usage belong in [README.md](README.md).

## Project Intent

`imagegen` is a Python Flask application for preparing image generation and
image-edit requests, sending them to configured image providers, and keeping
generated images available in a local metadata-rich gallery.

## Required Commands

The project is managed with `uv`.

Use the project-local commands:

```bash
uv sync
uv run pytest
uv run ruff format src tests
uv run ruff check --fix src tests
```

When adding runtime dependencies, use `uv add <package>`. When adding test or
tooling dependencies, use `uv add --dev <package>`.

Project scripts live in `scripts/`:

- `scripts/run-dev.sh`: start the Flask development server on
  `127.0.0.1:5002` by default, or `0.0.0.0:5002` with `--secure-network`.
  Debug mode is enabled only with `--dev`.
- `scripts/run-dev.cmd`: Windows CMD version of the Flask launcher.
- `scripts/get_schema_replicate owner/model`: fetch Replicate schema data.
- `scripts/get_schema_falai text-api-url [edit-api-url]`: fetch fal.ai endpoint
  docs, schema, pricing, and optional linked edit endpoint information.

## Progressive Discovery

Keep this file short. Detailed internal working material belongs under
[`development/`](development/index.md).

Before work, load only the focused detail file needed for the task:

- Provider/model registry work: [development/provider-models.md](development/provider-models.md)
- Generated image storage and metadata: [development/generated-images.md](development/generated-images.md)
- Prompt palette work: [development/prompt-palettes.md](development/prompt-palettes.md)
- UI work: [development/ui-guidance.md](development/ui-guidance.md)
- Testing rules: [development/testing.md](development/testing.md)
- Refactoring reviews: [development/refactoring.md](development/refactoring.md)
- Security-sensitive work: [development/security-boundary.md](development/security-boundary.md)
- New feature planning, audits, and decisions: [development/index.md](development/index.md)

For new non-trivial work, create or update a focused workstream under
`development/epics/` with user stories, tickets, notes, and audit output. Root
planning files such as `PLAN.md`, `USER-STORY.md`, `AUDIT.md`, and
`SCENARIO.md` are legacy or temporary artifacts; prefer `development/` for
future work unless the user explicitly asks otherwise.

## Expected Application Shape

Keep the application small and explicit until real duplication appears.

Preferred structure as the app grows:

- `src/imagegen/`: application package.
- `src/imagegen/app.py`: Flask application factory and route registration.
- `src/imagegen/replicate_client.py`: Replicate provider wrapper.
- `src/imagegen/falai_client.py`: fal.ai provider wrapper.
- `src/imagegen/generation_log.py`: SQLite generation request/result history.
- `src/imagegen/metadata_embed.py`: embedded image metadata read/write helpers.
- `src/imagegen/metadata.py`: metadata provider boundary used by routes/gallery.
- `src/imagegen/model_registry.py`: configured provider/model metadata.
- `src/imagegen/palettes.py`: filesystem palette repository and validation.
- `src/imagegen/prompt_annotations.py`: prompt annotation validation/stripping.
- `src/imagegen/templates/`: Jinja templates.
- `src/imagegen/static/`: CSS, JavaScript, and local UI assets.
- `tests/`: focused tests for behavior and route/provider boundaries.

Use the Flask application factory `create_app(config: dict | None = None)` so
tests can create isolated apps.

## Hard Guardrails

- Do not commit API tokens, generated private images, uploaded user images, or
  local `.env` files.
- Do not make real image provider API calls from tests.
- Do not introduce network calls in unit tests unless they are explicitly
  marked integration tests and skipped by default.
- Keep runtime data under ignored `data/` or another private
  `IMAGEGEN_DATA_DIR`. Keep sample/reference payloads under `data-example/`.
- Store generated-image metadata in embedded image metadata, not JSON sidecars.
- Do not use shell metadata tools such as `exiftool`.
- Do not strip metadata from the stored gallery image when creating a clean
  download.
- Do not write clean exports into the gallery output directory or list them as
  gallery images.
- Do not bypass `ImageMetadataProvider`, `SQLiteGenerationLog`,
  `PaletteRepository`, provider wrappers, or gallery/repository boundaries from
  route/template/JavaScript-facing code.
- Do not overwrite existing user prompts, palette files, or generated outputs
  without an explicit user action.
- Do not create or delete whole palette directories from the UI.
- Do not send prompt annotation syntax to model providers.
- Do not add broad abstractions before at least two concrete integrations prove
  the shape.
- Do not make provider fixed safety inputs user-configurable when policy says
  they must be fixed.
- Do not hide provider errors behind generic messages in logs; preserve
  actionable details while avoiding credential leakage.
- Do not trust browser-submitted parameters, filenames, MIME types, metadata, or
  output URLs.
- Keep gallery deletion inside the configured output directory; validate
  filenames, require CSRF protection, and move deleted images to the configured
  trash directory instead of unlinking them from routes.
- Do not use destructive git commands or revert unrelated user changes.
- Do not skip `uv run pytest` and `uv run ruff check src tests` after code
  changes unless the reason is documented in the final response.
- Assume tests are quick and cheap; run `uv run pytest` in full, not only
  individual tests, before finishing code changes.

## Documentation

Keep [README.md](README.md) focused on end users:

- What the app does.
- Requirements.
- Installation.
- Configuration.
- Running the Flask app.
- Basic usage.
- Where generated files are stored.

Keep internal user stories, tickets, audits, security-boundary notes, and
architecture decisions under `development/`.
