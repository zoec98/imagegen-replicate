import { describe, expect, it, vi } from "vitest";

import { setupImageUpload } from "../../src/imagegen/frontend/image-upload.js";

function jsonResponse(data, init = {}) {
  return new Response(JSON.stringify(data), {
    headers: { "Content-Type": "application/json" },
    status: init.status || 200,
  });
}

function renderUploadWorkspace() {
  document.body.innerHTML = `
    <form class="prompt-form">
      <button class="upload-toggle" type="button"></button>
    </form>
    <div
      class="upload-overlay"
      data-api-import-url="/api/images/import-url"
      data-api-upload-url="/api/images/import-upload"
      hidden
    >
      <button class="upload-close" type="button"></button>
      <input class="upload-url">
      <button class="upload-url-load" type="button"></button>
      <div class="upload-drop-target"></div>
      <input class="upload-file-input" type="file">
      <button class="upload-file-choose" type="button"></button>
      <div class="upload-status"></div>
      <div class="upload-immich-browser">
        <button class="upload-immich-prev" type="button"></button>
        <button class="upload-immich-next" type="button"></button>
        <span class="upload-immich-page"></span>
        <div class="upload-immich-empty" hidden></div>
        <div class="upload-immich-gallery"></div>
      </div>
    </div>
  `;
}

