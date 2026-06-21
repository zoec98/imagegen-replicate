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
npm run js:format
npm run js:check
```

When adding runtime dependencies, use `uv add <package>`. When adding test or
tooling dependencies, use `uv add --dev <package>`.

Node dependencies are only needed when changing browser JavaScript. Running the
Flask app does not require Node. Use `npm install` after checkout if
`node_modules/` is absent and JavaScript work is needed.

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
- Refactoring reviews: [development/refactoring.md](development/refactoring.md)
- Security-sensitive work: [development/security-boundary.md](development/security-boundary.md)
- Development folder structure: [development/README.md](development/README.md)
- Current JavaScript refactor decisions and tickets:
  [development/2026-06-07-js-refactor/tickets.md](development/2026-06-07-js-refactor/tickets.md)
- Image upload planning:
  [development/2026-06-07-image-upload/tickets.md](development/2026-06-07-image-upload/tickets.md)
  and [development/2026-06-07-image-upload/user-story.md](development/2026-06-07-image-upload/user-story.md)
- Gallery cleanup findings and follow-up work:
  [development/2026-06-08-gallery-cleanup/analysis.md](development/2026-06-08-gallery-cleanup/analysis.md),
  [development/2026-06-08-gallery-cleanup/audit.md](development/2026-06-08-gallery-cleanup/audit.md),
  [development/2026-06-08-gallery-cleanup/test-notes.md](development/2026-06-08-gallery-cleanup/test-notes.md),
  and [development/2026-06-08-gallery-cleanup/tickets.md](development/2026-06-08-gallery-cleanup/tickets.md)
- Historical route/UI boundary and refactoring audits:
  [development/2026-06-05-refactor-route-and-ui-boundaries/tickets.md](development/2026-06-05-refactor-route-and-ui-boundaries/tickets.md),
  [development/2026-06-05-refactoring-audit/2026-06-05-refactoring-audit.md](development/2026-06-05-refactoring-audit/2026-06-05-refactoring-audit.md),
  and [development/2026-06-05-test-audit/audit.md](development/2026-06-05-test-audit/audit.md)

For new non-trivial work, create or update a focused workstream under
`development/` with a date-prefixed directory such as
`development/YYYY-MM-DD-short-name/`. Store user stories, tickets, notes, and
audit output there. Root planning files such as `PLAN.md`, `USER-STORY.md`,
`AUDIT.md`, and `SCENARIO.md` are legacy or temporary artifacts; prefer
`development/` for future work unless the user explicitly asks otherwise.

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
- `src/imagegen/frontend/`: editable browser JavaScript source modules.
- `src/imagegen/static/`: CSS, generated JavaScript, generated sourcemaps, and
  local UI assets.
- `tests/`: focused tests for behavior and route/provider boundaries.
- `tests/js/`: Vitest + jsdom tests for browser JavaScript behavior.

Use the Flask application factory `create_app(config: dict | None = None)` so
tests can create isolated apps.

Browser JavaScript source of truth lives under `src/imagegen/frontend/`.
`src/imagegen/static/app.js` and `src/imagegen/static/app.js.map` are generated
by `npm run js:build`; do not edit them directly. Keep generated `app.js`
committed so end users can run the Flask app without Node.

Current frontend modules:

- `main.js`: workspace bootstrap and workflow wiring.
- `api.js`: shared JSON, `fetch`, and CSRF request helpers.
- `dom.js`: small DOM creation and attribute helpers.
- `gallery.js`: gallery refresh, card rendering, gallery actions, delete, mask
  trigger, Immich upload trigger, and source-select dispatch.
- `metadata.js`: embedded metadata loading and image information tooltip data.
- `trash.js`: trash overlay listing, restore, empty, count, and close behavior.
- `palettes.js`: prompt palette insertion and palette editor behavior.
- `source-images.js`: edit mode, selected source image state, limits, and
  source-image UI state.
- `generation.js`: generation payload assembly, submit, polling, and completion
  status handling.
- `mask-editor.js`: mask overlay, brush controls, drawing state, invert, and
  save behavior.
- `image-upload.js`: upload overlay, URL import, file/drop import, and Immich
  import browser behavior.

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
- Do not bypass the JavaScript workflow modules in `src/imagegen/frontend/`
  from unrelated browser code. Wire behavior through the existing setup
  functions and service callbacks unless a focused refactor changes ownership.
- Keep gallery deletion inside the configured output directory; validate
  filenames, require CSRF protection, and move deleted images to the configured
  trash directory instead of unlinking them from routes.
- Do not use destructive git commands or revert unrelated user changes.
- Do not skip `uv run pytest` and `uv run ruff check src tests` after code
  changes unless the reason is documented in the final response.
- Do not skip `npm run js:check` after browser JavaScript changes unless the
  reason is documented in the final response.
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
