import { describe, expect, it } from "vitest";

import { setupSourceImages } from "../../src/imagegen/frontend/source-images.js";

function renderSourceWorkspace() {
  document.body.innerHTML = `
    <form class="prompt-form">
      <button class="edit-toggle" type="button"></button>
      <span class="source-counter"></span>
      <button class="source-clear" type="button"></button>
      <span class="source-selection-status"></span>
    </form>
    <div class="gallery">
      <figure class="gallery-item" data-filename="first.png">
        <button class="source-select" type="button"></button>
      </figure>
      <figure class="gallery-item" data-filename="second.png">
        <button class="source-select" type="button"></button>
      </figure>
    </div>
  `;
}

describe("setupSourceImages", () => {
  it("selects and clears source images while edit mode is enabled", () => {
    renderSourceWorkspace();
    const sourceImages = setupSourceImages(document, {
      getModel: () => ({ edit_capable: true, source_image_max: 2 }),
    });

    sourceImages.setEditMode(true);
    sourceImages.toggle("first.png");

    expect(sourceImages.selected()).toEqual(["first.png"]);
    expect(document.querySelector(".source-counter").textContent).toBe("1 selected");
    expect(document.querySelector("[data-filename='first.png']").className).toContain(
      "gallery-item-selected",
    );

    sourceImages.clear();

    expect(sourceImages.selected()).toEqual([]);
    expect(document.querySelector(".source-counter").textContent).toBe("0 selected");
  });

  it("enforces the selected model source image limit", () => {
    renderSourceWorkspace();
    const sourceImages = setupSourceImages(document, {
      getModel: () => ({ edit_capable: true, source_image_max: 1 }),
    });

    sourceImages.setEditMode(true);
    sourceImages.toggle("first.png");
    sourceImages.toggle("second.png");

    expect(sourceImages.selected()).toEqual(["first.png"]);
    expect(document.querySelector(".source-selection-status").textContent).toBe(
      "Select up to 1 source image.",
    );
    expect(
      document
        .querySelector(".source-selection-status")
        .classList.contains("source-selection-status-error"),
    ).toBe(true);
  });

  it("returns edit-mode payload state", () => {
    renderSourceWorkspace();
    const sourceImages = setupSourceImages(document, {
      getModel: () => ({ edit_capable: true, source_image_max: 2 }),
    });

    sourceImages.setEditMode(true);
    sourceImages.toggle("first.png");

    expect(sourceImages.payload()).toEqual({
      editMode: true,
      sourceImages: ["first.png"],
    });
  });

  it("resets selection when provider or non-editable model changes", () => {
    renderSourceWorkspace();
    let model = { edit_capable: true, source_image_max: 2 };
    const sourceImages = setupSourceImages(document, {
      getModel: () => model,
    });
    sourceImages.setEditMode(true);
    sourceImages.toggle("first.png");

    sourceImages.resetForProviderChange();

    expect(sourceImages.payload()).toEqual({ editMode: false, sourceImages: [] });

    sourceImages.setEditMode(true);
    sourceImages.toggle("first.png");
    model = { edit_capable: false };
    sourceImages.resetForModelChange();

    expect(sourceImages.payload()).toEqual({ editMode: false, sourceImages: [] });
    expect(document.querySelector(".edit-toggle").disabled).toBe(true);
  });
});
