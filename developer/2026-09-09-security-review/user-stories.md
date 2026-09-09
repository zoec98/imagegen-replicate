# Security Hardening User Stories

Date: 2026-09-09
Source review: [security-review.md](security-review.md)

## Epic Goal

As an imagegen operator, I want browser, provider, and image inputs to remain
within explicit network, memory, filesystem, and execution boundaries so that a
local or trusted-household-LAN deployment stays safe without adding accounts or
changing its simple operating model.

The supported deployment remains localhost or a trusted household LAN. Public
internet exposure and application user isolation are outside this epic.

## Story 1: Safe outbound image imports

As an operator, I want URL imports to connect only to permitted public
destinations so that imported URLs cannot reach services on the imagegen host or
private network.

Acceptance criteria:

- Unsafe IPv4 and IPv6 destination classes are rejected before connection.
- Every redirect is checked against the same destination policy.
- Mixed safe and unsafe DNS answers fail closed.
- Permitted public image imports continue to work.

## Story 2: Early request-size enforcement

As an operator, I want oversized HTTP requests rejected before they are fully
materialized so that a reachable client cannot exhaust application memory or
temporary storage with one request.

Acceptance criteria:

- Oversized JSON and multipart requests receive HTTP 413 before image parsing or
  mutation work.
- Multipart reads stop at the route limit plus one byte.
- Valid uploads, edits, and masks retain their existing behavior.

## Story 3: Safe web-launcher modes

As an operator, I want debug mode restricted to loopback so that development
diagnostics are not exposed to other LAN clients.

Acceptance criteria:

- `imagegen-web --dev --secure-network` fails before starting Flask.
- `imagegen-web --dev` binds only to loopback.
- Non-debug trusted-LAN mode remains available.

## Story 4: Bounded clean-export lifetime

As an operator, I want clean-download temporary files removed after each
response so that repeated downloads cannot steadily fill the data filesystem.

Acceptance criteria:

- Successful and failed responses leave no per-request clean export behind.
- Startup cleanup remains available for interrupted processes.
- Clean exports never appear in the gallery or mutate stored images.

## Story 5: Bounded decoded images

As an operator, I want every application-owned image decode to enforce the same
dimension and pixel budget so that compressed images cannot allocate an
unbounded raster.

Acceptance criteria:

- Oversized dimensions or pixel counts are rejected before full decoding.
- Import, edit, metadata, mask, and export paths use the same policy.
- Rejection leaves no partial gallery image.

## Story 6: Server-owned gallery filenames

As an operator, I want gallery filenames allocated by imagegen so that provider
identifiers cannot overwrite existing images.

Acceptance criteria:

- Repeated or adversarial provider identifiers produce distinct local paths.
- Publication cannot overwrite an existing gallery file.
- Provider identifiers remain recorded in metadata and generation history.

## Story 7: Bounded provider results

As an operator, I want provider output collections constrained by the validated
request and a hard resource budget so that a faulty provider cannot monopolize
the worker or data filesystem.

Acceptance criteria:

- Extra provider URLs are rejected before download.
- Each generation has a cumulative byte and work budget.
- Budget failure removes partial files and retains an actionable, credential-safe
  error.
- Replicate, fal.ai, and Wiro share the same persistence invariant.

## Documentation Story

As a developer, I want the security boundary and contributor instructions to
describe the installed web and CLI entry points so that future changes preserve
the actual trust model.

Acceptance criteria:

- Documentation no longer refers to removed `scripts/run-dev*` launchers.
- `imagegen-web`, `imagegen`, Wiro credentials, and multipart CSRF protection
  are documented.
- The CLI is classified as a trusted local-shell boundary rather than a remote
  interface.

## Deferred Hardening

Immich response-size limits and provider diagnostic-size limits remain
defense-in-depth work. They should become implementation stories only if
deployment evidence establishes a realistic lower-trust source or the validated
findings are complete.
