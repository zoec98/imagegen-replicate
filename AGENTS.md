# AGENTS.md

This file is for developers and coding agents working on `imagegen`. End-user setup and usage belong in [README.md](README.md).

## Project Intent

`imagegen` is a Python Flask application for preparing and submitting image generation requests to Replicate through the official Python API module.

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

Project scripts live in `scripts/`:

- `scripts/run-dev.sh`: start the Flask development server on `0.0.0.0:5002`.
- `scripts/run-dev.cmd`: Windows CMD version of the Flask development server launcher.
- `scripts/get_schema owner/model`: fetch `https://replicate.com/<owner>/<model>/api/schema`.

## Expected Application Shape

Keep the application small and explicit until real duplication appears.

Preferred structure as the app grows:

- `src/imagegen/`: application package.
- `src/imagegen/app.py`: Flask application factory and route registration.
- `src/imagegen/replicate_client.py`: wrapper around Replicate API calls, downloads, and error handling.
- `src/imagegen/generation_log.py`: SQLite generation request and result history.
- `src/imagegen/metadata_embed.py`: embedded image metadata read/write helpers.
- `src/imagegen/metadata.py`: image metadata provider boundary used by routes and gallery code.
- `src/imagegen/models.py`: configured model metadata and parameter schemas.
- `src/imagegen/palettes.py`: filesystem palette repository, validation, and CRUD helpers.
- `src/imagegen/prompt_annotations.py`: server-side annotation validation and provider-prompt stripping.
- `src/imagegen/templates/`: Jinja templates.
- `src/imagegen/static/`: CSS, JavaScript, and local UI assets.
- `tests/`: focused tests for request construction, palette handling, downloads, and route behavior.

Use a Flask application factory, for example `create_app(config: dict | None = None)`, so tests can create isolated apps.

## Replicate Integration

Use the official `replicate` Python package for Replicate API access.

Do not hard-code credentials. Read Replicate authentication from environment variables, primarily:

```bash
REPLICATE_API_TOKEN
```

Keep Replicate-specific code behind a small project wrapper so the UI and route tests can use fakes without calling the network.

Always send `disable_safety_checker: true` for models that support that parameter. This is an application policy and should be stored in fixed model inputs, not exposed as a normal user-facing parameter.

For generated images:

- Treat Replicate outputs as untrusted remote URLs or file-like values.
- Download results through a single helper that applies timeouts, size limits where practical, and content-type checks.
- Store downloaded files under an application-controlled output directory.
- Generate collision-resistant filenames.
- Preserve useful metadata, such as model name, prompt, parameters, source URL, and creation time.
- Read generated-image author metadata from `AUTHOR`; synthesize copyright from
  `AUTHOR` and the generated image's creation year.
- Treat the stored generated file as the canonical metadata-rich image.
- Store generated image metadata in embedded image metadata, not JSON sidecars. PNG uses an application text chunk; JPEG and WebP use EXIF fields.
- Store a human-readable generated-image description for external tools, and parseable application metadata separately in the embedded payload.
- Write and strip image metadata with Python helpers, not by shelling out to `exiftool` or other metadata tools.
- Keep open/view, normal download, and clean download behavior distinct. Open/view serves the stored file for browser display. Normal download serves the stored metadata-rich file with attachment headers. Clean download serves a temporary metadata-stripped copy without mutating the stored file.
- Store clean export files under the configured temporary directory, not in the gallery output directory, and do not expose them as gallery assets.
- Store durable generation request/result history in SQLite under the configured data directory, `data/` by default.
- Keep route and gallery code behind provider/repository boundaries. Do not read embedded metadata or SQLite tables directly from templates or JavaScript-facing route code.
- Store source image references as local filenames, not image bytes or database blobs.
- GIF files are unsupported for generated outputs and source images.

## Model Configuration

Model definitions should be data-driven. Each supported model should declare:

- Stable internal id.
- Display name.
- Replicate model key, such as `bytedance/seedream-4.5`.
- Pinned Replicate version id.
- Schema URL in the form `https://replicate.com/<owner>/<model>/api/schema`.
- Edit capability as a boolean, stored in model metadata outside normal parameters. Set it to `true` for any model that accepts one or more source images.
- Fixed input values that must always be sent but are not user-facing parameters, such as `disable_safety_checker: true`.
- Mode: `text-to-image` or `image-edit`.
- Prompt field behavior.
- Required and optional parameters.
- Parameter widget type, such as text, textarea, number, slider, select, checkbox, image upload, or seed.
- Defaults, bounds, choices, array item formats, and display order.
- Output shape, especially whether outputs are image URLs.

