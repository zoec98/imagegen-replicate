# Test Audit - 2026-06-05

Scope: current tests under `tests/`, with emphasis on whether they are
outside-in, behavior-oriented, and likely to survive refactoring in the spirit
of GOOS.

## Summary

The suite is generally strong. It has broad route-level and domain-boundary
coverage, uses fakes at external boundaries, avoids real provider calls, and
protects many user-visible behaviors. The biggest weakness is not lack of
tests; it is over-specific assertions in some server-rendered HTML tests and
large route test files that mix several workflows.

The tests mostly support refactoring, but some would fail on harmless markup or
presentation reshaping. Those tests should be softened before major UI
refactors.

## GOOS / Outside-In Assessment

### Strong examples

- `tests/test_generation_api.py` exercises the JSON API boundary and accepted
  request records rather than private route helpers.
- `tests/test_image_routes.py` covers real HTTP behavior for image view,
  metadata, delete-to-trash, trash restore/empty, and mask save edge cases.
- `tests/test_palette_api.py` and `tests/test_palettes.py` separate route
  behavior from palette repository behavior.
- `tests/test_replicate_client.py` and `tests/test_falai_client.py` use fake
  provider boundaries and fake persistence instead of real network calls.
- `tests/test_image_store.py` uses `httpx.MockTransport`, which is an
  appropriate architectural boundary fake.
- `tests/test_worker.py` checks worker/provider/log/store behavior with fakes
  at the provider boundary.

These tests should mostly survive internal moves, renames, and extractions
because they assert observable behavior or boundary protocols.

### Brittle examples

- `tests/test_workspace_routes.py` asserts many exact HTML byte substrings,
  class names, option snippets, and ordering through `response.data.index`.
  This catches useful regressions, but it can also break during harmless markup
  restructuring.
- `tests/test_image_routes.py` asserts full JSON payloads in several places.
  This is useful for public API shape, but overly exact when only one field is
  relevant to the behavior under test.
- `tests/test_generation_api.py` asserts exact error strings heavily. Error
  strings are user-visible, so this is often justified, but it can make
  validation refactors noisy.
- `tests/test_model_registry.py` pins exact registry behavior and some data
  shape. That is appropriate for registry contracts, but it may make provider
  storage remodeling harder unless tests stay focused on public registry
  functions.

## File-Level Notes

### `tests/test_workspace_routes.py`

Strengths:

- Tests server-rendered workspace behavior as a user-facing page.
- Covers provider options, model registry JSON, palette data, trash shell,
  Immich action rendering, static asset cache busting, and configured start
  model.

Risks:

- Many tests assert exact snippets of generated HTML. This is not fully
  GOOS-like because changing markup structure without changing behavior can
  break tests.
- Ordering checks with `response.data.index` are appropriate for the trash vs
  palette button bug, but should remain rare and tied to real UX behavior.

Suggested improvement:

- Introduce a small HTML parser helper using the standard library
  `html.parser` or a dependency already available in the project, then assert
  on elements, attributes, and text semantically.
- Keep exact substring checks only for intentional public hooks such as
  `data-api-*`, script IDs, and form control names.

### `tests/test_image_routes.py`

Strengths:

- Strong outside-in coverage of HTTP routes.
- Good coverage of security-sensitive filename handling, CSRF, trash behavior,
  and mask upload bounds.

Risks:

- The file is large and spans several workflows: image serving, clean download,
  metadata, gallery API, trash API, delete, and mask save.
- Full `response.json == {...}` assertions can be brittle when an endpoint adds
  unrelated fields.

Suggested improvement:

- Split by behavior surface when refactoring:
  - `test_image_file_routes.py`
  - `test_gallery_api.py`
  - `test_trash_api.py`
  - `test_mask_api.py`
- For large JSON responses, assert required fields and selected invariants
  unless the entire response is intentionally the public contract.

### `tests/test_generation_api.py`

Strengths:

- Good API-level tests for generation request creation, provider/model
  selection, validation, edit mode, source images, and request logging.
- Tests are mostly outside-in and should survive provider-wrapper refactors.

Risks:

- It is large and mixes provider selection, validation, request store, worker,
  and log assertions.
- Some tests inspect request log internals. That can be acceptable because
  durable request logging is business behavior, but future log schema changes
  may create noisy failures.

Suggested improvement:

- Keep API submission examples at the route boundary.
- Move detailed validation matrix expectations to `tests/test_validation.py`
  when they do not need HTTP.
- Keep only log assertions that describe durable reproducibility behavior.

### Provider client tests

Files:

- `tests/test_replicate_client.py`
- `tests/test_falai_client.py`
- `tests/test_immich_client.py`

Strengths:

- Fakes and mock transports are used at external-service boundaries.
- Tests assert provider payloads, upload behavior, output normalization,
  timeout/failure handling, and persistence metadata.

Risks:

- Some payload tests assert exact provider input dictionaries. This is correct
  when provider request shape is the behavior, but should not expand into
  private call-sequence assertions.

Suggested improvement:

- Keep these as contract tests for provider payload shape.
- Avoid asserting every intermediate call unless the provider protocol requires
  it.

### Domain tests

Files:

- `tests/test_gallery.py`
- `tests/test_palettes.py`
- `tests/test_prompt_annotations.py`
- `tests/test_validation.py`
- `tests/test_metadata.py`
- `tests/test_metadata_embed.py`
- `tests/test_image_store.py`
- `tests/test_generation_log.py`

Strengths:

- These are mostly behavior-level tests through public module APIs.
- They cover useful domain rules and edge cases.
- They are likely to survive internal implementation changes.

Risks:

- `tests/test_validation.py` has many examples and may become a broad matrix.
  This is acceptable while validation remains a public boundary.
- `tests/test_generation_log.py` may be more schema-sensitive than pure
  behavior tests, but SQLite persistence schema is a real contract for durable
  history.

Suggested improvement:

- Keep comments at the top of each file describing protected behaviors.
- When adding validation cases, prefer representative examples over exhaustive
  one-test-per-branch coverage.

## Test Smells Found

- Heavy exact HTML matching in workspace tests.
- Very large route test files that make workflow boundaries harder to see.
- Some exact JSON equality where only a subset of the response matters.
- Some exact error-string assertions. These are acceptable for user-facing API
  messages, but should be intentional.

## Recommended Test Refactoring Tickets

1. Add semantic HTML extraction helpers for route tests.
2. Soften workspace rendering assertions to semantic element/attribute checks.
3. Split `tests/test_image_routes.py` by route surface.
4. Split `tests/test_generation_api.py` into API submission, provider
   selection, edit/source handling, and generation status sections or files.
5. Review exact JSON equality assertions and convert to selected-field
   assertions where the full response is not the behavior.

## Open Questions

- Do we want a small browser/DOM test tool for JavaScript behavior, or should
  frontend behavior remain manually validated by the user?
- Should route tests use an HTML parser helper without adding dependencies, or
  is adding a test-only parser dependency acceptable?
- Which JSON responses are considered stable public contracts where exact
  equality is desired?
