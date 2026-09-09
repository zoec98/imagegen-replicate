# Installable Tool User Story

## Story

As a user, I want `uv tool install .` to install both the image-generation CLI
and the local web application so that I can run imagegen outside the source
checkout with persistent, tool-specific configuration and data storage.

## User Goals

- Run image generation with the existing `imagegen` command.
- Start the web application with an installed `imagegen-web` command.
- Keep the existing web launcher options on macOS, Linux, and Windows.
- Use a project-local `.env` when one is present.
- Otherwise, use a tool-specific `~/.imagegen.env` configuration file.
- Store runtime data at the configured relative or absolute
  `IMAGEGEN_DATA_DIR` path.

## Installed Commands

The package exposes these console entry points:

```toml
[project.scripts]
imagegen = "imagegen.cli:main"
imagegen-web = "imagegen.web:main"
```

The Python web launcher replaces `scripts/run-dev.sh` and
`scripts/run-dev.cmd`.

### Acceptance Criteria

- `uv tool install .` installs both `imagegen` and `imagegen-web`.
- `imagegen` continues to invoke the existing generation CLI.
- `imagegen-web` starts the Flask web application on `127.0.0.1:5002` by
  default.
- `imagegen-web --dev` enables Flask debug mode.
- `imagegen-web --secure-network` listens on `0.0.0.0:5002`.
- The two options can be used together.
- Unknown options produce a usage error and a non-zero exit status.
- The launcher behaves consistently on macOS, Linux, and Windows.
- The obsolete platform-specific launch scripts are removed after their
  behavior is covered by the installed command.

## Configuration Discovery

At startup, both installed commands use the same dotenv discovery order:

1. Use `.env` in the current working directory when it exists.
2. Otherwise, use `~/.imagegen.env`.

### Acceptance Criteria

- A current-directory `.env` takes precedence over `~/.imagegen.env`.
- The two dotenv files are alternatives and are not merged.
- Existing process environment variables continue to take precedence over
  values loaded from the selected dotenv file.
- The selected dotenv file receives any missing expected settings using the
  application's existing configuration-update behavior.
- When neither file exists, the application creates `~/.imagegen.env` with the
  expected settings and a generated Flask secret.
- Running an installed command does not create `.env` in an arbitrary current
  working directory.
- Paths containing `~` are expanded using the current user's home directory.

## Data Directory Resolution

`IMAGEGEN_DATA_DIR` remains the single configuration setting for runtime data.

### Acceptance Criteria

- An absolute `IMAGEGEN_DATA_DIR` is used unchanged.
- A relative `IMAGEGEN_DATA_DIR` is resolved relative to the selected dotenv
  file's directory.
- With a current-directory `.env` containing `IMAGEGEN_DATA_DIR=data`, runtime
  data is stored under that current directory's `data` directory.
- With `~/.imagegen.env` containing `IMAGEGEN_DATA_DIR=data`, runtime data is
  stored under `~/data`.
- The configured data directory continues to contain the existing `images`,
  `fragments`, `trash`, and `tmp` directories and the SQLite generation log.
- The application does not impose `.local` or another hidden-directory
  convention; users may choose Finder-accessible paths in their configuration.

## Compatibility Boundaries

- Provider credentials and all existing dotenv settings retain their current
  names and behavior.
- The change does not migrate or copy existing dotenv files or runtime data.
- The Flask server remains a local development-style server; introducing a
  production WSGI server is outside this epic.
