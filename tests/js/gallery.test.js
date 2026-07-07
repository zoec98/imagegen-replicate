import { describe, expect, it, vi } from "vitest";

import { setupGallery } from "../../src/imagegen/frontend/gallery.js";
import { setupMetadata } from "../../src/imagegen/frontend/metadata.js";

function jsonResponse(data, init = {}) {
  return new Response(JSON.stringify(data), {
    headers: { "Content-Type": "application/json" },
    status: init.status || 200,
  });
}

function renderGalleryWorkspace() {
  document.body.innerHTML = `
    <form class="prompt-form" data-api-images-url="/api/images"></form>
    <div class="gallery"></div>
  `;
}

function imageFixture(overrides = {}) {
  return {
    blur_save_url: "/api/images/example.png/blur",
    clean_download_url: "/downloads/clean/example.png",
    content_type: "image/png",
    crop_save_url: "/api/images/example.png/crop",
    created_at: "2026-06-21T12:00:00Z",
    delete_url: "/api/images/example.png/delete",
    download_url: "/downloads/example.png",
    filename: "example.png",
    immich_upload_url: "/api/images/example.png/immich",
    mask_save_url: "/api/images/example.png/mask",
    mask_url: "/images/example.png/mask",
    metadata_url: "/api/images/example.png/metadata",
    url: "/images/example.png",
    ...overrides,
  };
}

