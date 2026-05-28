# AGENTS.md

This file is for developers and coding agents working on `imagen`. End-user setup and usage belong in [README.md](README.md).

## Project Intent

`imagen` is a Python Flask application for preparing and submitting image generation requests to Replicate through the official Python API module.

The application should support:

- Text-to-image models.
- Image-edit models that accept an input image plus prompt and model options.
- Multiple Replicate models with model-specific parameters.
- Style palettes that insert reusable style prompt sections.
- Character palettes that insert reusable character description snippets.
- A responsive browser UI targeting iOS, iPadOS, and desktop browsers.
- Downloaded image results stored locally and made available for later use.

## Development Environment

The project is managed with `uv`.

Use the project-local commands:

```bash
uv sync
uv run pytest
uv run ruff format src tests
uv run ruff check --fix src tests
```

When adding runtime dependencies, use `uv add <package>`. When adding test or tooling dependencies, use `uv add --dev <package>`.

## Expected Application Shape

Keep the application small and explicit until real duplication appears.

Preferred structure as the app grows:

- `src/imagen/`: application package.
- `src/imagen/app.py`: Flask application factory and route registration.
- `src/imagen/replicate_client.py`: wrapper around Replicate API calls, downloads, and error handling.
- `src/imagen/models.py`: configured model metadata and parameter schemas.
- `src/imagen/palettes.py`: style and character palette loading and validation.
- `src/imagen/templates/`: Jinja templates.
- `src/imagen/static/`: CSS, JavaScript, and local UI assets.
- `tests/`: focused tests for request construction, palette handling, downloads, and route behavior.

Use a Flask application factory, for example `create_app(config: dict | None = None)`, so tests can create isolated apps.

## Replicate Integration

Use the official `replicate` Python package for Replicate API access.

Do not hard-code credentials. Read Replicate authentication from environment variables, primarily:

```bash
REPLICATE_API_TOKEN
```

Keep Replicate-specific code behind a small project wrapper so the UI and route tests can use fakes without calling the network.

For generated images:

- Treat Replicate outputs as untrusted remote URLs or file-like values.
- Download results through a single helper that applies timeouts, size limits where practical, and content-type checks.
- Store downloaded files under an application-controlled output directory.
- Generate collision-resistant filenames.
- Preserve useful metadata, such as model name, prompt, parameters, source URL, and creation time.

## Model Configuration

Model definitions should be data-driven. Each supported model should declare:

- Stable internal id.
- Display name.
- Replicate model/version identifier.
- Mode: `text-to-image` or `image-edit`.
- Prompt field behavior.
- Required and optional parameters.
- Parameter widget type, such as text, textarea, number, slider, select, checkbox, image upload, or seed.
- Defaults, bounds, and choices.

Validate all submitted parameters server-side. The browser UI may help the user, but server validation is authoritative.

## Prompt Palettes

Style and character palettes are reusable prompt fragments. Store them in a form that is easy to test and review, such as JSON, TOML, YAML, or Python data structures.

Palette entries should have:

- Stable id.
- Human-readable label.
- Prompt snippet.
- Optional tags or notes.

When inserting palette content, keep the user's original prompt visible and editable. Do not silently replace user-entered text.

## UI Guidance

Build the first screen as the actual generation workspace, not a marketing page.

The UI should provide:

- Model selector.
- Mode-aware fields for text-to-image and image-edit workflows.
- Image upload controls for image-edit models.
- Model-specific parameter widgets.
- Style and character palette insertion.
- Generate button with loading and error states.
- Result preview gallery.
- Download/open controls for generated files.

Responsive behavior matters. Test layouts at mobile, tablet, and desktop widths. Controls should remain usable on touch devices, with adequate spacing and no text overlap.

Keep JavaScript progressive and focused. Server-rendered Flask/Jinja pages are preferred unless there is a clear reason for a heavier frontend.

## Testing Expectations

Maintain meaningful tests. Add tests with each behavior change unless the change is documentation-only or purely mechanical.

Prioritize tests for:

- Request payload construction per model.
- Server-side parameter validation.
- Palette loading and insertion behavior.
- Image-edit upload handling.
- Replicate wrapper behavior using fakes/mocks.
- Result download handling and metadata creation.
- Flask route success and error paths.

Tests must not call the real Replicate API by default.

## Documentation Expectations

Keep [README.md](README.md) focused on end users:

- What the app does.
- Requirements.
- Installation.
- Configuration.
- Running the Flask app.
- Basic usage.
- Where generated files are stored.

Keep this file focused on contributors and agents.

## Agent Guardrails

- Do not commit API tokens, generated private images, uploaded user images, or local `.env` files.
- Do not make real Replicate API calls from tests.
- Do not introduce network calls in unit tests unless they are explicitly marked integration tests and skipped by default.
- Do not store uploaded files or generated outputs in source-controlled paths unless they are intentional fixtures.
- Do not overwrite existing user prompts, palette files, or generated outputs without an explicit user action.
- Do not add broad abstractions before at least two concrete model integrations prove the shape.
- Do not skip `uv run pytest` and `uv run ruff check src tests` after code changes unless the reason is documented in the final response.
- Assume tests are quick and cheap, always run `uv run pytest` in full, not individual tests.
- Do not hide Replicate errors behind generic messages in logs; preserve actionable details while avoiding credential leakage.
- Do not trust browser-submitted parameters, filenames, MIME types, or output URLs.
- Do not use destructive git commands or revert unrelated user changes.
