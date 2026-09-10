import { csrfJsonRequest, requestJson } from "./api.js";
import { createElement, createSvgIcon, setBooleanAttribute } from "./dom.js";
import {
  createActionRibbon,
  createImageCard,
  createImageCardRibbon,
  createImageMedia,
  createInfoAction,
  toggleInfoAction,
} from "./image-card.js";

const IMPORT_ICON_PATH =
  "M19.35 10.04A7.49 7.49 0 0 0 12 4 7.5 7.5 0 0 0 5.35 8.04 6 6 0 0 0 6 20h13a5 5 0 0 0 .35-9.96zM14 12h3l-5 5-5-5h3V8h4z";

export function setupImmichImport(root = document, services = {}) {
  const {
    csrfToken = "",
    refreshGallery = async () => {},
    setStatus = () => {},
  } = services;
  const overlay = root.querySelector(".upload-overlay");
  const browser = overlay?.querySelector(".upload-immich-browser");
  const previousButton = browser?.querySelector(".upload-immich-prev");
  const nextButton = browser?.querySelector(".upload-immich-next");
  const pageLabel = browser?.querySelector(".upload-immich-page");
  const emptyState = browser?.querySelector(".upload-immich-empty");
  const gallery = browser?.querySelector(".upload-immich-gallery");
  let currentPage = 1;
  let nextPage = null;
  let previousPage = null;
  let loading = false;

  function setLoading(isLoading) {
    loading = isLoading;
    setBooleanAttribute(gallery, "aria-busy", isLoading);
    if (previousButton) {
      previousButton.disabled = isLoading || !previousPage;
    }
    if (nextButton) {
      nextButton.disabled = isLoading || !nextPage;
    }
  }

  function setPageLabel(text) {
    if (pageLabel) {
      pageLabel.textContent = text;
    }
  }

  function renderAssets(data) {
    if (!gallery || !emptyState) {
      return;
    }
    const assets = Array.isArray(data.assets) ? data.assets : [];
    currentPage = Number.isFinite(data.page) ? data.page : currentPage;
    const pageSize = Number.isFinite(data.page_size) ? data.page_size : 20;
    nextPage = data.next_page || (assets.length >= pageSize ? currentPage + 1 : null);
    previousPage = data.previous_page || null;
    setPageLabel(`Page ${currentPage}`);
    gallery.replaceChildren(
      ...assets.map((asset) => immichAssetFigure(asset, reportThumbnailError)),
    );
    emptyState.hidden = assets.length !== 0;
  }

  async function loadPage(page) {
    const baseUrl = overlay?.dataset.apiImmichAssetsUrl;
    if (!baseUrl || !browser || loading) {
      return;
    }
    setPageLabel("Loading");
    setLoading(true);
    if (emptyState) {
      emptyState.hidden = true;
    }
    const url = new URL(
      baseUrl,
      root.defaultView?.location?.href || window.location.href,
    );
    url.searchParams.set("page", String(page));
    try {
      renderAssets(
        await requestJson(url.toString(), {
          fallbackMessage: "Immich gallery could not be loaded.",
        }),
      );
    } catch (error) {
      setPageLabel(`Page ${currentPage}`);
      throw error;
    } finally {
      setLoading(false);
    }
  }

  async function importAsset(figure) {
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
      const data = await csrfJsonRequest(
        overlay?.dataset.apiImmichImportUrl,
        { asset_id: assetId },
        { csrfToken, fallbackMessage: "Immich image could not be imported." },
      );
      await refreshGallery();
      const filename = data?.image?.filename;
      setStatus(
        filename ? `${filename} imported.` : "Immich image imported.",
        "success",
      );
    } catch (error) {
      if (button) {
        button.disabled = false;
      }
      setStatus(error.message || "Immich image could not be imported.", "error");
    } finally {
      button?.removeAttribute("aria-busy");
    }
  }

  async function reportThumbnailError(thumbnailUrl) {
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

  function open() {
    if (overlay?.dataset.apiImmichAssetsUrl) {
      loadPage(1).catch((error) => {
        setStatus(error.message || "Immich gallery could not be loaded.", "error");
      });
    }
  }

  previousButton?.addEventListener("click", () => {
    if (previousPage && !loading) {
      loadPage(previousPage).catch((error) => {
        setStatus(error.message || "Immich gallery could not be loaded.", "error");
      });
    }
  });
  nextButton?.addEventListener("click", () => {
    if (nextPage && !loading) {
      loadPage(nextPage).catch((error) => {
        setStatus(error.message || "Immich gallery could not be loaded.", "error");
      });
    }
  });
  gallery?.addEventListener("click", (event) => {
    const infoButton = event.target.closest(".gallery-info");
    if (infoButton) {
      toggleInfoAction(gallery, infoButton);
      return;
    }
    const importButton = event.target.closest(".upload-immich-import");
    if (importButton) {
      importAsset(importButton.closest(".upload-immich-item"));
    }
  });

  return { loadPage, open };
}

function immichAssetFigure(asset, reportThumbnailError) {
  const figure = createImageCard("upload-immich-item");
  figure.dataset.assetId = asset.asset_id || "";
  const media = createImageMedia({
    alt: asset.label || "Immich image",
    className: "upload-immich-media",
    loading: "lazy",
    onError: () => {
      figure.classList.add("upload-immich-item-thumbnail-error");
      reportThumbnailError(asset.thumbnail_url);
    },
    src: asset.thumbnail_url || "",
  });
  const caption = createImageCardRibbon();
  const metadata = createElement("span", { className: "upload-immich-metadata" });
  const dimensions =
    asset.width && asset.height ? `${asset.width} x ${asset.height}` : "";
  metadata.append(
    createElement("span", {
      className: "upload-immich-size",
      textContent: dimensions || "Size unavailable",
    }),
    createElement("span", {
      className: "upload-immich-date",
      textContent: asset.created_at || "Date unavailable",
    }),
  );
  const importButton = createElement("button", {
    attributes: {
      "aria-label": `Import ${asset.label || asset.asset_id || "Immich image"}`,
      title: "Import image",
    },
    children: [createSvgIcon(IMPORT_ICON_PATH)],
    className: "gallery-action upload-immich-import",
    disabled: !asset.import_eligible || !asset.asset_id,
    type: "button",
  });
  const actions = createActionRibbon("Immich image actions");
  actions.append(
    createInfoAction({
      label: `Immich image information for ${asset.label || "image"}`,
      tooltipText: asset.label || "Immich image",
    }),
    importButton,
  );
  caption.append(metadata, actions);
  figure.append(media, caption);
  return figure;
}
