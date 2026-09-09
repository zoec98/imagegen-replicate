import { describe, expect, it } from "vitest";

import {
  cropRectangle,
  invertMask,
  isValidCropSelection,
  paintMask,
  pointerPosition,
} from "../../src/imagegen/frontend/image-editor-operations.js";

describe("image editor operations", () => {
  it("maps displayed pointer coordinates to natural pixels", () => {
    expect(
      pointerPosition(
        { clientX: 40, clientY: 30 },
        { left: 20, top: 10, width: 200, height: 100 },
        100,
        50,
      ),
    ).toEqual({ scale: 0.5, x: 10, y: 10 });
  });

  it("normalizes and clamps crop rectangles", () => {
    expect(cropRectangle({ x: 90, y: 40 }, { x: -10, y: 80 }, 100, 50)).toEqual({
      height: 10,
      width: 90,
      x: 0,
      y: 40,
    });
    expect(isValidCropSelection({ width: 10, height: 10 })).toBe(true);
    expect(isValidCropSelection({ width: 9, height: 20 })).toBe(false);
  });

  it("paints clamped mask intensity with falloff", () => {
    const mask = new Float32Array(9);

    paintMask(mask, 3, 3, { scale: 1, x: 1, y: 1 }, 2, 0.5);

    expect(mask[4]).toBe(1);
    expect(mask[0]).toBe(0);
    expect(mask[1]).toBeGreaterThan(0);
    expect(mask[1]).toBeLessThan(1);
  });

  it("inverts and clamps mask values", () => {
    const mask = new Float32Array([-1, 0.25, 2]);

    invertMask(mask);

    expect([...mask]).toEqual([1, 0.75, 0]);
  });
});
