# Security Hardening Tickets

Status: approved for implementation
Sources: [user-stories.md](user-stories.md), [security-review.md](security-review.md)

These tickets are ordered for implementation. Each ticket starts with one
behavior-focused failing test and is committed before the next ticket begins.

## Resource Sizing Decision

Use one binary 1 GiB (`1024 ** 3` bytes) application request budget. Derive
subordinate request and decode ceilings from that budget while preserving any
existing tighter semantic limit:

- The imported-image payload remains capped at its existing 100 MiB, which is
  tighter than one eighth of the global budget.
- The maximum decoded image or mask allocation is one quarter of the global
  budget: 256 MiB.
- The corresponding maximum pixel count assumes four decoded bytes per pixel:
  67,108,864 pixels.
- A Base64 mask request ceiling is calculated from the 256 MiB decoded limit
  using Base64 expansion plus the existing fixed JSON overhead; it is not a
  separate hand-maintained constant.
- Every route applies the smaller of its derived transport allowance and its
  content-specific semantic limit.

The 1 GiB value is a request ceiling, not permission for a route to allocate
that much memory. Generated outputs use a single 64 MiB per-file download limit;
the global 16-image count therefore caps one response at 1 GiB of downloaded
output data. Decompression and raster-memory limits remain governed by Ticket 3.

## Ticket 1: Keep debug mode on loopback

Finding: SR-03

Goal: prevent the installed web launcher from exposing Flask debug mode on a
network interface.

Public behavior:

- `imagegen-web --dev` continues to start the development server on
  `127.0.0.1:5002`.
- `imagegen-web --secure-network` continues to start a non-debug server on
  `0.0.0.0:5002`.
- `imagegen-web --dev --secure-network` exits nonzero with a clear safety error
  before calling Flask.

Test boundary:

- Exercise every launcher flag combination through `imagegen.web.main()` with
  the Flask runner replaced by a test double.
- Assert the rejected combination never invokes the runner.

Done when:

- The public behavior above passes.
- Launcher help and security guidance agree.
- Full Python checks pass.

## Ticket 2: Reject oversized HTTP requests early

Finding: SR-02

Goal: bound JSON and multipart request bodies before route handlers fully
materialize them.

Public behavior:

- A request exceeding the 1 GiB application ceiling receives HTTP 413.
- Uploads exceeding their smaller image limit receive HTTP 413 without an
  unbounded file read.
- Existing valid JSON mutations, uploads, masks, and edits remain accepted.
- JSON and multipart requests retain their existing CSRF requirements.

Test boundary:

- Send oversized JSON and multipart requests through the Flask test client and
  prove route mutation work does not run.
- Use a bounded test stream to prove upload reads stop at the upload limit plus
  one byte.
- Retain valid-request regression cases.

Done when:

- The 1 GiB root budget and every derived limit are documented in one
  authoritative place, and in user-facing documentation in a "Limits" section.
- Oversized requests fail before image parsing or storage.
- Full Python checks pass.

## Ticket 3: Enforce one decoded-image budget

Finding: SR-05

Goal: reject images whose width, height, or total pixel count exceeds the
decoded-image policy derived from the 1 GiB root budget before full raster
decoding.

Public behavior:

- Import, edit, metadata, mask, and clean-export operations reject an image over
  the shared 256 MiB decoded-image or 67,108,864-pixel budget.
- Rejection is actionable and leaves no partial or modified gallery file.
- Supported images within the budget retain their current behavior.

Test boundary:

- Begin with an import case whose compact encoded form declares dimensions over
  the budget and prove rejection occurs before `Image.load()`.
- Cover each remaining application-owned decode entry point against the same
  policy.
- Preserve representative valid images at and below the boundary.

Done when:

- Every application-owned Pillow decode uses the same policy.
- The configured model dimensions remain supported.
- Full Python checks pass.

Depends on: Ticket 2 establishes the transport limit; this ticket bounds the
decoded representation.

## Ticket 4: Restrict outbound image destinations

Finding: SR-01

Goal: prevent browser-directed imports from reaching non-public destinations
and constrain provider-result downloads to the selected provider's documented
domain family.

Public behavior:

- Existing public HTTP and HTTPS image imports continue to work.
- IPv4 and IPv6 loopback, private, link-local, multicast, unspecified, and
  reserved destinations are rejected before connection.
- Hostnames with any unsafe resolved address fail closed.
- Every redirect target is resolved and checked before connection.
- Redirect loops and excessive redirects fail with an actionable import error.
- Provider-result downloads require HTTPS and accept only these host families:
  - Replicate: `replicate.delivery` and `*.replicate.delivery`.
  - fal.ai: `*.fal.media`.
  - Wiro: `*.wiro.ai`.
- Provider wildcard matching requires a dot-delimited subdomain; lookalike
  suffixes such as `evilfal.media` and `evilwiro.ai` are rejected.
- A provider-result redirect outside that provider's host family is rejected.

Test boundary:

- Use deterministic resolver and HTTP test doubles; tests perform no real
  network calls.
- Cover literal addresses, hostnames, mixed DNS answers, safe-to-unsafe
  redirects, and a valid public redirect chain.
- Cover each provider's documented output host, a valid subdomain, the domain
  apex where it is not listed, lookalike suffixes, and cross-provider redirects.
- Prove the HTTP client never receives a rejected destination.

