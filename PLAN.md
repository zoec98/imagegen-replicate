# Palette Prompt Fragments Implementation Plan

This plan turns `SCENARIO.md` into implementation tickets for a file-backed
palette system. The first implementation should use plain textarea annotations;
rich inline formatting is explicitly deferred and will not be implemented in
this sprint.

The prompt lifecycle is:

- Browser annotation handling owns cursor-aware insert, replace, and prompt
  editing behavior.
- The server accepts either a plain prompt or a valid non-nested annotated
  prompt, and rejects invalid annotation syntax on generation.
- The application stores and displays the annotated prompt everywhere it keeps
  user-authored prompt data, including request state, SQLite history, and
  embedded image metadata.
- Immediately before creating the provider request, the server unwraps
  annotations so only fragment content and plain prompt text are sent to the
  model provider.

## Implementation Order

1. Add palette filesystem repository and validation.
2. Add server prompt annotation validation and provider-prompt stripping.
3. Expose palette data to the browser.
4. Add palette selection UI and prompt insertion/replacement.
5. Wire stripped provider prompts into generation while preserving annotated
   prompts in logs and metadata.
6. Add hidden palette CRUD editor.
7. Update documentation and guardrails.

## Ticket 1: Palette Filesystem Repository

### Scope

- Add a palette repository boundary, for example `src/imagegen/palettes.py`.
- Add `IMAGEGEN_FRAGMENT_ROOT` to application config, `.env` generation, and
  `env.example`, defaulting to `data/fragments`.
- Store fragments as plain text files under the configured fragment root:
  - `data/fragments/<palette>/<fragment>.txt`
- Treat every directory under the configured fragment root as one palette.
- Use singular palette names, such as `character` and `style`.
- Treat every `.txt` file under a palette directory as a fragment entry.
- Ignore non-`.txt` files.
- Treat a missing configured fragment root as an empty palette set.
- Sort palette names and fragment entries alphabetically for display.
- Normalize UI-entered spaces in fragment names to underscores for storage.
- Display stored underscores as spaces in the UI.
- Validate palette and fragment names:
  - allowed characters: `A-Z`, `a-z`, `0-9`, `_`, `-`;
  - names must start with a letter.
- Validate fragment content:
  - maximum size: 256 bytes;
  - content may not contain `(`, `)`, or `:`.

### Acceptance Criteria

- The repository lists palettes and fragments from the configured fragment root.
- Missing fragment root returns an empty list without error.
- Palette and fragment names are returned in stable alphabetical order.
- Fragment display names replace underscores with spaces.
- Invalid names are rejected before filesystem access.
- Invalid fragment content is rejected or excluded with clear error reporting.
- Repository APIs never expose or access files outside the configured fragment
  root.

### Suggested Tests

- List palettes from a temporary fragment tree.
- Verify sorting of palette names and fragment names.
- Verify non-`.txt` files are ignored.
- Verify missing fragment root returns no palettes.
- Verify names with path traversal, leading digits, spaces after normalization
  failure, or unsupported characters are rejected.
- Verify valid UI names with spaces normalize to underscores.
- Verify oversized content is rejected.
- Verify content containing `(`, `)`, or `:` is rejected.
- Verify `IMAGEGEN_FRAGMENT_ROOT` defaults to `data/fragments` and supports
  relative paths resolved from the `.env` file location.

## Ticket 2: Server Prompt Annotation Validation And Stripping

### Scope

- Add a server prompt annotation boundary, for example
  `src/imagegen/prompt_annotations.py`.
- Support annotation shape:

```text
(character: zoe <fragment content>)
```

- Parse annotations into:
  - start offset;
  - end offset;
  - palette name;
  - fragment name;
  - fragment content.
- Validate that submitted prompts are either plain text or valid non-nested
  annotated text.
- Reject malformed annotations on `/api/generate` before creating request state,
  SQLite rows, or worker jobs.
- Reject nested annotations.
- Strip annotation delimiters and metadata to produce provider-ready prompt
  text.
- Keep stripping server-side so the browser is never trusted to produce the
  provider prompt.
