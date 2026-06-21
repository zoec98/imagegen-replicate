import { csrfJsonRequest, requestJson } from "./api.js";
import { createElement, createSvgIcon, setBooleanAttribute } from "./dom.js";

export function setupGallery(root = document, services = {}) {
  const {
    csrfToken,
    metadata = {},
    openMaskEditor = () => {},
    removeSourceImage = () => {},
    setTrashCount = () => {},
    showMessage = () => {},
    toggleSourceImage = () => {},
    updateSourceSelectionUi = () => {},
  } = services;
  const form = root.querySelector(".prompt-form");
  const gallery = root.querySelector(".gallery");
  let armedDeleteButton = null;

  function disarmDelete() {
    if (!armedDeleteButton) {
      return;
    }
    armedDeleteButton.classList.remove("gallery-delete-armed");
    const filename = armedDeleteButton.closest(".gallery-item")?.dataset.filename;
    armedDeleteButton.setAttribute("aria-label", `Delete ${filename || "image"}`);
    armedDeleteButton.setAttribute("title", "Delete image");
    armedDeleteButton = null;
  }

  function armDelete(button) {
    if (!button) {
      return;
    }
    if (armedDeleteButton && armedDeleteButton !== button) {
      disarmDelete();
    }
    armedDeleteButton = button;
    const filename = button.closest(".gallery-item")?.dataset.filename || "image";
    button.classList.add("gallery-delete-armed");
    button.setAttribute("aria-label", `Confirm delete ${filename}`);
    button.setAttribute("title", "Confirm delete image");
    showMessage(`Click delete again to remove ${filename}.`, "info");
  }

  async function deleteImage(figure) {
    const deleteUrl = figure?.dataset.deleteUrl;
    const filename = figure?.dataset.filename || "image";
    if (!deleteUrl) {
      showMessage("This image cannot be deleted.", "error");
      return;
    }
    await csrfJsonRequest(
      deleteUrl,
      {},
      {
        csrfToken,
        fallbackMessage: `Could not delete ${filename}.`,
      },
    );
    removeSourceImage(filename);
    showMessage(`${filename} deleted.`, "success");
    await refresh();
  }

  async function uploadToImmich(figure) {
    const uploadUrl = figure?.dataset.immichUploadUrl;
    const filename = figure?.dataset.filename || "image";
    const button = figure?.querySelector(".gallery-immich");
    if (!uploadUrl) {
      showMessage("Immich upload is not configured for this image.", "error");
      return;
    }
    if (button) {
      button.disabled = true;
      button.classList.remove("gallery-immich-failed");
      button.classList.add("gallery-immich-uploading");
      button.setAttribute("aria-label", `Uploading ${filename} to Immich`);
      button.setAttribute("title", "Uploading to Immich");
    }
    let data;
    try {
      data = await csrfJsonRequest(
        uploadUrl,
        {},
        {
          csrfToken,
          fallbackMessage: `Could not upload ${filename} to Immich.`,
        },
      );
    } catch (error) {
      if (button) {
        button.disabled = false;
        button.classList.remove("gallery-immich-uploading");
        button.classList.add("gallery-immich-failed");
        button.setAttribute("aria-label", `Immich upload failed for ${filename}`);
        button.setAttribute("title", "Upload to Immich");
      }
      throw error;
    }
    if (button) {
      button.disabled = false;
      button.classList.remove("gallery-immich-uploading", "gallery-immich-failed");
      button.classList.add("gallery-immich-uploaded");
      button.setAttribute("aria-label", `${filename} uploaded to Immich`);
      button.setAttribute("title", "Uploaded to Immich");
    }
    const status = data.status === "already_present" ? "already present" : "uploaded";
    showMessage(`${filename} ${status} in Immich.`, "success");
  }

  async function refresh() {
    if (!gallery || !form?.dataset.apiImagesUrl) {
      return;
    }
    disarmDelete();
    const data = await requestJson(form.dataset.apiImagesUrl, {
      fallbackMessage: "Gallery refresh failed.",
    });
    if (Object.prototype.hasOwnProperty.call(data, "trash_count")) {
      setTrashCount(data.trash_count);
    }
    render(data.images);
    updateSourceSelectionUi();
  }

  function render(images) {
    if (!gallery) {
      return;
    }
    gallery.replaceChildren();
    if (!Array.isArray(images) || images.length === 0) {
      gallery.append(
        createElement("p", {
          className: "empty",
          textContent: "No generated images yet.",
        }),
      );
      return;
    }
    images.forEach((image) => gallery.append(imageFigure(image)));
  }

  gallery?.addEventListener("click", (event) => {
    const infoButton = event.target.closest(".gallery-info");
    if (infoButton) {
      disarmDelete();
      metadata.refreshTooltip?.(infoButton.closest(".gallery-item"));
      return;
    }
    const loadButton = event.target.closest(".gallery-load");
    if (loadButton) {
      disarmDelete();
      metadata.load?.(loadButton.closest(".gallery-item")).catch((error) => {
        showMessage(error.message || "Image metadata could not be loaded.", "error");
      });
      return;
    }
    if (event.target.closest(".gallery-download, .gallery-download-clean")) {
      disarmDelete();
      return;
    }
    const maskButton = event.target.closest(".gallery-mask");
    if (maskButton) {
      disarmDelete();
      openMaskEditor(maskButton.closest(".gallery-item"));
      return;
    }
    const deleteButton = event.target.closest(".gallery-delete");
    if (deleteButton) {
      const figure = deleteButton.closest(".gallery-item");
      if (armedDeleteButton !== deleteButton) {
        armDelete(deleteButton);
        return;
      }
      deleteImage(figure).catch((error) => {
        disarmDelete();
        showMessage(error.message || "Image could not be deleted.", "error");
      });
      return;
    }
    const immichButton = event.target.closest(".gallery-immich");
    if (immichButton) {
      disarmDelete();
      uploadToImmich(immichButton.closest(".gallery-item")).catch((error) => {
        showMessage(error.message || "Image could not be uploaded to Immich.", "error");
      });
      return;
    }
    const button = event.target.closest(".source-select");
    if (!button) {
      return;
    }
    disarmDelete();
    const figure = button.closest(".gallery-item");
    toggleSourceImage(figure?.dataset.filename || "");
  });

  gallery?.addEventListener("mouseover", (event) => {
    const infoButton = event.target.closest(".gallery-info");
    if (!infoButton) {
      return;
    }
    metadata.refreshTooltip?.(infoButton.closest(".gallery-item"));
  });
  gallery?.addEventListener("focusin", (event) => {
    const infoButton = event.target.closest(".gallery-info");
    if (!infoButton) {
      return;
    }
    metadata.refreshTooltip?.(infoButton.closest(".gallery-item"));
  });

  return {
    disarmDelete,
    refresh,
    render,
  };
}

