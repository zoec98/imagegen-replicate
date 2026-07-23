# Gallery Image Ratio User Stories

## Summary

Show the natural image aspect ratio in the gallery info tooltip alongside the
existing pixel dimensions.

Current tooltip example:

```text
540 x 720
```

Target tooltip example:

```text
540 x 720 (3:4)
```

## User Story

As a user inspecting generated or imported gallery images, I want the info
tooltip to show both pixel dimensions and the reduced aspect ratio so I can
quickly compare image shape without doing the math myself.

## Acceptance Criteria

- The info tooltip continues to use the loaded image's natural dimensions.
- A valid image with natural dimensions displays dimensions as:
  `WIDTH x HEIGHT (RATIO_WIDTH:RATIO_HEIGHT)`.
- The ratio is computed by reducing `naturalWidth:naturalHeight` with the
  greatest common divisor.
- Square images display as `1:1`.
- Common exact dimensions reduce naturally, for example:
  - `540 x 720 (3:4)`
  - `720 x 540 (4:3)`
  - `1024 x 1024 (1:1)`
  - `1920 x 1080 (16:9)`
  - `3072 x 4096 (3:4)`
- If dimensions are unavailable, the tooltip keeps the existing unavailable
  message and does not show a ratio.

## Implementation Notes

- Implement the ratio in the existing browser-side tooltip code.
- Prefer a small `gcd(width, height)` helper and an `imageRatio(width, height)`
  helper.
- Do not snap near-miss dimensions to common ratios in the first pass. Use the
  exact reduced ratio only.
- Keep the implementation deterministic and independent of model metadata.

## Test Notes

- Add focused JavaScript-unit coverage only if/when the project has browser-side
  test tooling.
- Until then, keep this covered by manual UI verification and avoid adding a new
  JavaScript toolchain for this small feature.

## Open Questions

- Should future versions snap near-miss dimensions, such as `1023 x 1536`, to a
  common ratio when within a small tolerance? Recommendation: defer unless real
  generated images produce confusing ratios often.
