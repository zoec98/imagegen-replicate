import { csrfFormRequest, csrfJsonRequest } from "./api.js";
import { setBooleanAttribute } from "./dom.js";
import { setupImmichImport } from "./immich-import.js";

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
  let busy = false;

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
    busy = isBusy;
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
    setStatus("Add an image URL, choose image files, or drop image files.", "empty");
    urlInput?.focus();
    immichWorkflow.open();
  }

  function close() {
    if (!overlay) {
      return;
    }
    overlay.hidden = true;
    if (!busy) {
      setBusy(false);
    }
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

  const immichWorkflow = setupImmichImport(root, {
    csrfToken,
    refreshGallery,
    setStatus,
  });

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

  function uploadFileLabel(file) {
    return file?.name || "unnamed file";
  }

  function classifyUploadFiles(files) {
    const accepted = [];
    const failed = [];
    files.forEach((file) => {
      if (!file.type || !file.type.startsWith("image/")) {
        failed.push(`${uploadFileLabel(file)} (not an image)`);
        return;
      }
      accepted.push(file);
    });
    return { accepted, failed };
  }

  async function importUploadFiles(files, emptyMessage) {
    if (files.length === 0) {
      setStatus(emptyMessage, "empty");
      return;
    }
    const { accepted, failed } = classifyUploadFiles(files);
    const imported = [];
    if (accepted.length === 0) {
      setStatus(`No images uploaded; failed: ${failed.join(", ")}.`, "error");
      return;
    }
    setBusy(true);
    try {
      for (const [index, file] of accepted.entries()) {
        setStatus(`Uploading image ${index + 1} of ${accepted.length}.`, "info");
        const formData = new FormData();
        formData.append("image", file);
        try {
          const data = await postForm(
            overlay?.dataset.apiUploadUrl,
            formData,
            "Image file could not be uploaded.",
          );
          imported.push(data?.image?.filename || uploadFileLabel(file));
        } catch (error) {
          failed.push(`${uploadFileLabel(file)}: ${error.message || "upload failed"}`);
        }
      }
      if (imported.length) {
        await refreshGallery();
      }
      if (failed.length) {
        const uploaded = `${imported.length} image${imported.length === 1 ? "" : "s"} uploaded`;
        setStatus(
          `${imported.length ? uploaded : "No images uploaded"}; failed: ${failed.join(", ")}.`,
          "error",
        );
      } else if (imported.length === 1) {
        setStatus(`${imported[0]} imported.`, "success");
      } else {
        setStatus(`${imported.length} images uploaded.`, "success");
      }
    } catch (error) {
      setStatus(error.message || "Image files could not be uploaded.", "error");
    } finally {
      setBusy(false);
    }
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
    importUploadFiles(selectedUploadFiles(), "Choose image files.").catch((error) => {
      setBusy(false);
      setStatus(error.message || "Image files could not be uploaded.", "error");
    });
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
    importUploadFiles(droppedFiles(event), "Drop image files.").catch((error) => {
      setBusy(false);
      setStatus(error.message || "Image files could not be uploaded.", "error");
    });
  });
  return {
    close,
    importUrl,
    isOpen: () => Boolean(overlay && !overlay.hidden),
    open,
  };
}
