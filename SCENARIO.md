# User Scenarios

## Gallery Mask Creation

### Story: Open a mask editor from a gallery image

As a user editing an existing image, I want to open a mask editor from a gallery image so that I can define which part of that image should be affected by a selective edit model.

Acceptance criteria:

- Each eligible gallery image exposes a mask action.
- Activating the mask action opens an editor overlay above the current workspace without navigating away.
- The overlay shows the selected image at a usable size.
- The overlay can be dismissed without saving a mask.

### Story: Paint a visible edit mask

As a user creating a selective edit mask, I want to paint over the image with a visible red glow so that I can see the region that will be edited while still seeing the underlying image.

Acceptance criteria:

- Painting adds a semi-transparent red overlay over the selected image.
- Unpainted areas remain visually unchanged.
- The editor provides a brush size control.
- The editor provides a brush falloff control that changes how quickly the brush fades from an opaque center to its edge.
- The editor provides an invert mask button that swaps masked and unmasked areas.
- Brush controls update subsequent strokes without losing the existing mask.

### Story: Save a provider-ready layer mask

As a user preparing a selective image edit request, I want the painted overlay saved as a black-and-white 8-bit PNG layer mask so that it can be submitted to image edit models that accept masks.

Acceptance criteria:

- Saving creates a PNG file in the gallery image directory.
- The mask filename is the source image stem followed by `-mask.png`.
- The saved mask has the same pixel dimensions as the selected source image.
- The saved mask is black where no mask was painted and white where the mask is fully painted.
- Soft brush falloff is represented as grayscale values between black and white when supported by the saved mask.
- Saving does not mutate the original gallery image.

## Open Questions

- Which JavaScript paint implementation should the mask editor use?
  - Native Canvas 2D: Smallest dependency footprint and likely enough for a focused mask editor. It would require implementing brush input, undo if needed, mask export, and touch handling ourselves. References: [getImageData](https://developer.mozilla.org/en-US/docs/Web/API/CanvasRenderingContext2D/getImageData), [toBlob](https://developer.mozilla.org/en-US/docs/Web/API/HTMLCanvasElement/toBlob), [globalCompositeOperation](https://developer.mozilla.org/en-US/docs/Web/API/CanvasRenderingContext2D/globalCompositeOperation).
  - Konva: A focused canvas interaction library with layers, desktop/mobile input support, and free drawing examples. It may reduce event and layer handling complexity without becoming a full image editor. References: [Konva overview](https://konvajs.org/docs/overview.html), [free drawing demo](https://new.konvajs.org/docs/sandbox/Free_Drawing.html).
  - Fabric.js: A mature Canvas abstraction with built-in free drawing mode and object serialization. It may be useful if mask editing grows into richer object-based editing, but it is more abstraction than the first mask workflow needs. References: [free drawing demo](https://fabricjs.com/demos/free-drawing/), [core concepts](https://fabricjs.com/docs/core-concepts/).
  - Pintura: A polished commercial image editor SDK with image processing hooks and mask examples. It is likely overkill unless the app needs a full image editor surface. References: [Pintura image editor](https://pqina.nl/pintura/docs/v8/api/image-editor/), [mask image example](https://pqina.nl/pintura/docs/v8/examples/mask-image/).
-> Decision: We are trying Native Canvas 2D to keep the dependencies small.
  - We might need to make followup decisions for dependency management and JS "compile"/"compaction"; if that is the case, ask, do not infer, and make suggestions.
