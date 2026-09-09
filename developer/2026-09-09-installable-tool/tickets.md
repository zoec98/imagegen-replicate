# Installable Tool — Tickets

These tickets implement the committed installable-tool user story in
behavior-first order. Configuration discovery is implemented first because both
installed commands depend on it.

## 1. Discover persistent dotenv configuration

Make default configuration loading select a current-directory `.env` when it
exists and otherwise select the current user's `~/.imagegen.env`.

Behavior to prove first:

- A default configuration load uses `.env` from the current working directory
  when that file exists.
- Without a current-directory `.env`, the load uses an existing
  `~/.imagegen.env`.
- The selected files are alternatives; values from the lower-priority file are
  not merged into the higher-priority file.
- Without either file, the load creates and uses `~/.imagegen.env`, including a
  generated Flask secret, without creating `.env` in the working directory.
- Process environment variables retain precedence over values in the selected
  dotenv file.
- An explicitly supplied dotenv path continues to select that exact file for
  tests and embedded application use.
- A relative `IMAGEGEN_DATA_DIR` resolves from the selected dotenv file's
  directory, an absolute path remains absolute, and `~` is expanded.

Keep discovery in the existing configuration boundary; callers should continue
to use `load_config()` rather than locate dotenv files themselves.

Public interface: `imagegen.config.load_config`, including its existing
explicit-path form and its new default discovery behavior.

Likely touchpoints: `src/imagegen/config.py` and `tests/test_config.py`.

Verification: add one failing configuration behavior at a time, implement the
smallest shared selection change, then run `uv run pytest` and
`uv run ruff check src tests`.

## 2. Provide the cross-platform web launcher

Add a testable Python web entry point that preserves the behavior of the two
platform-specific development launchers.

Behavior to prove first:

- `imagegen.web.main([])` starts the Flask application on `127.0.0.1:5002`
  without debug mode.
- `--dev` enables Flask debug mode.
- `--secure-network` changes the host to `0.0.0.0`.
- Both options work together and retain port `5002`.
- Unknown arguments produce standard usage output and exit status `2` without
  starting Flask.
- Application construction continues through `create_app()` and therefore uses
  the shared dotenv discovery behavior from ticket 1.
- The entry point does not invoke `uv`, the Flask CLI, or a platform shell as a
  subprocess.

Use the Python standard library argument parser already used by the generation
CLI. Do not add a CLI framework or production WSGI server.

Public interface: `imagegen.web.main(arguments)`.

Likely touchpoints: a focused `src/imagegen/web.py` module and
`tests/test_web.py`.

Verification: exercise the public callable with a fake Flask application, then
run `uv run pytest` and `uv run ruff check src tests`.

## 3. Package and document both installed commands

Expose the existing generation CLI and the new web launcher as package console
entry points, then remove the superseded platform scripts and update end-user
instructions.

Behavior to verify:

- Project metadata maps `imagegen` directly to `imagegen.cli:main`.
- Project metadata maps `imagegen-web` to `imagegen.web:main`.
- A built and installed project exposes both commands.
- README installation uses `uv tool install .` and explains any required PATH
  setup without requiring a source checkout for normal use.
- README web examples use `imagegen-web`, `imagegen-web --dev`,
  `imagegen-web --secure-network`, and the combined option form.
- README configuration documentation explains `.env` precedence,
  `~/.imagegen.env` fallback, and relative versus absolute
  `IMAGEGEN_DATA_DIR` resolution.
- `scripts/run-dev.sh` and `scripts/run-dev.cmd` are removed only after their
  supported behavior is available through `imagegen-web`.
- No `.local` data-directory convention or automatic migration of existing
  configuration and data is introduced.

Public interface: the installed `imagegen` and `imagegen-web` commands and the
documented configuration contract.

Likely touchpoints: `pyproject.toml`, `README.md`, `scripts/run-dev.sh`, and
`scripts/run-dev.cmd`.

Verification:

- `uv build`
- inspect the built wheel's console entry-point metadata
- `uv run pytest`
- `uv run ruff format src tests`
- `uv run ruff check --fix src tests`
- `uv run imagegen --help`
- `uv run imagegen-web --help`

Browser JavaScript is outside this epic; do not run or change the JavaScript
build unless implementation unexpectedly changes browser JavaScript scope, in
which case return to this ticket plan for approval first.
