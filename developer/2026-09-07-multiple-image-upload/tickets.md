# Multiple Image Upload Tickets

Source story: `developer/2026-09-07-multiple-image-upload/user-story.md`.

## Decisions Applied

- Reuse the existing single-file multipart upload API once per file instead of
  adding a batch API.
- Process files sequentially so the existing busy state prevents overlapping
  batches and status can identify the current file.
- Refresh the gallery once after the batch finishes when at least one upload
  succeeded.
- Continue after an individual file fails and report failed filenames in the
  final batch status.
- Keep URL and Immich import behavior unchanged.

## Ticket 1: Accept And Upload Multiple Local Images

### Goal

Let creators choose or drop multiple local images in one interaction and keep
every successful upload when another file in the same batch fails.

### Observable Behavior

- The native file chooser permits selecting multiple image files.
- The drop target accepts multiple dropped files.
- Upload panel labels and instructions describe multi-image selection and
  dropping.
- Each file is submitted to the existing `/api/images/import-upload` endpoint
  as the endpoint's single `image` multipart field.
- While the batch runs, the upload controls remain disabled and status shows
  progress through the batch.
- A failed file does not stop later files from uploading.
- After the batch finishes, the gallery refreshes once if at least one file
  succeeded.
- The final status distinguishes complete success, partial success, and complete
  failure; partial and complete failures identify the failed filenames.
- A single selected or dropped image follows the same batch path and retains
  existing behavior.
- An empty chooser selection or drop performs no upload and gives the existing
  empty-state guidance.

### Public Interface

- The `.upload-file-input` element exposes native multi-selection.
- `setupImageUpload(root, services)` keeps its existing signature and service
  dependencies.
- `/api/images/import-upload` keeps its existing request and response contract;
  no backend route change is required.

### Verification

- Add or update browser tests covering multi-file chooser selection, multi-file
  drop, progress, complete success, partial success, complete failure, empty
  input, single-file regression, one gallery refresh per successful batch, and
  controls returning to their enabled state.
- Add or update workspace render tests for the native multi-file attribute and
  plural upload labels.
- Manually verify native multi-selection and drag-and-drop behavior in a real
  browser.
- `npm run js:format`
- `npm run js:check`
- `uv run pytest`
- `uv run ruff check src tests`
