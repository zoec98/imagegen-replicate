import { csrfFormRequest, csrfJsonRequest, requestJson } from "./api.js";
import { createElement, createSvgIcon, setBooleanAttribute } from "./dom.js";

export function setupImageUpload(root = document, services = {}) {
  const { csrfToken = "", refreshGallery = async () => {} } = services;
  const form = root.querySelector(".prompt-form");
  const uploadToggle = form?.querySelector(".upload-toggle");
  const overlay = root.querySelector(".upload-overlay");
  const closeButton = overlay?.querySelector(".upload-close");
  const urlInput = overlay?.querySelector(".upload-url");
  const urlLoad = overlay?.querySelector(".upload-url-load");
  const dropTarget = overlay?.querySelector(".upload-drop-target");
  const fileInput = overlay?.querySelector(".upload-file-input");
  const fileChoose = overlay?.querySelector(".upload-file-choose");
  const status = overlay?.querySelector(".upload-status");
  const immichBrowser = overlay?.querySelector(".upload-immich-browser");
  const immichPrev = overlay?.querySelector(".upload-immich-prev");
  const immichNext = overlay?.querySelector(".upload-immich-next");
  const immichPage = overlay?.querySelector(".upload-immich-page");
  const immichEmpty = overlay?.querySelector(".upload-immich-empty");
  const immichGallery = overlay?.querySelector(".upload-immich-gallery");
  let immichCurrentPage = 1;
  let immichNextPage = null;
  let immichPreviousPage = null;
  let immichLoading = false;

  function setStatus(text, category = "info") {
    if (!status) {
      return;
    }
    status.textContent = text || "";
    status.className = "upload-status";
    dropTarget?.classList.remove(
      "upload-drop-target-empty",
      "upload-drop-target-error",
      "upload-drop-target-info",
      "upload-drop-target-success",
    );
    if (text) {
      status.classList.add(`upload-status-${category}`);
      dropTarget?.classList.add(`upload-drop-target-${category}`);
    }
  }

  function setBusy(isBusy) {
    if (urlLoad) {
      urlLoad.disabled = isBusy;
      setBooleanAttribute(urlLoad, "aria-busy", isBusy);
    }
    if (urlInput) {
      urlInput.disabled = isBusy;
    }
    if (dropTarget) {
      dropTarget.classList.toggle("upload-drop-target-busy", isBusy);
      setBooleanAttribute(dropTarget, "aria-disabled", isBusy);
    }
    if (fileInput) {
      fileInput.disabled = isBusy;
    }
    if (fileChoose) {
      fileChoose.disabled = isBusy;
    }
  }

  function open() {
    if (!overlay) {
      return;
    }
    overlay.hidden = false;
    setStatus(
      "Add an image URL, choose one image file, or drop one image file.",
      "empty",
    );
    urlInput?.focus();
    if (overlay.dataset.apiImmichAssetsUrl) {
      loadImmichPage(1).catch((error) => {
        setStatus(error.message || "Immich gallery could not be loaded.", "error");
      });
    }
  }

  function close() {
    if (!overlay) {
      return;
    }
    overlay.hidden = true;
    setBusy(false);
    dropTarget?.classList.remove("upload-drop-target-active");
  }

  async function postJson(url, body, fallbackMessage) {
    if (!url) {
      throw new Error("Upload URL is unavailable.");
    }
    return csrfJsonRequest(url, body, {
      csrfToken,
      fallbackMessage,
    });
  }

  async function postForm(url, formData, fallbackMessage) {
    if (!url) {
      throw new Error("Upload URL is unavailable.");
    }
    return csrfFormRequest(url, formData, {
      csrfToken,
      fallbackMessage,
    });
  }

  async function finishImport(data, message) {
    await refreshGallery();
    const filename = data?.image?.filename;
    setStatus(filename ? `${filename} imported.` : message, "success");
  }

  function setImmichLoading(isLoading) {
    immichLoading = isLoading;
    setBooleanAttribute(immichGallery, "aria-busy", isLoading);
    if (immichPrev) {
      immichPrev.disabled = isLoading || !immichPreviousPage;
    }
    if (immichNext) {
      immichNext.disabled = isLoading || !immichNextPage;
    }
  }

  function setImmichPageLabel(text) {
    if (immichPage) {
      immichPage.textContent = text;
    }
  }

  function immichAssetFigure(asset) {
    const figure = createImageCard("image-card upload-immich-item");
    figure.dataset.assetId = asset.asset_id || "";

    const media = createImageMedia({
      alt: asset.label || "Immich image",
      className: "upload-immich-media",
      loading: "lazy",
      onError: () => {
        figure.classList.add("upload-immich-item-thumbnail-error");
        reportImmichThumbnailError(asset.thumbnail_url);
      },
      src: asset.thumbnail_url || "",
    });

    const caption = createImageCardRibbon();
    const metadata = document.createElement("span");
    metadata.className = "upload-immich-metadata";

    const dimensions =
      asset.width && asset.height ? `${asset.width} x ${asset.height}` : "";
    const sizeLine = document.createElement("span");
    sizeLine.className = "upload-immich-size";
    sizeLine.textContent = dimensions || "Size unavailable";
    const dateLine = document.createElement("span");
    dateLine.className = "upload-immich-date";
    dateLine.textContent = asset.created_at || "Date unavailable";
    metadata.append(sizeLine, dateLine);

    const importButton = document.createElement("button");
    importButton.className = "upload-immich-import";
    importButton.type = "button";
    importButton.disabled = !asset.import_eligible || !asset.asset_id;
    importButton.setAttribute("title", "Import image");
    importButton.setAttribute(
      "aria-label",
      `Import ${asset.label || asset.asset_id || "Immich image"}`,
    );
    const importIcon = createSvgIcon(
      "M19.35 10.04A7.49 7.49 0 0 0 12 4 7.5 7.5 0 0 0 5.35 8.04 6 6 0 0 0 6 20h13a5 5 0 0 0 .35-9.96zM14 12h3l-5 5-5-5h3V8h4z",
    );
    importButton.append(importIcon);

    caption.append(metadata);
    caption.append(importButton);
    figure.append(media, caption);
    return figure;
  }

  async function reportImmichThumbnailError(thumbnailUrl) {
    if (!thumbnailUrl) {
      setStatus("Immich thumbnail could not be loaded.", "error");
      return;
    }
    try {
      await requestJson(thumbnailUrl, {
        fallbackMessage: "Immich thumbnail could not be loaded.",
      });
    } catch (error) {
      setStatus(error.message || "Immich thumbnail could not be loaded.", "error");
    }
  }

  function renderImmichAssets(data) {
    if (!immichGallery || !immichEmpty) {
      return;
    }
    const assets = Array.isArray(data.assets) ? data.assets : [];
    immichCurrentPage = Number.isFinite(data.page) ? data.page : immichCurrentPage;
    const pageSize = Number.isFinite(data.page_size) ? data.page_size : 20;
    immichNextPage =
      data.next_page || (assets.length >= pageSize ? immichCurrentPage + 1 : null);
    immichPreviousPage = data.previous_page || null;
    setImmichPageLabel(`Page ${immichCurrentPage}`);
    immichGallery.replaceChildren();
    if (assets.length === 0) {
      immichEmpty.hidden = false;
      return;
    }
    immichEmpty.hidden = true;
    assets.forEach((asset) => {
      immichGallery.append(immichAssetFigure(asset));
    });
  }

  async function loadImmichPage(page) {
    const baseUrl = overlay?.dataset.apiImmichAssetsUrl;
    if (!baseUrl || !immichBrowser || immichLoading) {
      return;
    }
    setImmichPageLabel("Loading");
    setImmichLoading(true);
    if (immichEmpty) {
      immichEmpty.hidden = true;
    }
    const url = new URL(baseUrl, window.location.href);
    url.searchParams.set("page", String(page));
    try {
      const data = await requestJson(url.toString(), {
        fallbackMessage: "Immich gallery could not be loaded.",
      });
      renderImmichAssets(data);
    } catch (error) {
      setImmichPageLabel(`Page ${immichCurrentPage}`);
      throw error;
    } finally {
      setImmichLoading(false);
    }
  }

  async function importImmichAsset(figure) {
    const assetId = figure?.dataset.assetId || "";
    const button = figure?.querySelector(".upload-immich-import");
    if (!assetId) {
      setStatus("Immich asset id is unavailable.", "error");
      return;
    }
    if (button) {
      button.disabled = true;
      button.setAttribute("aria-busy", "true");
    }
    setStatus("Importing Immich image.", "info");
    try {
      const data = await postJson(
        overlay?.dataset.apiImmichImportUrl,
        { asset_id: assetId },
        "Immich image could not be imported.",
      );
      await finishImport(data, "Immich image imported.");
    } catch (error) {
      if (button) {
        button.disabled = false;
      }
      setStatus(error.message || "Immich image could not be imported.", "error");
    } finally {
      if (button) {
        button.removeAttribute("aria-busy");
      }
    }
  }

  async function importUrl() {
    const url = urlInput?.value.trim() || "";
    if (!url) {
      setStatus("Enter an image URL.", "empty");
      return;
    }
    setBusy(true);
    setStatus("Loading image.", "info");
    try {
      const data = await postJson(
        overlay?.dataset.apiImportUrl,
        { url },
        "Image URL could not be imported.",
      );
      if (urlInput) {
        urlInput.value = "";
      }
      await finishImport(data, "Image imported.");
    } catch (error) {
      setStatus(error.message || "Image URL could not be imported.", "error");
    } finally {
      setBusy(false);
    }
  }

  function droppedFiles(event) {
    return Array.from(event.dataTransfer?.files || []);
  }

  function selectedUploadFiles() {
    return Array.from(fileInput?.files || []);
  }

  function validateDroppedImage(files) {
    if (files.length === 0) {
      return null;
    }
    if (files.length > 1) {
      throw new Error("Drop one image file at a time.");
    }
    const file = files[0];
    if (!file.type || !file.type.startsWith("image/")) {
      throw new Error("Drop one image file with browser MIME type image/*.");
    }
    return file;
  }

  async function importDroppedImage(file) {
    const formData = new FormData();
    formData.append("image", file);
    setBusy(true);
    setStatus("Uploading image.", "info");
    try {
      const data = await postForm(
        overlay?.dataset.apiUploadUrl,
        formData,
        "Image file could not be uploaded.",
      );
      await finishImport(data, "Image uploaded.");
    } catch (error) {
      setStatus(error.message || "Image file could not be uploaded.", "error");
    } finally {
      setBusy(false);
    }
  }

  function importUploadFile(file) {
    importDroppedImage(file).catch((error) => {
      setBusy(false);
      setStatus(error.message || "Image file could not be uploaded.", "error");
    });
  }

  uploadToggle?.addEventListener("click", () => {
    open();
  });
  closeButton?.addEventListener("click", () => {
    close();
  });
  overlay?.addEventListener("click", (event) => {
    if (event.target === overlay) {
      close();
    }
  });
  urlLoad?.addEventListener("click", () => {
    importUrl().catch((error) => {
      setBusy(false);
      setStatus(error.message || "Image URL could not be imported.", "error");
    });
  });
  urlInput?.addEventListener("keydown", (event) => {
    if (event.key !== "Enter") {
      return;
    }
    event.preventDefault();
    importUrl().catch((error) => {
      setBusy(false);
      setStatus(error.message || "Image URL could not be imported.", "error");
    });
  });
  fileChoose?.addEventListener("click", () => {
    if (dropTarget?.classList.contains("upload-drop-target-busy")) {
      return;
    }
    fileInput?.click();
  });
  fileInput?.addEventListener("change", () => {
    if (dropTarget?.classList.contains("upload-drop-target-busy")) {
      return;
    }
    let file;
    try {
      file = validateDroppedImage(selectedUploadFiles());
    } catch (error) {
      fileInput.value = "";
      setStatus(error.message || "Selected file is not an image.", "error");
      return;
    }
    if (!file) {
      setStatus("Choose one image file.", "empty");
      return;
    }
    importUploadFile(file);
    fileInput.value = "";
  });
  dropTarget?.addEventListener("dragenter", (event) => {
    event.preventDefault();
    dropTarget.classList.add("upload-drop-target-active");
  });
  dropTarget?.addEventListener("dragover", (event) => {
    event.preventDefault();
    if (event.dataTransfer) {
      event.dataTransfer.dropEffect = "copy";
    }
    dropTarget.classList.add("upload-drop-target-active");
  });
  dropTarget?.addEventListener("dragleave", (event) => {
    if (event.relatedTarget && dropTarget.contains(event.relatedTarget)) {
      return;
    }
    dropTarget.classList.remove("upload-drop-target-active");
  });
  dropTarget?.addEventListener("drop", (event) => {
    event.preventDefault();
    dropTarget.classList.remove("upload-drop-target-active");
    if (dropTarget.classList.contains("upload-drop-target-busy")) {
      return;
    }
    let file;
    try {
      file = validateDroppedImage(droppedFiles(event));
    } catch (error) {
      setStatus(error.message || "Dropped file is not an image.", "error");
      return;
    }
    if (!file) {
      setStatus("Drop one image file.", "empty");
      return;
    }
    importUploadFile(file);
  });
  immichPrev?.addEventListener("click", () => {
    if (!immichPreviousPage || immichLoading) {
      return;
    }
    loadImmichPage(immichPreviousPage).catch((error) => {
      setStatus(error.message || "Immich gallery could not be loaded.", "error");
    });
  });
  immichNext?.addEventListener("click", () => {
    if (!immichNextPage || immichLoading) {
      return;
    }
    loadImmichPage(immichNextPage).catch((error) => {
      setStatus(error.message || "Immich gallery could not be loaded.", "error");
    });
  });
  immichGallery?.addEventListener("click", (event) => {
    const importButton = event.target.closest(".upload-immich-import");
    if (!importButton) {
      return;
    }
    importImmichAsset(importButton.closest(".upload-immich-item")).catch((error) => {
      setStatus(error.message || "Immich image could not be imported.", "error");
    });
  });

  return {
    close,
    importUrl,
    isOpen: () => Boolean(overlay && !overlay.hidden),
    open,
  };
}

function createImageCard(className) {
  return createElement("figure", { className });
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
