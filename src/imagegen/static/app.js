(() => {
  const form = document.querySelector(".prompt-form");
  if (!form) {
    return;
  }

  const promptInput = form.querySelector("#prompt");
  const modelSelector = form.querySelector("#model-selector");
  const parameterGrid = form.querySelector(".parameter-grid");
  const generateButton = form.querySelector(".generate-button");
  const messages = form.querySelector(".messages");
  const gallery = document.querySelector(".gallery");
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

  function loadModelRegistry() {
    const element = document.querySelector("#model-registry-data");
    if (!element?.textContent) {
      return [];
    }
    try {
      const models = JSON.parse(element.textContent);
      return Array.isArray(models) ? models : [];
    } catch {
      return [];
    }
  }

  const modelRegistry = loadModelRegistry();
  const parameterState = {};

  function selectedModel() {
    const selectedAlias = modelSelector?.value;
    return (
      modelRegistry.find((model) => model.alias === selectedAlias) ||
      modelRegistry[0] ||
      null
    );
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

  function readControlValue(control) {
    return control.type === "checkbox" ? control.checked : control.value;
  }

  function syncParameterStateFromDom() {
    const controls = form.querySelectorAll(".parameter-grid input, .parameter-grid select");
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
    generateButton.disabled = isGenerating || isPageStale;
    generateButton.setAttribute("aria-busy", isGenerating ? "true" : "false");
    generateButton.textContent = isGenerating
      ? "Generating"
      : generateButton.dataset.defaultLabel || "Generate";
  }

  function markPageStale() {
    isPageStale = true;
    setGenerating(false);
    showMessage("This page is out of date. Reload the page before generating.", "error");
  }

  async function checkAppFreshness() {
    if (!pageChecksum || !form.dataset.apiAppVersionUrl) {
      return true;
    }
    const response = await fetch(form.dataset.apiAppVersionUrl, {
      credentials: "same-origin",
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "App version check failed.");
    }
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
          (parameter.name === control.width_parameter || parameter.name === control.height_parameter)
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
        (parameter.name === dimensionControl.width_parameter || parameter.name === dimensionControl.height_parameter)
      ) {
        return;
      }
      if (dimensionControl && customActive && parameter.name === dimensionControl.scale_parameter) {
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

  function imageFigure(image) {
    const figure = document.createElement("figure");
    figure.className = "gallery-item";
    if (image.metadata_url) {
      figure.dataset.metadataUrl = image.metadata_url;
    }
    if (image.content_type) {
      figure.dataset.contentType = image.content_type;
    }
    if (image.created_at) {
      figure.dataset.createdAt = image.created_at;
    }

    const link = document.createElement("a");
    link.href = image.url;
    link.target = "_blank";
    link.rel = "noopener";

    const img = document.createElement("img");
    img.src = image.url;
    img.alt = image.filename;

    const caption = document.createElement("figcaption");
    caption.textContent = image.filename;

    link.append(img);
    figure.append(link, caption);
    return figure;
  }

  async function refreshGallery() {
    if (!gallery || !form.dataset.apiImagesUrl) {
      return;
    }
    const response = await fetch(form.dataset.apiImagesUrl, {
      credentials: "same-origin",
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "Gallery refresh failed.");
    }
    gallery.replaceChildren();
    if (!Array.isArray(data.images) || data.images.length === 0) {
      const empty = document.createElement("p");
      empty.className = "empty";
      empty.textContent = "No generated images yet.";
      gallery.append(empty);
      return;
    }
    data.images.forEach((image) => gallery.append(imageFigure(image)));
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
      const response = await fetch(statusUrl, {
        credentials: "same-origin",
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || "Generation status request failed.");
      }

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
      const response = await fetch(form.dataset.apiGenerateUrl, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": csrfToken,
        },
        body: JSON.stringify({
          model: modelSelector?.value || undefined,
          prompt,
          parameters: collectParameters(),
        }),
      });
      const data = await response.json();
      if (!response.ok) {
        setGenerating(false);
        showMessage(data.error || "Generation request failed.", "error");
        return;
      }
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

  checkAppFreshness().catch((error) => {
    showMessage(error.message || "App version check failed.", "error");
  });
  modelSelector?.addEventListener("change", () => {
    renderParameters(selectedModel());
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
  renderParameters(selectedModel());
  form.addEventListener("submit", submitGeneration);
})();
