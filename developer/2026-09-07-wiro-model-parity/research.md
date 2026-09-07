# Wiro model parity research

Research performed on 2026-09-07. No Wiro Run endpoint was called: this
report used Wiro's authenticated, non-generating Tool List and Tool Detail
APIs through `scripts/get_schema_wiro`.

## Method and evidence

- [Wiro's API documentation](https://wiro.ai/docs) defines Tool List as the
  searchable model catalog and Tool Detail as the model-specific parameter and
  pricing contract.
- [Wiro's model catalog](https://wiro.ai/models/) and authenticated Tool List
  searches supplied candidate identities. Searches used the inventory names,
  their vendor names, and broader terms for `flux`, `imagen`, `krea`, `wan`,
  and `seedream`.
- Every exact endpoint marked available or already covered was accepted by the
  authenticated Tool Detail API. The generated reports contained no API key,
  authentication header, private file, signed URL, or Run result.
- Wiro's generic task contract says non-LLM `outputs` are an array of generated
  CDN files. Tool Detail did not return a more specific output schema for any
  candidate, so `image-urls` is the only supported registry shape; model-level
  output structure was not inferred beyond that documented contract.

Absence means an authenticated catalog search returned no matching model; it
does not claim that Wiro can never add the model. Ambiguous means Wiro returned
related names but did not establish identity with the inventoried endpoint.

## Inventory result

The counts reconcile to the committed inventory: 19 researched rows comprise
10 available, 5 unavailable, and 4 ambiguous results; 7 rows were excluded by
scope; and 2 rows were already covered.

| Model | Interest | Wiro status | Evidence and conclusion |
| --- | --- | --- | --- |
| Bria Fibo | Skip | Excluded | Not queried or proposed, as required by the committed scope. |
| Ernie Image | Skip | Excluded | Not queried or proposed, as required by the committed scope. |
| Ernie Image Turbo | Skip | Excluded | Not queried or proposed, as required by the committed scope. |
| Flux 2 | Research | Ambiguous | No exact Flux 2 identity. Catalog results include `wiro/flux-2-dev`, `wiro/flux-2-dev-turbo`, four Flux 2 Klein variants, Flex, and Pro, but do not prove which contract matches `falai:flux-2`. |
| Flux 2 Flex | Research | Available | Exact Tool Detail match: `black-forest-labs/flux-2-flex`. |
| Flux 2 Pro | Skip | Excluded | Not queried or proposed, as required by the committed scope. |
| Flux 2 Realism | Research | Unavailable | Exact and broader `flux realism` searches returned no model; the only `realism` result was an unrelated Wiro video workflow. |
| GPT Image 1.5 | Research | Available | Exact Tool Detail match: `openai/gpt-image-1-5`. |
| GPT Image 2 | Research | Available | Exact Tool Detail match: `openai/gpt-image-2`; `openai/gpt-image-2-custom` is an alternate, report-only endpoint. |
| Grok Imagine Image | Research | Available | Exact Tool Detail match: `xai/grok-imagine-image`; `xai/grok-imagine-image-v2` is a newer report-only alternate. |
| HiDream I1 Dev | Research | Available | Exact Tool Detail match: `hidreamai/hidream-i1-dev`. |
| HiDream I1 Fast | Research | Available | Exact Tool Detail match: `hidreamai/hidream-i1-fast`. |
| HiDream I1 Full | Skip | Excluded | Not queried or proposed, as required by the committed scope. |
| Imagen 4 | Research | Ambiguous | Exact and broad authenticated catalog searches returned no Imagen endpoint. Wiro's general documentation mentions “Imagen V4” as an example, but supplies no exact catalog identity or Tool Detail contract. |
| Imagen 4 Fast | Research | Ambiguous | Same catalog/documentation conflict as Imagen 4; no exact endpoint could be verified. |
| Imagen 4 Ultra | Research | Ambiguous | Same catalog/documentation conflict as Imagen 4; no exact endpoint could be verified. |
| Krea 2 Large | Research | Unavailable | Exact and broad Krea searches returned only `black-forest-labs/flux-1-krea-dev`, which is not Krea 2. |
| Krea 2 Medium | Research | Unavailable | Exact and broad Krea searches returned only `black-forest-labs/flux-1-krea-dev`, which is not Krea 2. |
| Krea 2 Turbo | Research | Unavailable | Exact and broad Krea searches returned only `black-forest-labs/flux-1-krea-dev`, which is not Krea 2. |
| Nano Banana 2 | Research | Available | Exact Tool Detail match: `google/nano-banana-2`; `google/nano-banana-2-lite` and older `google/nano-banana` are report-only alternates. |
| Nano Banana Pro | Research | Available | Exact Tool Detail match: `google/nano-banana-pro`. |
| Qwen Image 2512 | Skip | Excluded | Not queried or proposed, as required by the committed scope. |
| Seedream 4 | Skip | Excluded | Not queried or proposed, as required by the committed scope. |
| Seedream 4.5 | Research | Available | Both `bytedance/seedream-v4-5-uncensored` and normal `bytedance/seedream-v4-5` passed Tool Detail. The uncensored endpoint is the implementation candidate. |
| Seedream 5 Lite | Already covered | Covered | Existing `bytedance/seedream-v5-lite-uncensored` passed Tool Detail. Normal `bytedance/seedream-v5-lite` is available but remains report-only. |
| Seedream 5 Pro | Already covered | Covered | Existing `bytedance/seedream-v5-pro-uncensored` passed Tool Detail. Normal `bytedance/seedream-v5-pro` is available but remains report-only. |
| Wan 2.7 Image Pro | Research | Unavailable | Exact search returned only `alibaba/wan-2-7` and `alibaba/wan-2-7-reference`, both video models. Broader image searches returned unrelated `pruna/wan-image-small`. |
| Z-Image Turbo | Research | Available | Exact Tool Detail match: `tongyi-mai/z-image-turbo`. |

## Recommended implementation set

Only these ten exact endpoints should become later code tickets:

| Proposed Wiro alias | Display name | Exact endpoint | Mode |
| --- | --- | --- | --- |
| `flux-2-flex` | Flux 2 Flex | `black-forest-labs/flux-2-flex` | Text and edit |
| `gpt-image-15` | GPT Image 1.5 | `openai/gpt-image-1-5` | Text and edit |
| `gpt-image-2` | GPT Image 2 | `openai/gpt-image-2` | Text and edit |
| `grok-imagine` | Grok Imagine Image | `xai/grok-imagine-image` | Text and edit |
| `hidream-dev` | HiDream I1 Dev | `hidreamai/hidream-i1-dev` | Text only |
| `hidream-fast` | HiDream I1 Fast | `hidreamai/hidream-i1-fast` | Text only |
| `nano-banana-2` | Nano Banana 2 | `google/nano-banana-2` | Text and edit |
| `nano-banana-pro` | Nano Banana Pro | `google/nano-banana-pro` | Text and edit |
| `seedream45-uncensored` | Seedream 4.5 Uncensored | `bytedance/seedream-v4-5-uncensored` | Text and edit |
| `z-image-turbo` | Z-Image Turbo | `tongyi-mai/z-image-turbo` | Text only |

Provider-scoped aliases allow these names to coexist with Replicate and
fal.ai aliases. No unavailable, ambiguous, excluded, already-covered, or
alternate endpoint is recommended for implementation.

## Confirmed contracts

All documentation links follow
`https://wiro.ai/models/<owner>/<model>` and all runtime URLs follow
`https://api.wiro.ai/v1/Run/<owner>/<model>`. Prices below are the Tool Detail
values in US dollars. `cpr` is Wiro's per-run method and `cpo` is per output.

### Flux 2 Flex

`black-forest-labs/flux-2-flex` is normal (no uncensored alternate found),
supports text and up to 8 edit sources, and reports a 10-second runtime.

| Parameter | Contract |
| --- | --- |
| `prompt` | Required text. |
| `inputImage` | Optional combined file input, maximum 8; edit only in the app. |
| `width`, `height` | Optional numbers, default 1024, reported bounds 0–2048; description additionally requires 64–2048 in multiples of 16 when nonzero. |
| `safetyTolerance` | Integer 0–5, default 2. This is Wiro's supplied control; no different safety behavior is inferred. |
| `seed` | Integer 0–9,999,999, default 123. |
| `guidance` | Number 1.5–10, default 4.5. |
| `steps` | Integer 1–50, default 50. |
| `outputFormat` | `jpeg` or `png`; Wiro defaults to PNG, while application policy should default to JPEG. |

Pricing is `$0.06` per computed pixel unit with the same Tool Detail price for
zero or one input image; the one-input tier additionally reports a `$0.06`
input charge. Wiro's `cp-pixel` conditions must be retained in operator-facing
pricing text rather than misrepresented as a flat per-image price.

### GPT Image 1.5

`openai/gpt-image-1-5` is normal, supports text, up to 16 edit sources, and one
separate mask file, and reports a 10-second runtime.

| Parameter | Contract |
| --- | --- |
| `prompt` | Required text, maximum 32,000 characters. |
| `inputImage` | Optional combined file input, maximum 16. |
| `inputImageMask` | Optional combined file input, maximum 1; requires source images. |
| `size` | Required `auto`, `1:1`, `3:2`, or `2:3`; default `auto`. |
| `quality` | Required `low`, `medium`, or `high`; default `low`. |
| `background` | Optional `auto`, `transparent`, or `opaque`; default `auto`. |
| `outputFormat` | Optional `png`, `jpeg`, or `webp`; Wiro defaults to PNG, application policy should default to JPEG. |
| `outputCompression` | Optional integer 0–100, default 100. |
| `samples` | Required integer 1–10, default 1. |
| `moderation` | Optional `auto` or `low`, default `low`. |
| `inputFidelity` | Optional edit control `high` or `low`, default `high`. |

Per-run pricing matrix:

| Quality | 1:1 | 3:2 | 2:3 | auto |
| --- | ---: | ---: | ---: | ---: |
| low | $0.009 | $0.013 | $0.013 | $0.013 |
| medium | $0.034 | $0.050 | $0.050 | $0.050 |
| high | $0.133 | $0.200 | $0.200 | $0.200 |

### GPT Image 2

`openai/gpt-image-2` is normal, supports text, up to 16 edit sources, and one
separate mask file, and reports a 10-second runtime.

| Parameter | Contract |
| --- | --- |
| `prompt` | Required text, maximum 32,000 characters. |
| `inputImage` | Optional combined file input, maximum 16. |
| `inputImageMask` | Optional combined file input, maximum 1; requires source images. |
| `resolution` | Required `1k`, `2k`, or `4k`; default `1k`. |
| `ratio` | Required `1:1`, `3:2`, `2:3`, `4:3`, `3:4`, `16:9`, or `9:16`; default `1:1`. |
| `quality` | Required `low`, `medium`, or `high`; default `low`. |
| `background` | Optional `auto` or `opaque`; default `auto`. |
| `outputFormat` | Optional `png`, `jpeg`, or `webp`; Wiro defaults to PNG, application policy should default to JPEG. |
| `outputCompression` | Optional integer 0–100, default 100. |
| `samples` | Required integer 1–10, default 1. |
| `moderation` | Optional `auto` or `low`, default `low`. |

Per-run pricing matrix; values across each row follow ratios
`1:1 / 3:2 / 2:3 / 4:3 / 3:4 / 16:9 / 9:16`:

| Resolution, quality | Prices |
| --- | --- |
| 1k low | $0.006 / $0.005 / $0.005 / $0.005 / $0.005 / $0.003 / $0.003 |
| 1k medium | $0.053 / $0.041 / $0.041 / $0.042 / $0.042 / $0.028 / $0.028 |
| 1k high | $0.211 / $0.165 / $0.165 / $0.167 / $0.167 / $0.114 / $0.114 |
| 2k low | $0.012 / $0.008 / $0.008 / $0.007 / $0.007 / $0.005 / $0.005 |
| 2k medium | $0.107 / $0.067 / $0.067 / $0.067 / $0.067 / $0.042 / $0.042 |
| 2k high | $0.428 / $0.269 / $0.269 / $0.267 / $0.267 / $0.170 / $0.170 |
| 4k low | $0.020 / $0.013 / $0.013 / $0.014 / $0.014 / $0.011 / $0.011 |
| 4k medium | $0.178 / $0.115 / $0.115 / $0.125 / $0.125 / $0.100 / $0.100 |
| 4k high | $0.712 / $0.459 / $0.459 / $0.502 / $0.502 / $0.400 / $0.400 |

### Grok Imagine Image

`xai/grok-imagine-image` is normal, supports text and one edit source, and
reports a 10-second runtime. Parameters are required `prompt`; required
`samples` integer 1–10, default 1; optional `aspectRatio`, default `16:9`, with
`16:9`, `9:16`, `1:1`, `4:3`, `3:4`, `3:2`, `2:3`, `2:1`, `1:2`, `19.5:9`,
`9:19.5`, `20:9`, and `9:20`; and required `resolution` (`1k` or `2k`, default
`1k`). Tool Detail reports `$0.02` per output.

### HiDream I1 Dev and Fast

Both normal endpoints are text-only and expose the same parameter shape:
required `prompt`; optional `negativePrompt`; numeric `steps` 1–500; numeric
`scale` 0–20, default 0; numeric `flowShift` 1–10; required `samples` 1–8,
default 1; text-valued numeric `seed` 0–9,999,999,999, default 0; and required
`width` and `height` 0–2048, default 1024. Dev defaults to 30 steps and flow
shift 6.0 with a 40-second runtime; Fast defaults to 20 steps and flow shift
3.0 with a 25-second runtime. Tool Detail returned no `dynamicprice` for either
model, so no model-specific price can be truthfully placed in the registry;
Wiro documents per-second fallback pricing when that field is absent.

### Nano Banana 2

`google/nano-banana-2` is normal, supports text and up to 14 edit sources, and
reports a 10-second runtime. It requires `prompt`; offers optional
`aspectRatio`, default auto/empty, with `Match Input Image`, `1:1`, `1:4`,
`1:8`, `2:3`, `3:2`, `3:4`, `4:1`, `4:3`, `4:5`, `5:4`, `8:1`, `9:16`,
`16:9`, and `21:9`; optional `resolution` (`512`, `1K`, `2K`, `4K`, default
`1K`); and optional `safetySetting` (`BLOCK_LOW_AND_ABOVE`,
`BLOCK_MEDIUM_AND_ABOVE`, `BLOCK_ONLY_HIGH`, `BLOCK_NONE`, or `OFF`, default
`OFF`). Per-output prices are `$0.045` at 512, `$0.067` at 1K, `$0.101` at
2K, and `$0.151` at 4K.

### Nano Banana Pro

`google/nano-banana-pro` is normal, supports text and up to 14 edit sources,
and reports a 10-second runtime. It requires `prompt`; offers optional
`aspectRatio`, default auto/empty, with `Match Input Image`, `1:1`, `2:3`,
`3:2`, `3:4`, `4:3`, `4:5`, `5:4`, `9:16`, `16:9`, and `21:9`; optional
`resolution` (`1K`, `2K`, `4K`, default `1K`); and the same optional
`safetySetting` choices and `OFF` default as Nano Banana 2. Per-output prices
are `$0.14` at 1K or 2K and `$0.24` at 4K.

### Seedream 4.5 Uncensored

`bytedance/seedream-v4-5-uncensored` is the preferred uncensored endpoint,
supports text and up to 14 edit sources, and reports a 30-second runtime. It
requires `prompt`; offers optional `resolution` (`auto`, `2k`, `4k`) and
`aspectRatio` (`auto`, `1:1`, `2:3`, `3:2`, `3:4`, `4:3`, `4:5`, `5:4`,
`16:9`, `9:16`, `21:9`, `9:21`) with empty defaults; required `maxImages`
integer 1–15, default 1; and required string-valued `watermark` (`false` or
`true`), default `false`. Sources plus generated outputs may not exceed 15.
Tool Detail reports `$0.04` per output. The normal endpoint has the same
observed shape and price and remains report-only.

### Z-Image Turbo

`tongyi-mai/z-image-turbo` is normal, text-only, and reports a 20-second
runtime. It requires `prompt`; exposes integer `steps` 1–50, default 9;
numeric `scale` 0–20, default 0.0; text-valued numeric `seed`
0–9,999,999,999, default 0; required `resolution` (`480P`, `580P`, `720P`,
`1080P`, default `480P`); and required `aspectRatio` (`16:9`, `9:16`, `1:1`,
default `1:1`). Tool Detail reports `$0.006` per run.

## Report-only alternate endpoints

- `openai/gpt-image-2-custom` supports text/edit with custom 480–3840 pixel
  width and height and token-derived pricing. It is not the inventoried GPT
  Image 2 endpoint and is not proposed.
- `xai/grok-imagine-image-v2` supports text/edit and adds `auto` ratio plus
  low/medium quality tiers. It is a newer alternate rather than the exact
  inventoried endpoint and is not proposed.
- `google/nano-banana-2-lite` supports only 1K output at `$0.034` per output.
  It is not the inventoried Nano Banana 2 endpoint and is not proposed.
- Normal Seedream endpoints `bytedance/seedream-v4-5`,
  `bytedance/seedream-v5-lite`, and `bytedance/seedream-v5-pro` all passed Tool
  Detail. The first loses to its uncensored sibling under the committed rule;
  the latter two are alternates of already-covered families.
- Related Flux results are reported in the inventory table, but none establishes
  exact equivalence to the versionless fal.ai Flux 2 entry.

## Integration constraints for later tickets

1. `GenerationTarget` has one `SourceImageBinding`. GPT Image 1.5 and GPT Image
   2 have two distinct trusted file fields, `inputImage` and `inputImageMask`.
   Ordinary multi-image editing can use the existing binding, but exposing mask
   editing requires a separately designed registry/client contract. Do not put
   `inputImageMask` in generic browser-submitted parameters.
2. `ModelParameter` records numeric bounds but not a multiple-of-16 constraint
   or a cross-field pixel/ratio constraint. Flux 2 Flex's nonzero dimensions
   and the report-only GPT Image 2 Custom dimensions cannot be represented
   exactly without validation work. Only Flux 2 Flex is in implementation
   scope.
3. Conditional pricing is stored as display metadata, not executable billing
   logic. GPT Image and Nano Banana matrices can be listed precisely; Flux's
   `cp-pixel` contract must not be collapsed to a false flat price. HiDream's
   absent dynamic price should remain unknown rather than guessed.
4. Wiro's generic non-LLM output-array contract matches the existing Wiro
   client's `image-urls` normalization. No paid probe is needed to implement
   registry discovery and fake-transport coverage. A real smoke test remains a
   separate, explicit authorization decision.
5. Preserve the project policies already established for Wiro: prefer JPEG
   when an endpoint exposes a format choice, and default watermark to `false`
   when Wiro exposes that control. Provider-supplied safety controls retain
   their exact names, choices, and defaults.
