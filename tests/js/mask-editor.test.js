import { describe, expect, it, vi } from "vitest";

import { setupMaskEditor } from "../../src/imagegen/frontend/mask-editor.js";

function jsonResponse(data, init = {}) {
  return new Response(JSON.stringify(data), {
    headers: { "Content-Type": "application/json" },
    status: init.status || 200,
  });
}

function renderMaskWorkspace() {
  document.body.innerHTML = `
    <div class="gallery">
      <figure
        class="gallery-item"
        data-filename="source.png"
        data-mask-url="/images/source-mask.png"
        data-mask-save-url="/api/images/source-mask.png"
      >
        <img alt="source.png" src="/images/source.png">
      </figure>
    </div>
    <div class="mask-editor-overlay" hidden>
      <div class="mask-editor-stage"></div>
      <div class="mask-editor-canvas-wrap"></div>
      <canvas class="mask-editor-source"></canvas>
      <canvas class="mask-editor-mask"></canvas>
      <select class="mask-editor-operation">
        <option value="crop">Crop</option>
        <option value="blur">Blur</option>
        <option value="mask">Mask</option>
      </select>
      <div class="mask-editor-control-group mask-editor-brush-controls">
        <input class="mask-editor-brush-size" type="range" value="48">
        <input class="mask-editor-brush-falloff" type="range" value="0.65">
        <span class="mask-editor-brush-size-value"></span>
        <span class="mask-editor-brush-falloff-value"></span>
      </div>
      <div class="mask-editor-control-group mask-editor-crop-controls" hidden>
        <button class="mask-editor-crop" type="button"></button>
      </div>
      <div class="mask-editor-control-group mask-editor-blur-controls" hidden>
        <input class="mask-editor-blur-radius" type="range" value="0">
      </div>
      <button class="mask-editor-invert" type="button"></button>
      <button class="mask-editor-save" type="button"></button>
      <h2 id="mask-editor-title">Image editor</h2>
      <button class="mask-editor-close" type="button" aria-label="Close image editor"></button>
    </div>
  `;
}

function stubCanvas() {
  const context = {
    clearRect: vi.fn(),
    createImageData: vi.fn((width, height) => ({
      data: new Uint8ClampedArray(width * height * 4),
    })),
    drawImage: vi.fn(),
    putImageData: vi.fn(),
  };
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(context);
  vi.spyOn(HTMLCanvasElement.prototype, "toDataURL").mockReturnValue(
    "data:image/png;base64,mask",
  );
  return context;
}

function fakeImageFactory() {
  const image = {
    naturalHeight: 2,
    naturalWidth: 2,
    onerror: null,
    onload: null,
    set src(value) {
      this.currentSrc = value;
      queueMicrotask(() => this.onload?.());
    },
  };
  return image;
}

