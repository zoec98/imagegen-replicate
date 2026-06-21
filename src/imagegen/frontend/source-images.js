import { setBooleanAttribute } from "./dom.js";

export function setupSourceImages(root = document, services = {}) {
  const { getModel = () => null } = services;
  const form = root.querySelector(".prompt-form");
  const editToggle = form?.querySelector(".edit-toggle");
  const sourceCounter = form?.querySelector(".source-counter");
  const sourceClear = form?.querySelector(".source-clear");
  const sourceSelectionStatus = form?.querySelector(".source-selection-status");
  const gallery = root.querySelector(".gallery");
  const selectedSourceImages = new Set();
  let editModeEnabled = false;

  function sourceImageLimit(model) {
    const limit = Number.parseInt(model?.source_image_max, 10);
    return Number.isFinite(limit) && limit > 0 ? limit : 0;
  }

  function sourceStatus(text, isError = false) {
    if (!sourceSelectionStatus) {
      return;
    }
    sourceSelectionStatus.textContent = text || "";
    sourceSelectionStatus.classList.toggle("source-selection-status-error", isError);
  }

  function clear() {
    selectedSourceImages.clear();
    update();
  }

  function remove(filename) {
    selectedSourceImages.delete(filename);
    update();
  }

  function setEditMode(enabled) {
    const model = getModel();
    editModeEnabled = Boolean(enabled && model?.edit_capable);
    if (!editModeEnabled) {
      selectedSourceImages.clear();
      sourceStatus("");
    }
    update();
  }

  function update() {
    const model = getModel();
    const editCapable = Boolean(model?.edit_capable);
    const count = selectedSourceImages.size;

    if (editToggle) {
      editToggle.disabled = !editCapable;
      setBooleanAttribute(editToggle, "aria-pressed", editModeEnabled);
      editToggle.classList.toggle("edit-toggle-active", editModeEnabled);
    }
    if (sourceCounter) {
      sourceCounter.textContent = `${count} selected`;
    }
    if (sourceClear) {
      sourceClear.hidden = count === 0;
      sourceClear.disabled = count === 0;
    }
    gallery?.classList.toggle("gallery-edit-active", editModeEnabled);
    gallery?.querySelectorAll(".gallery-item").forEach((figure) => {
      const filename = figure.dataset.filename;
      const selected = Boolean(filename && selectedSourceImages.has(filename));
      figure.classList.toggle("gallery-item-selected", selected);
      const button = figure.querySelector(".source-select");
      if (!button) {
        return;
      }
      button.disabled = !editModeEnabled;
      setBooleanAttribute(button, "aria-pressed", selected);
      button.setAttribute(
        "aria-label",
        `${selected ? "Deselect" : "Select"} ${filename || "image"} as source image`,
      );
    });
  }

  function toggle(filename) {
    if (!editModeEnabled || !filename) {
      return;
    }
    if (selectedSourceImages.has(filename)) {
      selectedSourceImages.delete(filename);
      sourceStatus("");
      update();
      return;
    }
    const limit = sourceImageLimit(getModel());
    if (limit > 0 && selectedSourceImages.size >= limit) {
      sourceStatus(
        `Select up to ${limit} source image${limit === 1 ? "" : "s"}.`,
        true,
      );
      return;
    }
    selectedSourceImages.add(filename);
    sourceStatus("");
    update();
  }

  function resetForProviderChange() {
    selectedSourceImages.clear();
    editModeEnabled = false;
    sourceStatus("");
    update();
  }

  function resetForModelChange() {
    selectedSourceImages.clear();
    if (!getModel()?.edit_capable) {
      editModeEnabled = false;
    }
    sourceStatus("");
    update();
  }

  function setFromMetadata(sourceImages, editMode) {
    selectedSourceImages.clear();
    sourceImages.forEach((filename) => selectedSourceImages.add(filename));
    editModeEnabled = Boolean(editMode || sourceImages.length > 0);
    update();
  }

  function selected() {
    return Array.from(selectedSourceImages);
  }

  function payload() {
    return {
      editMode: editModeEnabled,
      sourceImages: selected(),
    };
  }

  editToggle?.addEventListener("click", () => {
    setEditMode(!editModeEnabled);
  });
  sourceClear?.addEventListener("click", () => {
    clear();
    sourceStatus("");
  });

  return {
    clear,
    isEditMode: () => editModeEnabled,
    payload,
    remove,
    resetForModelChange,
    resetForProviderChange,
    selected,
    setEditMode,
    setFromMetadata,
    toggle,
    update,
  };
}