Done when:

- User imports and provider-result downloads use explicit policies appropriate
  to their separate interfaces, with shared unsafe-address enforcement.
- Existing timeout, content-type, and byte limits remain effective.
- Full Python checks pass.

## Ticket 5: Keep one predictable clean export per image

Finding: SR-04

Goal: bound clean-export storage to one reusable file per source image rather
than creating a new file for every download.

Public behavior:

- A clean export is stored under the temporary directory as
  `<source-stem>-clean<source-extension>`.
- A current clean export is reused; a missing or stale export is regenerated.
- Regeneration writes a unique regular file in the same temporary directory and
  atomically replaces an existing regular export, so concurrent downloads never
  observe a partial image.
- An observed directory or symbolic link at the predictable destination is
  rejected. The atomic replacement remains the security boundary: it never
  follows a raced-in destination symlink, and a raced-in directory makes the
  replacement fail.
- Repeated downloads of one source retain at most one clean export.
- Moving a source image to trash removes its corresponding clean export.
- Startup cleanup removes clean exports and interrupted-publication leftovers.
- Clean exports never enter gallery listings or alter stored images.

Test boundary:

- Assert the predictable name for every supported source extension.
- Repeat a download and prove the same current export is reused without growing
  retained file count.
- Change the source and prove the clean export is replaced atomically.
- Exercise concurrent generation and prove no response observes partial bytes.
- Place a directory and a symbolic link at the predictable destination and
  prove neither its contents nor the symlink target is modified.
- Replace the destination between validation and publication and prove the
  publication never follows that entry outside the temporary directory.
- Move the source to trash and prove its clean export is removed.
- Preserve metadata-stripping and gallery-integrity assertions.

Done when:

- Clean-export storage is bounded by source images rather than request count.
- Cache invalidation follows source replacement and deletion.
- Publication and cleanup behave correctly on supported operating systems.
- Full Python checks pass.

## Ticket 6: Allocate gallery filenames locally

Finding: SR-06

Goal: prevent provider identifiers from selecting or overwriting gallery
pathnames.

Public behavior:

- Generated images use the convention
  `<trusted-model-alias>-<local-request-uuid>-<sequence><validated-extension>`.
- All images returned by one provider prediction share the existing local
  request UUID; a new identifier is not allocated for each result.
- The sequence is a two-digit, one-based counter (`01` through `16`).
- The generated name is a basename whose parent is exactly the configured
  gallery output directory.
- The model alias comes from the local registry, the request UUID is allocated
  by imagegen before provider dispatch, and the extension comes from the
  validated response content type.
- Provider identifiers remain available in embedded metadata and generation
  history but do not determine the local basename.
- Repeated, malformed, or adversarial provider identifiers produce safe,
  distinct gallery paths.
- Publishing a completed image cannot overwrite an existing file.
- Failed publication leaves no completed or partial gallery image.

Test boundary:

- Return multiple images for one request and prove their basenames share one
  model-and-request prefix with distinct consecutive counters.
- Run a second request and prove it receives a different prefix.
- Return the same provider identifier for multiple results and prove the first
  image remains unchanged.
- Exercise provider identifiers containing path separators, traversal syntax,
  absolute paths, and shell metacharacters and prove none affect the local name.
- Exercise an existing-path collision and prove it cannot be overwritten.
- Verify provider identifiers remain observable in metadata and history.

Done when:

- All provider adapters satisfy the same server-owned basename contract.
- Existing gallery, metadata, and generation-history behavior remains intact.
- Full Python checks pass.

## Ticket 7: Bound provider output persistence

Finding: SR-07

Goal: constrain every provider response with one global output-count limit and
one global 64 MiB per-file download limit.

Public behavior:

- One global `16`-image limit applies to Replicate, fal.ai, and Wiro; there are
  no provider- or model-specific persistence limits.
- The current registry's largest declared provider/model maximum is 15; 16 also
  serves as the conservative ceiling when a provider publishes no maximum.
- The normalized provider output list is checked before any result URL is
  downloaded. More than 16 results rejects the whole response and fetches none.
- Responses containing 1 through 16 results proceed only when each image is at
  most 64 MiB (`64 * 1024 * 1024` bytes).
- Count or download failure removes partial files and records an actionable,
  credential-safe generation error.

Test boundary:

- Return 17 URLs and prove none are fetched.
- Return exactly 16 individually valid results and prove they are accepted.
- Fail a later download and prove already-persisted results from that response
  are cleaned up and the error is recorded.
- Cover successful multi-output responses for each provider adapter without
  real network calls.

Done when:

- One shared constant enforces the 16-image persistence boundary before
  downloads in every provider path.
- Count, 64 MiB per-file resource, cleanup, and diagnostic behavior are tested.
- Full Python checks pass.

Depends on: Ticket 6 defines safe publication and cleanup behavior used by
multi-output persistence.

## Epic Completion

- All seven tickets are committed independently in order.
- `uv run pytest` and `uv run ruff check src tests` pass after every ticket.
- `npm run js:check` is required only if browser JavaScript changes.
- Tests make no live provider, Immich, DNS, or arbitrary network calls.
- A follow-up security review verifies the original seven findings against the
  completed changes.

Deferred hardening for Immich response sizes and provider diagnostic sizes is
not part of these tickets. Add it only when deployment evidence establishes the
need.