describe("setupImageUpload", () => {
  it("is safe when upload markup is absent", () => {
    document.body.innerHTML = `<form class="prompt-form"></form>`;

    const upload = setupImageUpload(document);

    expect(() => upload.open()).not.toThrow();
    expect(() => upload.close()).not.toThrow();
    expect(upload.isOpen()).toBe(false);
  });

  it("opens and closes the upload overlay", () => {
    renderUploadWorkspace();
    const upload = setupImageUpload(document);
    const overlay = document.querySelector(".upload-overlay");

    document.querySelector(".upload-toggle").click();

    expect(upload.isOpen()).toBe(true);
    expect(overlay.hidden).toBe(false);
    expect(document.querySelector(".upload-status").textContent).toBe(
      "Add an image URL, choose image files, or drop image files.",
    );

    document.querySelector(".upload-close").click();

    expect(upload.isOpen()).toBe(false);
    expect(overlay.hidden).toBe(true);
  });

  it("imports an image URL and refreshes the gallery", async () => {
    renderUploadWorkspace();
    const refreshGallery = vi.fn().mockResolvedValue(undefined);
    const fetcher = vi.fn().mockResolvedValue(
      jsonResponse({
        image: { filename: "imported.png" },
      }),
    );
    vi.stubGlobal("fetch", fetcher);
    setupImageUpload(document, {
      csrfToken: "csrf-token",
      refreshGallery,
    });
    document.querySelector(".upload-toggle").click();
    document.querySelector(".upload-url").value = "https://example.test/image.png";

    document.querySelector(".upload-url-load").click();

    await vi.waitFor(() => {
      expect(fetcher).toHaveBeenCalledWith(
        "/api/images/import-url",
        expect.objectContaining({ method: "POST" }),
      );
    });
    expect(JSON.parse(fetcher.mock.calls[0][1].body)).toEqual({
      url: "https://example.test/image.png",
    });
    await vi.waitFor(() => {
      expect(refreshGallery).toHaveBeenCalled();
      expect(document.querySelector(".upload-status").textContent).toBe(
        "imported.png imported.",
      );
      expect(document.querySelector(".upload-url").value).toBe("");
    });
  });

  it("uploads every file selected in one chooser interaction", async () => {
    renderUploadWorkspace();
    const refreshGallery = vi.fn().mockResolvedValue(undefined);
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ image: { filename: "first.png" } }))
      .mockResolvedValueOnce(jsonResponse({ image: { filename: "second.png" } }));
    vi.stubGlobal("fetch", fetcher);
    setupImageUpload(document, { csrfToken: "csrf-token", refreshGallery });

    const first = new File(["first"], "first.png", { type: "image/png" });
    const second = new File(["second"], "second.png", { type: "image/png" });
    const fileInput = document.querySelector(".upload-file-input");
    Object.defineProperty(fileInput, "files", {
      configurable: true,
      value: [first, second],
    });

    fileInput.dispatchEvent(new Event("change"));

    await vi.waitFor(() => expect(fetcher).toHaveBeenCalledTimes(2));
    expect(fetcher.mock.calls).toHaveLength(2);
    expect(fetcher.mock.calls[0][0]).toBe("/api/images/import-upload");
    expect(fetcher.mock.calls[1][0]).toBe("/api/images/import-upload");
    await vi.waitFor(() => expect(refreshGallery).toHaveBeenCalledTimes(1));
    expect(document.querySelector(".upload-status").textContent).toBe(
      "2 images uploaded.",
    );
  });

  it("continues a batch after one file fails", async () => {
    renderUploadWorkspace();
    const refreshGallery = vi.fn().mockResolvedValue(undefined);
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ image: { filename: "first.png" } }))
      .mockRejectedValueOnce(new Error("Unsupported image format."))
      .mockResolvedValueOnce(jsonResponse({ image: { filename: "third.png" } }));
    vi.stubGlobal("fetch", fetcher);
    setupImageUpload(document, { csrfToken: "csrf-token", refreshGallery });

    const files = [
      new File(["first"], "first.png", { type: "image/png" }),
      new File(["second"], "second.png", { type: "image/png" }),
      new File(["third"], "third.png", { type: "image/png" }),
    ];
    const fileInput = document.querySelector(".upload-file-input");
    Object.defineProperty(fileInput, "files", {
      configurable: true,
      value: files,
    });

    fileInput.dispatchEvent(new Event("change"));

    await vi.waitFor(() => expect(fetcher).toHaveBeenCalledTimes(3));
    await vi.waitFor(() => expect(refreshGallery).toHaveBeenCalledTimes(1));
    expect(document.querySelector(".upload-status").textContent).toContain(
      "second.png: Unsupported image format.",
    );
    expect(document.querySelector(".upload-file-choose").disabled).toBe(false);
  });

  it("uploads every file dropped in one interaction", async () => {
    renderUploadWorkspace();
    const refreshGallery = vi.fn().mockResolvedValue(undefined);
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ image: { filename: "first.png" } }))
      .mockResolvedValueOnce(jsonResponse({ image: { filename: "second.png" } }));
    vi.stubGlobal("fetch", fetcher);
    setupImageUpload(document, { csrfToken: "csrf-token", refreshGallery });

    const files = [
      new File(["first"], "first.png", { type: "image/png" }),
      new File(["second"], "second.png", { type: "image/png" }),
    ];
    const event = new Event("drop", { bubbles: true, cancelable: true });
    Object.defineProperty(event, "dataTransfer", { value: { files } });

    document.querySelector(".upload-drop-target").dispatchEvent(event);

    await vi.waitFor(() => expect(fetcher).toHaveBeenCalledTimes(2));
    await vi.waitFor(() => expect(refreshGallery).toHaveBeenCalledTimes(1));
    expect(document.querySelector(".upload-status").textContent).toBe(
      "2 images uploaded.",
    );
  });

  it("keeps valid files when a dropped file has a non-image MIME type", async () => {
    renderUploadWorkspace();
    const refreshGallery = vi.fn().mockResolvedValue(undefined);
    const fetcher = vi
      .fn()
      .mockResolvedValue(jsonResponse({ image: { filename: "valid.png" } }));
    vi.stubGlobal("fetch", fetcher);
    setupImageUpload(document, { csrfToken: "csrf-token", refreshGallery });

    const files = [
      new File(["valid"], "valid.png", { type: "image/png" }),
      new File(["invalid"], "notes.txt", { type: "text/plain" }),
    ];
    const event = new Event("drop", { bubbles: true, cancelable: true });
    Object.defineProperty(event, "dataTransfer", { value: { files } });

    document.querySelector(".upload-drop-target").dispatchEvent(event);

    await vi.waitFor(() => expect(fetcher).toHaveBeenCalledTimes(1));
    await vi.waitFor(() => expect(refreshGallery).toHaveBeenCalledTimes(1));
    expect(document.querySelector(".upload-status").textContent).toContain(
      "notes.txt (not an image)",
    );
  });

  it("keeps controls busy when the overlay closes during a batch", async () => {
    renderUploadWorkspace();
    const refreshGallery = vi.fn().mockResolvedValue(undefined);
    let resolveUpload;
    const uploadResponse = new Promise((resolve) => {
      resolveUpload = resolve;
    });
    const fetcher = vi.fn().mockReturnValue(uploadResponse);
    vi.stubGlobal("fetch", fetcher);
    setupImageUpload(document, { csrfToken: "csrf-token", refreshGallery });

    const fileInput = document.querySelector(".upload-file-input");
    Object.defineProperty(fileInput, "files", {
      configurable: true,
      value: [new File(["first"], "first.png", { type: "image/png" })],
    });
    fileInput.dispatchEvent(new Event("change"));
    await vi.waitFor(() => expect(fetcher).toHaveBeenCalledTimes(1));

    document.querySelector(".upload-close").click();
    document.querySelector(".upload-toggle").click();
    fileInput.dispatchEvent(new Event("change"));

    expect(document.querySelector(".upload-file-choose").disabled).toBe(true);
    expect(fetcher).toHaveBeenCalledTimes(1);

    resolveUpload(jsonResponse({ image: { filename: "first.png" } }));
    await vi.waitFor(() => expect(refreshGallery).toHaveBeenCalledTimes(1));
    expect(document.querySelector(".upload-file-choose").disabled).toBe(false);
  });
});
