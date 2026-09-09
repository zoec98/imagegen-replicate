import { describe, expect, it, vi } from "vitest";

import { setupGallery } from "../../src/imagegen/frontend/gallery.js";
import { setupImmichImport } from "../../src/imagegen/frontend/immich-import.js";
import { setupTrash } from "../../src/imagegen/frontend/trash.js";

function jsonResponse(data) {
  return new Response(JSON.stringify(data), {
    headers: { "Content-Type": "application/json" },
  });
}

function expectSharedCard(card, alt) {
  expect(card.tagName).toBe("FIGURE");
  expect(card.classList).toContain("image-card");
  expect(card.querySelector(".image-card-media img").alt).toBe(alt);
  expect(card.querySelector(".image-card-ribbon")).not.toBeNull();
  expect(card.querySelector(".gallery-actions")).not.toBeNull();
  expect(card.querySelector(".gallery-info").title).toContain("information");
  expect(card.querySelector('[role="tooltip"] .tooltip-line')).not.toBeNull();
}

describe("shared image card contract", () => {
  it("renders the main gallery card with safe linked media", () => {
    document.body.innerHTML =
      '<form class="prompt-form"></form><div class="gallery"></div>';
    setupGallery(document).render([
      {
        filename: "main.png",
        url: "/images/main.png",
      },
    ]);

    const card = document.querySelector(".gallery-item");
    expectSharedCard(card, "main.png");
    const media = card.querySelector(".image-card-media");
    expect(media.target).toBe("_blank");
    expect(media.rel).toBe("noopener");
  });

  it("renders the trash card with the same information action", async () => {
    document.body.innerHTML = `
      <button class="trashcan-toggle" data-api-trash-url="/api/trash"></button>
      <span class="trashcan-count"></span>
      <div class="trash-overlay"><div class="trash-gallery"></div><div class="trash-empty-state"></div></div>
    `;
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse({
          images: [
            { filename: "trash.png", url: "/trash/trash.png", restore_url: "/restore" },
          ],
          trash_count: 1,
        }),
      ),
    );
    setupTrash(document).refresh();

    await vi.waitFor(() =>
      expect(document.querySelector(".trash-item")).not.toBeNull(),
    );
    const card = document.querySelector(".trash-item");
    expectSharedCard(card, "trash.png");
    expect(
      card.querySelector(".image-info-wrap").classList.contains("image-info-open"),
    ).toBe(false);
    card.querySelector(".gallery-info").click();
    expect(
      card.querySelector(".image-info-wrap").classList.contains("image-info-open"),
    ).toBe(true);
  });

  it("renders the Immich card with the same information action", async () => {
    document.body.innerHTML = `
      <div class="upload-overlay" data-api-immich-assets-url="/api/immich/assets">
        <div class="upload-immich-browser">
          <button class="upload-immich-prev" type="button"></button>
          <button class="upload-immich-next" type="button"></button>
          <span class="upload-immich-page"></span>
          <div class="upload-immich-empty" hidden></div>
          <div class="upload-immich-gallery"></div>
        </div>
      </div>
    `;
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse({
          assets: [
            { asset_id: "asset-1", label: "Immich image", thumbnail_url: "/thumb" },
          ],
          page: 1,
        }),
      ),
    );
    setupImmichImport(document).open();

    await vi.waitFor(() =>
      expect(document.querySelector(".upload-immich-item")).not.toBeNull(),
    );
    const card = document.querySelector(".upload-immich-item");
    expectSharedCard(card, "Immich image");
    card.querySelector(".gallery-info").click();
    expect(
      card.querySelector(".image-info-wrap").classList.contains("image-info-open"),
    ).toBe(true);
  });
});
