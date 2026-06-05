# Generated Images

Generated files are local, metadata-rich assets controlled by the app.

## Provider Outputs

Treat provider outputs as untrusted remote URLs or file-like values.

Download results through a single helper that applies:

- timeouts
- size limits where practical
- content-type checks
- collision-resistant filenames

Supported generated output/source image formats are PNG, JPEG, and WebP. GIF is
unsupported.

## Storage

Store downloaded files under the configured output directory derived from
`IMAGEGEN_DATA_DIR`.

Preserve useful metadata:

- provider
- model name/model alias
- prompt
- parameters
- source URL
- source image filenames
- creation time

Read generated-image author metadata from `AUTHOR`; synthesize copyright from
`AUTHOR` and the generated image creation year.

Treat the stored generated file as the canonical metadata-rich image.

## Embedded Metadata

Store generated image metadata in embedded image metadata, not JSON sidecars.

- PNG uses an application text chunk.
- JPEG and WebP use EXIF fields.

Store a human-readable generated-image description for external tools, and
parseable application metadata separately in the embedded payload.

Write and strip image metadata with Python helpers, not by shelling out to
`exiftool` or other metadata tools.

## Download Modes

Keep open/view, normal download, and clean download behavior distinct:

- Open/view serves the stored file for browser display.
- Normal download serves the stored metadata-rich file with attachment headers.
- Clean download serves a temporary metadata-stripped copy without mutating the
  stored file.

Store clean export files under the configured temporary directory, not in the
gallery output directory, and do not expose them as gallery assets.

## History

Store durable generation request/result history in SQLite under the configured
data directory, `data/` by default.

Keep route and gallery code behind provider/repository boundaries. Do not read
embedded metadata or SQLite tables directly from templates or
JavaScript-facing route code.

Store source image references as local filenames, not image bytes or database
blobs.
