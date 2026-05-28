# imagegen

`imagegen` is a Flask web application for creating image generation requests and running them through Replicate. It is intended to support text-to-image and image-edit workflows, multiple Replicate models, model-specific parameters, reusable style palettes, reusable character palettes, and local access to downloaded image results.

This project is currently an early scaffold. Developer and agent contribution guidance lives in [AGENTS.md](AGENTS.md).

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

For local development, you can place environment setup in your shell profile or a local `.env` file if the application adds dotenv support later. Do not commit secrets.

## Running

At this scaffold stage, the package exposes a placeholder command:

```bash
uv run imagegen
```

Once the Flask app entry point is implemented, the expected local run command will be:

```bash
uv run flask --app imagegen.app run --debug
```

Then open:

```text
http://127.0.0.1:5000
```

## Usage

The planned UI flow is:

1. Choose a Replicate model.
2. Pick text-to-image or image-edit mode when the model supports it.
3. Enter the prompt.
4. Insert optional style palette snippets.
5. Insert optional character palette snippets.
6. Set model-specific parameters such as image size, guidance, seed, or number of outputs.
7. Upload an input image for image-edit models.
8. Press Generate.
9. Preview the returned image results.
10. Download or reuse the generated files from the local results area.

Generated files should be downloaded from Replicate and stored locally by the application with useful metadata, including the model, prompt, parameters, source URL, and creation time.

## Development

Use `uv` for all project commands:

```bash
uv sync
uv run pytest
uv run ruff format src tests
uv run ruff check --fix src tests
```

See [AGENTS.md](AGENTS.md) for project structure, testing expectations, Replicate integration rules, UI guidance, and agent guardrails.
