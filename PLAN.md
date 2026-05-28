# MVP Implementation Plan

This plan targets a basic end-to-end testable Flask MVP for submitting a text prompt to Replicate, downloading generated images, and browsing local image results.

## Stage 1: Project Dependencies And Configuration

Add the runtime dependencies needed for the MVP:

- `flask`
- `replicate`
- `python-dotenv`
- `httpx` or `requests` for downloading returned image URLs

Add development dependencies if missing:

- `pytest`
- `ruff`

Configuration behavior:

- Load `.env` at app startup.
  - We have an expected shape for the .env file: Each possible variable is present with a default and a comment.
  - We check if the .env file is present, if not we create it.
  - We check for each variable if it is present and has a value. If not, we use the default value and add the comment explaining the options.
- Read `REPLICATE_API_TOKEN` from the environment.
- Read optional app settings such as `IMAGEGEN_OUTPUT_DIR`, `IMAGEGEN_MODEL`, and `IMAGEGEN_FLASK_SECRET_KEY`.
- Default generated image storage to `data/images/`.
- Ensure `data/` remains ignored by git.

Missing information and parts:

- Exact first Replicate model/version to use for the MVP.
  - We use the currently most current version and pin it.
- Whether model id should be configured as owner/model, owner/model:version, or a project-specific alias.
  - We maintain a model registry. It is keyed with a model specific alias, for example "seedream45".
  - For each model, the registry stores:
    - The replicate documentation URL, here "https://replicate.com/bytedance/seedream-4.5/api"
    - The replicate python module name, here ""bytedance/seedream-4.5"
    - The models input JSON parameters, each with name, description, type and default values (optional list of valid choices)
      - Here apparently "size", "prompt" and "aspect_ratio".
- Whether generated output metadata should be stored in sidecar JSON files in this stage.
  - We want at this stage store a metadata JSON next to the downloaded image, with the full image name + ".json"
- Whether `.env.example` should be committed with non-secret defaults.
  - Yes, but even then we want the default generation mechanism.

## Stage 2: Flask Application Skeleton

Create a Flask application factory:

- `src/imagegen/app.py`
- `create_app(config: dict | None = None) -> Flask`

Add routes:

- `GET /`: render the main generation page.
- `POST /generate`: accept prompt text, call the Replicate service, download result images, then redirect back to `/`.
- `GET /images/<filename>`: serve local generated images.
- `GET /images/<filename>/view`: render or redirect to a full-tab image view.

Use `url_for` for links and static assets.

Missing information and parts:

- Final route naming convention.
- Whether image full view should be a plain direct image response or an HTML page with the image centered.
- Whether failed generations should redirect with flash messages or return an inline error response.
- Whether the app should use sessions and Flask flash messages in the MVP.

## Stage 3: Replicate Service Wrapper

Create a small wrapper around Replicate:

- `src/imagegen/replicate_client.py`
- Accept prompt text and model configuration.
- Submit the request through the official `replicate` package.
- Normalize output into a list of downloadable image URLs or file-like outputs.
- Avoid direct Replicate calls outside this wrapper.

For tests:

- Provide a fake client or injectable callable.
- Ensure unit tests never call the real Replicate API.

Missing information and parts:

- Exact Replicate API call shape for the chosen MVP model.
- Expected Replicate output format for the chosen model.
- Timeout and retry policy for generation requests.
- Whether the MVP should support streaming/progress or only blocking generation.

## Stage 4: Image Download And Local Gallery

Implement image persistence:

- Download returned image URLs.
- Validate successful response status.
- Validate content type starts with `image/`.
- Generate collision-resistant filenames.
- Store images under `data/images/`.
- List existing image files on page load.
- Sort newest first.

Supported file extensions for discovery:

- `.png`
- `.jpg`
- `.jpeg`
- `.webp`
- `.gif`

Missing information and parts:

- Maximum image download size.
- Whether original output format should always be preserved.
- Whether generated images should have metadata sidecars.
- Whether uploads and generated outputs should share a storage root later.
- Whether old generated files need cleanup or retention limits.

## Stage 5: Main UI

Build a single responsive page:

- A large resizable prompt text area.
- A Generate button at the top right of the prompt area.
- A local image gallery below the prompt.
- Each gallery item links to a new tab.
- Selecting an image opens the full image in a new tab.

Responsive gallery behavior:

- Phone: 1 column.
- iPad/tablet: 3 columns where space allows.
- Desktop: 3 columns by default, with room to expand later if useful.

Implementation details:

- Use server-rendered Jinja templates.
- Keep CSS in `src/imagegen/static/`.
- Use CSS grid with responsive media queries.
- Make the textarea vertically resizable.
- Preserve prompt text after failed submissions where practical.

Missing information and parts:

- Desired visual style beyond a functional MVP.
- Whether the gallery should use square thumbnails or natural image aspect ratios.
- Whether the image should open via direct file URL or a dedicated full-view route.
- Whether the prompt field needs a minimum/maximum length.
- Whether keyboard shortcuts are desired for generate.

## Stage 6: Local Tests

Add tests for the MVP behavior:

- App factory creates a Flask app.
- `GET /` returns the prompt form and gallery.
- Gallery lists discovered image files.
- `POST /generate` rejects empty prompts.
- `POST /generate` calls an injected fake Replicate service for valid prompts.
- Download helper writes image files for valid image responses.
- Download helper rejects non-image responses.
- Image route serves stored files and blocks unsafe paths.

Use temporary directories for all tests.

Commands:

```bash
uv run pytest
uv run ruff format src tests
uv run ruff check --fix src tests
```

Missing information and parts:

- Whether browser-level tests are required for this MVP or deferred.
- Whether test fixtures should include tiny local image files.
- Whether integration tests against Replicate should exist but be skipped by default.
- Whether CI configuration is in scope.

## Stage 7: Manual End-To-End Verification

Run the Flask app locally:

```bash
uv run flask --app imagegen.app run --debug
```

Manual verification flow:

1. Open `http://127.0.0.1:5000`.
2. Enter a prompt in the resizable textarea.
3. Press Generate.
4. Confirm the request is sent to Replicate.
5. Confirm returned image files are downloaded into `data/images/`.
6. Confirm the gallery updates and shows the generated image.
7. Open an image in a new tab.
8. Confirm mobile, iPad, and desktop widths use appropriate gallery columns.

Missing information and parts:

- Availability of a valid `REPLICATE_API_TOKEN` for manual testing.
- Expected generation latency for the selected model.
- Whether local manual testing should use a fake Replicate mode.
- Whether generated images should be visually inspected or only existence-checked.

## Stage 8: MVP Definition Of Done

The MVP is complete when:

- `uv sync` installs all dependencies.
- `.env` configuration is loaded.
- The Flask app starts locally.
- The main page has a resizable prompt textarea and top-right Generate button.
- Submitting a prompt calls Replicate through a wrapper.
- Returned image results are downloaded locally.
- The main page displays local image files in a responsive gallery.
- Gallery images open in a new browser tab at full size.
- Unit tests cover the app factory, routes, gallery discovery, request dispatch, and download behavior.
- `uv run pytest` passes.
- `uv run ruff format src tests` has been run.
- `uv run ruff check --fix src tests` passes.

Missing information and parts:

- Final MVP model choice.
- Final output directory naming.
- Final error-message copy.
- Whether a committed `.env.example` is required.
- Whether README should be updated during the same implementation pass.
