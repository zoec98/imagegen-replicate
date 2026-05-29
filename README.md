# imagegen

`imagegen` is a Flask web application for creating image generation requests and running them through Replicate. It is intended to support text-to-image and image-edit workflows, multiple Replicate models, model-specific parameters, reusable style palettes, reusable character palettes, and local access to downloaded image results.

Developer and agent contribution guidance lives in [AGENTS.md](AGENTS.md).

## Requirements

- Python 3.14 or newer, matching the project configuration.
- `uv`.
- A Replicate account and API token.

## Installation

Clone the repository and enter the project directory:

```bash
cd img-replicate
```

Install the project environment:

```bash
uv sync
```

Set your Replicate API token:

```bash
export REPLICATE_API_TOKEN="your-token"
```

Optional Replicate timing settings:

```bash
export IMAGEGEN_REPLICATE_POLL_SECONDS="1.0"
export IMAGEGEN_REPLICATE_TIMEOUT_SECONDS="60.0"
```

For local development, you can place environment setup in your shell profile or a local `.env` file. The application creates missing default `.env` keys when it starts. Do not commit secrets.

## Running

Start the Flask development server:

```bash
scripts/run-dev.sh
```

Then open:

```text
http://127.0.0.1:5002
```

The Flask app submits Replicate predictions through JSON API routes, polls for completion from the browser, downloads returned images, and stores local metadata for gallery use.

## Usage

The MVP UI flow is:

1. Enter the prompt.
2. Set the currently exposed Seedream 4.5 parameters.
3. Press Generate.
4. Keep the page open while the browser polls request status.
5. Preview the returned image results in the gallery.
6. Open generated files directly from the gallery in a new tab.

The page requires JavaScript for generation. It does not reload for normal generation requests, so the prompt and selected parameter controls remain visible while work runs.

Generated files are downloaded from Replicate into `data/images/` by default. Gallery links point directly to `/images/<filename>`. The current metadata provider reads sidecar files named `<image-filename>.json` with model, prompt, parameters, source URL, creation time, content type, and byte size; metadata access is modular because this is expected to move into image EXIF later.

Image-edit source images are prepared at the API layer but do not yet have UI selection controls. Source images are expected to live in the same `data/images/` directory as generated images so generated results can be re-used for later edits.

## Development

Use `uv` for all project commands:

```bash
uv sync
uv run pytest
uv run ruff format src tests
uv run ruff check --fix src tests
```

See [AGENTS.md](AGENTS.md) for project structure, testing expectations, Replicate integration rules, UI guidance, and agent guardrails.

Developer scripts live in [scripts/](scripts):

- `scripts/run-dev.sh`
- `scripts/run-dev.cmd`
- `scripts/get_schema bytedance/seedream-4.5`
