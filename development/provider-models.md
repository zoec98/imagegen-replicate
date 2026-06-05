# Provider Models

Model definitions should be data-driven. Each supported model should declare:

- Stable internal id.
- Display name.
- Provider model key.
- Pinned provider version id when available.
- Schema URL.
- Edit capability as model metadata outside normal parameters.
- Fixed input values that must always be sent but are not user-facing
  parameters.
- Mode: `text-to-image` or `image-edit`.
- Prompt field behavior.
- Required and optional parameters.
- Parameter widget type such as text, textarea, number, slider, select,
  checkbox, image upload, or seed.
- Defaults, bounds, choices, array item formats, and display order.
- Output shape, especially whether outputs are image URLs.

## Replicate

Use the official `replicate` Python package for Replicate API access.

Read Replicate authentication from:

```bash
REPLICATE_API_TOKEN
```

Keep Replicate-specific code behind a small project wrapper so UI and route
tests can use fakes without calling the network.

Always send `disable_safety_checker: true` for Replicate models that support
that parameter. This is application policy and belongs in fixed model inputs,
not exposed as a user-facing parameter.

Use `scripts/get_schema_replicate owner/model` before adding or updating a
Replicate model registry entry. The Replicate schema page is HTML, but it
embeds a dereferenced OpenAPI schema in JSON script data. Extract useful
registry information from `components.schemas.Input` and
`components.schemas.Output`.

Replicate model keys look like:

```text
bytedance/seedream-4.5
```

## fal.ai

Read fal.ai authentication from:

```bash
FAL_KEY
```

Use `scripts/get_schema_falai text-api-url [edit-api-url]` before adding or
updating a fal.ai model registry entry. Pass fal.ai model API documentation URLs
ending in `/api`, such as:

```text
https://fal.ai/models/fal-ai/bytedance/seedream/v4.5/text-to-image/api
```

For paired fal.ai text/edit models, pass the text endpoint URL first and the
linked edit endpoint URL second so registry data can preserve fal.ai's separate
endpoints while the UI treats them as one user-facing model.

When fal.ai exposes `enable_safety_checker`, application policy is to send it as
`false` whenever the parameter is provided.

## Schema Extraction

For provider schemas, extract useful registry information from schema input and
output components:

- `required`: server-required input names.
- `properties`: parameter names and metadata.
- image/source input fields such as `image_input`: evidence that the model is
  edit-capable.
- `type` and nested `items`: widget and validation shape.
- `enum`: select choices.
- `default`: form defaults.
- `minimum` and `maximum`: numeric bounds.
- `format`: URI/date/file hints.
- `x-order`: stable UI ordering.
- `description`: user-facing help text.

If the page exposes multiple embedded schemas or versions, prefer the schema
associated with the current/latest version shown by the page, and record the
schema URL and pinned version in the registry. If that association is ambiguous,
document the ambiguity in the change summary instead of guessing silently.

Do not assume one provider's schema is a complete description of another
provider's capabilities, even when the underlying model supplier is the same.
Provider-specific and conditional parameters must be represented explicitly.

Validate all submitted parameters server-side. The browser UI may help the
user, but server validation is authoritative.

Image-edit requests must submit selected source images through the top-level
`source_images` field with `edit_mode: true`. Do not accept model source-image
parameters through the generic `parameters` object.
