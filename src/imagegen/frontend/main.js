import { requestJson } from "./api.js";
import { readJsonScript } from "./dom.js";
import { setupGallery } from "./gallery.js";
import { setupGeneration } from "./generation.js";
import { setupImageUpload } from "./image-upload.js";
import { setupMaskEditor } from "./mask-editor.js";
import { setupMetadata } from "./metadata.js";
import { setupPalettes } from "./palettes.js";
import { setupSourceImages } from "./source-images.js";
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
  const messages = form.querySelector(".messages");
  const csrfToken = document
    .querySelector('meta[name="csrf-token"]')
    ?.getAttribute("content");
  const pageChecksum = document
    .querySelector('meta[name="app-build"]')
    ?.getAttribute("content");
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
  let sourceWorkflow = null;
  let galleryWorkflow = null;
  let generationWorkflow = null;
  let maskEditorWorkflow = null;
  let uploadWorkflow = null;

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

  function updateSourceSelectionUi() {
    sourceWorkflow?.update();
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
    generationWorkflow?.setGenerating(isGenerating);
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
    sourceWorkflow.setFromMetadata(sourceImages, metadata.edit_mode);
    Object.keys(parameterState).forEach((name) => {
      delete parameterState[name];
    });
    Object.assign(parameterState, nextParameters);
    renderPricing(model);
    renderParameters(model);
    updateSourceSelectionUi();
  }

  async function refreshGallery() {
    await galleryWorkflow?.refresh();
  }

  const trashWorkflow = setupTrash(document, {
    csrfToken,
    refreshGallery,
    showMessage,
  });
  sourceWorkflow = setupSourceImages(document, {
    getModel: selectedModel,
  });
  const metadataWorkflow = setupMetadata(document, {
    applyMetadata: applyImageMetadata,
    modelRegistry,
    showMessage,
  });
  maskEditorWorkflow = setupMaskEditor(document, {
    csrfToken,
    refreshGallery,
    showMessage,
  });
  uploadWorkflow = setupImageUpload(document, {
    csrfToken,
    refreshGallery,
  });
  galleryWorkflow = setupGallery(document, {
    csrfToken,
    metadata: metadataWorkflow,
    openMaskEditor: (figure) => maskEditorWorkflow.open(figure),
    removeSourceImage: (filename) => sourceWorkflow.remove(filename),
    setTrashCount: (value) => trashWorkflow.setCount(value),
    showMessage,
    toggleSourceImage: (filename) => sourceWorkflow.toggle(filename),
    updateSourceSelectionUi,
  });
  generationWorkflow = setupGeneration(document, {
    checkAppFreshness,
    collectParameters,
    csrfToken,
    getModel: selectedModel,
    getModelAlias: () => modelSelector?.value || undefined,
    getProvider: () => providerSelector?.value || undefined,
    isPageStale: () => isPageStale,
    pollMilliseconds,
    refreshGallery,
    showMessage,
    sourceState: () => sourceWorkflow.payload(),
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
    sourceWorkflow.resetForProviderChange();
    renderPricing(model);
    renderParameters(model);
    updateSourceSelectionUi();
    setGenerating(false);
  });
  modelSelector?.addEventListener("change", () => {
    const model = selectedModel();
    sourceWorkflow.resetForModelChange();
    renderPricing(model);
    renderParameters(model);
    updateSourceSelectionUi();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && maskEditorWorkflow.isOpen()) {
      maskEditorWorkflow.close();
      return;
    }
    if (event.key === "Escape" && trashWorkflow.isOpen()) {
      trashWorkflow.close();
      return;
    }
    if (event.key === "Escape" && uploadWorkflow.isOpen()) {
      uploadWorkflow.close();
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
  updateSourceSelectionUi();
})();
