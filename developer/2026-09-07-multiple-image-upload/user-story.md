# Multiple Image Upload

## User Story

As a creator of images in edit mode, I want the Upload panel drop zone and
Choose Image selector to accept multiple image files at once so that I can add
a set of source images without repeating the upload flow for every file.

## Acceptance Criteria

- The Upload panel file selector allows the user to select one or more image
  files in a single chooser interaction.
- The Upload panel drop zone accepts one or more dropped image files in a
  single drop interaction.
- Every accepted file is validated and stored through the existing image import
  boundary.
- A batch containing multiple valid images uploads every image and refreshes the
  local gallery when the batch finishes.
- A batch containing invalid or unsupported files reports which files failed
  while retaining successfully uploaded images.
- Upload progress and the final status make clear whether the whole batch
  succeeded or only part of it succeeded.
- The controls remain unavailable while a batch is being uploaded, preventing a
  second batch from starting concurrently.
- Selecting or dropping a single image continues to work as it does today.
- Existing files are not overwritten, and browser-provided filenames and MIME
  types remain untrusted.

## Out of Scope

- Selecting uploaded images as edit sources automatically.
- Reordering files within an upload batch.
- Retrying failed files automatically.
- Changing URL or Immich imports to support batches.
