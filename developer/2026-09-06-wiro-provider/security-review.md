# Wiro provider security review

## Scope

This review covers adding Wiro as an external generation provider for the two
uncensored Seedream 5 endpoints in this epic. It considers provider
credentials, source-image uploads, untrusted provider responses, remote output
downloads, and error reporting.

## Required controls

### Credentials and transport

- Keep `WIRO_API_KEY` and the account-issued `WIRO_API_SECRET` server-side in
  the ignored `.env` file.
- Send it only to the fixed HTTPS Wiro API origin in the `x-api-key` header.
- Do not load or transmit `WIRO_API_SECRET` when API-key-only authentication
  succeeds.
- Never accept a Wiro base URL, callback URL, or authentication header from the
  browser or model metadata.
- Never serialize the key or request headers into logs, errors, SQLite history,
  or embedded image metadata.

### Source images

- Resolve source images only through the existing gallery/source-image
  boundary; do not accept arbitrary local paths.
- Preserve existing safe-filename, extension, count, and containment checks
  before opening a file for upload.
- Close every opened upload stream on success or failure.
- Send only the source images explicitly selected for the current request.

### Provider responses and downloads

- Treat every Wiro response, task status, error, and output URL as untrusted.
- Validate response structure and require both a terminal success status and a
  successful provider exit value.
- Reuse the existing image store for HTTPS-only output downloads, redirect and
  resolved-address checks, content-type validation, byte limits, and local
  collision-resistant filenames.
- Do not render provider error text as HTML.

### Availability and billing

- Poll only the task identifier returned by the original submission.
- Bound polling with the configured timeout and do not resubmit automatically
  after an ambiguous response or timeout.
- Handle rate limits and task failures without hiding the provider task
  identifier needed for support.
- Tests must use fakes and must never submit a real billable request.

### Endpoint policy

- Represent `Uncensored` as part of the exact model identity, not as a generic
  flag that can be applied to other providers or models.
- Do not claim that the endpoint removes legal, account, or provider-policy
  obligations.
- Do not weaken application input, filesystem, CSRF, download, or metadata
  validation because the selected provider endpoint is less restrictive.

## Open verification items

- Confirm both model references and their availability with the authenticated
  Wiro model-detail API.
- Confirm that the API-key-only project accepts `x-api-key` without the issued
  `WIRO_API_SECRET`; treat the dashboard/documentation mismatch as unresolved
  until that call succeeds.
- Confirm the exact source-image multipart representation and maximum counts.
- Confirm pricing, terminal task states, success exit representation, output
  object shape, and API error envelopes.
- Confirm through paid smoke tests that API-key requests behave consistently
  with the interactive Wiro tests.

## Conclusion

The provider can fit the current trust boundary without weakening existing
controls. No security blocker is identified, provided authenticated schema
discovery resolves the open API-contract details before tickets are finalized.
