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
        data-blur-save-url="/api/images/source.png/blur"
        data-crop-save-url="/api/images/source.png/crop"
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
        <input class="mask-editor-brush-size" type="range" value="50">
        <label class="mask-editor-falloff-tool">
          <input class="mask-editor-brush-falloff" type="range" value="0">
        </label>
        <span class="mask-editor-brush-size-value"></span>
        <span class="mask-editor-brush-falloff-value"></span>
      </div>
      <div class="mask-editor-control-group mask-editor-crop-controls" hidden>
        <button class="mask-editor-crop" type="button" disabled></button>
      </div>
      <div class="mask-editor-control-group mask-editor-blur-controls" hidden>
        <input class="mask-editor-blur-radius" type="range" min="0" max="50" step="0.1" value="20">
        <span class="mask-editor-blur-radius-value"></span>
        <button class="mask-editor-blur" type="button" disabled></button>
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
    fillRect: vi.fn(),
    putImageData: vi.fn(),
    strokeRect: vi.fn(),
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

function largeFakeImageFactory() {
  const image = {
    naturalHeight: 50,
    naturalWidth: 100,
    onerror: null,
    onload: null,
    set src(value) {
      this.currentSrc = value;
      queueMicrotask(() => this.onload?.());
    },
  };
  return image;
}

function setCanvasRect(canvas, rect) {
  vi.spyOn(canvas, "getBoundingClientRect").mockReturnValue(rect);
}

function pointer(type, x, y) {
  const EventConstructor = window.PointerEvent || window.Event;
  const event = new EventConstructor(type, { bubbles: true });
  Object.defineProperties(event, {
    clientX: { value: x },
    clientY: { value: y },
    pointerId: { value: 1 },
  });
  return event;
}