function imageFigure(image) {
  const figure = createElement("figure", {
    className: "gallery-item image-card",
  });
  figure.dataset.filename = image.filename;
  setDatasetValue(figure, "cleanDownloadUrl", image.clean_download_url);
  setDatasetValue(figure, "contentType", image.content_type);
  setDatasetValue(figure, "createdAt", image.created_at);
  setDatasetValue(figure, "deleteUrl", image.delete_url);
  setDatasetValue(figure, "downloadUrl", image.download_url);
  setDatasetValue(figure, "immichUploadUrl", image.immich_upload_url);
  setDatasetValue(figure, "maskSaveUrl", image.mask_save_url);
  setDatasetValue(figure, "maskUrl", image.mask_url);
  setDatasetValue(figure, "metadataUrl", image.metadata_url);
  const link = createImageMedia({
    alt: image.filename,
    href: image.url,
    src: image.url,
  });
  const caption = createImageCardRibbon();
  const actions = createActionRibbon("Image actions");
  const infoWrap = createInfoAction({
    label: `Image information for ${image.filename}`,
    tooltipText: image.filename,
  });

  let immichButton = null;
  if (image.immich_upload_url) {
    immichButton = iconButton(
      "gallery-immich",
      `Upload ${image.filename} to Immich`,
      "M19.35 10.04A7.49 7.49 0 0 0 12 4 7.5 7.5 0 0 0 5.35 8.04 6 6 0 0 0 6 20h13a5 5 0 0 0 .35-9.96zM14 17h-4v-4H7l5-5 5 5h-3z",
      "Upload to Immich",
    );
  }

  const downloadLink = iconLink(
    "gallery-download",
    `Download ${image.filename}`,
    image.download_url,
    "M19.35 10.04A7.49 7.49 0 0 0 12 4 7.5 7.5 0 0 0 5.35 8.04 6 6 0 0 0 6 20h13a5 5 0 0 0 .35-9.96zM14 12h3l-5 5-5-5h3V8h4z",
    null,
    "Download with metadata",
  );
  const cleanDownloadLink = iconLink(
    "gallery-download-clean",
    `Download clean ${image.filename}`,
    image.clean_download_url,
    "M19.35 10.04A7.49 7.49 0 0 0 12 4 7.5 7.5 0 0 0 5.35 8.04 6 6 0 0 0 6 20h13a5 5 0 0 0 .35-9.96zM14 12h3l-5 5-5-5h3V8h4z",
    "M12 2l2.2 7.8L22 12l-7.8 2.2L12 22l-2.2-7.8L2 12l7.8-2.2z",
    "Download without metadata",
  );
  const maskButton = iconButton(
    "gallery-mask",
    `Create mask for ${image.filename}`,
    "M7 20c-1.7 0-3-1.3-3-3 0-1.1.6-2.1 1.5-2.6L15 4.9c.9-.9 2.3-.9 3.2 0l.9.9c.9.9.9 2.3 0 3.2l-9.5 9.5C9.1 19.4 8.1 20 7 20zm1.2-3.1 8.8-8.8-1.1-1.1-8.8 8.8c-.4.4-.4.9 0 1.2.3.3.8.3 1.1-.1z",
    "Create mask",
  );
  const loadButton = iconButton(
    "gallery-load",
    `Load metadata from ${image.filename}`,
    "M3 6.5A2.5 2.5 0 0 1 5.5 4H10l2 2h6.5A2.5 2.5 0 0 1 21 8.5v9A2.5 2.5 0 0 1 18.5 20h-13A2.5 2.5 0 0 1 3 17.5z",
    "Load metadata",
  );
  loadButton.disabled = !image.metadata_url;
  const deleteButton = iconButton(
    "gallery-delete",
    `Delete ${image.filename}`,
    "M9 3h6l1 2h4v2H4V5h4zm-3 6h12l-.7 11H6.7z",
    "Delete image",
  );
  actions.append(infoWrap, loadButton, downloadLink, cleanDownloadLink, maskButton);
  if (immichButton) {
    actions.append(immichButton);
  }
  actions.append(deleteButton);

  const sourceButton = createElement("button", {
    attributes: { "aria-label": `Select ${image.filename} as source image` },
    className: "source-select",
    type: "button",
  });

  caption.append(actions);
  figure.append(link, sourceButton, caption);
  return figure;
}

