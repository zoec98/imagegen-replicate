import { csrfJsonRequest, requestJson } from "./api.js";
import { createElement } from "./dom.js";

export function setupTrash(root = document, services = {}) {
  const {
    csrfToken,
    refreshGallery = async () => {},
    showMessage = () => {},
  } = services;
  const toggle = root.querySelector(".trashcan-toggle");
  const count = root.querySelector(".trashcan-count");
  const overlay = root.querySelector(".trash-overlay");
  const closeButton = overlay?.querySelector(".trash-close");
  const emptyButton = overlay?.querySelector(".trash-empty");
  const gallery = overlay?.querySelector(".trash-gallery");
  const emptyState = overlay?.querySelector(".trash-empty-state");

  function setCount(value) {
    if (!count) {
      return;
    }
    const parsed = Number.parseInt(value, 10);
    count.textContent = String(Number.isFinite(parsed) ? Math.max(parsed, 0) : 0);
  }

  function render(images) {
    if (!gallery || !emptyState) {
      return;
    }
    gallery.replaceChildren();
    if (!Array.isArray(images) || images.length === 0) {
      emptyState.hidden = false;
      return;
    }
    emptyState.hidden = true;
    images.forEach((image) => gallery.append(trashFigure(image)));
  }

  async function refresh() {
    const url = toggle?.dataset.apiTrashUrl;
    if (!url) {
      return;
    }
    const data = await requestJson(url, {
      fallbackMessage: "Trash refresh failed.",
    });
    setCount(data.trash_count);
    render(data.images);
  }

  function open() {
    if (!overlay) {
      return;
    }
    overlay.hidden = false;
    closeButton?.focus();
    refresh().catch((error) => {
      showMessage(error.message || "Trash refresh failed.", "error");
    });
  }

  function close() {
    if (!overlay) {
      return;
    }
    overlay.hidden = true;
  }

  function isOpen() {
    return Boolean(overlay && !overlay.hidden);
  }

  async function restore(figure) {
    const restoreUrl = figure?.dataset.restoreUrl;
    const filename = figure?.dataset.filename || "image";
    if (!restoreUrl) {
      showMessage("This trash image cannot be restored.", "error");
      return;
    }
    const data = await csrfJsonRequest(
      restoreUrl,
      {},
      {
        csrfToken,
        fallbackMessage: `Could not restore ${filename}.`,
      },
    );
    if (Object.prototype.hasOwnProperty.call(data, "trash_count")) {
      setCount(data.trash_count);
    }
    await refreshGallery();
    await refresh();
    showMessage(`${data.filename || filename} restored.`, "success");
  }

  async function empty() {
    const url = toggle?.dataset.apiEmptyTrashUrl;
    if (!url) {
      showMessage("Empty trash URL is unavailable.", "error");
      return;
    }
    const data = await csrfJsonRequest(
      url,
      {},
      {
        csrfToken,
        fallbackMessage: "Trash could not be emptied.",
      },
    );
    if (Object.prototype.hasOwnProperty.call(data, "trash_count")) {
      setCount(data.trash_count);
    }
    await refresh();
    const deleted = Array.isArray(data.deleted) ? data.deleted.length : 0;
    showMessage(
      deleted === 1 ? "1 trash image deleted." : `${deleted} trash images deleted.`,
      "success",
    );
  }

  toggle?.addEventListener("click", open);
  closeButton?.addEventListener("click", close);
  emptyButton?.addEventListener("click", () => {
    emptyButton.disabled = true;
    empty()
      .catch((error) => {
        showMessage(error.message || "Trash could not be emptied.", "error");
      })
      .finally(() => {
        emptyButton.disabled = false;
      });
  });
  overlay?.addEventListener("click", (event) => {
    if (event.target === overlay) {
      close();
    }
  });
  gallery?.addEventListener("click", (event) => {
    const restoreButton = event.target.closest(".trash-restore");
    if (!restoreButton) {
      return;
    }
    restoreButton.disabled = true;
    restore(restoreButton.closest(".trash-item")).catch((error) => {
      restoreButton.disabled = false;
      showMessage(error.message || "Trash image could not be restored.", "error");
    });
  });

  return {
    close,
    isOpen,
    refresh,
    setCount,
  };
}

function trashFigure(image) {
  const figure = createElement("figure", {
    className: "gallery-item image-card trash-item",
    dataset: {
      filename: image.filename || "",
      restoreUrl: image.restore_url,
    },
  });
  const link = createImageMedia({
    alt: image.filename || "Trash image",
    href: image.url || "#",
    src: image.url || "",
  });
  const caption = createElement("figcaption", { className: "image-card-ribbon" });
  const actions = createElement("div", {
    attributes: { "aria-label": "Trash image actions" },
    className: "gallery-actions",
  });
  const infoWrap = createInfoAction({
    label: `Trash image information for ${image.filename || "image"}`,
    tooltipText: image.filename || "Image",
  });
  const restoreButton = createElement("button", {
    attributes: { "aria-label": `Restore ${image.filename || "image"}` },
    className: "trash-restore",
    disabled: !image.restore_url,
    textContent: "Restore",
    type: "button",
  });
  actions.append(infoWrap, restoreButton);
  caption.append(actions);
  figure.append(link, caption);
  return figure;
}

function createImageMedia({ alt, className = "", href = null, src }) {
  const media = createElement(href ? "a" : "span", {
    className: ["image-card-media", className].filter(Boolean).join(" "),
  });
  if (href) {
    media.href = href;
    media.target = "_blank";
    media.rel = "noopener";
  }

  const img = createElement("img", { alt, src });
  media.append(img);
  return media;
}

function createInfoAction({ label, tooltipText }) {
  const infoButton = createElement("button", {
    attributes: {
      "aria-label": label,
      title: label,
    },
    className: "gallery-action gallery-info",
    type: "button",
  });
  const tooltipLine = createElement("span", {
    className: "tooltip-line",
    textContent: tooltipText,
  });
  const tooltip = createElement("span", {
    attributes: { role: "tooltip" },
    children: [tooltipLine],
    className: "image-info-tooltip image-info-selectable",
  });
  return createElement("span", {
    children: [infoButton, tooltip],
    className: "image-info-wrap",
  });
}