describe("setupGallery", () => {
  it("renders gallery image cards with the expected user actions", () => {
    renderGalleryWorkspace();

    const gallery = setupGallery(document);
    gallery.render([imageFixture()]);

    const figure = document.querySelector(".gallery-item");
    expect(figure.dataset.filename).toBe("example.png");
    expect(figure.dataset.blurSaveUrl).toBe("/api/images/example.png/blur");
    expect(figure.dataset.cropSaveUrl).toBe("/api/images/example.png/crop");
    expect(figure.dataset.metadataUrl).toBe("/api/images/example.png/metadata");
    expect(figure.querySelector("img").getAttribute("src")).toBe("/images/example.png");
    expect(figure.querySelector(".source-select")).toBeTruthy();
    expect(figure.querySelector(".gallery-load").disabled).toBe(false);
    expect(figure.querySelector(".gallery-mask").getAttribute("aria-label")).toBe(
      "Edit image example.png",
    );
    expect(figure.querySelector(".gallery-mask").getAttribute("title")).toBe(
      "Edit image",
    );
    expect(figure.querySelector(".gallery-immich")).toBeTruthy();
    expect(figure.querySelector(".gallery-download").getAttribute("href")).toBe(
      "/downloads/example.png",
    );
  });

  it("refreshes the gallery from the image API and publishes the trash count", async () => {
    renderGalleryWorkspace();
    const setTrashCount = vi.fn();
    const updateSourceSelectionUi = vi.fn();
    globalThis.fetch = vi.fn().mockResolvedValue(
      jsonResponse({
        images: [imageFixture({ filename: "fresh.png", url: "/images/fresh.png" })],
        trash_count: 3,
      }),
    );

    const gallery = setupGallery(document, {
      setTrashCount,
      updateSourceSelectionUi,
    });
    await gallery.refresh();

    expect(globalThis.fetch).toHaveBeenCalledWith(
      "/api/images",
      expect.objectContaining({ credentials: "same-origin" }),
    );
    expect(document.querySelector(".gallery-item").dataset.filename).toBe("fresh.png");
    expect(setTrashCount).toHaveBeenCalledWith(3);
    expect(updateSourceSelectionUi).toHaveBeenCalled();
  });

  it("dispatches source image selection through the gallery click handler", () => {
    renderGalleryWorkspace();
    const toggleSourceImage = vi.fn();
    const gallery = setupGallery(document, { toggleSourceImage });
    gallery.render([imageFixture()]);

    document.querySelector(".source-select").click();

    expect(toggleSourceImage).toHaveBeenCalledWith("example.png");
  });

  it("dispatches metadata and mask actions through gallery hooks", () => {
    renderGalleryWorkspace();
    const metadata = {
      load: vi.fn().mockResolvedValue(undefined),
      refreshTooltip: vi.fn(),
    };
    const openMaskEditor = vi.fn();
    const gallery = setupGallery(document, { metadata, openMaskEditor });
    gallery.render([imageFixture()]);
    const figure = document.querySelector(".gallery-item");

    document.querySelector(".gallery-info").click();
    document.querySelector(".gallery-load").click();
    document.querySelector(".gallery-mask").click();

    expect(metadata.refreshTooltip).toHaveBeenCalledWith(figure);
    expect(metadata.load).toHaveBeenCalledWith(figure);
    expect(openMaskEditor).toHaveBeenCalledWith(figure);
  });

  it("opens image information with metadata on click", async () => {
    renderGalleryWorkspace();
    globalThis.fetch = vi.fn().mockResolvedValue(
      jsonResponse({
        model_alias: "flux",
        prompt: "A click-open prompt",
      }),
    );
    const metadata = setupMetadata(document, {
      modelRegistry: [{ alias: "flux", display_name: "Flux Schnell" }],
    });
    const gallery = setupGallery(document, { metadata });
    gallery.render([imageFixture()]);

    document.querySelector(".gallery-info").click();

    await vi.waitFor(() => {
      expect(
        document
          .querySelector(".image-info-wrap")
          .classList.contains("image-info-open"),
      ).toBe(true);
      expect(
        [...document.querySelectorAll(".tooltip-line")].map((line) => line.textContent),
      ).toEqual([
        "example.png",
        "Flux Schnell",
        "Dimensions unavailable",
        "A click-open prompt",
      ]);
    });
  });

  it("toggles image information active state on repeated clicks", () => {
    renderGalleryWorkspace();
    const gallery = setupGallery(document, {
      metadata: { refreshTooltip: vi.fn() },
    });
    gallery.render([imageFixture()]);
    const infoButton = document.querySelector(".gallery-info");
    const infoWrap = document.querySelector(".image-info-wrap");

    infoButton.click();

    expect(infoWrap.classList.contains("image-info-open")).toBe(true);
    expect(infoButton.classList.contains("gallery-info-active")).toBe(true);

    infoButton.click();

    expect(infoWrap.classList.contains("image-info-open")).toBe(false);
    expect(infoButton.classList.contains("gallery-info-active")).toBe(false);
  });

  it("keeps only one image information box open", () => {
    renderGalleryWorkspace();
    const gallery = setupGallery(document, {
      metadata: { refreshTooltip: vi.fn() },
    });
    gallery.render([
      imageFixture(),
      imageFixture({
        filename: "second.png",
        metadata_url: "/api/images/second.png/metadata",
        url: "/images/second.png",
      }),
    ]);
    const infoButtons = [...document.querySelectorAll(".gallery-info")];
    const infoWraps = [...document.querySelectorAll(".image-info-wrap")];

    infoButtons[0].click();
    infoButtons[1].click();

    expect(infoWraps[0].classList.contains("image-info-open")).toBe(false);
    expect(infoButtons[0].classList.contains("gallery-info-active")).toBe(false);
    expect(infoWraps[1].classList.contains("image-info-open")).toBe(true);
    expect(infoButtons[1].classList.contains("gallery-info-active")).toBe(true);
  });

  it("deletes an armed gallery image and refreshes the gallery", async () => {
    renderGalleryWorkspace();
    const showMessage = vi.fn();
    const removeSourceImage = vi.fn();
    globalThis.fetch = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ ok: true }))
      .mockResolvedValueOnce(jsonResponse({ images: [], trash_count: 1 }));
    const gallery = setupGallery(document, {
      csrfToken: "csrf-token",
      removeSourceImage,
      showMessage,
    });
    gallery.render([imageFixture()]);

    document.querySelector(".gallery-delete").click();
    document.querySelector(".gallery-delete").click();
    await vi.waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledWith(
        "/api/images/example.png/delete",
        expect.objectContaining({
          headers: expect.objectContaining({ "X-CSRF-Token": "csrf-token" }),
          method: "POST",
        }),
      );
    });

    await vi.waitFor(() => {
      expect(removeSourceImage).toHaveBeenCalledWith("example.png");
      expect(showMessage).toHaveBeenCalledWith("example.png deleted.", "success");
      expect(document.querySelector(".empty").textContent).toBe(
        "No generated images yet.",
      );
    });
  });

  it("uploads a gallery image to Immich", async () => {
    renderGalleryWorkspace();
    const showMessage = vi.fn();
    globalThis.fetch = vi
      .fn()
      .mockResolvedValue(jsonResponse({ status: "already_present" }));
    const gallery = setupGallery(document, {
      csrfToken: "csrf-token",
      showMessage,
    });
    gallery.render([imageFixture()]);

    document.querySelector(".gallery-immich").click();

    await vi.waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledWith(
        "/api/images/example.png/immich",
        expect.objectContaining({
          headers: expect.objectContaining({ "X-CSRF-Token": "csrf-token" }),
          method: "POST",
        }),
      );
    });
    await vi.waitFor(() => {
      expect(document.querySelector(".gallery-immich-uploaded")).toBeTruthy();
      expect(showMessage).toHaveBeenCalledWith(
        "example.png already present in Immich.",
        "success",
      );
    });
  });
});