- Cursor-aware insert and replace behavior is intentionally not part of the
  server boundary; Ticket 4 implements that in browser code.

### Acceptance Criteria

- Server validation accepts plain prompts.
- Server validation accepts valid non-nested annotated prompts.
- Server validation rejects malformed or nested annotations.
- Provider prompt stripping removes annotation syntax and keeps fragment content.
- Malformed annotations produce clear validation errors and do not enter request
  state, SQLite history, or worker execution.

### Suggested Tests

- Parse one annotation.
- Parse multiple annotations.
- Strip one annotation into provider text.
- Strip multiple annotations into provider text.
- Accept plain prompts.
- Reject unterminated annotations.
- Reject nested annotations.
- Verify malformed annotations are rejected by `/api/generate` before request
  creation.

## Ticket 3: Palette Data API And Template Exposure

### Scope

- Expose available palettes and fragments to the browser.
- Include:
  - palette name;
  - palette display name;
  - fragment name;
  - fragment display name;
  - fragment content.
- Use the repository from Ticket 1.
- Initial exposure can be embedded in the rendered page as JSON, or served from
  a JSON API route if that better matches the existing UI structure.
- Do not expose invalid fragments as usable controls.
- Do not expose files outside the configured fragment root.
- External file changes are picked up on page refresh only.
- Do not implement live reload or stale-menu detection.

### Acceptance Criteria

- The rendered page or palette API contains all valid palettes and fragments.
- Palette data is sorted and display-normalized.
- Invalid fragments do not produce usable controls.
- With no fragment root, the UI receives an empty palette list.
- Existing generation UI still renders when no palettes exist.

### Suggested Tests

- Template or API test verifies palette JSON shape.
- Test verifies empty palette state.
- Test verifies display names convert underscores to spaces.
- Test verifies invalid fragment files are excluded or reported consistently.

## Ticket 4: Palette Selection UI

### Scope

- Render palette controls near the prompt editor.
- Use plain textarea annotations for the first implementation.
- Implement cursor-aware annotation handling in the browser.
- Each palette control lists fragments alphabetically.
- Selecting a fragment:
  - inserts `(palette: fragment <content>)` at the cursor when outside any
    annotation;
  - replaces the full current annotation when inside an annotation of the same
    palette type;
  - rejects the action with a clear error message when inside a different
    palette type.
- Keep prompt text selected/cursor behavior predictable after insert or replace.
- Optionally disable the generate button when the current prompt is neither
  plain text nor valid annotated text. This is a convenience only; server
  validation remains authoritative.
- Optionally disable or lock unavailable palette controls while the cursor is
  inside another annotation type.

### Acceptance Criteria

- Palette controls render when palettes exist.
- No palette controls render, or an unobtrusive empty state renders, when no
  palettes exist.
- Selecting a fragment outside any annotation inserts at the cursor.
- Selecting a same-type fragment inside an annotation replaces the full block.
- Selecting a different-type fragment inside an annotation shows an error and
  leaves the prompt unchanged.
- Fragment annotations use singular palette names.
- Prompt text remains editable as normal textarea text.
- Browser prompt validation, if present, matches the non-nested annotation rules
  enforced by the server.

### Suggested Tests

- Browser/manual test for insertion at cursor.
- Browser/manual test for same-type replacement.
- Browser/manual test for different-type rejection.
- Browser/manual test for alphabetical ordering.
- Browser/manual test for optional generate-button disabling on invalid
  annotations, if implemented.
- JavaScript unit-style tests if the project adds a JS test harness.

## Ticket 5: Provider Prompt Stripping In Generation Flow

### Scope

- Keep annotated prompt text as the browser-submitted prompt.
- Strip annotations server-side immediately before calling model providers.
- Do not require or trust the browser to strip annotations.
- Validate annotation syntax before accepting the generation request, as defined
  in Ticket 2.
- Preserve annotated prompts in:
  - request status responses;
  - SQLite generation logs;
  - embedded image metadata.
- Use stripped provider prompts only for the actual Replicate request.
- Continue passing the annotated prompt into image metadata embedding even when
  the Replicate request uses the stripped provider prompt.