Use `scripts/get_schema owner/model` before adding or updating a model registry entry. The Replicate schema page is HTML, but it embeds a dereferenced OpenAPI schema in JSON script data. Extract useful registry information from `components.schemas.Input` and `components.schemas.Output`:

- `required`: server-required input names.
- `properties`: parameter names and metadata.
- image/source input fields such as `image_input`: evidence that the model is edit-capable.
- `type` and nested `items`: widget and validation shape.
- `enum`: select choices.
- `default`: form defaults.
- `minimum` and `maximum`: numeric bounds.
- `format`: URI/date/file hints.
- `x-order`: stable UI ordering.
- `description`: user-facing help text.

If the page exposes multiple embedded schemas or versions, prefer the schema associated with the current/latest version shown by the page, and record the schema URL and pinned version in the registry. If that association is ambiguous, document the ambiguity in the change summary instead of guessing silently.

Do not assume the Replicate schema is a complete description of the underlying model's capabilities across all suppliers. For Seedream 4.5 specifically, other suppliers support and honor custom `width` and `height` parameters. Model metadata should be flexible enough to represent provider-specific and conditional parameters, for example showing `width` and `height` only when a provider/schema supports `size: custom`.

Validate all submitted parameters server-side. The browser UI may help the user, but server validation is authoritative.

Image-edit requests must submit selected source images through the top-level `source_images` field with `edit_mode: true`. Do not accept model source-image parameters through the generic `parameters` object.

## Prompt Palettes

Style, character, and other palettes are reusable prompt fragments. Store fragments as plain text files under the fragment root derived from `IMAGEGEN_DATA_DIR`, which defaults to:

```text
data/fragments
```

Committed sample fragments live under `data-example/fragments`. Keep local
runtime data under ignored `data/` or another private `IMAGEGEN_DATA_DIR` value.

Every directory under the fragment root is one singular palette, for example:

```text
data/fragments/
|-- character
|   |-- aoife.txt
|   `-- zoe.txt
`-- style
    |-- comic_lawrence.txt
    `-- photo.txt
