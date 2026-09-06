# Wiro smoke-test record

Date: 2026-09-06

## Verified

Two authorized text-generation probes were run exactly once, one per model,
with the prompt recorded in `schema-discovery.md`. Both requests completed
through the API with `task_postprocess_end` and `pexit: "0"`:

| Model | Task | Output | Cost |
| --- | ---: | --- | ---: |
| `bytedance/seedream-v5-pro-uncensored` | `3066517` | HTTPS `image/png` URL | `$0.045` |
| `bytedance/seedream-v5-lite-uncensored` | `3066542` | HTTPS `image/jpeg` URL | `$0.035` |

Only safe task/result facts are recorded here. Credentials, headers, signed
URLs, private images, prompts, and local paths are deliberately omitted.
The application defaults to JPEG even though the Pro probe deliberately used
PNG to capture the alternate provider output shape.

## Edit confirmation

On 2026-09-06 the project owner confirmed that paid API smoke tests for text
generation and one-image editing succeeded for both Pro and Lite. Exact edit
task ids, costs, URLs, prompts, and local source paths were not supplied and
are intentionally not invented here. The interactive Wiro playground is not
treated as API verification.
