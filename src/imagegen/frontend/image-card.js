import { createElement, createSvgIcon } from "./dom.js";

const INFO_ICON_PATH =
  "M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm-1 8h2v7h-2zm0-3h2v2h-2z";

export function createImageCard(className = "") {
  return createElement("figure", {
    className: ["image-card", className].filter(Boolean).join(" "),
  });
}

export function createImageMedia({
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
  const image = createElement("img", { alt, src });
  if (loading) {
    image.loading = loading;
  }
  if (onError) {
    image.addEventListener("error", onError);
  }
  media.append(image);
  return media;
}

export function createImageCardRibbon(children = []) {
  return createElement("figcaption", {
    children,
    className: "image-card-ribbon",
  });
}

export function createActionRibbon(label) {
  return createElement("div", {
    attributes: { "aria-label": label },
    className: "gallery-actions",
  });
}

export function createInfoAction({ label, tooltipText }) {
  const infoWrap = createElement("span", { className: "image-info-wrap" });
  const infoButton = createElement("button", {
    attributes: { "aria-label": label, title: label },
    children: [createSvgIcon(INFO_ICON_PATH)],
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
  infoWrap.append(infoButton, tooltip);
  return infoWrap;
}

export function toggleInfoAction(container, button) {
  const infoWrap = button?.closest(".image-info-wrap");
  if (!infoWrap) {
    return;
  }
  container?.querySelectorAll(".image-info-wrap").forEach((other) => {
    if (other !== infoWrap) {
      other.classList.remove("image-info-open");
      other.querySelector(".gallery-info")?.classList.remove("gallery-info-active");
    }
  });
  const open = infoWrap.classList.toggle("image-info-open");
  button.classList.toggle("gallery-info-active", open);
}
