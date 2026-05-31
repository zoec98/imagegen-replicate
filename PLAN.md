# Gallery Trash And Data Directory Plan

This plan captures the next implementation tickets for gallery deletion safety
and data directory configuration. It supersedes direct-delete gallery behavior
with a trash workflow and consolidates configurable storage under one data root.

## Implementation Order

1. Add configurable data root and derived storage paths.
2. Rename committed example data to `data-example`.
3. Add server-side trash storage and move-on-delete behavior.
4. Add browser-side two-step gallery delete confirmation.
5. Adjust gallery action layout and destructive-action styling.
6. Update documentation, examples, and guardrails.

## Ticket 1: Data Root Configuration

### Scope

- Replace these environment variables:
  - `IMAGEGEN_OUTPUT_DIR=data/images`
  - `IMAGEGEN_DB_PATH=data/imagegen.sqlite3`
  - `IMAGEGEN_FRAGMENT_ROOT=data/fragments`
- Add one environment variable:
  - `IMAGEGEN_DATA_DIR=data`
- Derive fixed application paths from `IMAGEGEN_DATA_DIR`:
  - generated images: `<data_dir>/images`
  - SQLite database: `<data_dir>/imagegen.sqlite3`
  - palette fragments: `<data_dir>/fragments`
  - gallery trash: `<data_dir>/trash` (see Ticket 3)
- Resolve relative `IMAGEGEN_DATA_DIR` values from the `.env` file location,
  matching the current relative-path behavior.
- Update `AppConfig` so callers continue to use typed paths, but those paths are
  derived from `data_dir`.
- Ensure these paths exist on startup/app initialization.
- Update `.env` generation and `env.example`.
- Decide migration behavior for old `.env` files:
  - fail clearly with documentation if old names are present.

### Acceptance Criteria

- New `.env` files contain `IMAGEGEN_DATA_DIR=data` and no longer contain the
  three old path variables.
- `load_config()` resolves `output_dir`, `generation_log_path`,
  `fragment_root`, and `trash_dir` from `data_dir`.
- Relative and absolute `IMAGEGEN_DATA_DIR` values both work.
- Tests cover default path derivation and custom data directory derivation.
- Any old-name compatibility or rejection behavior is explicit and tested.

### Suggested Tests

- `ensure_env_file()` writes `IMAGEGEN_DATA_DIR=data`.
- `write_env_example()` writes `IMAGEGEN_DATA_DIR=data`.
- `load_config()` with `IMAGEGEN_DATA_DIR=custom-data` derives all fixed paths.
- Existing direct construction of `AppConfig` in tests includes `trash_dir`.

## Ticket 2: Move Example Data To `data-example`

### Scope

- Rename the committed example payload tree from `data/` to `data-example/`.
- Move current committed palette fragments and example payloads with it.
- Keep `.gitignore` ignoring `data/`, because `data/` is the expected local
  production/runtime directory.
- Ensure `data-example/` is committed and not ignored.
- Update docs to explain:
  - `data-example/` is sample/reference data;
  - `data/` is local production/runtime data;
  - users should configure `IMAGEGEN_DATA_DIR=data` or another private path for
    real use.
  - This is also the default when `.env` is being generated.

### Acceptance Criteria

- The repository no longer tracks runtime/example files under `data/`.
- The current committed example payloads are available under `data-example/`.
- `.gitignore` continues to ignore `data/`.
- `data-example/` remains visible to git.
- Documentation tells users how to copy or reference example fragments if they
  want to start from the sample data.

### Suggested Tests

- No code test required unless path fixtures depend on committed example data.
- Use `git status --short --ignored` or equivalent manual verification to
  confirm `data/` is ignored and `data-example/` is trackable.

## Ticket 3: Server-Side Trash Directory

### Scope

- Add `trash_dir` to `AppConfig`, derived from `IMAGEGEN_DATA_DIR`.
- Create a gallery trash helper or keep the implementation in the existing
  image/gallery boundary, but do not perform direct unlink from API routes.
- Change `POST /api/images/<filename>/delete` so it moves the file from
  `<data_dir>/images` to `<data_dir>/trash`.
- Preserve gallery deletion safety:
  - validate filenames with the existing safe filename checks;
  - only move files from the configured output directory;
  - never move arbitrary paths;
  - keep CSRF protection.
- Generate collision-resistant trash filenames if the same filename already
  exists in trash.
- Trash directory should be created on demand.
- The API response should still indicate which gallery filename was removed.

### Acceptance Criteria

- Gallery delete no longer unlinks the image file.
- Deleted gallery images disappear from `data/images`.
- Deleted files appear under `data/trash` or the configured equivalent.
- Duplicate trash names do not overwrite existing trash files.
- Unsafe filenames remain rejected.
- Missing image files still return a clear not-found response.

### Suggested Tests

- API delete moves a valid image into trash.
- API delete creates the trash directory if missing.
- API delete handles trash filename collisions without overwriting.
- API delete rejects unsafe paths and GIFs as before.
- API delete still requires CSRF.

## Ticket 4: Two-Step Browser Delete Confirmation

### Scope

- Add browser-side protection for gallery delete buttons:
  - first click arms the trash button and makes it larger;
  - second click while armed performs the delete request.
- Only one trash button should be armed at a time.
- Disarm the current trash button when:
  - another trash button is clicked;
  - a non-delete gallery action is clicked;
  - gallery refreshes;
  - delete succeeds or fails.
- The enlarged state should be visually obvious but should not shift the gallery
  layout.
- Keep server-side CSRF and filename validation authoritative; browser
  confirmation is only a UX protection.

### Acceptance Criteria

- First click on a trash icon does not call the delete API.
- First click enlarges/arms the icon.
- Second click on the same armed icon calls the delete API.
- Clicking another delete icon transfers the armed state.
- Gallery refresh clears armed state.
- Keyboard/focus behavior remains usable.

### Suggested Tests

- Manual/browser test for first-click arm and second-click delete.
- Manual/browser test for switching armed buttons.
- Optional JS unit-style test if a JS test harness is added.

## Ticket 5: Gallery Action Layout And Destructive Spacing

### Scope

- In gallery cards, keep non-destructive actions grouped on the left.
- Move the trash button to the far right of the action row.
- Add spacing between the trash action and non-destructive actions.
- Keep the layout responsive in narrow gallery cards.
- Preserve accessible labels and current icon-only button behavior.

### Acceptance Criteria

- Trash icon is right-aligned in each gallery action row.
- Trash icon is visually separated from info, file type, Immich, and load
  actions.
- The action row does not overlap or wrap awkwardly on mobile card widths.
- Enlarged armed trash state remains within the card action area.

### Suggested Tests

- Manual/browser visual check at mobile, tablet, and desktop widths.
- Existing route/render tests continue to verify gallery action markup.

## Ticket 6: Documentation And Guardrails

### Scope

- Update README:
  - `IMAGEGEN_DATA_DIR`;
  - derived directories;
  - `data-example/` purpose;
  - `data/` as ignored local runtime data;
  - trash behavior instead of direct delete.
- Update AGENTS:
  - no direct gallery unlink from routes;
  - use the configured trash directory for delete actions;
  - do not commit production `data/`;
  - keep `data-example/` limited to intentional sample payloads.
- Update `env.example`.
- Update any references to old path variables.

### Acceptance Criteria

- Docs do not instruct users to configure the old individual path variables.
- Docs explain how gallery delete moves files to trash.
- Contributor guardrails mention trash move semantics and `data-example/`.

### Suggested Tests

- Documentation-only ticket; no automated tests required unless docs tooling is
  added.