```

Every `.txt` file under a palette directory is one fragment entry. Ignore non-`.txt` files. Missing fragment roots are valid and mean there are no palettes.

Palette and fragment names:

- Use singular palette directory names, such as `character` and `style`.
- Must start with a letter.
- May contain only `A-Z`, `a-z`, `0-9`, `_`, and `-`.
- Store spaces in fragment filenames as underscores.
- Display underscores as spaces in the UI.
- Normalize UI-entered fragment names by replacing spaces with underscores before validation.

Fragment content:

- Must be UTF-8 text.
- Must be at most 256 bytes.
- May not contain `(`, `)`, or `:`.
- Must be validated before exposure to the browser or writes from the UI.

Palette entries exposed to the browser should include:

- Palette name.
- Palette display name.
- Fragment name.
- Fragment display name.
- Fragment content.

When inserting palette content, keep the user's original prompt visible and editable. Do not silently replace user-entered text.

Prompt annotations use this plain textarea syntax:

```text
(character: zoe fragment content)
```

The browser owns cursor-aware annotation insertion and replacement. If the cursor is inside an annotation of the same palette, selecting a new fragment replaces the full annotation. If the cursor is inside a different palette annotation, the browser must reject the edit and leave the prompt unchanged.

The server is authoritative for generation submission. It accepts either a plain prompt or a valid non-nested annotated prompt. Invalid or nested annotations must be rejected before request state, SQLite rows, or worker jobs are created.

Provider prompt stripping happens server-side immediately before constructing the model-provider request. The provider receives annotation content without app-specific syntax. The app must preserve annotated prompts in request status, SQLite history, and embedded image metadata. `request_sent_json` stores the provider-ready payload for reproducibility.

Palette routes and UI code must use `PaletteRepository`; do not read or write fragment files directly from templates or ad hoc route code. Palette write routes require CSRF. Palette read routes may be non-mutating JSON routes, but still validate names before filesystem access and must not expose files outside the configured fragment root.

External filesystem edits are picked up on page refresh. Do not add live reload or stale palette menu checks unless explicitly requested. The UI may create, update, and delete entries inside existing palette directories, but creating or deleting whole palette directories remains a manual filesystem task.

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
- Gallery controls for loading embedded metadata into the workspace and deleting local images.

Responsive behavior matters. Test layouts at mobile, tablet, and desktop widths. Controls should remain usable on touch devices, with adequate spacing and no text overlap.

Keep JavaScript progressive and focused. Server-rendered Flask/Jinja pages are preferred unless there is a clear reason for a heavier frontend.

## Testing Expectations

Maintain meaningful tests. Add tests with each behavior change unless the change is documentation-only or purely mechanical.

Write tests in the style of GOOS / outside-in TDD. Start from observable behavior, not implementation details. A good test should survive refactoring.

Prioritize tests for:

- Request payload construction per model.
- Server-side parameter validation.
- Palette loading and insertion behavior.
- Image-edit upload handling.
- Replicate wrapper behavior using fakes/mocks.
- Result download handling and metadata creation.
- Flask route success and error paths.

Tests must not call the real Replicate API by default.

Testing rules:

- Start from observable behavior, not implementation details.
- Prefer tests through public APIs, CLI commands, HTTP endpoints, or domain-level interfaces.
- Do not test private methods directly.
- Do not assert exact internal call sequences unless the protocol is the behavior.
- Use mocks only at architectural boundaries: filesystem, network, database, clock, random, and external services.
- Avoid one-test-per-function.
- Prefer examples that describe user-visible or business-visible behavior.
- A good test should survive refactoring.
- If a test would break after renaming, extracting, or moving internal functions without changing behavior, rewrite it.
- Use red-green-refactor:
  1. Add one failing test for missing behavior.
  2. Implement the smallest change.
  3. Refactor only with tests green.
- Before writing tests, list the behaviors worth protecting in the test file comments.
- After writing tests, review them and delete tests that only pin implementation details.

## Refactoring Policy

When asked to refactor, do not change code immediately. First create or update [REFACTOR.md](REFACTOR.md).

For each module under review:

- State its intended responsibility at the top of the module in a comment block.
- State the same intended responsibility in `REFACTOR.md`.
- List functions/classes that do not match that responsibility.
- Identify duplicated behavior, near-duplicate code, and concepts implemented in multiple places.
- Propose moves, extractions, merges, or renames.
- Do not change code yet.
- For each proposed refactoring, list the behavior tests needed before the change.
- These tests must cover observable behavior and must not depend on the current internal structure.

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
- Do not store uploaded files or generated outputs in source-controlled paths unless they are intentional fixtures. Keep sample/reference payloads under `data-example/`, not `data/`.
- Do not read or write JSON sidecars for generated-image metadata.
- Do not use shell metadata tools such as `exiftool`; keep metadata writes and clean exports in Python.
- Do not strip metadata from the stored gallery image when creating a clean download.
- Do not write clean exports into the gallery output directory or list them as gallery images.
- Do not bypass `ImageMetadataProvider` or `SQLiteGenerationLog` from route/gallery code.
- Do not bypass `PaletteRepository` for palette file access.
- Do not overwrite existing user prompts, palette files, or generated outputs without an explicit user action.
- Do not create or delete whole palette directories from the UI.
- Do not send annotation syntax to model providers; strip annotations at the provider boundary.
- Do not add broad abstractions before at least two concrete model integrations prove the shape.
- Do not skip `uv run pytest` and `uv run ruff check src tests` after code changes unless the reason is documented in the final response.
- Assume tests are quick and cheap, always run `uv run pytest` in full, not individual tests.
- Do not make `disable_safety_checker` user-configurable when a model supports it; keep it set to `true` in generated Replicate payloads.
- Do not hide Replicate errors behind generic messages in logs; preserve actionable details while avoiding credential leakage.
- Do not trust browser-submitted parameters, filenames, MIME types, or output URLs.
- Keep gallery deletion inside the configured output directory; validate filenames, require CSRF protection, and move deleted images to the configured trash directory instead of unlinking them from routes.
- Do not use destructive git commands or revert unrelated user changes.
