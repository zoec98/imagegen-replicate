# Testing

Maintain meaningful tests. Add tests with each behavior change unless the
change is documentation-only or purely mechanical.

Write tests in the style of GOOS / outside-in TDD. Start from observable
behavior, not implementation details. A good test should survive refactoring.

Prioritize tests for:

- Request payload construction per model.
- Server-side parameter validation.
- Palette loading and insertion behavior.
- Image-edit source handling.
- Provider wrapper behavior using fakes/mocks.
- Result download handling and metadata creation.
- Flask route success and error paths.

Tests must not call real image generation providers by default.

## Rules

- Start from observable behavior, not implementation details.
- Prefer tests through public APIs, CLI commands, HTTP endpoints, or
  domain-level interfaces.
- Do not test private methods directly.
- Do not assert exact internal call sequences unless the protocol is the
  behavior.
- Use mocks only at architectural boundaries: filesystem, network, database,
  clock, random, and external services.
- Avoid one-test-per-function.
- Prefer examples that describe user-visible or business-visible behavior.
- A good test should survive refactoring.
- If a test would break after renaming, extracting, or moving internal functions
  without changing behavior, rewrite it.
- Use red-green-refactor:
  1. Add one failing test for missing behavior.
  2. Implement the smallest change.
  3. Refactor only with tests green.
- Before writing tests, list the behaviors worth protecting in the test file
  comments.
- After writing tests, review them and delete tests that only pin
  implementation details.

After code changes, run:

```bash
uv run ruff format src tests
uv run ruff check src tests
uv run pytest
```
