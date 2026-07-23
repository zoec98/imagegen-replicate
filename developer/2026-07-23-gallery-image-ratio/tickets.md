# Gallery Image Ratio Tickets

These tickets implement the gallery tooltip ratio story in TDD order. The
near-miss snapping clarification supersedes the open question in
`user-stories.md`: dimensions within 2% tolerance of a common ratio should show
the common ratio instead of the exact reduced ratio.

## Ticket 1: Locate Tooltip Interface and Test Surface

**Goal:** Identify the public browser-side behavior that formats gallery image
dimensions for the info tooltip.

**Acceptance criteria:**

- Find the existing tooltip code that reads loaded image `naturalWidth` and
  `naturalHeight`.
- Identify whether JavaScript unit tests already exist for that behavior.
- Do not add a new JavaScript test toolchain for this feature.
- Record the chosen test or manual-verification path in the implementation
  notes or final change summary.

**TDD notes:**

- If a JavaScript test surface already exists, use it through the existing
  public module/interface.
- If no test surface exists, keep this ticket to discovery and use the later
  manual verification ticket instead of creating tooling.

**Implementation notes:**

- Tooltip formatting lives in `src/imagegen/frontend/metadata.js` through
  `setupMetadata(...).refreshTooltip(figure)`, which updates
  `.image-info-tooltip` from the gallery figure and its contained `img`.
- Existing JavaScript unit coverage lives in `tests/js/metadata.test.js`; use
  the public `setupMetadata` interface and assert visible `.tooltip-line` text.
- No new JavaScript test toolchain is needed.

## Ticket 2: Exact Ratio Formatting Tracer Bullet

**Goal:** Add the smallest behavior slice that displays an exact reduced ratio
beside available natural dimensions.

**Acceptance criteria:**

- A loaded image with natural dimensions displays:
  `WIDTH x HEIGHT (RATIO_WIDTH:RATIO_HEIGHT)`.
- `540 x 720` displays as `540 x 720 (3:4)`.
- The tooltip continues to use the image element's natural dimensions, not
  metadata or rendered CSS dimensions.
- If dimensions are unavailable, the existing unavailable message remains
  unchanged and no ratio is shown.

**TDD notes:**

- RED: Add one behavior test for the visible tooltip text if an existing JS test
  surface is available.
- GREEN: Add minimal browser-side ratio formatting using exact GCD reduction.
- If no JS test surface exists, make the implementation slice small enough to
  verify manually in the browser.

## Ticket 3: Cover Core Exact-Ratio Cases

**Goal:** Broaden exact-ratio behavior after the tracer bullet passes.

**Acceptance criteria:**

- `720 x 540` displays as `720 x 540 (4:3)`.
- `1024 x 1024` displays as `1024 x 1024 (1:1)`.
- `1920 x 1080` displays as `1920 x 1080 (16:9)`.
- `3072 x 4096` displays as `3072 x 4096 (3:4)`.
- Zero, missing, or non-finite dimensions do not produce a ratio.

**TDD notes:**

- Add one case at a time and keep each RED-GREEN cycle vertical.
- Prefer behavior-oriented tests against the formatter or tooltip interface
  already exposed by the frontend module.

## Ticket 4: Snap Near-Miss Dimensions to Common Ratios

**Goal:** Display familiar aspect ratios when natural dimensions are within 2%
of a common ratio.

**Acceptance criteria:**

- Define a small deterministic common-ratio list that includes at least:
  `1:1`, `3:4`, `4:3`, `16:9`, `9:16`, `2:3`, and `3:2`.
- If `naturalWidth / naturalHeight` is within 2% relative tolerance of a common
  ratio, display the common ratio.
- Near-miss examples display as:
  - `1023 x 1536 (2:3)`
  - `1536 x 1023 (3:2)`
  - `1910 x 1080 (16:9)`
- Exact common ratios still display the same common ratio.
- Ratios outside the 2% tolerance continue to display the exact reduced ratio.

**TDD notes:**

- RED: Add one near-miss case, such as `1023 x 1536`.
- GREEN: Introduce common-ratio matching behind the same ratio helper.
- Then add outside-tolerance coverage before broadening the common-ratio table.

## Ticket 5: Deterministic Tie-Breaking and Helper Boundaries

**Goal:** Keep ratio selection predictable and the tooltip code easy to read.

**Acceptance criteria:**

- Ratio calculation lives behind small helpers, preferably `gcd(width, height)`
  and `imageRatio(width, height)`.
- Common-ratio snapping is deterministic when more than one common ratio could
  match.
- Exact reduced ratio remains the fallback for valid dimensions outside common
  ratio tolerance.
- The implementation stays independent of provider/model metadata.

**TDD notes:**

- Add a focused behavior case only if tie-breaking or fallback behavior is not
  already covered by previous tests.
- Refactor only while tests are green.

## Ticket 6: Wire, Build, and Verify the Gallery Tooltip

**Goal:** Confirm the browser gallery shows the new tooltip text with generated
static assets updated as needed.

**Acceptance criteria:**

- The gallery info tooltip displays dimensions and snapped/reduced ratios in
  the running app.
- Unavailable dimensions still show the existing unavailable message.
- If browser JavaScript changed, regenerate committed static assets with the
  existing build command.
- Run required project checks:
  - `uv run pytest`
  - `uv run ruff check src tests`
  - `npm run js:check`
- If JavaScript formatting is affected, run `npm run js:format`.

**TDD notes:**

- Use manual UI verification for the full tooltip behavior if no existing JS
  unit test surface is present.
- Keep the final verification notes explicit about test coverage versus manual
  coverage.
