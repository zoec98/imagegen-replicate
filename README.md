# imagegen

`imagegen` is a Flask web application for preparing image generation and image edit requests, sending them to Replicate, and keeping the generated images available in a local gallery.

Developer and agent contribution guidance lives in [AGENTS.md](AGENTS.md).

## Requirements

- Python 3.14 or newer, matching the project configuration.
- `uv`.
- A Replicate account and API token for real generation requests.

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

For local development, you can place environment setup in a local `.env` file. Do not commit secrets. See `.env.example` for supported configuration.

## Running

Start the Flask development server:

```bash
scripts/run-dev.sh
```

Then open:

```text
http://127.0.0.1:5002
```

The page includes an app build checksum. If the server-side assets change while a browser tab is open, generation is blocked and the UI asks you to reload before submitting another request.

## Usage

1. Choose a model from the model selector.
2. Enter a prompt.
3. Set model-specific parameters such as image size, aspect ratio, guidance, seed, output format, or custom dimensions.
4. For image edits, enable `Edit`, select one or more existing gallery images as sources, then submit the request.
5. Press `Generate`.
6. Watch request status in the message area.
7. Use the gallery to open generated images, inspect metadata, load metadata back into the workspace, or delete local images.

Image edit sources are selected from local gallery images. Source images are submitted as local filenames; image bytes are not placed in the browser JSON payload.

## Gallery

Generated images appear in the local gallery. Each gallery card provides:

- An information button with filename, model, dimensions, and prompt.
- A file type badge for PNG, JPG, or WebP.
- A load button that reads embedded metadata and replaces the current prompt, model, and supported settings.
- A delete button that removes the local image after a CSRF-protected server request.

Loading metadata requires metadata embedded by this app. If metadata is missing or references an unsupported model/settings shape, the UI shows an error and preserves the current workspace.

## Storage

Generated files are downloaded from Replicate into `data/images` by default. Supported local image formats are PNG, JPEG, and WebP. GIF files are not accepted as source images or stored generation results.

The app embeds generated-image metadata directly into PNG, JPEG, and WebP files. Metadata includes the model, prompt, parameters, source URL, creation time, and related generation identifiers. New generated images do not use JSON sidecar files.

Durable request history is recorded in SQLite at `data/imagegen.sqlite3` by default. The database stores accepted request facts, prediction lifecycle state, and generated asset rows. The active browser polling state remains in memory.

## Development

Use `uv` for all project commands:

```bash
uv sync
uv run pytest
uv run ruff format src tests
uv run ruff check --fix src tests
```

Developer scripts live in [scripts/](scripts):

- `scripts/run-dev.sh`
- `scripts/run-dev.cmd`
- `scripts/get_schema bytedance/seedream-4.5`

See [AGENTS.md](AGENTS.md) for project structure, testing expectations, Replicate integration rules, UI guidance, and guardrails.
