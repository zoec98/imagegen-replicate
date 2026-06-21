import { describe, expect, test } from "vitest";

import {
  createElement,
  createSvgIcon,
  readJsonScript,
  setBooleanAttribute,
} from "../../src/imagegen/frontend/dom.js";

describe("readJsonScript", () => {
  test("reads JSON embedded in the workspace", () => {
    document.body.innerHTML = `
      <script id="model-registry-data" type="application/json">
        [{"alias":"seedream45"}]
      </script>
    `;

    expect(readJsonScript("#model-registry-data")).toEqual([{ alias: "seedream45" }]);
  });

  test("uses fallback data when script JSON is unavailable", () => {
    document.body.innerHTML = `
      <script id="model-registry-data" type="application/json">not json</script>
    `;

    expect(readJsonScript("#model-registry-data", { fallback: [] })).toEqual([]);
    expect(readJsonScript("#missing", { fallback: ["fallback"] })).toEqual([
      "fallback",
    ]);
  });
});

test("createElement builds visible DOM with attributes and children", () => {
  const icon = createElement("span", {
    className: "icon",
    textContent: "!",
  });

  const button = createElement("button", {
    attributes: { "aria-label": "Import image" },
    children: [icon],
    className: "gallery-action",
    dataset: { filename: "sample.png" },
    type: "button",
  });

  expect(button.outerHTML).toBe(
    '<button class="gallery-action" type="button" aria-label="Import image" data-filename="sample.png"><span class="icon">!</span></button>',
  );
});

test("createSvgIcon creates a hidden SVG path icon", () => {
  const icon = createSvgIcon("M1 1h2v2z");

  expect(icon.namespaceURI).toBe("http://www.w3.org/2000/svg");
  expect(icon.getAttribute("aria-hidden")).toBe("true");
  expect(icon.getAttribute("viewBox")).toBe("0 0 24 24");
  expect(icon.querySelector("path").getAttribute("d")).toBe("M1 1h2v2z");
});

test("setBooleanAttribute writes browser boolean string attributes", () => {
  const button = document.createElement("button");

  setBooleanAttribute(button, "aria-pressed", true);
  expect(button.getAttribute("aria-pressed")).toBe("true");

  setBooleanAttribute(button, "aria-pressed", false);
  expect(button.getAttribute("aria-pressed")).toBe("false");

  expect(() => setBooleanAttribute(null, "aria-pressed", true)).not.toThrow();
});
