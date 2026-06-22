import { csrfJsonRequest } from "./api.js";

export function setupMaskEditor(root = document, services = {}) {
  const {
    csrfToken = "",
    imageFactory = () => new Image(),
    refreshGallery = async () => {},
    showMessage = () => {},
  } = services;
  const overlay = root.querySelector(".mask-editor-overlay");
  const stage = overlay?.querySelector(".mask-editor-stage");
  const wrap = overlay?.querySelector(".mask-editor-canvas-wrap");
  const sourceCanvas = overlay?.querySelector(".mask-editor-source");
  const maskCanvas = overlay?.querySelector(".mask-editor-mask");
  const operationInput = overlay?.querySelector(".mask-editor-operation");
  const brushControls = overlay?.querySelector(".mask-editor-brush-controls");
  const cropControls = overlay?.querySelector(".mask-editor-crop-controls");
  const blurControls = overlay?.querySelector(".mask-editor-blur-controls");
  const cropButton = overlay?.querySelector(".mask-editor-crop");
  const brushSizeInput = overlay?.querySelector(".mask-editor-brush-size");
  const brushFalloffInput = overlay?.querySelector(".mask-editor-brush-falloff");
  const brushSizeValue = overlay?.querySelector(".mask-editor-brush-size-value");
  const brushFalloffValue = overlay?.querySelector(".mask-editor-brush-falloff-value");
  const invertButton = overlay?.querySelector(".mask-editor-invert");
  const saveButton = overlay?.querySelector(".mask-editor-save");
  const title = overlay?.querySelector("#mask-editor-title");
  const closeButton = overlay?.querySelector(".mask-editor-close");
  let sourceImage = null;
  let maskData = null;
  let isPainting = false;
  let brushSize = 48;
  let brushFalloff = 0.65;
  let operation = "crop";
  let cropStart = null;
  let cropSelection = null;
  let isCropping = false;

  function numberFromInput(input, fallback) {
    const value = Number.parseFloat(input?.value || "");
    return Number.isFinite(value) ? value : fallback;
  }

  function updateBrushControls() {
    brushSize = Math.max(numberFromInput(brushSizeInput, brushSize), 1);
    brushFalloff =
      Math.min(
        Math.max(numberFromInput(brushFalloffInput, brushFalloff * 100), 0),
        100,
      ) / 100;
    if (brushSizeValue) {
      brushSizeValue.textContent = `${Math.round(brushSize)} px`;
    }
    if (brushFalloffValue) {
      brushFalloffValue.textContent = `${Math.round(brushFalloff * 100)}%`;
    }
  }

  function updateOperationControls() {
    operation = operationInput?.value || "mask";
    if (!["crop", "blur", "mask"].includes(operation)) {
      operation = "mask";
    }
    if (operationInput && operationInput.value !== operation) {
      operationInput.value = operation;
    }
    if (brushControls) {
      brushControls.hidden = operation === "crop";
    }
    if (cropControls) {
      cropControls.hidden = operation !== "crop";
    }
    if (blurControls) {
      blurControls.hidden = operation !== "blur";
    }
    if (invertButton) {
      invertButton.hidden = operation !== "mask";
    }
    if (saveButton) {
      saveButton.hidden = operation !== "mask";
    }
  }

  function resetOperation() {
    operation = "crop";
    if (operationInput) {
      operationInput.value = operation;
    }
    updateOperationControls();
  }

  function resetCropSelection() {
    cropStart = null;
    cropSelection = null;
    isCropping = false;
    updateCropControls();
  }

  function open(figure) {
    const filename = figure?.dataset.filename;
    const imageUrl = figure?.querySelector("img")?.src;
    const cropSaveUrl = figure?.dataset.cropSaveUrl;
    const maskUrl = figure?.dataset.maskUrl;
    const maskSaveUrl = figure?.dataset.maskSaveUrl;
    if (
      !overlay ||
      !sourceCanvas ||
      !maskCanvas ||
      !filename ||
      !imageUrl ||
      !cropSaveUrl ||
      !maskUrl ||
      !maskSaveUrl
    ) {
      return;
    }
    overlay.dataset.filename = filename;
    overlay.dataset.imageUrl = imageUrl;
    overlay.dataset.cropSaveUrl = cropSaveUrl;
    overlay.dataset.maskUrl = maskUrl;
    overlay.dataset.maskSaveUrl = maskSaveUrl;
    if (title) {
      title.textContent = filename;
    }
    resetCropSelection();
    resetOperation();
    updateBrushControls();
    overlay.hidden = false;
    loadImage(imageUrl);
    closeButton?.focus();
  }

  function close() {
    if (!overlay) {
      return;
    }
    overlay.hidden = true;
    delete overlay.dataset.filename;
    delete overlay.dataset.imageUrl;
    delete overlay.dataset.cropSaveUrl;
    delete overlay.dataset.maskUrl;
    delete overlay.dataset.maskSaveUrl;
    sourceImage = null;
    maskData = null;
    isPainting = false;
    resetCropSelection();
    resetOperation();
    resetCanvases();
    if (title) {
      title.textContent = "Image editor";
    }
  }

  function loadImage(imageUrl) {
    const image = imageFactory();
    image.onload = () => {
      if (overlay?.dataset.imageUrl !== imageUrl) {
        return;
      }
      sourceImage = image;
      maskData = new Float32Array(image.naturalWidth * image.naturalHeight);
      resetCanvases(image.naturalWidth, image.naturalHeight);
      redraw();
    };
    image.onerror = () => {
      if (overlay?.dataset.imageUrl === imageUrl) {
        showMessage("Mask source image could not be loaded.", "error");
        close();
      }
    };
    image.src = imageUrl;
  }

  function resetCanvases(width = 0, height = 0) {
    [sourceCanvas, maskCanvas].forEach((canvas) => {
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
    if (wrap) {
      wrap.style.width = "";
      wrap.style.height = "";
    }
  }

  function resizeCanvases() {
    if (!stage || !wrap || !sourceImage || !sourceCanvas || !maskCanvas) {
      return;
    }
    const maxWidth = Math.max(stage.clientWidth, 1);
    const maxHeight = Math.max(window.innerHeight - 176, 192);
    const scale = Math.min(
      maxWidth / sourceImage.naturalWidth,
      maxHeight / sourceImage.naturalHeight,
      1,
    );
    const displayWidth = Math.max(Math.round(sourceImage.naturalWidth * scale), 1);
    const displayHeight = Math.max(Math.round(sourceImage.naturalHeight * scale), 1);
    wrap.style.width = `${displayWidth}px`;
    wrap.style.height = `${displayHeight}px`;
    [sourceCanvas, maskCanvas].forEach((canvas) => {
      canvas.style.width = `${displayWidth}px`;
      canvas.style.height = `${displayHeight}px`;
    });
  }

  function redraw() {
    if (!sourceImage || !sourceCanvas || !maskCanvas) {
      return;
    }
    resizeCanvases();
    const sourceContext = sourceCanvas.getContext("2d");
    sourceContext?.clearRect(0, 0, sourceCanvas.width, sourceCanvas.height);
    sourceContext?.drawImage(
      sourceImage,
      0,
      0,
      sourceCanvas.width,
      sourceCanvas.height,
    );
    redrawOverlay();
  }

  function redrawOverlay() {
    if (!maskCanvas || !maskData) {
      return;
    }
    const context = maskCanvas.getContext("2d");
    if (!context) {
      return;
    }
    if (operation === "crop") {
      redrawCropOverlay(context);
      return;
    }
    const imageData = context.createImageData(maskCanvas.width, maskCanvas.height);
    for (let index = 0; index < maskData.length; index += 1) {
      const alpha = Math.round(Math.min(maskData[index], 1) * 150);
      const offset = index * 4;
      imageData.data[offset] = 255;
      imageData.data[offset + 1] = 42;
      imageData.data[offset + 2] = 42;
      imageData.data[offset + 3] = alpha;
    }
    context.putImageData(imageData, 0, 0);
  }

  function redrawCropOverlay(context) {
    context.clearRect(0, 0, maskCanvas.width, maskCanvas.height);
    if (!cropSelection) {
      return;
    }
    context.fillStyle = "rgba(15, 23, 42, 0.48)";
    context.fillRect(0, 0, maskCanvas.width, maskCanvas.height);
    context.clearRect(
      cropSelection.x,
      cropSelection.y,
      cropSelection.width,
      cropSelection.height,
    );
    context.strokeStyle = "#ffffff";
    context.lineWidth = Math.max(Math.round(maskCanvas.width / 300), 1);
    context.strokeRect(
      cropSelection.x,
      cropSelection.y,
      cropSelection.width,
      cropSelection.height,
    );
  }

  function pointerPosition(event) {
    if (!maskCanvas) {
      return null;
    }
    const rect = maskCanvas.getBoundingClientRect();
    if (rect.width <= 0 || rect.height <= 0) {
      return null;
    }
    return {
      x: ((event.clientX - rect.left) / rect.width) * maskCanvas.width,
      y: ((event.clientY - rect.top) / rect.height) * maskCanvas.height,
      scale: maskCanvas.width / rect.width,
    };
  }

  function paintAt(position) {
    if (!position || !maskCanvas || !maskData) {
      return;
    }
    const radius = Math.max((brushSize * position.scale) / 2, 1);
    const innerRadius = radius * (1 - brushFalloff);
    const minX = Math.max(Math.floor(position.x - radius), 0);
    const maxX = Math.min(Math.ceil(position.x + radius), maskCanvas.width - 1);
    const minY = Math.max(Math.floor(position.y - radius), 0);
    const maxY = Math.min(Math.ceil(position.y + radius), maskCanvas.height - 1);
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
        const index = y * maskCanvas.width + x;
        maskData[index] = Math.max(maskData[index], intensity);
      }
    }
    redrawOverlay();
  }

  function cropRectangle(start, end) {
    if (!start || !end) {
      return null;
    }
    const minX = Math.max(Math.min(start.x, end.x), 0);
    const minY = Math.max(Math.min(start.y, end.y), 0);
    const maxX = Math.min(Math.max(start.x, end.x), maskCanvas.width);
    const maxY = Math.min(Math.max(start.y, end.y), maskCanvas.height);
    return {
      height: Math.round(maxY - minY),
      width: Math.round(maxX - minX),
      x: Math.round(minX),
      y: Math.round(minY),
    };
  }

  function isValidCropSelection() {
    return Boolean(cropSelection?.width >= 10 && cropSelection?.height >= 10);
  }

  function updateCropControls() {
    if (cropButton) {
      cropButton.disabled = !isValidCropSelection();
    }
  }

  function startCrop(event) {
    if (!maskCanvas || !sourceImage) {
      return;
    }
    const position = pointerPosition(event);
    if (!position) {
      return;
    }
    event.preventDefault();
    cropStart = position;
    cropSelection = null;
    isCropping = true;
    maskCanvas.setPointerCapture?.(event.pointerId);
    updateCropControls();
    redrawOverlay();
  }

  function continueCrop(event) {
    if (!isCropping || !cropStart) {
      return;
    }
    const position = pointerPosition(event);
    if (!position) {
      return;
    }
    event.preventDefault();
    cropSelection = cropRectangle(cropStart, position);
    updateCropControls();
    redrawOverlay();
  }

  function stopCrop(event) {
    if (!isCropping) {
      return;
    }
    isCropping = false;
    maskCanvas?.releasePointerCapture?.(event.pointerId);
    updateCropControls();
  }

  async function crop() {
    if (!overlay?.dataset.cropSaveUrl) {
      showMessage("Crop URL is unavailable.", "error");
      return;
    }
    if (!csrfToken) {
      showMessage("Missing CSRF token.", "error");
      return;
    }
    if (!isValidCropSelection()) {
      return;
    }
    if (cropButton) {
      cropButton.disabled = true;
    }
    showMessage("Cropping image.", "info");
    try {
      const data = await csrfJsonRequest(
        overlay.dataset.cropSaveUrl,
        { rectangle: cropSelection },
        { csrfToken, fallbackMessage: "Image could not be cropped." },
      );
      close();
      await refreshGallery();
      showMessage(`${data.image?.filename || "Image"} cropped.`, "success");
    } catch (error) {
      showMessage(error.message || "Image could not be cropped.", "error");
      updateCropControls();
    }
  }

  function invert() {
    if (!maskData) {
      return;
    }
    for (let index = 0; index < maskData.length; index += 1) {
      maskData[index] = 1 - Math.min(Math.max(maskData[index], 0), 1);
    }
    redrawOverlay();
  }

  function pngDataUrl() {
    if (!maskCanvas || !maskData) {
      throw new Error("Mask data is unavailable.");
    }
    const canvas = document.createElement("canvas");
    canvas.width = maskCanvas.width;
    canvas.height = maskCanvas.height;
    const context = canvas.getContext("2d");
    if (!context) {
      throw new Error("Mask export is unavailable.");
    }
    const imageData = context.createImageData(canvas.width, canvas.height);
    for (let index = 0; index < maskData.length; index += 1) {
      const value = Math.round(Math.min(Math.max(maskData[index], 0), 1) * 255);
      const offset = index * 4;
      imageData.data[offset] = value;
      imageData.data[offset + 1] = value;
      imageData.data[offset + 2] = value;
      imageData.data[offset + 3] = 255;
    }
    context.putImageData(imageData, 0, 0);
    return canvas.toDataURL("image/png");
  }

  async function save() {
    if (!overlay?.dataset.maskSaveUrl) {
      showMessage("Mask save URL is unavailable.", "error");
      return;
    }
    if (!csrfToken) {
      showMessage("Missing CSRF token.", "error");
      return;
    }
    if (saveButton) {
      saveButton.disabled = true;
    }
    showMessage("Saving mask.", "info");
    try {
      const data = await csrfJsonRequest(
        overlay.dataset.maskSaveUrl,
        { mask_png: pngDataUrl() },
        { csrfToken, fallbackMessage: "Mask could not be saved." },
      );
      close();
      await refreshGallery();
      showMessage(`${data.filename || "Mask"} saved.`, "success");
    } catch (error) {
      showMessage(error.message || "Mask could not be saved.", "error");
    } finally {
      if (saveButton) {
        saveButton.disabled = false;
      }
    }
  }

  function startPainting(event) {
    if (operation === "crop") {
      startCrop(event);
      return;
    }
    if (!maskData || !maskCanvas) {
      return;
    }
    event.preventDefault();
    isPainting = true;
    maskCanvas.setPointerCapture?.(event.pointerId);
    paintAt(pointerPosition(event));
  }

  function continuePainting(event) {
    if (operation === "crop") {
      continueCrop(event);
      return;
    }
    if (!isPainting) {
      return;
    }
    event.preventDefault();
    paintAt(pointerPosition(event));
  }

  function stopPainting(event) {
    if (operation === "crop") {
      stopCrop(event);
      return;
    }
    if (!isPainting) {
      return;
    }
    isPainting = false;
    maskCanvas?.releasePointerCapture?.(event.pointerId);
  }

  closeButton?.addEventListener("click", () => {
    close();
  });
  overlay?.addEventListener("click", (event) => {
    if (event.target === overlay) {
      close();
    }
  });
  maskCanvas?.addEventListener("pointerdown", startPainting);
  maskCanvas?.addEventListener("pointermove", continuePainting);
  maskCanvas?.addEventListener("pointerup", stopPainting);
  maskCanvas?.addEventListener("pointercancel", stopPainting);
  maskCanvas?.addEventListener("pointerleave", stopPainting);
  brushSizeInput?.addEventListener("input", updateBrushControls);
  brushFalloffInput?.addEventListener("input", updateBrushControls);
  operationInput?.addEventListener("change", updateOperationControls);
  cropButton?.addEventListener("click", () => {
    crop().catch((error) => {
      showMessage(error.message || "Image could not be cropped.", "error");
    });
  });
  invertButton?.addEventListener("click", invert);
  saveButton?.addEventListener("click", () => {
    save().catch((error) => {
      showMessage(error.message || "Mask could not be saved.", "error");
    });
  });
  window.addEventListener("resize", () => {
    if (overlay && !overlay.hidden) {
      redraw();
    }
  });

  updateBrushControls();
  updateOperationControls();

  return {
    close,
    isOpen: () => Boolean(overlay && !overlay.hidden),
    open,
    redraw,
    save,
    updateBrushControls,
    updateOperationControls,
  };
}
