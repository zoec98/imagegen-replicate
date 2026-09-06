# Authenticated Wiro schema discovery

Date: 2026-09-06

## Method

Authenticated `POST https://api.wiro.ai/v1/Tool/Detail` requests were made with
only `WIRO_API_KEY` in the `x-api-key` header. Both requests returned HTTP 200
with `result: true`; the account-issued `WIRO_API_SECRET` was not used.

The model-detail response describes inputs, capabilities, and pricing, but does
not provide the completed Task Detail output schema. Two explicitly authorized
text-generation spike probes (one per model) filled that gap. No edit request
was made.

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

## Text-generation spike response shapes

Date: 2026-09-06. Prompt: `A choclate cookie.` Each model was run exactly once
with its documented text-generation inputs, and each returned task was polled
without resubmission. The probe task ids are retained as safe support
references; credentials, socket tokens, access keys, signed URLs, and image
content are intentionally not recorded.

Both probes returned HTTP 200 envelopes with these top-level keys:

```text
errors, result, tasklist, total
```

Both reached `task_postprocess_end` with `pexit: "0"`, one image output, and a
successful `totalcost`. The completed task object included the task lifecycle
timestamps, submitted `parameters`, `status`, `pexit`, `debugoutput`,
`dynamicprice`, model identity, `outputs`, `totalcost`, and the provider's
internal accounting fields. The client only needs the task id, status, pexit,
outputs, and safe diagnostic fields.

### Pro

- Probe task: `3066517`.
- Inputs: `resolution=1k`, `aspectRatio=1:1`, `outputFormat=png`,
  `watermark=false`.
- Final cost: `$0.045`.
- Output content type: `image/png`; URL host: `cdn1.wiro.ai`.
- Output item keys included `name`, `contenttype`, `size`, `url`, and Wiro
  file/account fields. `url` is an HTTPS CDN URL and must be treated as
  untrusted input before download.

### Lite

- Probe task: `3066542`.
- Inputs: `resolution=auto`, `aspectRatio=auto`, `maxImages=1`,
  `watermark=false`.
- Final cost: `$0.035`.
- Output content type: `image/jpeg`; URL host: `api.wiro.ai` under the
  provider's `/v1/File/` route.
- Provider debug output said that an `auto` resolution defaulted to 2K and an
  `auto` aspect ratio defaulted to 16:9 for this run. The registry should keep
  the provider's `auto` choices and must not substitute a local fixed size.
- The Task Detail parameters echoed `maxImages` as the string `"1"`, so the
  client should accept provider JSON type coercion in responses while sending
  the registry-validated request value.

The observed Task Detail output item has these keys and value types:

```text
id:str, name:str, contenttype:str, parentid:str, uuid:str, size:str,
addedtime:str, modifiedtime:str, accesskey:str, foldercount:str,
filecount:str, ispublic:int, expiretime:null, url:str
```

`accesskey` and `url` are response credentials/remote locations; neither may
be written to application metadata or logs beyond the existing safe download
boundary.
