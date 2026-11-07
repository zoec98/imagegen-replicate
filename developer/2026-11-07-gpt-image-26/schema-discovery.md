# GPT Image 2.6 provider discovery

November 7, 2026

OpenAI announced Images 2.6 on November 4, 2026, with Flare for fast
generation and Sunburst for detailed generation and precise edits.
[OpenAI release](https://openai.com/index/introducing-images-2-6/)

All three providers publish both models. fal.ai separates generation and
editing into different endpoints. Replicate and Wiro accept reference
images on the same endpoint used for text-only requests.

| Provider | Variant | Text-to-image model ID | Image-edit model ID |
| --- | --- | --- | --- |
| fal.ai | Flare | [`openai/gpt-image-2.6/flare/text-to-image`](https://fal.ai/models/openai/gpt-image-2.6/flare/text-to-image/api) | [`openai/gpt-image-2.6/flare/edit`](https://fal.ai/models/openai/gpt-image-2.6/flare/edit/api) |
| fal.ai | Sunburst | [`openai/gpt-image-2.6/sunburst/text-to-image`](https://fal.ai/models/openai/gpt-image-2.6/sunburst/text-to-image/api) | [`openai/gpt-image-2.6/sunburst/edit`](https://fal.ai/models/openai/gpt-image-2.6/sunburst/edit/api) |
| Replicate | Flare | [`openai/gpt-image-2.6-flare`](https://replicate.com/openai/gpt-image-2.6-flare) | Same ID, with `input_images` |
| Replicate | Sunburst | [`openai/gpt-image-2.6-sunburst`](https://replicate.com/openai/gpt-image-2.6-sunburst) | Same ID, with `input_images` |
| Wiro | Flare | [`openai/gpt-image-2-6-flare`](https://wiro.ai/models/openai/gpt-image-2-6-flare) | Same ID, with reference images |
| Wiro | Sunburst | [`openai/gpt-image-2-6-sunburst`](https://wiro.ai/models/openai/gpt-image-2-6-sunburst) | Same ID, with reference images |

fal.ai's edit endpoints require `image_urls` and accept up to 16
references. [Flare edit schema](https://fal.ai/models/openai/gpt-image-2.6/flare/edit/api),
[Sunburst edit schema](https://fal.ai/models/openai/gpt-image-2.6/sunburst/edit/api)

Replicate serves its official model IDs at
`POST https://api.replicate.com/v1/models/{model_id}/predictions`.
[Replicate official model API](https://replicate.com/docs/topics/models/official-models)

Wiro serves its model IDs at `POST https://api.wiro.ai/v1/Run/{model_id}`.
The standard models take resolution and aspect ratio. Wiro also publishes
`openai/gpt-image-2-6-flare-custom` and `openai/gpt-image-2-6-sunburst-custom`.
These accept explicit width and height and support editing with up to 16
reference images. The public Flare Custom description lists GIF output for
text-only requests, while authenticated Tool Detail describes GIF output with
or without references.
[Wiro Flare](https://wiro.ai/models/openai/gpt-image-2-6-flare),
[Wiro Sunburst](https://wiro.ai/models/openai/gpt-image-2-6-sunburst),
[Wiro Flare Custom](https://wiro.ai/models/openai/gpt-image-2-6-flare-custom),
[Wiro Sunburst Custom](https://wiro.ai/models/openai/gpt-image-2-6-sunburst-custom)

## Schema helper results

The following read-only schema commands succeeded for both variants.

```bash
for variant in flare sunburst; do
  fal_base="https://fal.ai/models/openai/gpt-image-2.6/${variant}"
  scripts/get_schema_falai "${fal_base}/text-to-image/api" "${fal_base}/edit/api"
  scripts/get_schema_replicate "openai/gpt-image-2.6-${variant}"
  scripts/get_schema_wiro "openai/gpt-image-2-6-${variant}"
  scripts/get_schema_wiro "openai/gpt-image-2-6-${variant}-custom"
done
```

- fal.ai returned separate OpenAPI contracts. Both modes use
  `reasoning_effort` with `low`, `medium`, and `high` and default to
  `high`. Editing requires `image_urls`. Both modes expose
  `enable_safety_checker`, which the application sets to `false`. The
  pricing API reports $1 per billing unit for each endpoint.
  [Flare](https://fal.ai/models/openai/gpt-image-2.6/flare/text-to-image/api),
  [Sunburst](https://fal.ai/models/openai/gpt-image-2.6/sunburst/text-to-image/api)
- Replicate returned one schema candidate per model, each matching the
  model page's latest version. Flare returned
  `6a0b1916900193c203b23c479a562ffc0a4b2990c9eeee28be13f74b4c6d8908`.
  Sunburst returned
  `b4fdded822860ed68bb8b7f00c5dd5e66551d3e08c323c722742bb083a071196`.
  The schema records the version under an internal model name. Requests use
  the official public model endpoint. Both models use `complexity` and
  return an array of image URLs. The helper reported no maximum for
  `input_images`, so the app uses the same 10-source limit as its Replicate
  GPT Image 2.5 entries.
  [Flare schema](https://replicate.com/openai/gpt-image-2.6-flare/api/schema),
  [Sunburst schema](https://replicate.com/openai/gpt-image-2.6-sunburst/api/schema)
- Wiro Tool Detail confirmed all four IDs. The standard models support
  `inputImage` for up to 16 sources, `complexity`, and a provider price
  matrix ranging from $0.013 to $0.712. Flare defaults to a 16:9 aspect ratio
  and Sunburst to 1:1. The app sets `moderation` to `low` for both.
  [Flare](https://wiro.ai/models/openai/gpt-image-2-6-flare),
  [Sunburst](https://wiro.ai/models/openai/gpt-image-2-6-sunburst)

The registry adds the six standard provider/variant combinations under
`gpt-image-26-flare` and `gpt-image-26-sunburst`. It offers JPEG, PNG, and
WebP, which the gallery can store. Separate mask and markup inputs, GIF and
SVG output, and the Wiro Custom variants are outside these entries. fal.ai
uses the provider's optional compression default.
