# fal.ai FLUX 3

Add selectable `falai:flux-3` (Flux 3), with linked text and edit targets.

## Contract discovery

- [Text API](https://fal.ai/models/blackforestlabs/flux-3/text-to-image/api)
- [Edit API](https://fal.ai/models/blackforestlabs/flux-3/edit-image/api)
- Public schemas: `https://fal.ai/api/openapi/queue/openapi.json?endpoint_id=blackforestlabs/flux-3/text-to-image` and the corresponding `edit-image` endpoint.
- Required helper was run with both URLs, but failed because the page no longer exposes its expected meta-based JSON-LD identifier. Verified schemas via the pages' linked public OpenAPI instead.
- Shared controls: aspect ratio (15 choices, default auto), resolution (512sq, 768sq, 1k default, 2k, 4k), prompt expansion (false), integer safety tolerance (0–4, default 2), JPEG/PNG (JPEG default). No seed or output count.
- Fixed `sync_mode: false` preserves URL outputs. Schema permits only `version: latest`, sent as a fixed input; no immutable version is available. No enable_safety_checker field exists.
- Edit sources use trusted top-level source_images, bound to image_urls (1–10). Provider additionally requires each reference to be at least 256 pixels per dimension and at most 4 MP; existing source upload behavior delegates these dimension restrictions to the provider. Auto aspect ratio follows the first source.
- Output: images array of ImageFile objects with URL. Existing fal.ai wrapper handles it.
- Page billing reports $0.024/megapixel, while descriptive pricing says a flat price by resolution, starting at $0.0205; 1K is $0.024 during a launch discount ending October 8, then $0.048. Registry uses static variable-price guidance with the standard 1K example, avoiding a permanent promotional quote or invented tier prices.

## Validation

Registry contract, request parameter validation, edit source limits, and fake-provider edit submission cover the addition. No real image generation calls were made.

Full `uv run pytest`: 549 passed. `uv run ruff check src tests`: passed.
