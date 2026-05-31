# User Stories

## Story 1: Choose An Image Generation Provider

As a user, I want to choose whether an image generation request is sent through
Replicate or fal.ai, so that I can use the provider that has the model,
performance, pricing, or availability I need.

### Acceptance Notes

- The UI exposes provider selection clearly before generation.
- The image generation provider is the first choice a user has to make, so it should be in the top left corner, left of the model selector, which changes depending on the provider chosen.
- The selected provider is part of the accepted generation request.
- The server validates that the selected provider is supported.
- Choosing (or changing) the provider also changes the model selection options.
- The selected provider is stored in request history and embedded application
  metadata.
- Tests must not call real Replicate or fal.ai APIs by default.
- It is okay for API keys to be absent in the .env file. Model providers without API key are not offered, instead a clear error message is shown.

### Examples

- I choose `replicate` and model choices are drawn from the Replicate registry.
- I choose `fal` and model choices are drawn from the fal.ai registry.
- If I submit an unsupported provider value, the server rejects the request
  before queuing work.

## Story 2: Use Provider-Specific Model Registries

As a user, I want model options to match the provider I selected, so that I do
not accidentally submit Replicate-shaped settings to fal.ai or fal.ai-shaped
settings to Replicate.

### Acceptance Notes

- Model registry data is provider-aware.
- A model that exists on both providers may have different provider keys,
  versions, input names, defaults, limits, output shapes, and capabilities.
- The application may use separate registries per provider or one registry
  filtered by provider, but the public behavior must keep provider-specific
  metadata distinct.
- Server-side parameter validation uses the selected provider's model metadata.
- Request construction uses the selected provider's API shape.
- Gallery metadata and request history preserve both provider and provider
  model identity.

### Examples

- A model shown as `Seedream 4.5` on two providers may map to different
  provider model identifiers.
- A provider may expose `width` and `height` while another exposes `size`.
- A provider may support image edit for a model while another provider exposes
  only text-to-image.

## Story 3: Use Provider-Specific Schema Helper Scripts

As a maintainer, I want provider-specific schema helper scripts, so that adding
or updating model registry entries uses the correct provider schema source.

### Acceptance Notes

- The existing `scripts/get_schema` helper is renamed to
  `scripts/get_schema_replicate`.
- A new `scripts/get_schema_falai` helper fetches or prints useful schema
  information for fal.ai models.
- Documentation and contributor guidance reference the provider-specific script
  names.
- The old generic script name is removed or replaced with a clear compatibility
  message, so maintainers do not accidentally fetch a Replicate schema while
  working on fal.ai metadata.
- Script behavior is testable without calling external provider APIs in normal
  unit tests.
- Provider-specific tooling records how pricing was sourced:
  - fal.ai pricing should be fetched from the fal.ai Platform API when
    available;
  - Replicate pricing remains static registry metadata unless Replicate exposes
    a stable pricing API for the needed model or hardware data;
  - unknown or unavailable pricing is represented explicitly instead of guessed.
- Registry entries distinguish provider API pricing, static pricing, and unknown
  pricing.

### Examples

- I run `scripts/get_schema_replicate bytedance/seedream-4.5` to inspect the
  Replicate schema source for a Replicate registry entry.
- I run `scripts/get_schema_falai fal-ai/example-model` to inspect the fal.ai
  schema source for a fal.ai registry entry.
- `scripts/get_schema_falai fal-ai/flux/dev` can include pricing fetched from
  `https://api.fal.ai/v1/models/pricing?endpoint_id=fal-ai/flux/dev`.
- A Replicate registry entry can keep static pricing metadata with source
  `static`, because Replicate does not currently provide an equivalent
  documented per-model pricing API.

## Story 4: Download A Clean Gallery Image

As a user, I want to download a gallery image with metadata removed, so that I
can publish or share an image without embedded prompt, request, author, or
application metadata.

### Acceptance Notes

- The gallery offers a clean download action.
- The clean download does not mutate the stored gallery image.
- The downloaded copy has application metadata and EXIF metadata removed where
  supported by the image format.
- The clean download path is implemented in Python, not by shelling out to
  `exiftool`.
- Unsupported image formats remain unsupported rather than being converted
  silently.

### Examples

- I download `sample.jpg` clean and the resulting file contains no prompt EXIF,
  no author EXIF, and no application metadata payload.
- The original `data/images/sample.jpg` still contains the app's embedded
  metadata for gallery reload and audit purposes.

## Story 5: Store Gallery Images With Synthetic Metadata

As a user, I want generated gallery images stored with useful synthetic metadata,
so that the image files on disk already contain prompt, display, authorship,
copyright, and generation date information.

### Acceptance Notes

- The stored gallery image is the canonical metadata-rich image.
- Existing embedded prompt and user-display metadata remain in the stored image.
- The app adds the missing author and copyright metadata from `.env`.
- Metadata writing is implemented in Python, not by shelling out to `exiftool`.
- The stored synthetic metadata includes:
  - author information configured from `.env`;
  - copyright information configured or derived from `.env`;
  - generation timestamp from the stored generation metadata;
  - prompt text from the stored generation metadata;
  - application/software identity for this app.
- The synthetic metadata does not need to fake full camera metadata such as
  make, model, aperture, focal length, ISO, or exposure settings.
- If required author/copyright configuration is missing, the UI or server gives
  a clear error instead of emitting misleading metadata.
- The application metadata needed for gallery reload remains preserved in the
  same stored gallery image.

### Examples

- With `.env` author `Zoé Cordelier`, a generated timestamp in 2026, and prompt
  `portrait in soft light`, the stored gallery image contains author
  `Zoé Cordelier`, a 2026 copyright value, the generation timestamp, and the
  prompt.
- A generated JPEG or WebP stores the synthetic values in EXIF fields where
  supported.
- A generated PNG stores equivalent text metadata where EXIF is not
  the natural container.

## Story 6: Keep Metadata Export Choices Explicit

As a user, I want stored-image download and clean download to be separate
actions, so that I always know whether the exported file contains metadata.

### Acceptance Notes

- The gallery makes normal download/open and clean download visually and
  behaviorally distinct.
- Normal download uses a cloud-with-down-arrow icon.
- Clean download uses the same cloud-with-down-arrow icon with a small sparkle
  overlay offset to the right, signaling the stripped/cleaned export.
- Do not use disk icons for these actions; disk icons read as saving workspace
  state rather than downloading an image from the web UI.
- The default browser open/view action continues to serve the stored
  metadata-rich image.
- Export actions produce download responses rather than rewriting the gallery
  source file.
- Filenames make the export mode clear enough to avoid confusion when both
  files are saved locally.

### Examples

- `sample.jpg` opens the stored image.
- A clean export may download as `sample-clean.jpg`.
- A normal download may keep the stored filename `sample.jpg` because that file
  already contains the synthetic metadata.
