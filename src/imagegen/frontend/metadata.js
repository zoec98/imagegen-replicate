import { requestJson } from "./api.js";
import { createElement } from "./dom.js";

const COMMON_RATIOS = [
  [1, 1],
  [3, 4],
  [4, 3],
  [16, 9],
  [9, 16],
  [2, 3],
  [3, 2],
];
const COMMON_RATIO_TOLERANCE = 0.02;

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

    tooltip.replaceChildren(...lineElements);
  }

  return {
    load,
    refreshTooltip,
  };
}

function imageDimensions(figure) {
  const image = figure?.querySelector("img");
  if (!validDimension(image?.naturalWidth) || !validDimension(image?.naturalHeight)) {
    return "Dimensions unavailable";
  }
  return `${image.naturalWidth} x ${image.naturalHeight} (${imageRatio(
    image.naturalWidth,
    image.naturalHeight,
  )})`;
}

function validDimension(value) {
  return Number.isFinite(value) && value > 0;
}

function imageRatio(width, height) {
  const commonRatio = commonRatioFor(width, height);
  if (commonRatio) {
    return commonRatio;
  }
  const divisor = gcd(width, height);
  return `${width / divisor}:${height / divisor}`;
}

function commonRatioFor(width, height) {
  const actualRatio = width / height;
  for (const [ratioWidth, ratioHeight] of COMMON_RATIOS) {
    const commonRatio = ratioWidth / ratioHeight;
    if (
      Math.abs(actualRatio - commonRatio) / commonRatio <=
      COMMON_RATIO_TOLERANCE
    ) {
      return `${ratioWidth}:${ratioHeight}`;
    }
  }
  return null;
}

function gcd(a, b) {
  let x = a;
  let y = b;
  while (y) {
    const next = x % y;
    x = y;
    y = next;
  }
  return x;
}
