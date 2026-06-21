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
      "Add an image URL, choose one image file, or drop one image file.",
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
});