describe("setupMaskEditor", () => {
  it("opens and closes the image editor for a gallery image", () => {
    renderMaskWorkspace();
    stubCanvas();
    const editor = setupMaskEditor(document, { imageFactory: fakeImageFactory });
    const overlay = document.querySelector(".mask-editor-overlay");

    editor.open(document.querySelector(".gallery-item"));

    expect(overlay.hidden).toBe(false);
    expect(overlay.dataset.filename).toBe("source.png");
    expect(overlay.dataset.maskSaveUrl).toBe("/api/images/source-mask.png");
    expect(document.querySelector("#mask-editor-title").textContent).toBe("source.png");
    expect(document.querySelector(".mask-editor-operation").value).toBe("mask");

    document.querySelector(".mask-editor-close").click();

    expect(overlay.hidden).toBe(true);
    expect(overlay.dataset.filename).toBeUndefined();
    expect(document.querySelector("#mask-editor-title").textContent).toBe(
      "Image editor",
    );
  });

  it("shows operation-specific controls without closing the editor", () => {
    renderMaskWorkspace();
    stubCanvas();
    const editor = setupMaskEditor(document, { imageFactory: fakeImageFactory });
    const overlay = document.querySelector(".mask-editor-overlay");
    editor.open(document.querySelector(".gallery-item"));

    const operation = document.querySelector(".mask-editor-operation");
    expect([...operation.options].map((option) => option.value)).toEqual([
      "crop",
      "blur",
      "mask",
    ]);
    expect(document.querySelector(".mask-editor-brush-controls").hidden).toBe(false);
    expect(document.querySelector(".mask-editor-crop-controls").hidden).toBe(true);
    expect(document.querySelector(".mask-editor-blur-controls").hidden).toBe(true);

    operation.value = "crop";
    operation.dispatchEvent(new Event("change", { bubbles: true }));

    expect(overlay.hidden).toBe(false);
    expect(document.querySelector(".mask-editor-brush-controls").hidden).toBe(true);
    expect(document.querySelector(".mask-editor-crop-controls").hidden).toBe(false);
    expect(document.querySelector(".mask-editor-blur-controls").hidden).toBe(true);

    operation.value = "blur";
    operation.dispatchEvent(new Event("change", { bubbles: true }));

    expect(document.querySelector(".mask-editor-brush-controls").hidden).toBe(false);
    expect(document.querySelector(".mask-editor-crop-controls").hidden).toBe(true);
    expect(document.querySelector(".mask-editor-blur-controls").hidden).toBe(false);

    operation.value = "mask";
    operation.dispatchEvent(new Event("change", { bubbles: true }));

    expect(document.querySelector(".mask-editor-brush-controls").hidden).toBe(false);
    expect(document.querySelector(".mask-editor-crop-controls").hidden).toBe(true);
    expect(document.querySelector(".mask-editor-blur-controls").hidden).toBe(true);
  });

  it("resets transient editor mode when closed", () => {
    renderMaskWorkspace();
    stubCanvas();
    const editor = setupMaskEditor(document, { imageFactory: fakeImageFactory });
    editor.open(document.querySelector(".gallery-item"));
    const operation = document.querySelector(".mask-editor-operation");
    operation.value = "crop";
    operation.dispatchEvent(new Event("change", { bubbles: true }));

    document.querySelector(".mask-editor-close").click();
    editor.open(document.querySelector(".gallery-item"));

    expect(operation.value).toBe("mask");
    expect(document.querySelector(".mask-editor-brush-controls").hidden).toBe(false);
    expect(document.querySelector(".mask-editor-crop-controls").hidden).toBe(true);
    expect(document.querySelector(".mask-editor-blur-controls").hidden).toBe(true);
  });

  it("updates brush control labels", () => {
    renderMaskWorkspace();
    stubCanvas();
    setupMaskEditor(document, { imageFactory: fakeImageFactory });

    const size = document.querySelector(".mask-editor-brush-size");
    const falloff = document.querySelector(".mask-editor-brush-falloff");
    size.value = "64";
    falloff.value = "25";
    size.dispatchEvent(new Event("input", { bubbles: true }));
    falloff.dispatchEvent(new Event("input", { bubbles: true }));

    expect(document.querySelector(".mask-editor-brush-size-value").textContent).toBe(
      "64 px",
    );
    expect(document.querySelector(".mask-editor-brush-falloff-value").textContent).toBe(
      "25%",
    );
  });

  it("saves mask data and refreshes the gallery", async () => {
    renderMaskWorkspace();
    stubCanvas();
    const refreshGallery = vi.fn().mockResolvedValue(undefined);
    const showMessage = vi.fn();
    const fetcher = vi.fn().mockResolvedValue(jsonResponse({ filename: "mask.png" }));
    vi.stubGlobal("fetch", fetcher);
    const editor = setupMaskEditor(document, {
      csrfToken: "csrf-token",
      imageFactory: fakeImageFactory,
      refreshGallery,
      showMessage,
    });
    editor.open(document.querySelector(".gallery-item"));
    await new Promise((resolve) => queueMicrotask(resolve));

    document.querySelector(".mask-editor-save").click();

    await vi.waitFor(() => {
      expect(fetcher).toHaveBeenCalledWith(
        "/api/images/source-mask.png",
        expect.objectContaining({ method: "POST" }),
      );
    });
    expect(JSON.parse(fetcher.mock.calls[0][1].body)).toEqual({
      mask_png: "data:image/png;base64,mask",
    });
    await vi.waitFor(() => {
      expect(refreshGallery).toHaveBeenCalled();
      expect(showMessage).toHaveBeenCalledWith("mask.png saved.", "success");
      expect(document.querySelector(".mask-editor-overlay").hidden).toBe(true);
    });
  });

  it("keeps the save button disabled while a save is pending", async () => {
    renderMaskWorkspace();
    stubCanvas();
    let resolveFetch;
    vi.stubGlobal(
      "fetch",
      vi.fn(
        () =>
          new Promise((resolve) => {
            resolveFetch = () => resolve(jsonResponse({ filename: "mask.png" }));
          }),
      ),
    );
    const editor = setupMaskEditor(document, {
      csrfToken: "csrf-token",
      imageFactory: fakeImageFactory,
    });
    editor.open(document.querySelector(".gallery-item"));
    await new Promise((resolve) => queueMicrotask(resolve));

    const save = document.querySelector(".mask-editor-save");
    save.click();

    expect(save.disabled).toBe(true);
    resolveFetch();
    await vi.waitFor(() => {
      expect(save.disabled).toBe(false);
    });
  });

  it("reports save errors and leaves the editor open", async () => {
    renderMaskWorkspace();
    stubCanvas();
    const showMessage = vi.fn();
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          jsonResponse({ error: "Mask could not be saved." }, { status: 500 }),
        ),
    );
    const editor = setupMaskEditor(document, {
      csrfToken: "csrf-token",
      imageFactory: fakeImageFactory,
      showMessage,
    });
    editor.open(document.querySelector(".gallery-item"));
    await new Promise((resolve) => queueMicrotask(resolve));

    document.querySelector(".mask-editor-save").click();

    await vi.waitFor(() => {
      expect(showMessage).toHaveBeenCalledWith("Mask could not be saved.", "error");
    });
    expect(document.querySelector(".mask-editor-overlay").hidden).toBe(false);
    expect(document.querySelector(".mask-editor-save").disabled).toBe(false);
  });
});
