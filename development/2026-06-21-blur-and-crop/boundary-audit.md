# Blur And Crop Boundary Audit

Implemented for ticket 1 in `development/2026-06-21-blur-and-crop/tickets.md`.

## Summary

Crop and blur should be added as local image-edit operations under the existing
JSON API route surface. The current project already has good boundaries for
browser-submitted image filenames, CSRF, gallery serialization, mask payload
size checks, metadata reads, and safe gallery listing. It does not yet have a
single reusable helper for writing a new locally edited image while preserving
the source image metadata exactly, so the backend tickets should add that small
module before or during the crop implementation.

## Source Image Filename Validation

Use `imagegen.source_images.validate_source_image_filename()` for crop and blur
source filenames.

- `src/imagegen/source_images.py` owns the local source image boundary for
  edit inputs.
- `validate_source_image_filename(filename, output_dir=...)` rejects non-string,
  blank, unsafe, unsupported-extension, and missing source filenames.
- It delegates filename safety to `imagegen.filenames.safe_image_filename()`.
- `safe_image_filename()` uses `werkzeug.utils.secure_filename()` and only
  accepts `.jpeg`, `.jpg`, `.png`, and `.webp`.
- Existing generation validation already uses this path through
  `validate_source_images()`.

Do not duplicate this logic in route handlers. Route handlers should catch
`SourceImageError` and return a JSON `400` for malformed/unsafe payloads or a
JSON `404` only if the implementation chooses to preserve the current image
route convention for missing files.

## Image Path Resolution

Use `imagegen.source_images.source_image_path()` after filename validation.

- The helper currently returns `output_dir / filename`.
- It is safe only after `validate_source_image_filename()` has accepted the
  filename.
- Crop and blur should keep all source and output files under
  `app_config.output_dir`.

If a future ticket needs stronger defense in depth, add a tiny helper that
combines validation and path return in `source_images.py` instead of resolving
paths ad hoc in routes.

## Output File Writing

Add a new local edit storage helper for crop and blur outputs.

Existing options are close but not exact:

- `imagegen.image_imports.store_imported_image()` validates uploaded/imported
  bytes and writes collision-safe `import-<uuid>` filenames with exclusive
  create. It preserves metadata only because it stores the original bytes
  unchanged.
- `imagegen.image_store.persist_generated_images()` downloads provider outputs
  and writes generation metadata, which is not correct for crop and blur.
- `imagegen.trash._collision_safe_path()` generates collision-safe names but is
  private to trash restore/move behavior.
- `imagegen.mask_store.save_mask_payload()` writes a deterministic
  `<source>-mask.png` and may overwrite an existing mask. That is correct for
  the current mask workflow, but not for crop and blur edited gallery outputs.

Recommended implementation:

- Add a focused module such as `src/imagegen/image_edits.py`.
- Generate server-owned names such as
  `<source-stem>-crop-<uuid><source-suffix>` and
  `<source-stem>-blur-<uuid><source-suffix>`.
- Use exclusive file creation or a collision loop so existing files are never
  overwritten.
- Keep the output format tied to the source format unless a later ticket
  explicitly decides otherwise.
- Return the new filename and path so the API route can use the existing
  gallery JSON shaping.

## Metadata Preservation

Preserve source embedded metadata exactly as application metadata, without
adding operation history.

Existing helpers:

- `imagegen.metadata_embed.read_embedded_metadata()` reads the app metadata
  payload from PNG text or JPEG/WebP EXIF.
- `imagegen.metadata_embed.write_embedded_metadata()` writes a normalized app
  metadata payload and synthetic human-readable fields.

Important implementation detail:

- For crop and blur, simply saving a Pillow-derived image copy will not
  automatically satisfy the user decision for embedded app metadata.
- The edit helper should read the source metadata with
  `read_embedded_metadata(source_path)`.
- If metadata exists, write the exact same dictionary to the edited output with
  `write_embedded_metadata(output_path, metadata)`.
- If metadata is absent, do not call `write_embedded_metadata()` and do not add
  operation metadata.

This preserves the application-level embedded metadata contract exactly. Binary
metadata chunk identity is not guaranteed by the existing writer and is not the
project's current metadata abstraction.

## Mask Payload Boundary

Reuse the existing mask payload decoding and sizing rules for blur where
practical, but do not couple blur to mask file storage.

Existing behavior:

- `imagegen.mask_store.save_mask_payload()` validates request size, decodes
  base64 PNG payloads, verifies PNG format, checks source-size match, converts
  to grayscale, and writes a provider-ready mask file.
- The lower-level decode helpers are currently private.

Recommended implementation:

- Extract a public helper from `mask_store.py`, for example
  `decode_mask_payload(payload, source_size=..., content_length=...)`, returning
  a grayscale `PIL.Image.Image`.
- Keep `save_mask_payload()` as the existing mask-mode storage wrapper.
- Use the new decode helper from blur so blur can validate the same payload
  shape without writing `<source>-mask.png`.
- Add blur-specific validation that the mask has non-empty marked content.

## CSRF Boundary

Use `imagegen.security.require_api_csrf` for both new endpoints.

Existing mutating JSON endpoints in `src/imagegen/api_routes.py` use
`@require_api_csrf`, including:

- `POST /api/generate`
- palette create/update/delete routes
- trash restore/empty routes
- image delete route
- `POST /api/images/<filename>/mask`

Crop and blur should follow the mask endpoint pattern:

- `POST /api/images/<path:filename>/crop`
- `POST /api/images/<path:filename>/blur`
- both decorated with `@require_api_csrf`
- both JSON-only

## Gallery Integration

Reuse existing gallery listing and response shaping.

Existing helpers:

- `imagegen.gallery.list_gallery_images()` lists files under
  `app_config.output_dir` by supported extension and newest mtime first.
- `api_routes._gallery_image_by_filename()` finds the newly written image in
  the normal gallery list.
- `api_routes._gallery_image_json()` shapes the browser-facing image payload.

Recommended route response for crop and blur:

```json
{
  "image": {
    "...": "same shape as /api/images entries"
  }
}
```

Use status `201` for successful edited image creation, matching import
endpoints.

## Tests To Add In Later Tickets

Backend crop tests should cover:

- valid crop writes a new unique image
- original image remains unchanged
- unsafe, missing, malformed, out-of-bounds, negative, empty, and too-small
  rectangles fail
- unsafe source filenames fail
- metadata exists: exact application metadata dictionary is preserved
- metadata absent: output has no added application metadata

Backend blur tests should cover:

- valid blur writes a new unique image and only marked pixels are affected
- original image remains unchanged
- unsafe source filenames fail
- radius validation accepts floats from 0 to 20 and rejects outside range
- malformed, missing, wrong-sized, and empty masks fail
- brush size is not accepted as a server operation parameter
- metadata exists: exact application metadata dictionary is preserved
- metadata absent: output has no added application metadata

Route tests should follow existing `tests/test_image_routes.py` style and use
`route_helpers.extract_csrf_token()` for CSRF-protected requests.

## Implementation Decisions For Next Tickets

- Add `src/imagegen/image_edits.py` for crop/blur operations, validation
  errors, collision-safe edited filenames, and metadata-preserving output
  writes.
- Add `tests/test_image_edits.py` for operation-level crop/blur behavior.
- Extend `tests/test_image_routes.py` for route-level CSRF, validation, JSON
  response, and gallery integration behavior.
- Refactor `mask_store.py` just enough to expose reusable mask decoding for
  blur; keep the existing mask save endpoint behavior unchanged.
