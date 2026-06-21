import { csrfFormRequest, csrfJsonRequest, requestJson } from "./api.js";
import {
  createElement,
  createSvgIcon,
  readJsonScript,
  setBooleanAttribute,
} from "./dom.js";
import { setupGallery } from "./gallery.js";
import { setupMetadata } from "./metadata.js";
import { setupPalettes } from "./palettes.js";
import { setupTrash } from "./trash.js";

(() => {
  const form = document.querySelector(".prompt-form");
  if (!form) {
    return;
  }

  const promptInput = form.querySelector("#prompt");
  const providerSelector = form.querySelector("#provider-selector");
  const modelSelector = form.querySelector("#model-selector");
  const pricingInfo = form.querySelector(".pricing-info");
  const pricingTooltip = form.querySelector(".pricing-tooltip");
  const parameterGrid = form.querySelector(".parameter-grid");
  const generateButton = form.querySelector(".generate-button");
  const editToggle = form.querySelector(".edit-toggle");
  const sourceCounter = form.querySelector(".source-counter");
  const sourceClear = form.querySelector(".source-clear");
  const sourceSelectionStatus = form.querySelector(".source-selection-status");
  const messages = form.querySelector(".messages");
  const gallery = document.querySelector(".gallery");
  const uploadToggle = form.querySelector(".upload-toggle");
  const uploadOverlay = document.querySelector(".upload-overlay");
  const uploadClose = uploadOverlay?.querySelector(".upload-close");
  const uploadUrlInput = uploadOverlay?.querySelector(".upload-url");
  const uploadUrlLoad = uploadOverlay?.querySelector(".upload-url-load");
  const uploadDropTarget = uploadOverlay?.querySelector(".upload-drop-target");
  const uploadFileInput = uploadOverlay?.querySelector(".upload-file-input");
  const uploadFileChoose = uploadOverlay?.querySelector(".upload-file-choose");
  const uploadStatus = uploadOverlay?.querySelector(".upload-status");
  const uploadImmichBrowser = uploadOverlay?.querySelector(".upload-immich-browser");
  const uploadImmichPrev = uploadOverlay?.querySelector(".upload-immich-prev");
  const uploadImmichNext = uploadOverlay?.querySelector(".upload-immich-next");
  const uploadImmichPage = uploadOverlay?.querySelector(".upload-immich-page");
  const uploadImmichEmpty = uploadOverlay?.querySelector(".upload-immich-empty");
  const uploadImmichGallery = uploadOverlay?.querySelector(".upload-immich-gallery");
  const maskEditorOverlay = document.querySelector(".mask-editor-overlay");
  const maskEditorStage = maskEditorOverlay?.querySelector(".mask-editor-stage");
  const maskEditorWrap = maskEditorOverlay?.querySelector(".mask-editor-canvas-wrap");
  const maskEditorSource = maskEditorOverlay?.querySelector(".mask-editor-source");
  const maskEditorMask = maskEditorOverlay?.querySelector(".mask-editor-mask");
  const maskEditorBrushSizeInput = maskEditorOverlay?.querySelector(
    ".mask-editor-brush-size",
  );
  const maskEditorBrushFalloffInput = maskEditorOverlay?.querySelector(
    ".mask-editor-brush-falloff",
  );
  const maskEditorBrushSizeValue = maskEditorOverlay?.querySelector(
    ".mask-editor-brush-size-value",
  );
  const maskEditorBrushFalloffValue = maskEditorOverlay?.querySelector(
    ".mask-editor-brush-falloff-value",
  );
  const maskEditorInvert = maskEditorOverlay?.querySelector(".mask-editor-invert");
  const maskEditorSave = maskEditorOverlay?.querySelector(".mask-editor-save");
  const maskEditorTitle = maskEditorOverlay?.querySelector("#mask-editor-title");
  const maskEditorClose = maskEditorOverlay?.querySelector(".mask-editor-close");
  const csrfToken = document
    .querySelector('meta[name="csrf-token"]')
    ?.getAttribute("content");
  const pageChecksum = document
    .querySelector('meta[name="app-build"]')
    ?.getAttribute("content");
  const terminalStatuses = new Set(["succeeded", "failed", "timeout"]);
  const pollSeconds = Number.parseFloat(form.dataset.pollSeconds || "1");
  const pollMilliseconds = Math.max(
    250,
    (Number.isFinite(pollSeconds) ? pollSeconds : 1) * 1000,
  );
  let isPageStale = false;

  function loadJsonArray(selector) {
    const value = readJsonScript(selector, { fallback: [] });
    return Array.isArray(value) ? value : [];
  }

  const modelRegistry = loadJsonArray("#model-registry-data");
  const parameterState = {};
  const selectedSourceImages = new Set();
  let galleryWorkflow = null;
  let editModeEnabled = false;
  let maskEditorSourceImage = null;
  let maskEditorMaskData = null;
  let maskEditorPainting = false;
  let maskEditorBrushSize = 48;
  let maskEditorBrushFalloff = 0.65;
  let immichCurrentPage = 1;
  let immichNextPage = null;
  let immichPreviousPage = null;
  let immichLoading = false;

  function selectedProvider() {
    return providerSelector?.value || null;
  }

  function modelsForProvider(provider) {
    return modelRegistry.filter((model) => model.provider === provider);
  }

  function selectedModel() {
    const provider = selectedProvider();
    const selectedAlias = modelSelector?.value;
    const providerModels = modelsForProvider(provider);
    return (
      providerModels.find((model) => model.alias === selectedAlias) ||
      providerModels[0] ||
      null
    );
  }

  function renderModelOptions(provider) {
    if (!modelSelector) {
      return selectedModel();
    }
    const providerModels = modelsForProvider(provider);
    const previous = modelSelector.value;
    modelSelector.replaceChildren();
    providerModels.forEach((model) => {
      const option = document.createElement("option");
      option.value = model.alias;
      option.textContent = model.display_name;
      modelSelector.append(option);
    });
    if (providerModels.some((model) => model.alias === previous)) {
      modelSelector.value = previous;
    } else if (providerModels[0]) {
      modelSelector.value = providerModels[0].alias;
    }
    modelSelector.disabled = providerModels.length === 0;
    return selectedModel();
  }

  function showMessage(text, category) {
    if (!messages) {
      return;
    }
    messages.replaceChildren();
    if (!text) {
      return;
    }
    const message = document.createElement("p");
    message.className = `message message-${category}`;
    message.textContent = text;
    messages.append(message);
  }

  function setUploadStatus(text, category = "info") {
    if (!uploadStatus) {
      return;
    }
    uploadStatus.textContent = text || "";
    uploadStatus.className = "upload-status";
    uploadDropTarget?.classList.remove(
      "upload-drop-target-empty",
      "upload-drop-target-error",
      "upload-drop-target-info",
      "upload-drop-target-success",
    );
    if (text) {
      uploadStatus.classList.add(`upload-status-${category}`);
      uploadDropTarget?.classList.add(`upload-drop-target-${category}`);
    }
  }

  function setUploadBusy(isBusy) {
    if (uploadUrlLoad) {
      uploadUrlLoad.disabled = isBusy;
      setBooleanAttribute(uploadUrlLoad, "aria-busy", isBusy);
    }
    if (uploadUrlInput) {
      uploadUrlInput.disabled = isBusy;
    }
    if (uploadDropTarget) {
      uploadDropTarget.classList.toggle("upload-drop-target-busy", isBusy);
      setBooleanAttribute(uploadDropTarget, "aria-disabled", isBusy);
    }
    if (uploadFileInput) {
      uploadFileInput.disabled = isBusy;
    }
    if (uploadFileChoose) {
      uploadFileChoose.disabled = isBusy;
    }
  }

  function openUploadOverlay() {
    if (!uploadOverlay) {
      return;
    }
    uploadOverlay.hidden = false;
    setUploadStatus(
      "Add an image URL, choose one image file, or drop one image file.",
      "empty",
    );
    uploadUrlInput?.focus();
    if (uploadOverlay.dataset.apiImmichAssetsUrl) {
      loadImmichPage(1).catch((error) => {
        setUploadStatus(
          error.message || "Immich gallery could not be loaded.",
          "error",
        );
      });
    }
  }

  function closeUploadOverlay() {
    if (!uploadOverlay) {
      return;
    }
    uploadOverlay.hidden = true;
    setUploadBusy(false);
    uploadDropTarget?.classList.remove("upload-drop-target-active");
  }

  async function postUploadJson(url, body, fallbackMessage) {
    if (!url) {
      throw new Error("Upload URL is unavailable.");
    }
    return csrfJsonRequest(url, body, {
      csrfToken,
      fallbackMessage,
    });
  }

  async function postUploadForm(url, formData, fallbackMessage) {
    if (!url) {
      throw new Error("Upload URL is unavailable.");
    }
    return csrfFormRequest(url, formData, {
      csrfToken,
      fallbackMessage,
    });
  }

  async function finishUploadImport(data, message) {
    await refreshGallery();
    const filename = data?.image?.filename;
    setUploadStatus(filename ? `${filename} imported.` : message, "success");
  }

  function setImmichLoading(isLoading) {
    immichLoading = isLoading;
    setBooleanAttribute(uploadImmichGallery, "aria-busy", isLoading);
    if (uploadImmichPrev) {
      uploadImmichPrev.disabled = isLoading || !immichPreviousPage;
    }
    if (uploadImmichNext) {
      uploadImmichNext.disabled = isLoading || !immichNextPage;
    }
  }

  function setImmichPageLabel(text) {
    if (uploadImmichPage) {
      uploadImmichPage.textContent = text;
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
      setUploadStatus("Immich thumbnail could not be loaded.", "error");
      return;
    }
    try {
      await requestJson(thumbnailUrl, {
        fallbackMessage: "Immich thumbnail could not be loaded.",
      });
    } catch (error) {
      setUploadStatus(
        error.message || "Immich thumbnail could not be loaded.",
        "error",
      );
    }
  }

  function renderImmichAssets(data) {
    if (!uploadImmichGallery || !uploadImmichEmpty) {
      return;
    }
    const assets = Array.isArray(data.assets) ? data.assets : [];
    immichCurrentPage = Number.isFinite(data.page) ? data.page : immichCurrentPage;
    const pageSize = Number.isFinite(data.page_size) ? data.page_size : 20;
    immichNextPage =
      data.next_page || (assets.length >= pageSize ? immichCurrentPage + 1 : null);
    immichPreviousPage = data.previous_page || null;
    setImmichPageLabel(`Page ${immichCurrentPage}`);
    uploadImmichGallery.replaceChildren();
    if (assets.length === 0) {
      uploadImmichEmpty.hidden = false;
      return;
    }
    uploadImmichEmpty.hidden = true;
    assets.forEach((asset) => {
      uploadImmichGallery.append(immichAssetFigure(asset));
    });
  }

  async function loadImmichPage(page) {
    const baseUrl = uploadOverlay?.dataset.apiImmichAssetsUrl;
    if (!baseUrl || !uploadImmichBrowser || immichLoading) {
      return;
    }
    setImmichPageLabel("Loading");
    setImmichLoading(true);
    if (uploadImmichEmpty) {
      uploadImmichEmpty.hidden = true;
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
      setUploadStatus("Immich asset id is unavailable.", "error");
      return;
    }
    if (button) {
      button.disabled = true;
      button.setAttribute("aria-busy", "true");
    }
    setUploadStatus("Importing Immich image.", "info");
    try {
      const data = await postUploadJson(
        uploadOverlay?.dataset.apiImmichImportUrl,
        { asset_id: assetId },
        "Immich image could not be imported.",
      );
      await finishUploadImport(data, "Immich image imported.");
    } catch (error) {
      if (button) {
        button.disabled = false;
      }
      setUploadStatus(error.message || "Immich image could not be imported.", "error");
    } finally {
      if (button) {
        button.removeAttribute("aria-busy");
      }
    }
  }

  async function importUploadUrl() {
    const url = uploadUrlInput?.value.trim() || "";
    if (!url) {
      setUploadStatus("Enter an image URL.", "empty");
      return;
    }
    setUploadBusy(true);
    setUploadStatus("Loading image.", "info");
    try {
      const data = await postUploadJson(
        uploadOverlay?.dataset.apiImportUrl,
        { url },
        "Image URL could not be imported.",
      );
      if (uploadUrlInput) {
        uploadUrlInput.value = "";
      }
      await finishUploadImport(data, "Image imported.");
    } catch (error) {
      setUploadStatus(error.message || "Image URL could not be imported.", "error");
    } finally {
      setUploadBusy(false);
    }
  }

  function droppedFiles(event) {
    return Array.from(event.dataTransfer?.files || []);
  }

  function selectedUploadFiles() {
    return Array.from(uploadFileInput?.files || []);
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
    setUploadBusy(true);
    setUploadStatus("Uploading image.", "info");
    try {
      const data = await postUploadForm(
        uploadOverlay?.dataset.apiUploadUrl,
        formData,
        "Image file could not be uploaded.",
      );
      await finishUploadImport(data, "Image uploaded.");
    } catch (error) {
      setUploadStatus(error.message || "Image file could not be uploaded.", "error");
    } finally {
      setUploadBusy(false);
    }
  }

  function importUploadFile(file) {
    importDroppedImage(file).catch((error) => {
      setUploadBusy(false);
      setUploadStatus(error.message || "Image file could not be uploaded.", "error");
    });
  }

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

  function clearSelectedSources() {
    selectedSourceImages.clear();
    updateSourceSelectionUi();
  }

  function numberFromInput(input, fallback) {
    const value = Number.parseFloat(input?.value || "");
    return Number.isFinite(value) ? value : fallback;
  }

  function updateMaskBrushControls() {
    maskEditorBrushSize = Math.max(
      numberFromInput(maskEditorBrushSizeInput, maskEditorBrushSize),
      1,
    );
    maskEditorBrushFalloff =
      Math.min(
        Math.max(
          numberFromInput(maskEditorBrushFalloffInput, maskEditorBrushFalloff * 100),
          0,
        ),
        100,
      ) / 100;
    if (maskEditorBrushSizeValue) {
      maskEditorBrushSizeValue.textContent = `${Math.round(maskEditorBrushSize)} px`;
    }
    if (maskEditorBrushFalloffValue) {
      maskEditorBrushFalloffValue.textContent = `${Math.round(
        maskEditorBrushFalloff * 100,
      )}%`;
    }
  }

  function openMaskEditor(figure) {
    const filename = figure?.dataset.filename;
    const imageUrl = figure?.querySelector("img")?.src;
    const maskUrl = figure?.dataset.maskUrl;
    const maskSaveUrl = figure?.dataset.maskSaveUrl;
    if (
      !maskEditorOverlay ||
      !maskEditorSource ||
      !maskEditorMask ||
      !filename ||
      !imageUrl ||
      !maskUrl ||
      !maskSaveUrl
    ) {
      return;
    }
    maskEditorOverlay.dataset.filename = filename;
    maskEditorOverlay.dataset.imageUrl = imageUrl;
    maskEditorOverlay.dataset.maskUrl = maskUrl;
    maskEditorOverlay.dataset.maskSaveUrl = maskSaveUrl;
    if (maskEditorTitle) {
      maskEditorTitle.textContent = filename;
    }
    updateMaskBrushControls();
    maskEditorOverlay.hidden = false;
    loadMaskEditorImage(imageUrl);
    maskEditorClose?.focus();
  }

  function closeMaskEditor() {
    if (!maskEditorOverlay) {
      return;
    }
    maskEditorOverlay.hidden = true;
    delete maskEditorOverlay.dataset.filename;
    delete maskEditorOverlay.dataset.imageUrl;
    delete maskEditorOverlay.dataset.maskUrl;
    delete maskEditorOverlay.dataset.maskSaveUrl;
    maskEditorSourceImage = null;
    maskEditorMaskData = null;
    maskEditorPainting = false;
    resetMaskEditorCanvases();
    if (maskEditorTitle) {
      maskEditorTitle.textContent = "Mask";
    }
  }

  function loadMaskEditorImage(imageUrl) {
    const image = new Image();
    image.onload = () => {
      if (maskEditorOverlay?.dataset.imageUrl !== imageUrl) {
        return;
      }
      maskEditorSourceImage = image;
      maskEditorMaskData = new Float32Array(image.naturalWidth * image.naturalHeight);
      resetMaskEditorCanvases(image.naturalWidth, image.naturalHeight);
      redrawMaskEditor();
    };
    image.onerror = () => {
      if (maskEditorOverlay?.dataset.imageUrl === imageUrl) {
        showMessage("Mask source image could not be loaded.", "error");
        closeMaskEditor();
      }
    };
    image.src = imageUrl;
  }

  function resetMaskEditorCanvases(width = 0, height = 0) {
    [maskEditorSource, maskEditorMask].forEach((canvas) => {
      if (!canvas) {
        return;
      }
      canvas.width = width;
      canvas.height = height;
      canvas.style.width = "";
      canvas.style.height = "";
      const context = canvas.getContext("2d");
      context?.clearRect(0, 0, Math.max(width, 1), Math.max(height, 1));
    });
    if (maskEditorWrap) {
      maskEditorWrap.style.width = "";
      maskEditorWrap.style.height = "";
    }
  }

  function resizeMaskEditorCanvases() {
    if (
      !maskEditorStage ||
      !maskEditorWrap ||
      !maskEditorSourceImage ||
      !maskEditorSource ||
      !maskEditorMask
    ) {
      return;
    }
    const maxWidth = Math.max(maskEditorStage.clientWidth, 1);
    const maxHeight = Math.max(window.innerHeight - 176, 192);
    const scale = Math.min(
      maxWidth / maskEditorSourceImage.naturalWidth,
      maxHeight / maskEditorSourceImage.naturalHeight,
      1,
    );
    const displayWidth = Math.max(
      Math.round(maskEditorSourceImage.naturalWidth * scale),
      1,
    );
    const displayHeight = Math.max(
      Math.round(maskEditorSourceImage.naturalHeight * scale),
      1,
    );
    maskEditorWrap.style.width = `${displayWidth}px`;
    maskEditorWrap.style.height = `${displayHeight}px`;
    [maskEditorSource, maskEditorMask].forEach((canvas) => {
      canvas.style.width = `${displayWidth}px`;
      canvas.style.height = `${displayHeight}px`;
    });
  }

  function redrawMaskEditor() {
    if (!maskEditorSourceImage || !maskEditorSource || !maskEditorMask) {
      return;
    }
    resizeMaskEditorCanvases();
    const sourceContext = maskEditorSource.getContext("2d");
    sourceContext?.clearRect(0, 0, maskEditorSource.width, maskEditorSource.height);
    sourceContext?.drawImage(
      maskEditorSourceImage,
      0,
      0,
      maskEditorSource.width,
      maskEditorSource.height,
    );
    redrawMaskOverlay();
  }

  function redrawMaskOverlay() {
    if (!maskEditorMask || !maskEditorMaskData) {
      return;
    }
    const context = maskEditorMask.getContext("2d");
    if (!context) {
      return;
    }
    const imageData = context.createImageData(
      maskEditorMask.width,
      maskEditorMask.height,
    );
    for (let index = 0; index < maskEditorMaskData.length; index += 1) {
      const alpha = Math.round(Math.min(maskEditorMaskData[index], 1) * 150);
      const offset = index * 4;
      imageData.data[offset] = 255;
      imageData.data[offset + 1] = 42;
      imageData.data[offset + 2] = 42;
      imageData.data[offset + 3] = alpha;
    }
    context.putImageData(imageData, 0, 0);
  }

  function maskPointerPosition(event) {
    if (!maskEditorMask) {
      return null;
    }
    const rect = maskEditorMask.getBoundingClientRect();
    if (rect.width <= 0 || rect.height <= 0) {
      return null;
    }
    return {
      x: ((event.clientX - rect.left) / rect.width) * maskEditorMask.width,
      y: ((event.clientY - rect.top) / rect.height) * maskEditorMask.height,
      scale: maskEditorMask.width / rect.width,
    };
  }

  function paintMaskAt(position) {
    if (!position || !maskEditorMask || !maskEditorMaskData) {
      return;
    }
    const radius = Math.max((maskEditorBrushSize * position.scale) / 2, 1);
    const innerRadius = radius * (1 - maskEditorBrushFalloff);
    const minX = Math.max(Math.floor(position.x - radius), 0);
    const maxX = Math.min(Math.ceil(position.x + radius), maskEditorMask.width - 1);
    const minY = Math.max(Math.floor(position.y - radius), 0);
    const maxY = Math.min(Math.ceil(position.y + radius), maskEditorMask.height - 1);
    for (let y = minY; y <= maxY; y += 1) {
      for (let x = minX; x <= maxX; x += 1) {
        const distance = Math.hypot(x - position.x, y - position.y);
        if (distance > radius) {
          continue;
        }
        const intensity =
          distance <= innerRadius
            ? 1
            : 1 - (distance - innerRadius) / Math.max(radius - innerRadius, 1);
        const index = y * maskEditorMask.width + x;
        maskEditorMaskData[index] = Math.max(maskEditorMaskData[index], intensity);
      }
    }
    redrawMaskOverlay();
  }

  function invertMaskEditorData() {
    if (!maskEditorMaskData) {
      return;
    }
    for (let index = 0; index < maskEditorMaskData.length; index += 1) {
      maskEditorMaskData[index] =
        1 - Math.min(Math.max(maskEditorMaskData[index], 0), 1);
    }
    redrawMaskOverlay();
  }

  function maskEditorPngDataUrl() {
    if (!maskEditorMask || !maskEditorMaskData) {
      throw new Error("Mask data is unavailable.");
    }
    const canvas = document.createElement("canvas");
    canvas.width = maskEditorMask.width;
    canvas.height = maskEditorMask.height;
    const context = canvas.getContext("2d");
    if (!context) {
      throw new Error("Mask export is unavailable.");
    }
    const imageData = context.createImageData(canvas.width, canvas.height);
    for (let index = 0; index < maskEditorMaskData.length; index += 1) {
      const value = Math.round(
        Math.min(Math.max(maskEditorMaskData[index], 0), 1) * 255,
      );
      const offset = index * 4;
      imageData.data[offset] = value;
      imageData.data[offset + 1] = value;
      imageData.data[offset + 2] = value;
      imageData.data[offset + 3] = 255;
    }
    context.putImageData(imageData, 0, 0);
    return canvas.toDataURL("image/png");
  }

  async function saveMaskEditorData() {
    if (!maskEditorOverlay?.dataset.maskSaveUrl) {
      showMessage("Mask save URL is unavailable.", "error");
      return;
    }
    if (!csrfToken) {
      showMessage("Missing CSRF token.", "error");
      return;
    }
    if (maskEditorSave) {
      maskEditorSave.disabled = true;
    }
    showMessage("Saving mask.", "info");
    try {
      const data = await csrfJsonRequest(
        maskEditorOverlay.dataset.maskSaveUrl,
        { mask_png: maskEditorPngDataUrl() },
        { csrfToken, fallbackMessage: "Mask could not be saved." },
      );
      closeMaskEditor();
      await refreshGallery();
      showMessage(`${data.filename || "Mask"} saved.`, "success");
    } catch (error) {
      showMessage(error.message || "Mask could not be saved.", "error");
    } finally {
      if (maskEditorSave) {
        maskEditorSave.disabled = false;
      }
    }
  }

  function startMaskPainting(event) {
    if (!maskEditorMaskData || !maskEditorMask) {
      return;
    }
    event.preventDefault();
    maskEditorPainting = true;
    maskEditorMask.setPointerCapture?.(event.pointerId);
    paintMaskAt(maskPointerPosition(event));
  }

  function continueMaskPainting(event) {
    if (!maskEditorPainting) {
      return;
    }
    event.preventDefault();
    paintMaskAt(maskPointerPosition(event));
  }

  function stopMaskPainting(event) {
    if (!maskEditorPainting) {
      return;
    }
    maskEditorPainting = false;
    maskEditorMask?.releasePointerCapture?.(event.pointerId);
  }

  function setEditMode(enabled) {
    const model = selectedModel();
    editModeEnabled = Boolean(enabled && model?.edit_capable);
    if (!editModeEnabled) {
      selectedSourceImages.clear();
      sourceStatus("");
    }
    updateSourceSelectionUi();
  }

  function updateSourceSelectionUi() {
    const model = selectedModel();
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

  function toggleSourceImage(filename) {
    if (!editModeEnabled || !filename) {
      return;
    }
    if (selectedSourceImages.has(filename)) {
      selectedSourceImages.delete(filename);
      sourceStatus("");
      updateSourceSelectionUi();
      return;
    }
    const limit = sourceImageLimit(selectedModel());
    if (limit > 0 && selectedSourceImages.size >= limit) {
      sourceStatus(
        `Select up to ${limit} source image${limit === 1 ? "" : "s"}.`,
        true,
      );
      return;
    }
    selectedSourceImages.add(filename);
    sourceStatus("");
    updateSourceSelectionUi();
  }

  function readControlValue(control) {
    return control.type === "checkbox" ? control.checked : control.value;
  }

  function syncParameterStateFromDom() {
    const controls = form.querySelectorAll(
      ".parameter-grid input, .parameter-grid select",
    );
    controls.forEach((control) => {
      if (!control.name) {
        return;
      }
      parameterState[control.name] = readControlValue(control);
    });
  }

  function parameterMetadata(model, name) {
    if (!model || !Array.isArray(model.parameters)) {
      return null;
    }
    return model.parameters.find((parameter) => parameter.name === name) || null;
  }

  function customDimensions(model) {
    return model?.custom_dimensions || null;
  }

  function isCustomDimensionsActive(model) {
    const control = customDimensions(model);
    if (!control) {
      return false;
    }
    const activationParameter = parameterMetadata(model, control.activation_parameter);
    const activationValue = Object.prototype.hasOwnProperty.call(
      parameterState,
      control.activation_parameter,
    )
      ? parameterState[control.activation_parameter]
      : activationParameter?.default;
    return activationValue === control.activation_value;
  }

  function setGenerating(isGenerating) {
    if (!generateButton) {
      return;
    }
    const hasProviderModel = Boolean(selectedModel());
    generateButton.disabled = isGenerating || isPageStale || !hasProviderModel;
    setBooleanAttribute(generateButton, "aria-busy", isGenerating);
    generateButton.textContent = isGenerating
      ? "Generating"
      : generateButton.dataset.defaultLabel || "Generate";
  }

  function markPageStale() {
    isPageStale = true;
    setGenerating(false);
    showMessage(
      "This page is out of date. Reload the page before generating.",
      "error",
    );
  }

  async function checkAppFreshness() {
    if (!pageChecksum || !form.dataset.apiAppVersionUrl) {
      return true;
    }
    const data = await requestJson(form.dataset.apiAppVersionUrl, {
      fallbackMessage: "App version check failed.",
    });
    if (data.app_checksum !== pageChecksum) {
      markPageStale();
      return false;
    }
    return true;
  }

  function collectParameters() {
    syncParameterStateFromDom();
    const model = selectedModel();
    if (!model || !Array.isArray(model.parameters)) {
      return {};
    }
    const parameters = {};
    const control = customDimensions(model);
    const customActive = isCustomDimensionsActive(model);

    model.parameters.forEach((parameter) => {
      if (!parameter.name) {
        return;
      }
      const value = Object.prototype.hasOwnProperty.call(parameterState, parameter.name)
        ? parameterState[parameter.name]
        : parameter.default;
      if (parameter.semantic_type === "seed" && value === "") {
        return;
      }
      if (control) {
        if (
          !customActive &&
          (parameter.name === control.width_parameter ||
            parameter.name === control.height_parameter)
        ) {
          return;
        }
        if (customActive && parameter.name === control.scale_parameter) {
          return;
        }
      }
      parameters[parameter.name] = value;
    });
    return parameters;
  }

  function collectGenerationPayload(prompt) {
    const payload = {
      provider: providerSelector?.value || undefined,
      model: modelSelector?.value || undefined,
      prompt,
      parameters: collectParameters(),
    };
    if (editModeEnabled) {
      payload.edit_mode = true;
    }
    if (editModeEnabled && selectedSourceImages.size > 0) {
      payload.source_images = Array.from(selectedSourceImages);
    }
    return payload;
  }

  function parameterLabel(name) {
    return name.replaceAll("_", " ");
  }

  function parameterValue(parameter) {
    const current = Object.prototype.hasOwnProperty.call(parameterState, parameter.name)
      ? parameterState[parameter.name]
      : parameter.default;
    if (Array.isArray(parameter.choices) && parameter.choices.length > 0) {
      return parameter.choices.includes(current) ? current : parameter.default;
    }
    return current;
  }

  function parameterInput(parameter) {
    const value = parameterValue(parameter);
    if (Array.isArray(parameter.choices) && parameter.choices.length > 0) {
      const select = document.createElement("select");
      parameter.choices.forEach((choice) => {
        const option = document.createElement("option");
        option.value = String(choice);
        option.textContent = String(choice);
        if (choice === value) {
          option.selected = true;
        }
        select.append(option);
      });
      return select;
    }

    const input = document.createElement("input");
    if (parameter.type === "integer" || parameter.type === "number") {
      input.type = "number";
      if (parameter.type === "number") {
        input.step = "any";
      }
      if (parameter.minimum !== null && parameter.minimum !== undefined) {
        input.min = String(parameter.minimum);
      }
      if (parameter.maximum !== null && parameter.maximum !== undefined) {
        input.max = String(parameter.maximum);
      }
    } else if (parameter.type === "boolean") {
      input.type = "checkbox";
      input.checked = value === true;
    } else {
      input.type = "text";
    }
    if (parameter.semantic_type === "seed") {
      input.placeholder = "Random";
    }
    if (value !== null && value !== undefined && value !== "") {
      input.value = String(value);
    }
    return input;
  }

  function renderParameters(model) {
    if (!parameterGrid || !model) {
      return;
    }
    parameterGrid.replaceChildren();
    if (!Array.isArray(model.parameters)) {
      return;
    }
    const dimensionControl = customDimensions(model);
    const customActive = isCustomDimensionsActive(model);
    model.parameters.forEach((parameter) => {
      if (
        dimensionControl &&
        !customActive &&
        (parameter.name === dimensionControl.width_parameter ||
          parameter.name === dimensionControl.height_parameter)
      ) {
        return;
      }
      if (
        dimensionControl &&
        customActive &&
        parameter.name === dimensionControl.scale_parameter
      ) {
        return;
      }
      const id = `parameter-${parameter.name}`;
      const label = document.createElement("label");
      label.className = "field";
      label.htmlFor = id;

      const text = document.createElement("span");
      text.textContent = parameterLabel(parameter.name);

      const control = parameterInput(parameter);
      control.id = id;
      control.name = parameter.name;
      if (parameter.description) {
        control.title = parameter.description;
      }

      label.append(text, control);
      parameterGrid.append(label);
    });
  }

  function renderPricing(model) {
    if (!pricingInfo || !pricingTooltip) {
      return;
    }
    pricingTooltip.replaceChildren();
    const pricing = Array.isArray(model?.pricing) ? model.pricing : [];
    pricingInfo.hidden = pricing.length === 0;
    if (pricing.length === 0) {
      return;
    }
    pricing.forEach((item) => {
      const line = document.createElement("span");
      line.textContent = `${item.price} ${item.title}${
        item.description ? ` ${item.description}` : ""
      }`;
      pricingTooltip.append(line);
    });
  }

  function modelForMetadata(metadata) {
    if (metadata.model_alias) {
      if (metadata.provider) {
        return (
          modelRegistry.find(
            (model) =>
              model.provider === metadata.provider &&
              model.alias === metadata.model_alias,
          ) || null
        );
      }
      return (
        modelRegistry.find((model) => model.alias === metadata.model_alias) || null
      );
    }
    if (metadata.model) {
      return (
        modelRegistry.find((model) => model.replicate_model === metadata.model) || null
      );
    }
    return null;
  }

  function parametersForModel(metadataParameters, model) {
    const sourceParameter = model.source_image_parameter;
    const supported = {};
    model.parameters.forEach((parameter) => {
      if (
        parameter.name === "prompt" ||
        parameter.name === sourceParameter ||
        Object.prototype.hasOwnProperty.call(model.fixed_inputs || {}, parameter.name)
      ) {
        return;
      }
      if (Object.prototype.hasOwnProperty.call(metadataParameters, parameter.name)) {
        supported[parameter.name] = metadataParameters[parameter.name];
      }
    });
    return supported;
  }

  function sourceImagesFromMetadata(metadata, model) {
    if (!model?.edit_capable) {
      return [];
    }
    if (Array.isArray(metadata.source_images)) {
      return metadata.source_images.filter(
        (filename) => typeof filename === "string" && filename.trim(),
      );
    }
    const sourceParameter = model.source_image_parameter;
    if (!sourceParameter || !metadata.parameters) {
      return [];
    }
    const value = metadata.parameters[sourceParameter];
    if (typeof value === "string" && value.trim()) {
      return [value];
    }
    if (Array.isArray(value)) {
      return value.filter(
        (filename) => typeof filename === "string" && filename.trim(),
      );
    }
    return [];
  }

  function applyImageMetadata(metadata) {
    if (!metadata || typeof metadata !== "object") {
      throw new Error("Image metadata is missing.");
    }
    const model = modelForMetadata(metadata);
    if (!model) {
      throw new Error("Image metadata references an unknown model.");
    }
    if (typeof metadata.prompt !== "string" || !metadata.prompt.trim()) {
      throw new Error("Image metadata does not include a prompt.");
    }
    if (!metadata.parameters || typeof metadata.parameters !== "object") {
      throw new Error("Image metadata does not include model settings.");
    }

    const nextParameters = parametersForModel(metadata.parameters, model);
    const sourceImages = sourceImagesFromMetadata(metadata, model);
    promptInput.value = metadata.prompt;
    if (providerSelector && model.provider) {
      providerSelector.value = model.provider;
      renderModelOptions(model.provider);
    }
    modelSelector.value = model.alias;
    selectedSourceImages.clear();
    sourceImages.forEach((filename) => selectedSourceImages.add(filename));
    editModeEnabled = Boolean(metadata.edit_mode || sourceImages.length > 0);
    Object.keys(parameterState).forEach((name) => {
      delete parameterState[name];
    });
    Object.assign(parameterState, nextParameters);
    renderPricing(model);
    renderParameters(model);
    updateSourceSelectionUi();
  }

  function statusMessage(data) {
    if (data.status === "failed" || data.status === "timeout") {
      return data.error || `Generation ${data.status}.`;
    }
    if (data.status === "succeeded") {
      return "Generation succeeded.";
    }
    const latestLog = Array.isArray(data.logs) ? data.logs.at(-1) : "";
    if (latestLog) {
      return latestLog;
    }
    return `Generation status: ${data.status}.`;
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

  async function refreshGallery() {
    await galleryWorkflow?.refresh();
  }

  function finishGeneration(data) {
    delete form.dataset.activeRequestId;
    setGenerating(false);
    if (data.status === "succeeded") {
      showMessage(statusMessage(data), "success");
      refreshGallery().catch((error) => showMessage(error.message, "error"));
      checkAppFreshness().catch(() => {});
      return;
    }
    showMessage(statusMessage(data), "error");
    checkAppFreshness().catch(() => {});
  }

  async function pollGeneration(statusUrl) {
    if (!statusUrl || !form.dataset.activeRequestId) {
      return;
    }
    try {
      const data = await requestJson(statusUrl, {
        fallbackMessage: "Generation status request failed.",
      });

      if (data.request_id !== form.dataset.activeRequestId) {
        return;
      }

      if (terminalStatuses.has(data.status)) {
        finishGeneration(data);
        return;
      }

      showMessage(statusMessage(data), "info");
      window.setTimeout(() => pollGeneration(statusUrl), pollMilliseconds);
    } catch (error) {
      delete form.dataset.activeRequestId;
      setGenerating(false);
      showMessage(error.message || "Generation status request failed.", "error");
    }
  }

  async function submitGeneration(event) {
    event.preventDefault();

    const prompt = promptInput?.value.trim() || "";
    if (!prompt) {
      showMessage("Prompt is required.", "error");
      promptInput?.focus();
      return;
    }

    if (!csrfToken) {
      showMessage("Missing CSRF token.", "error");
      return;
    }

    try {
      if (!(await checkAppFreshness())) {
        return;
      }
    } catch (error) {
      showMessage(error.message || "App version check failed.", "error");
      return;
    }

    setGenerating(true);
    showMessage("Generation request queued.", "info");

    try {
      const data = await csrfJsonRequest(
        form.dataset.apiGenerateUrl,
        collectGenerationPayload(prompt),
        { csrfToken, fallbackMessage: "Generation request failed." },
      );
      showMessage("Generation is running.", "info");
      form.dataset.activeRequestId = data.request_id;
      window.setTimeout(
        () => pollGeneration(data.status_url),
        Number.isFinite(data.poll_seconds)
          ? Math.max(250, data.poll_seconds * 1000)
          : pollMilliseconds,
      );
    } catch (error) {
      setGenerating(false);
      showMessage(error.message || "Generation request failed.", "error");
    }
  }

  const trashWorkflow = setupTrash(document, {
    csrfToken,
    refreshGallery,
    showMessage,
  });
  const metadataWorkflow = setupMetadata(document, {
    applyMetadata: applyImageMetadata,
    modelRegistry,
    showMessage,
  });
  galleryWorkflow = setupGallery(document, {
    csrfToken,
    metadata: metadataWorkflow,
    openMaskEditor,
    removeSourceImage: (filename) => selectedSourceImages.delete(filename),
    setTrashCount: (value) => trashWorkflow.setCount(value),
    showMessage,
    toggleSourceImage,
    updateSourceSelectionUi,
  });
  setupPalettes(document, {
    csrfToken,
    showMessage,
  });

  checkAppFreshness().catch((error) => {
    showMessage(error.message || "App version check failed.", "error");
  });
  providerSelector?.addEventListener("change", () => {
    const model = renderModelOptions(selectedProvider());
    selectedSourceImages.clear();
    editModeEnabled = false;
    sourceStatus("");
    renderPricing(model);
    renderParameters(model);
    updateSourceSelectionUi();
    setGenerating(false);
  });
  modelSelector?.addEventListener("change", () => {
    const model = selectedModel();
    selectedSourceImages.clear();
    if (!model?.edit_capable) {
      editModeEnabled = false;
    }
    sourceStatus("");
    renderPricing(model);
    renderParameters(model);
    updateSourceSelectionUi();
  });
  editToggle?.addEventListener("click", () => {
    setEditMode(!editModeEnabled);
  });
  sourceClear?.addEventListener("click", () => {
    clearSelectedSources();
    sourceStatus("");
  });
  uploadToggle?.addEventListener("click", () => {
    openUploadOverlay();
  });
  uploadClose?.addEventListener("click", () => {
    closeUploadOverlay();
  });
  uploadOverlay?.addEventListener("click", (event) => {
    if (event.target === uploadOverlay) {
      closeUploadOverlay();
    }
  });
  uploadUrlLoad?.addEventListener("click", () => {
    importUploadUrl().catch((error) => {
      setUploadBusy(false);
      setUploadStatus(error.message || "Image URL could not be imported.", "error");
    });
  });
  uploadUrlInput?.addEventListener("keydown", (event) => {
    if (event.key !== "Enter") {
      return;
    }
    event.preventDefault();
    importUploadUrl().catch((error) => {
      setUploadBusy(false);
      setUploadStatus(error.message || "Image URL could not be imported.", "error");
    });
  });
  uploadFileChoose?.addEventListener("click", () => {
    if (uploadDropTarget?.classList.contains("upload-drop-target-busy")) {
      return;
    }
    uploadFileInput?.click();
  });
  uploadFileInput?.addEventListener("change", () => {
    if (uploadDropTarget?.classList.contains("upload-drop-target-busy")) {
      return;
    }
    let file;
    try {
      file = validateDroppedImage(selectedUploadFiles());
    } catch (error) {
      uploadFileInput.value = "";
      setUploadStatus(error.message || "Selected file is not an image.", "error");
      return;
    }
    if (!file) {
      setUploadStatus("Choose one image file.", "empty");
      return;
    }
    importUploadFile(file);
    uploadFileInput.value = "";
  });
  uploadDropTarget?.addEventListener("dragenter", (event) => {
    event.preventDefault();
    uploadDropTarget.classList.add("upload-drop-target-active");
  });
  uploadDropTarget?.addEventListener("dragover", (event) => {
    event.preventDefault();
    if (event.dataTransfer) {
      event.dataTransfer.dropEffect = "copy";
    }
    uploadDropTarget.classList.add("upload-drop-target-active");
  });
  uploadDropTarget?.addEventListener("dragleave", (event) => {
    if (event.relatedTarget && uploadDropTarget.contains(event.relatedTarget)) {
      return;
    }
    uploadDropTarget.classList.remove("upload-drop-target-active");
  });
  uploadDropTarget?.addEventListener("drop", (event) => {
    event.preventDefault();
    uploadDropTarget.classList.remove("upload-drop-target-active");
    if (uploadDropTarget.classList.contains("upload-drop-target-busy")) {
      return;
    }
    let file;
    try {
      file = validateDroppedImage(droppedFiles(event));
    } catch (error) {
      setUploadStatus(error.message || "Dropped file is not an image.", "error");
      return;
    }
    if (!file) {
      setUploadStatus("Drop one image file.", "empty");
      return;
    }
    importUploadFile(file);
  });
  uploadImmichPrev?.addEventListener("click", () => {
    if (!immichPreviousPage || immichLoading) {
      return;
    }
    loadImmichPage(immichPreviousPage).catch((error) => {
      setUploadStatus(error.message || "Immich gallery could not be loaded.", "error");
    });
  });
  uploadImmichNext?.addEventListener("click", () => {
    if (!immichNextPage || immichLoading) {
      return;
    }
    loadImmichPage(immichNextPage).catch((error) => {
      setUploadStatus(error.message || "Immich gallery could not be loaded.", "error");
    });
  });
  uploadImmichGallery?.addEventListener("click", (event) => {
    const importButton = event.target.closest(".upload-immich-import");
    if (!importButton) {
      return;
    }
    importImmichAsset(importButton.closest(".upload-immich-item")).catch((error) => {
      setUploadStatus(error.message || "Immich image could not be imported.", "error");
    });
  });
  maskEditorClose?.addEventListener("click", () => {
    closeMaskEditor();
  });
  maskEditorOverlay?.addEventListener("click", (event) => {
    if (event.target === maskEditorOverlay) {
      closeMaskEditor();
    }
  });
  maskEditorMask?.addEventListener("pointerdown", startMaskPainting);
  maskEditorMask?.addEventListener("pointermove", continueMaskPainting);
  maskEditorMask?.addEventListener("pointerup", stopMaskPainting);
  maskEditorMask?.addEventListener("pointercancel", stopMaskPainting);
  maskEditorMask?.addEventListener("pointerleave", stopMaskPainting);
  maskEditorBrushSizeInput?.addEventListener("input", updateMaskBrushControls);
  maskEditorBrushFalloffInput?.addEventListener("input", updateMaskBrushControls);
  maskEditorInvert?.addEventListener("click", invertMaskEditorData);
  maskEditorSave?.addEventListener("click", () => {
    saveMaskEditorData().catch((error) => {
      showMessage(error.message || "Mask could not be saved.", "error");
    });
  });
  window.addEventListener("resize", () => {
    if (maskEditorOverlay && !maskEditorOverlay.hidden) {
      redrawMaskEditor();
    }
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && maskEditorOverlay && !maskEditorOverlay.hidden) {
      closeMaskEditor();
      return;
    }
    if (event.key === "Escape" && trashWorkflow.isOpen()) {
      trashWorkflow.close();
      return;
    }
    if (event.key === "Escape" && uploadOverlay && !uploadOverlay.hidden) {
      closeUploadOverlay();
    }
  });
  parameterGrid?.addEventListener("input", (event) => {
    const control = event.target;
    if (!control?.name) {
      return;
    }
    parameterState[control.name] = readControlValue(control);
  });
  parameterGrid?.addEventListener("change", (event) => {
    const control = event.target;
    if (!control?.name) {
      return;
    }
    parameterState[control.name] = readControlValue(control);
    if (control.name === customDimensions(selectedModel())?.activation_parameter) {
      renderParameters(selectedModel());
    }
  });
  renderModelOptions(selectedProvider());
  renderPricing(selectedModel());
  renderParameters(selectedModel());
  updateMaskBrushControls();
  updateSourceSelectionUi();
  form.addEventListener("submit", submitGeneration);
})();
