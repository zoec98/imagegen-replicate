import { describe, expect, it, vi } from "vitest";

import { setupMetadata } from "../../src/imagegen/frontend/metadata.js";

function jsonResponse(data, init = {}) {
  return new Response(JSON.stringify(data), {
    headers: { "Content-Type": "application/json" },
    status: init.status || 200,
  });
}

function renderMetadataFigure() {
  document.body.innerHTML = `
    <figure class="gallery-item" data-filename="example.png" data-metadata-url="/api/images/example.png/metadata">
      <img alt="example.png" src="/images/example.png">
      <span class="image-info-tooltip"></span>
    </figure>
  `;
  return document.querySelector(".gallery-item");
}

describe("setupMetadata", () => {
  it("loads embedded metadata into the prompt workspace", async () => {
    const figure = renderMetadataFigure();
    const applyMetadata = vi.fn();
    const showMessage = vi.fn();
    globalThis.fetch = vi.fn().mockResolvedValue(
      jsonResponse({
        model_alias: "flux",
        parameters: { steps: 4 },
        prompt: "A small test image",
      }),
    );

    const metadata = setupMetadata(document, { applyMetadata, showMessage });
    await metadata.load(figure);

    expect(applyMetadata).toHaveBeenCalledWith({
      model_alias: "flux",
      parameters: { steps: 4 },
      prompt: "A small test image",
    });
    expect(showMessage).toHaveBeenCalledWith("Image metadata loaded.", "success");
  });

  it("surfaces metadata compatibility warnings", async () => {
    const figure = renderMetadataFigure();
    const applyMetadata = vi.fn();
    const showMessage = vi.fn();
    globalThis.fetch = vi.fn().mockResolvedValue(
      jsonResponse({
        model_alias: "flux",
        parameters: {},
        prompt: "Prompt",
        warnings: ["Source image missing."],
      }),
    );

    const metadata = setupMetadata(document, { applyMetadata, showMessage });
    await metadata.load(figure);

    expect(showMessage).toHaveBeenCalledWith(
      "Image metadata loaded. Source image missing.",
      "warning",
    );
  });

  it("reports metadata load errors to the caller", async () => {
    const figure = renderMetadataFigure();
    globalThis.fetch = vi
      .fn()
      .mockResolvedValue(jsonResponse({ error: "metadata missing" }, { status: 404 }));

    const metadata = setupMetadata(document);

    await expect(metadata.load(figure)).rejects.toThrow("metadata missing");
  });

  it("presents metadata in the image information tooltip", async () => {
    const figure = renderMetadataFigure();
    globalThis.fetch = vi.fn().mockResolvedValue(
      jsonResponse({
        model_alias: "flux",
        prompt: "A tooltip prompt",
      }),
    );
    const metadata = setupMetadata(document, {
      modelRegistry: [{ alias: "flux", display_name: "Flux Schnell" }],
    });

    metadata.refreshTooltip(figure);
    await vi.waitFor(() => {
      expect(
        [...figure.querySelectorAll(".tooltip-line")].map((line) => line.textContent),
      ).toEqual([
        "example.png",
        "Flux Schnell",
        "Dimensions unavailable",
        "A tooltip prompt",
      ]);
    });
  });

  it("shows a copy prompt button in the tooltip when prompt is available", async () => {
    const figure = renderMetadataFigure();
    const writeText = vi.fn().mockResolvedValue(undefined);
    globalThis.navigator = { clipboard: { writeText } };
    globalThis.fetch = vi.fn().mockResolvedValue(
      jsonResponse({
        model_alias: "flux",
        prompt: "A copyable prompt",
      }),
    );
    const metadata = setupMetadata(document);

    metadata.refreshTooltip(figure);
    await vi.waitFor(() => {
      expect(figure.querySelector(".tooltip-copy-prompt")).not.toBeNull();
    });

    const copyBtn = figure.querySelector(".tooltip-copy-prompt");
    copyBtn.click();
    expect(writeText).toHaveBeenCalledWith("A copyable prompt");
  });

  it("does not show a copy prompt button when prompt is unavailable", async () => {
    const figure = renderMetadataFigure();
    globalThis.fetch = vi.fn().mockResolvedValue(jsonResponse({ model_alias: "flux" }));
    const metadata = setupMetadata(document);

    metadata.refreshTooltip(figure);
    await vi.waitFor(() => {
      expect(
        [...figure.querySelectorAll(".tooltip-line")].some((el) =>
          el.textContent.includes("Prompt unavailable"),
        ),
      ).toBe(true);
    });

    expect(figure.querySelector(".tooltip-copy-prompt")).toBeNull();
  });
});