function setDatasetValue(element, name, value) {
  if (value) {
    element.dataset[name] = value;
  }
}

function createImageMedia({
  alt,
  className = "",
  href = null,
  loading = null,
  onError = null,
  src,
}) {
  const media = createElement(href ? "a" : "span", {
    className: ["image-card-media", className].filter(Boolean).join(" "),
  });
  if (href) {
    media.href = href;
    media.target = "_blank";
    media.rel = "noopener";
  }

  const img = createElement("img", { alt, src });
  if (loading) {
    img.loading = loading;
  }
  if (onError) {
    img.addEventListener("error", onError);
  }

  media.append(img);
  return media;
}

function createImageCardRibbon() {
  return createElement("figcaption", { className: "image-card-ribbon" });
}

function createActionRibbon(label) {
  return createElement("div", {
    attributes: { "aria-label": label },
    className: "gallery-actions",
  });
}

function createInfoAction({ label, tooltipText }) {
  const infoWrap = createElement("span", { className: "image-info-wrap" });
  const infoButton = iconButton(
    "gallery-info",
    label,
    "M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm-1 8h2v7h-2zm0-3h2v2h-2z",
  );
  const tooltipLine = createElement("span", {
    className: "tooltip-line",
    textContent: tooltipText,
  });
  const tooltip = createElement("span", {
    attributes: { role: "tooltip" },
    children: [tooltipLine],
    className: "image-info-tooltip",
  });
  infoWrap.append(infoButton, tooltip);
  return infoWrap;
}

function iconButton(className, label, pathData, title = label) {
  return createElement("button", {
    attributes: {
      "aria-label": label,
      title,
    },
    children: [createSvgIcon(pathData)],
    className: `gallery-action ${className}`,
    type: "button",
  });
}

function iconLink(
  className,
  label,
  href,
  pathData,
  sparklePathData = null,
  title = label,
) {
  const link = createElement("a", {
    attributes: {
      "aria-label": label,
      title,
    },
    className: `gallery-action ${className}`,
    href: href || "#",
  });
  if (!href) {
    setBooleanAttribute(link, "aria-disabled", true);
  }

  link.append(createSvgIcon(pathData));

  if (sparklePathData) {
    const sparkle = createSvgIcon(sparklePathData);
    sparkle.classList.add("sparkle");
    link.append(sparkle);
  }
  return link;
}