- Do not store the provider-stripped prompt separately in SQLite for this
  scenario.
- Ensure request recreation data remains understandable:
  - annotated prompt is the user-authored source;
  - `request_sent_json` or equivalent contains the provider-ready prompt sent to
    Replicate.

### Acceptance Criteria

- Annotated prompts can be submitted to `/api/generate`.
- Replicate receives the prompt with annotation syntax removed.
- Request store/status still shows the annotated prompt.
- SQLite stores the annotated prompt in the user/request field.
- The final request JSON sent to Replicate contains the stripped prompt.
- Embedded image metadata stores the annotated prompt.
- The image metadata path never receives the stripped provider prompt as the
  stored user prompt.
- Plain prompts without annotations are unchanged.

### Suggested Tests

- API route test submits annotated prompt and verifies stored request prompt and
  SQLite user prompt remain annotated.
- API route or generation-log test verifies `request_sent_json` contains the
  stripped provider prompt.
- Worker/image metadata test verifies embedded metadata stores annotated prompt
  while the Replicate request receives the stripped prompt.
- Validation/parser test verifies plain prompts pass unchanged.

## Ticket 6: Palette CRUD Editor

### Scope

- Add a hidden-by-default single-page palette editor in the UI.
- The editor supports entries inside existing palette directories only.
- Do not support creating or deleting whole palettes in the UI.
- Use CSRF-protected API routes for writes.
- Read routes may be non-mutating same-origin JSON routes, but must still
  validate names before filesystem access and must not expose files outside the
  configured fragment root.
- CRUD operations:
  - create fragment entry;
  - read fragment entry;
  - update fragment entry;
  - delete fragment entry.
- Persist entries to the same configured filesystem layout:
  - `data/fragments/<palette>/<fragment>.txt`
- Validate names and fragment content using the same repository rules as
  Ticket 1.
- Refresh palette controls after successful UI edits.
- External filesystem edits require page refresh; no live reload is needed.

### Acceptance Criteria

- The editor is accessible from the GUI but hidden by default.
- Existing entries can be read and edited.
- New entries can be created in existing palettes.
- Entries can be deleted.
- Creating/deleting palettes is not available in the UI.
- Invalid names and invalid content return clear errors.
- Conflicting names and missing entries return clear errors.
- All write routes require CSRF.
- Read routes validate palette and fragment names before file access.
- Palette controls update after successful editor changes.

### Suggested Tests

- API route test creates a fragment.
- API route test updates a fragment.
- API route test deletes a fragment.
- API route test rejects missing palette directories.
- API route test rejects path traversal and invalid names.
- API route test rejects invalid content and oversized content.
- API route test verifies CSRF protection.
- API route test verifies read routes reject path traversal and invalid names.
- Browser/manual test verifies editor visibility and control refresh.

## Ticket 7: Documentation And Guardrails

### Scope

- Document palette storage under `data/fragments/`.
- Document `IMAGEGEN_FRAGMENT_ROOT` and its default value.
- Document singular palette directory naming.
- Document filename/display-name normalization.
- Document fragment content restrictions:
  - max 256 bytes;
  - no `(`, `)`, or `:`.
- Document annotation syntax and provider prompt stripping.
- Document that annotated prompts are stored in logs and embedded metadata.
- Document that external file edits require a page refresh.
- Add developer notes for where palette repository, annotation parser, and
  generation-flow stripping live.

### Acceptance Criteria

- README or equivalent docs explain how to create palettes manually.
- Docs include a sample `data/fragments/` tree.
- Docs explain what is sent to the model provider versus what is stored locally.
- Docs explain why whole-palette creation/deletion is filesystem-only.

### Suggested Tests

- Documentation-only ticket; no automated tests required unless docs tooling is
  added.

## Deferred / Out Of Scope

- Rich inline formatting inside the prompt editor. This is fully deferred to a
  later optional phase after the plain textarea annotation system is stable.
- Live reload for external palette file changes.
- Creating or deleting palette directories from the UI.
- Storing provider-stripped prompts as separate SQLite fields.