function selectMaskMode() {
  const operation = document.querySelector(".mask-editor-operation");
  operation.value = "mask";
  operation.dispatchEvent(new Event("change", { bubbles: true }));
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
    expect(overlay.dataset.blurSaveUrl).toBe("/api/images/source.png/blur");
    expect(overlay.dataset.cropSaveUrl).toBe("/api/images/source.png/crop");
    expect(overlay.dataset.maskSaveUrl).toBe("/api/images/source-mask.png");
    expect(document.querySelector("#mask-editor-title").textContent).toBe("source.png");
    expect(document.querySelector(".mask-editor-operation").value).toBe("crop");

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
    expect(document.querySelector(".mask-editor-brush-controls").hidden).toBe(true);
    expect(document.querySelector(".mask-editor-crop-controls").hidden).toBe(false);
    expect(document.querySelector(".mask-editor-blur-controls").hidden).toBe(true);

    operation.value = "mask";
    operation.dispatchEvent(new Event("change", { bubbles: true }));

    expect(overlay.hidden).toBe(false);
    expect(document.querySelector(".mask-editor-brush-controls").hidden).toBe(false);
    expect(document.querySelector(".mask-editor-crop-controls").hidden).toBe(true);
    expect(document.querySelector(".mask-editor-blur-controls").hidden).toBe(true);

    operation.value = "blur";
    operation.dispatchEvent(new Event("change", { bubbles: true }));

    expect(document.querySelector(".mask-editor-brush-controls").hidden).toBe(false);
    expect(document.querySelector(".mask-editor-falloff-tool").hidden).toBe(true);
    expect(document.querySelector(".mask-editor-crop-controls").hidden).toBe(true);
    expect(document.querySelector(".mask-editor-blur-controls").hidden).toBe(false);
    expect(document.querySelector(".mask-editor-blur-radius").min).toBe("0");
    expect(document.querySelector(".mask-editor-blur-radius").max).toBe("50");
    expect(document.querySelector(".mask-editor-blur-radius").step).toBe("0.1");

    operation.value = "mask";
    operation.dispatchEvent(new Event("change", { bubbles: true }));

    expect(document.querySelector(".mask-editor-brush-controls").hidden).toBe(false);
    expect(document.querySelector(".mask-editor-falloff-tool").hidden).toBe(false);
    expect(document.querySelector(".mask-editor-crop-controls").hidden).toBe(true);
    expect(document.querySelector(".mask-editor-blur-controls").hidden).toBe(true);
  });

  it("resets transient editor mode when closed", () => {
    renderMaskWorkspace();
    stubCanvas();
    const editor = setupMaskEditor(document, { imageFactory: fakeImageFactory });
    editor.open(document.querySelector(".gallery-item"));
    const operation = document.querySelector(".mask-editor-operation");
    operation.value = "mask";
    operation.dispatchEvent(new Event("change", { bubbles: true }));

    document.querySelector(".mask-editor-close").click();
    editor.open(document.querySelector(".gallery-item"));

    expect(operation.value).toBe("crop");
    expect(document.querySelector(".mask-editor-brush-controls").hidden).toBe(true);
    expect(document.querySelector(".mask-editor-crop-controls").hidden).toBe(false);
    expect(document.querySelector(".mask-editor-blur-controls").hidden).toBe(true);
  });

  it("draws a crop rectangle and enables crop when the selection is valid", async () => {
    renderMaskWorkspace();
    const context = stubCanvas();
    const editor = setupMaskEditor(document, {
      imageFactory: largeFakeImageFactory,
    });
    editor.open(document.querySelector(".gallery-item"));
    await new Promise((resolve) => queueMicrotask(resolve));
    const canvas = document.querySelector(".mask-editor-mask");
    setCanvasRect(canvas, {
      height: 100,
      left: 20,
      top: 10,
      width: 200,
    });

    canvas.dispatchEvent(pointer("pointerdown", 40, 30));
    canvas.dispatchEvent(pointer("pointermove", 100, 80));
    canvas.dispatchEvent(pointer("pointerup", 100, 80));

    expect(document.querySelector(".mask-editor-crop").disabled).toBe(false);
    expect(context.fillRect).toHaveBeenCalledWith(0, 0, 100, 50);
    expect(context.clearRect).toHaveBeenCalledWith(10, 10, 30, 25);
    expect(context.strokeRect).toHaveBeenCalledWith(10, 10, 30, 25);
  });

  it("keeps crop disabled for too-small selections", async () => {
    renderMaskWorkspace();
    stubCanvas();
    const editor = setupMaskEditor(document, {
      imageFactory: largeFakeImageFactory,
    });
    editor.open(document.querySelector(".gallery-item"));
    await new Promise((resolve) => queueMicrotask(resolve));
    const canvas = document.querySelector(".mask-editor-mask");
    setCanvasRect(canvas, {
      height: 100,
      left: 0,
      top: 0,
      width: 200,
    });

    canvas.dispatchEvent(pointer("pointerdown", 0, 0));
    canvas.dispatchEvent(pointer("pointermove", 10, 10));
    canvas.dispatchEvent(pointer("pointerup", 10, 10));

    expect(document.querySelector(".mask-editor-crop").disabled).toBe(true);
  });

  it("submits natural image crop coordinates and refreshes the gallery", async () => {
    renderMaskWorkspace();
    stubCanvas();
    const refreshGallery = vi.fn().mockResolvedValue(undefined);
    const showMessage = vi.fn();
    const fetcher = vi.fn().mockResolvedValue(
      jsonResponse({
        image: { filename: "source-crop-123.png" },
      }),
    );
    vi.stubGlobal("fetch", fetcher);
    const editor = setupMaskEditor(document, {
      csrfToken: "csrf-token",
      imageFactory: largeFakeImageFactory,
      refreshGallery,
      showMessage,
    });
    editor.open(document.querySelector(".gallery-item"));
    await new Promise((resolve) => queueMicrotask(resolve));
    const canvas = document.querySelector(".mask-editor-mask");
    setCanvasRect(canvas, {
      height: 100,
      left: 20,
      top: 10,
      width: 200,
    });
    canvas.dispatchEvent(pointer("pointerdown", 40, 30));
    canvas.dispatchEvent(pointer("pointermove", 100, 80));
    canvas.dispatchEvent(pointer("pointerup", 100, 80));

    document.querySelector(".mask-editor-crop").click();

    await vi.waitFor(() => {
      expect(fetcher).toHaveBeenCalledWith(
        "/api/images/source.png/crop",
        expect.objectContaining({ method: "POST" }),
      );
    });
    expect(JSON.parse(fetcher.mock.calls[0][1].body)).toEqual({
      rectangle: { height: 25, width: 30, x: 10, y: 10 },
    });
    await vi.waitFor(() => {
      expect(refreshGallery).toHaveBeenCalled();
      expect(showMessage).toHaveBeenCalledWith(
        "source-crop-123.png cropped.",
        "success",
      );
      expect(document.querySelector(".mask-editor-overlay").hidden).toBe(true);
    });
  });

  it("reports crop errors and leaves the editor open", async () => {
    renderMaskWorkspace();
    stubCanvas();
    const showMessage = vi.fn();
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          jsonResponse({ error: "Crop rectangle is invalid." }, { status: 400 }),
        ),
    );
    const editor = setupMaskEditor(document, {
      csrfToken: "csrf-token",
      imageFactory: largeFakeImageFactory,
      showMessage,
    });
    editor.open(document.querySelector(".gallery-item"));
    await new Promise((resolve) => queueMicrotask(resolve));
    const canvas = document.querySelector(".mask-editor-mask");
    setCanvasRect(canvas, {
      height: 100,
      left: 0,
      top: 0,
      width: 200,
    });
    canvas.dispatchEvent(pointer("pointerdown", 20, 20));
    canvas.dispatchEvent(pointer("pointermove", 80, 80));
    canvas.dispatchEvent(pointer("pointerup", 80, 80));

    document.querySelector(".mask-editor-crop").click();

    await vi.waitFor(() => {
      expect(showMessage).toHaveBeenCalledWith("Crop rectangle is invalid.", "error");
    });
    expect(document.querySelector(".mask-editor-overlay").hidden).toBe(false);
    expect(document.querySelector(".mask-editor-crop").disabled).toBe(false);
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

  it("uses image editor defaults", () => {
    renderMaskWorkspace();
    stubCanvas();
    setupMaskEditor(document, { imageFactory: fakeImageFactory });

    expect(document.querySelector(".mask-editor-brush-size").value).toBe("50");
    expect(document.querySelector(".mask-editor-brush-size-value").textContent).toBe(
      "50 px",
    );
    expect(document.querySelector(".mask-editor-brush-falloff").value).toBe("0");
    expect(document.querySelector(".mask-editor-brush-falloff-value").textContent).toBe(
      "0%",
    );
    expect(document.querySelector(".mask-editor-blur-radius").value).toBe("20");
    expect(document.querySelector(".mask-editor-blur-radius-value").textContent).toBe(
      "20 px",
    );
  });

  it("updates blur radius labels", () => {
    renderMaskWorkspace();
    stubCanvas();
    setupMaskEditor(document, { imageFactory: fakeImageFactory });

    const radius = document.querySelector(".mask-editor-blur-radius");
    radius.value = "7.5";
    radius.dispatchEvent(new Event("input", { bubbles: true }));

    expect(document.querySelector(".mask-editor-blur-radius-value").textContent).toBe(
      "7.5 px",
    );
  });

  it("submits painted blur mask and radius without brush size", async () => {
    renderMaskWorkspace();
    stubCanvas();
    const refreshGallery = vi.fn().mockResolvedValue(undefined);
    const showMessage = vi.fn();
    const fetcher = vi.fn().mockResolvedValue(
      jsonResponse({
        image: { filename: "source-blur-123.png" },
      }),
    );
    vi.stubGlobal("fetch", fetcher);
    const editor = setupMaskEditor(document, {
      csrfToken: "csrf-token",
      imageFactory: largeFakeImageFactory,
      refreshGallery,
      showMessage,
    });
    editor.open(document.querySelector(".gallery-item"));
    await new Promise((resolve) => queueMicrotask(resolve));
    const operation = document.querySelector(".mask-editor-operation");
    operation.value = "blur";
    operation.dispatchEvent(new Event("change", { bubbles: true }));
    const radius = document.querySelector(".mask-editor-blur-radius");
    radius.value = "7.5";
    radius.dispatchEvent(new Event("input", { bubbles: true }));
    const canvas = document.querySelector(".mask-editor-mask");
    setCanvasRect(canvas, {
      height: 100,
      left: 0,
      top: 0,
      width: 200,
    });

    canvas.dispatchEvent(pointer("pointerdown", 20, 20));
    canvas.dispatchEvent(pointer("pointermove", 80, 80));
    canvas.dispatchEvent(pointer("pointerup", 80, 80));
    expect(document.querySelector(".mask-editor-blur").disabled).toBe(false);
    document.querySelector(".mask-editor-blur").click();

    await vi.waitFor(() => {
      expect(fetcher).toHaveBeenCalledWith(
        "/api/images/source.png/blur",
        expect.objectContaining({ method: "POST" }),
      );
    });
    expect(JSON.parse(fetcher.mock.calls[0][1].body)).toEqual({
      blur_radius: 7.5,
      mask_png: "data:image/png;base64,mask",
    });
    await vi.waitFor(() => {
      expect(refreshGallery).toHaveBeenCalled();
      expect(showMessage).toHaveBeenCalledWith(
        "source-blur-123.png blurred.",
        "success",
      );
      expect(document.querySelector(".mask-editor-overlay").hidden).toBe(true);
    });
  });

  it("reports blur errors and leaves the editor open", async () => {
    renderMaskWorkspace();
    stubCanvas();
    const showMessage = vi.fn();
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          jsonResponse(
            { error: "Mask must mark at least one pixel." },
            { status: 400 },
          ),
        ),
    );
    const editor = setupMaskEditor(document, {
      csrfToken: "csrf-token",
      imageFactory: largeFakeImageFactory,
      showMessage,
    });
    editor.open(document.querySelector(".gallery-item"));
    await new Promise((resolve) => queueMicrotask(resolve));
    const operation = document.querySelector(".mask-editor-operation");
    operation.value = "blur";
    operation.dispatchEvent(new Event("change", { bubbles: true }));
    const canvas = document.querySelector(".mask-editor-mask");
    setCanvasRect(canvas, {
      height: 100,
      left: 0,
      top: 0,
      width: 200,
    });
    canvas.dispatchEvent(pointer("pointerdown", 20, 20));
    canvas.dispatchEvent(pointer("pointermove", 80, 80));
    canvas.dispatchEvent(pointer("pointerup", 80, 80));

    document.querySelector(".mask-editor-blur").click();

    await vi.waitFor(() => {
      expect(showMessage).toHaveBeenCalledWith(
        "Mask must mark at least one pixel.",
        "error",
      );
    });
    expect(document.querySelector(".mask-editor-overlay").hidden).toBe(false);
    expect(document.querySelector(".mask-editor-blur").disabled).toBe(false);
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
    selectMaskMode();
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
    selectMaskMode();
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
    selectMaskMode();
    await new Promise((resolve) => queueMicrotask(resolve));

    document.querySelector(".mask-editor-save").click();

    await vi.waitFor(() => {
      expect(showMessage).toHaveBeenCalledWith("Mask could not be saved.", "error");
    });
    expect(document.querySelector(".mask-editor-overlay").hidden).toBe(false);
    expect(document.querySelector(".mask-editor-save").disabled).toBe(false);
  });
});
