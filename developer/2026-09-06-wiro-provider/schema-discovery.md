# Authenticated Wiro schema discovery

Date: 2026-09-06

## Method

Authenticated `POST https://api.wiro.ai/v1/Tool/Detail` requests were made with
only `WIRO_API_KEY` in the `x-api-key` header. Both requests returned HTTP 200
with `result: true`; the account-issued `WIRO_API_SECRET` was not used.

The model-detail response describes inputs, capabilities, and pricing, but does
not provide the completed Task Detail output schema. Task completion and output
normalization therefore remain verification items for implementation tests and
the paid API smoke test.

## Seedream 5 Pro Uncensored

- Model: `bytedance/seedream-v5-pro-uncensored`
- Wiro tool id: `1919`
- Categories include `text-to-image` and `image-to-image`.
- Expected computing time: 60 seconds.
- Optional `inputImage`: combined URL/file input, maximum 10.
- Required `prompt`: textarea.
- Required `resolution`: `1k` or `2k`; default `1k`.
- Required `aspectRatio`: `1:1`, `2:3`, `3:2`, `3:4`, `4:3`, `16:9`,
  `9:16`, or `21:9`; default `1:1`.
- Optional `outputFormat`: `jpeg` or `png`; default `jpeg`.
- Required `watermark`: string choice `false` or `true`; default `false`.
- Provider pricing: `$0.045` at 1K and `$0.09` at 2K, reported with pricing
  method `cpr`.

## Seedream 5 Lite Uncensored

- Model: `bytedance/seedream-v5-lite-uncensored`
- Wiro tool id: `1744`
- Categories include `text-to-image` and `image-to-image`.
- Expected computing time: 30 seconds.
- Optional `inputImage`: combined URL/file input, maximum 14.
- Required `prompt`: textarea.
- Optional `resolution`: `auto`, `2k`, or `3k`; default `auto`. The provider
  also reports an empty legacy auto value that should not be presented as a
  duplicate user choice.
- Optional `aspectRatio`: `auto`, `1:1`, `2:3`, `3:2`, `3:4`, `4:3`, `16:9`,
  `9:16`, or `21:9`; default `auto`. The provider also reports an empty legacy
  auto value that should not be presented as a duplicate user choice.
- Required `maxImages`: integer 1–15; default 1. Input reference count plus
  generated image count must not exceed 15.
- Required `watermark`: string choice `false` or `true`; default `false`.
- Provider pricing: `$0.035`, reported with pricing method `cpo`.

## Registry implications

- Use separate Wiro parameter definitions; the two model contracts are not
  interchangeable.
- Treat `inputImage` and the example prompts/images returned by Tool Detail as
  schema examples, not application defaults.
- Preserve Wiro's camel-case field names in provider requests while exposing
  them through the existing registry-driven UI and CLI behavior.
- Represent Wiro's string-valued boolean choices exactly unless a paid request
  proves that JSON booleans are accepted.
- Do not infer a safety parameter. The uncensored behavior is selected by the
  exact model endpoint.
