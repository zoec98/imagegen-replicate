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

Selectable model aliases must be unique within each provider. Selectable model
display names must also be unique case-insensitively within each provider;
display names are valid user-facing model references for the `imagegen` CLI.

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

## Wiro

Read Wiro authentication from:

```bash
WIRO_API_KEY
```

Use an API-key-only Wiro project. Do not configure or send `WIRO_API_SECRET`.
Run `scripts/get_schema_wiro owner/model` before adding or updating a Wiro
registry entry. The command calls Wiro's authenticated Tool Detail endpoint
without starting a generation.

The Tool Detail retrievals and authorized text probes cover exactly these
provider model identities:

- `bytedance/seedream-v5-pro-uncensored`
- `bytedance/seedream-v5-lite-uncensored`
- `bytedance/seedream-v4-5-uncensored`

Pro has `resolution` (`1k`/`2k`), `aspectRatio`, `outputFormat` (`jpeg`/`png`),
and string-valued `watermark` (`false`/`true`), with a maximum of 10
`inputImage` sources for editing. Lite has `resolution` (`auto`/`2k`/`3k`),
`aspectRatio`, integer `maxImages` (1–15), and the same string-valued
`watermark`, with a maximum of 14 edit sources and a source-plus-output limit
of 15. The application defaults output to JPEG and watermark to `false`.

Wiro pricing is provider-reported: Pro is `$0.045` at 1K and `$0.09` at 2K;
Lite is `$0.035` per output; Seedream 4.5 Uncensored is `$0.04` per output.
Seedream 4.5 supports `resolution` (`auto`/`2k`/`4k`), `aspectRatio`
(`auto`, `1:1`, `2:3`, `3:2`, `3:4`, `4:3`, `4:5`, `5:4`, `16:9`, `9:16`,
`21:9`, `9:21`), integer `maxImages` (1–15), and string-valued `watermark`
(`false`/`true`). It accepts up to 14 edit sources, with source images plus
outputs limited to 15. Its Tool Detail response contains no output-format or
safety control; the application therefore keeps `watermark` at `false` and
does not invent a JPEG or safety input for this endpoint. The exact
`Uncensored` endpoint is part of each model identity. These endpoints do not
promise bypass of account, legal, or provider-policy limits.

For editing, selected local files are sent as repeated `inputImage` parts in a
multipart request. Text-only requests use JSON. Persisted metadata contains
local source filenames, never upload URLs, headers, credentials, or signed
URLs. See the authenticated response record in
`developer/2026-09-06-wiro-provider/schema-discovery.md`.

The additional text-only `tongyi-mai/z-image-turbo` contract exposes `steps`
(1–50, default 9), `scale` (0–20, default 0), string-valued `seed`
(0–9,999,999,999, default `0`), `resolution` (`480P`, `580P`, `720P`,
`1080P`, default `480P`), and `aspectRatio` (`16:9`, `9:16`, `1:1`, default
`1:1`). It costs `$0.006` per run and does not support editing.

The text-only `hidreamai/hidream-i1-dev` and `hidreamai/hidream-i1-fast`
contracts share prompt, `negativePrompt`, `scale`, `flowShift`, `samples`,
string-valued `seed`, `width`, and `height` inputs. Dev defaults to 30 steps,
flow shift 6.0, and a 40-second runtime; Fast defaults to 20 steps, flow shift
3.0, and a 25-second runtime. Steps range from 1–500, scale from 0–20, flow
shift from 1–10, samples from 1–8, seed from 0–9,999,999,999, and dimensions
from 0–2048 with 1024 defaults. Tool Detail reported no dynamic price for
either endpoint, so the registry does not invent one. Neither endpoint
supports editing.

The `xai/grok-imagine-image` contract supports text generation and editing with
one `inputImage` source. It exposes `samples` (1–10, default 1),
`aspectRatio` (`16:9`, `9:16`, `1:1`, `4:3`, `3:4`, `3:2`, `2:3`, `2:1`,
`1:2`, `19.5:9`, `9:19.5`, `20:9`, `9:20`, default `16:9`), and `resolution`
(`1k`/`2k`, default `1k`). Tool Detail reports a 10-second runtime and `$0.02`
per output. The Wiro V2 endpoint is a report-only alternate and is not
registered.

The `google/nano-banana-2` and `google/nano-banana-pro` contracts support text
generation and editing with up to 14 `inputImage` sources. Nano Banana 2
offers `resolution` (`512`, `1K`, `2K`, `4K`), while Pro offers (`1K`, `2K`,
`4K`); both default to `1K` and expose their documented aspect-ratio choices.
The application sends fixed `safetySetting: "OFF"` and does not expose that
provider control. Operator-facing price guidance is `$0.045–$0.151` for Nano
Banana 2 and `$0.14–$0.24` for Pro; provider billing remains authoritative.

The `black-forest-labs/flux-2-flex` contract supports text generation and
editing with up to eight `inputImage` sources. Width and height default to
1024, accept `0` to match the input image, and otherwise must be 64–2048 in
multiples of 16. It also exposes integer `seed` (0–9,999,999, default 123),
`guidance` (1.5–10, default 4.5), `steps` (1–50, default 50), and
`outputFormat` (`jpeg`/`png`, default `jpeg`). The application always sends
fixed `safetyTolerance: 5` and does not expose that control. Wiro reports
cp-pixel pricing from `$0.06/MP`; this is variable provider billing, not a
flat per-image price.

The `openai/gpt-image-1-5` contract supports text generation and editing with
up to 16 `inputImage` sources. It exposes `size` (`auto`, `1:1`, `3:2`, `2:3`),
`quality` (`low`, `medium`, `high`), `background` (`auto`, `transparent`,
`opaque`), `outputFormat` (`png`, `jpeg`, `webp`), `outputCompression` (0–100),
and `samples` (1–10). Edit requests additionally expose `inputFidelity`
(`high`/`low`). The `openai/gpt-image-2` contract has the same output controls
but uses `resolution` (`1k`, `2k`, `4k`) and `ratio` (`1:1`, `3:2`, `2:3`,
`4:3`, `3:4`, `16:9`, `9:16`). Both default output to JPEG and use fixed
`moderation: "low"`; that safety control is not user-configurable. Wiro
reports price matrices ranging from `$0.009–$0.200` for GPT Image 1.5 and
`$0.003–$0.712` for GPT Image 2, so the registry displays ranges rather than
flat per-run prices. The optional `inputImageMask` file field is deliberately
unsupported because the current trusted upload contract has only one source
file channel; ordinary multi-image edits remain supported.

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
