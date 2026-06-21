export function readJsonScript(selector, { root = document, fallback = [] } = {}) {
  const element = root.querySelector(selector);
  if (!element?.textContent) {
    return fallback;
  }
  try {
    return JSON.parse(element.textContent);
  } catch {
    return fallback;
  }
}

export function createElement(tagName, options = {}) {
  const element = document.createElement(tagName);
  applyElementOptions(element, options);
  return element;
}

export function createSvgIcon(pathData) {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("aria-hidden", "true");
  svg.setAttribute("viewBox", "0 0 24 24");
  const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
  path.setAttribute("d", pathData);
  svg.append(path);
  return svg;
}

export function setBooleanAttribute(element, name, value) {
  if (!element) {
    return;
  }
  element.setAttribute(name, value ? "true" : "false");
}

function applyElementOptions(element, options) {
  const {
    attributes = {},
    children = [],
    className,
    dataset = {},
    textContent,
    ...properties
  } = options;
  if (className) {
    element.className = className;
  }
  if (textContent !== undefined) {
    element.textContent = textContent;
  }
  Object.entries(properties).forEach(([name, value]) => {
    if (value !== undefined) {
      element[name] = value;
    }
  });
  Object.entries(attributes).forEach(([name, value]) => {
    if (value !== undefined) {
      element.setAttribute(name, String(value));
    }
  });
  Object.entries(dataset).forEach(([name, value]) => {
    if (value !== undefined) {
      element.dataset[name] = String(value);
    }
  });
  element.append(...children);
}
