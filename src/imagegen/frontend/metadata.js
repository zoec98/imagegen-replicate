import { requestJson } from "./api.js";
import { createElement, createSvgIcon } from "./dom.js";

export function setupMetadata(root = document, services = {}) {
  void root;
  const {
    applyMetadata = () => {},
    modelRegistry = [],
    showMessage = () => {},
  } = services;

  async function load(figure) {
    const metadataUrl = figure?.dataset.metadataUrl;
    if (!metadataUrl) {
      showMessage("This image has no embedded metadata to load.", "error");
      return;
    }
    const data = await requestJson(metadataUrl, {
      fallbackMessage: "Image metadata could not be loaded.",
    });
    applyMetadata(data);
    const warnings = Array.isArray(data.warnings) ? data.warnings : [];
    showMessage(
      warnings.length
        ? `Image metadata loaded. ${warnings.join(" ")}`
        : "Image metadata loaded.",
      warnings.length ? "warning" : "success",
    );
  }

  async function metadataForInfo(figure) {
    if (!figure?.dataset.metadataUrl) {
      return null;
    }
    if (figure.dataset.infoMetadata) {
      return JSON.parse(figure.dataset.infoMetadata);
    }
    let metadata;
    try {
      metadata = await requestJson(figure.dataset.metadataUrl);
    } catch {
      return null;
    }
    figure.dataset.infoMetadata = JSON.stringify(metadata);
    return metadata;
  }

  function refreshTooltip(figure) {
    updateInfoTooltip(figure, null);
    metadataForInfo(figure)
      .then((metadata) => updateInfoTooltip(figure, metadata))
      .catch(() => updateInfoTooltip(figure, null));
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

  function updateInfoTooltip(figure, metadata) {
    const tooltip = figure?.querySelector(".image-info-tooltip");
    if (!figure || !tooltip) {
      return;
    }
    const model = metadata ? modelForMetadata(metadata) : null;
    const prompt = metadata?.prompt || null;
    const lines = [
      figure.dataset.filename || "Image",
      model?.display_name ||
        metadata?.model_alias ||
        metadata?.model ||
        "Model unavailable",
      imageDimensions(figure),
      prompt || "Prompt unavailable",
    ];

    const lineElements = lines.map((line) =>
      createElement("span", {
        className: "tooltip-line",
        textContent: line,
      }),
    );

    const children = [...lineElements];

    if (prompt) {
      const copyBtn = createElement("button", {
        attributes: { "aria-label": "Copy prompt", title: "Copy prompt" },
        className: "tooltip-copy-prompt",
        type: "button",
        children: [
          createSvgIcon(
            "M16 1H4c-1.1 0-2 .9-2 2v14h2V3h12V1zm3 4H8c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h11c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0 16H8V7h11v14z",
          ),
        ],
      });
      copyBtn.addEventListener("click", (event) => {
        event.stopPropagation();
        navigator.clipboard.writeText(prompt).then(() => {
          copyBtn.classList.add("tooltip-copy-prompt-done");
          copyBtn.setAttribute("aria-label", "Prompt copied!");
          setTimeout(() => {
            copyBtn.classList.remove("tooltip-copy-prompt-done");
            copyBtn.setAttribute("aria-label", "Copy prompt");
          }, 1500);
        });
      });
      children.push(copyBtn);
    }

    tooltip.replaceChildren(...children);
  }

  return {
    load,
    refreshTooltip,
  };
}

function imageDimensions(figure) {
  const image = figure?.querySelector("img");
  if (!image?.naturalWidth || !image?.naturalHeight) {
    return "Dimensions unavailable";
  }
  return `${image.naturalWidth} x ${image.naturalHeight}`;
}
