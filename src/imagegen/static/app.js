(() => {
  const form = document.querySelector(".prompt-form");
  if (!form) {
    return;
  }

  const promptInput = form.querySelector("#prompt");
  const modelSelector = form.querySelector("#model-selector");
  const pricingInfo = form.querySelector(".pricing-info");
  const pricingTooltip = form.querySelector(".pricing-tooltip");
  const parameterGrid = form.querySelector(".parameter-grid");
  const paletteControls = form.querySelector(".palette-controls");
  const paletteEditorToggle = form.querySelector(".palette-editor-toggle");
  const paletteEditor = form.querySelector(".palette-editor");
  const paletteEditorPalette = form.querySelector("#palette-editor-palette");
  const paletteEditorFragment = form.querySelector("#palette-editor-fragment");
  const paletteEditorName = form.querySelector("#palette-editor-name");
  const paletteEditorContent = form.querySelector("#palette-editor-content");
  const paletteEditorCreate = form.querySelector(".palette-editor-create");
  const paletteEditorUpdate = form.querySelector(".palette-editor-update");
  const paletteEditorDelete = form.querySelector(".palette-editor-delete");
  const generateButton = form.querySelector(".generate-button");
  const editToggle = form.querySelector(".edit-toggle");
  const sourceCounter = form.querySelector(".source-counter");
  const sourceClear = form.querySelector(".source-clear");
  const sourceSelectionStatus = form.querySelector(".source-selection-status");
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

  function loadJsonData(selector) {
    const element = document.querySelector(selector);
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

  const modelRegistry = loadJsonData("#model-registry-data");
  let paletteData = loadJsonData("#palette-data");
  const parameterState = {};
  const selectedSourceImages = new Set();
  let armedDeleteButton = null;
  let editModeEnabled = false;

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

  function promptAnnotations(prompt) {
    const annotations = [];
    let index = 0;
    while (index < prompt.length) {
      if (prompt[index] !== "(") {
        index += 1;
        continue;
      }
      const match = prompt.slice(index).match(/^\(([A-Za-z][A-Za-z0-9_-]*):/);
      if (!match) {
        index += 1;
        continue;
      }
      const annotation = readPromptAnnotation(prompt, index, match[1]);
      annotations.push(annotation);
      index = annotation.end;
    }
    return annotations;
  }

  function readPromptAnnotation(prompt, start, paletteName) {
    let cursor = start + paletteName.length + 2;
    cursor = requireAnnotationWhitespace(prompt, cursor);
    const fragmentStart = cursor;
    while (
      cursor < prompt.length &&
      !/\s/.test(prompt[cursor]) &&
      prompt[cursor] !== ")"
    ) {
      cursor += 1;
    }
    const fragmentName = prompt.slice(fragmentStart, cursor);
    if (!/^[A-Za-z][A-Za-z0-9_-]*$/.test(fragmentName)) {
      throw new Error("Prompt annotation has an invalid fragment name.");
    }
    cursor = requireAnnotationWhitespace(prompt, cursor);
    const contentStart = cursor;
    while (cursor < prompt.length) {
      if (prompt[cursor] === ")") {
        if (cursor === contentStart) {
          throw new Error("Prompt annotation content is required.");
        }
        return {
          start,
          end: cursor + 1,
          paletteName,
          fragmentName,
          content: prompt.slice(contentStart, cursor),
        };
      }
      if (prompt[cursor] === "(") {
        throw new Error("Prompt annotations may not be nested.");
      }
      if (prompt[cursor] === ":") {
        throw new Error("Prompt annotation content may not contain ':'.");
      }
      cursor += 1;
    }
    throw new Error("Prompt annotation is missing a closing ')'.");
  }

  function requireAnnotationWhitespace(prompt, cursor) {
    if (cursor >= prompt.length || !/\s/.test(prompt[cursor])) {
      throw new Error("Prompt annotation must use '(palette: fragment content)' syntax.");
    }
    while (cursor < prompt.length && /\s/.test(prompt[cursor])) {
      cursor += 1;
    }
    return cursor;
  }

  function fragmentForPalette(paletteName, fragmentName) {
    const palette = paletteData.find((item) => item.name === paletteName);
    if (!palette || !Array.isArray(palette.fragments)) {
      return null;
    }
    return palette.fragments.find((fragment) => fragment.name === fragmentName) || null;
  }

  function annotationText(paletteName, fragment) {
    return `(${paletteName}: ${fragment.name} ${fragment.content})`;
  }

  function annotationAtCursor(annotations, cursor) {
    return (
      annotations.find(
        (annotation) => cursor > annotation.start && cursor < annotation.end,
      ) || null
    );
  }

  function insertPaletteFragment(paletteName, fragmentName) {
    if (!promptInput) {
      return;
    }
    const fragment = fragmentForPalette(paletteName, fragmentName);
    if (!fragment) {
      showMessage("Palette fragment is unavailable.", "error");
      return;
    }

    let annotations = [];
    try {
      annotations = promptAnnotations(promptInput.value);
    } catch (error) {
      showMessage(error.message || "Prompt annotations are invalid.", "error");
      return;
    }

    const cursor = promptInput.selectionStart ?? promptInput.value.length;
    const activeAnnotation = annotationAtCursor(annotations, cursor);
    const nextText = annotationText(paletteName, fragment);
    if (activeAnnotation && activeAnnotation.paletteName !== paletteName) {
      showMessage(
        `Move the cursor outside the ${activeAnnotation.paletteName} annotation first.`,
        "error",
      );
      return;
    }

    promptInput.focus();
    if (activeAnnotation) {
      promptInput.setSelectionRange(activeAnnotation.start, activeAnnotation.end);
    }
    promptInput.setRangeText(nextText, promptInput.selectionStart, promptInput.selectionEnd, "end");
    showMessage(`${fragment.display_name} inserted.`, "success");
  }

  function setPaletteEditorOpen(isOpen) {
    if (paletteEditor) {
      paletteEditor.hidden = !isOpen;
    }
    paletteEditorToggle?.classList.toggle("palette-editor-toggle-active", isOpen);
    paletteEditorToggle?.setAttribute("aria-pressed", isOpen ? "true" : "false");
  }

  function paletteUrl(path = "") {
    const base = form.dataset.apiPalettesUrl || "/api/palettes";
    return `${base}${path}`;
  }

  function encoded(value) {
    return encodeURIComponent(value);
  }

  function renderPromptPaletteControls() {
    if (!paletteControls) {
      return;
    }
    paletteControls.replaceChildren();
    paletteData.forEach((palette) => {
      const label = document.createElement("label");
      label.className = "palette-field";
      label.htmlFor = `palette-${palette.name}`;

      const text = document.createElement("span");
      text.textContent = palette.display_name;

      const select = document.createElement("select");
      select.id = `palette-${palette.name}`;
      select.dataset.paletteName = palette.name;

      const placeholder = document.createElement("option");
      placeholder.value = "";
      placeholder.textContent = `Select ${palette.display_name}`;
      select.append(placeholder);

      (palette.fragments || []).forEach((fragment) => {
        const option = document.createElement("option");
        option.value = fragment.name;
        option.textContent = fragment.display_name;
        select.append(option);
      });

      label.append(text, select);
      paletteControls.append(label);
    });
  }

  function populatePaletteEditor(selectedPalette = "", selectedFragment = "") {
    if (!paletteEditorPalette || !paletteEditorFragment) {
      return;
    }
    paletteEditorPalette.replaceChildren();
    paletteData.forEach((palette) => {
      const option = document.createElement("option");
      option.value = palette.name;
      option.textContent = palette.display_name;
      option.selected = palette.name === selectedPalette;
      paletteEditorPalette.append(option);
    });
    const palette =
      paletteData.find((item) => item.name === paletteEditorPalette.value) ||
      paletteData[0] ||
      null;
    paletteEditorFragment.replaceChildren();
    if (!palette) {
      return;
    }
    (palette.fragments || []).forEach((fragment) => {
      const option = document.createElement("option");
      option.value = fragment.name;
      option.textContent = fragment.display_name;
      option.selected = fragment.name === selectedFragment;
      paletteEditorFragment.append(option);
    });
  }

  async function refreshPaletteData(selectedPalette = "", selectedFragment = "") {
    if (!form.dataset.apiPalettesUrl) {
      return;
    }
    const response = await fetch(form.dataset.apiPalettesUrl, {
      credentials: "same-origin",
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "Palette refresh failed.");
    }
    paletteData = Array.isArray(data.palettes) ? data.palettes : [];
    renderPromptPaletteControls();
    populatePaletteEditor(selectedPalette, selectedFragment);
  }

  async function loadEditorFragment() {
    if (!paletteEditorPalette?.value || !paletteEditorFragment?.value) {
      if (paletteEditorContent) {
        paletteEditorContent.value = "";
      }
      return;
    }
    const response = await fetch(
      paletteUrl(
        `/${encoded(paletteEditorPalette.value)}/fragments/${encoded(
          paletteEditorFragment.value,
        )}`,
      ),
      { credentials: "same-origin" },
    );
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "Palette fragment could not be loaded.");
    }
    if (paletteEditorName) {
      paletteEditorName.value = "";
    }
    if (paletteEditorContent) {
      paletteEditorContent.value = data.fragment?.content || "";
    }
  }

  async function writePaletteFragment(method, url, body) {
    if (!csrfToken) {
      throw new Error("Missing CSRF token.");
    }
    const response = await fetch(url, {
      method,
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": csrfToken,
      },
      body: JSON.stringify(body),
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "Palette edit failed.");
    }
    return data;
  }

  async function createPaletteFragment() {
    const paletteName = paletteEditorPalette?.value || "";
    const name = paletteEditorName?.value || "";
    const content = paletteEditorContent?.value || "";
    const data = await writePaletteFragment(
      "POST",
      paletteUrl(`/${encoded(paletteName)}/fragments`),
      { name, content },
    );
    await refreshPaletteData(paletteName, data.fragment?.name || "");
    showMessage(`${data.fragment?.display_name || "Fragment"} created.`, "success");
  }

  async function updatePaletteFragment() {
    const paletteName = paletteEditorPalette?.value || "";
    const fragmentName = paletteEditorFragment?.value || "";
    const content = paletteEditorContent?.value || "";
    const data = await writePaletteFragment(
      "PUT",
      paletteUrl(`/${encoded(paletteName)}/fragments/${encoded(fragmentName)}`),
      { content },
    );
    await refreshPaletteData(paletteName, data.fragment?.name || fragmentName);
    showMessage(`${data.fragment?.display_name || "Fragment"} updated.`, "success");
  }

  async function deletePaletteFragment() {
    const paletteName = paletteEditorPalette?.value || "";
    const fragmentName = paletteEditorFragment?.value || "";
    const data = await writePaletteFragment(
      "DELETE",
      paletteUrl(`/${encoded(paletteName)}/fragments/${encoded(fragmentName)}`),
      {},
    );
    await refreshPaletteData(paletteName, "");
    if (paletteEditorContent) {
      paletteEditorContent.value = "";
    }
    showMessage(`${data.deleted || "Fragment"} deleted.`, "success");
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
      editToggle.setAttribute("aria-pressed", editModeEnabled ? "true" : "false");
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
      button.setAttribute("aria-pressed", selected ? "true" : "false");
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
      sourceStatus(`Select up to ${limit} source image${limit === 1 ? "" : "s"}.`, true);
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

  function collectGenerationPayload(prompt) {
    const payload = {
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
      return modelRegistry.find((model) => model.alias === metadata.model_alias) || null;
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
    promptInput.value = metadata.prompt;
    modelSelector.value = model.alias;
    selectedSourceImages.clear();
    editModeEnabled = false;
    Object.keys(parameterState).forEach((name) => {
      delete parameterState[name];
    });
    Object.assign(parameterState, nextParameters);
    renderPricing(model);
    renderParameters(model);
    updateSourceSelectionUi();
  }

  async function loadGalleryMetadata(figure) {
    const metadataUrl = figure?.dataset.metadataUrl;
    if (!metadataUrl) {
      showMessage("This image has no embedded metadata to load.", "error");
      return;
    }
    const response = await fetch(metadataUrl, {
      credentials: "same-origin",
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "Image metadata could not be loaded.");
    }
    applyImageMetadata(data);
    showMessage("Image metadata loaded.", "success");
  }

  async function deleteGalleryImage(figure) {
    const deleteUrl = figure?.dataset.deleteUrl;
    const filename = figure?.dataset.filename || "image";
    if (!deleteUrl) {
      showMessage("This image cannot be deleted.", "error");
      return;
    }
    if (!csrfToken) {
      showMessage("Missing CSRF token.", "error");
      return;
    }
    const response = await fetch(deleteUrl, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": csrfToken,
      },
      body: JSON.stringify({}),
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || `Could not delete ${filename}.`);
    }
    selectedSourceImages.delete(filename);
    showMessage(`${filename} deleted.`, "success");
    await refreshGallery();
  }

  function disarmGalleryDelete() {
    if (!armedDeleteButton) {
      return;
    }
    armedDeleteButton.classList.remove("gallery-delete-armed");
    const filename = armedDeleteButton.closest(".gallery-item")?.dataset.filename;
    armedDeleteButton.setAttribute(
      "aria-label",
      `Delete ${filename || "image"}`,
    );
    armedDeleteButton = null;
  }

  function armGalleryDelete(button) {
    if (!button) {
      return;
    }
    if (armedDeleteButton && armedDeleteButton !== button) {
      disarmGalleryDelete();
    }
    armedDeleteButton = button;
    const filename = button.closest(".gallery-item")?.dataset.filename || "image";
    button.classList.add("gallery-delete-armed");
    button.setAttribute("aria-label", `Confirm delete ${filename}`);
    showMessage(`Click delete again to remove ${filename}.`, "info");
  }

  async function uploadGalleryImageToImmich(figure) {
    const uploadUrl = figure?.dataset.immichUploadUrl;
    const filename = figure?.dataset.filename || "image";
    const button = figure?.querySelector(".gallery-immich");
    if (!uploadUrl) {
      showMessage("Immich upload is not configured for this image.", "error");
      return;
    }
    if (!csrfToken) {
      showMessage("Missing CSRF token.", "error");
      return;
    }
    if (button) {
      button.disabled = true;
      button.classList.remove("gallery-immich-failed");
      button.classList.add("gallery-immich-uploading");
      button.setAttribute("aria-label", `Uploading ${filename} to Immich`);
    }
    const response = await fetch(uploadUrl, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": csrfToken,
      },
      body: JSON.stringify({}),
    });
    const data = await response.json();
    if (!response.ok) {
      if (button) {
        button.disabled = false;
        button.classList.remove("gallery-immich-uploading");
        button.classList.add("gallery-immich-failed");
        button.setAttribute("aria-label", `Immich upload failed for ${filename}`);
      }
      throw new Error(data.error || `Could not upload ${filename} to Immich.`);
    }
    if (button) {
      button.disabled = false;
      button.classList.remove("gallery-immich-uploading", "gallery-immich-failed");
      button.classList.add("gallery-immich-uploaded");
      button.setAttribute("aria-label", `${filename} uploaded to Immich`);
    }
    const status = data.status === "already_present" ? "already present" : "uploaded";
    showMessage(`${filename} ${status} in Immich.`, "success");
  }

  async function metadataForInfo(figure) {
    if (!figure?.dataset.metadataUrl) {
      return null;
    }
    if (figure.dataset.infoMetadata) {
      return JSON.parse(figure.dataset.infoMetadata);
    }
    const response = await fetch(figure.dataset.metadataUrl, {
      credentials: "same-origin",
    });
    if (!response.ok) {
      return null;
    }
    const metadata = await response.json();
    figure.dataset.infoMetadata = JSON.stringify(metadata);
    return metadata;
  }

  function imageDimensions(figure) {
    const image = figure?.querySelector("img");
    if (!image?.naturalWidth || !image?.naturalHeight) {
      return "Dimensions unavailable";
    }
    return `${image.naturalWidth} x ${image.naturalHeight}`;
  }

  function updateInfoTooltip(figure, metadata) {
    const tooltip = figure?.querySelector(".image-info-tooltip");
    if (!figure || !tooltip) {
      return;
    }
    const model = metadata ? modelForMetadata(metadata) : null;
    const lines = [
      figure.dataset.filename || "Image",
      model?.display_name || metadata?.model_alias || metadata?.model || "Model unavailable",
      imageDimensions(figure),
      metadata?.prompt || "Prompt unavailable",
    ];
    tooltip.replaceChildren(
      ...lines.map((line) => {
        const item = document.createElement("span");
        item.className = "tooltip-line";
        item.textContent = line;
        return item;
      }),
    );
  }

  function refreshInfoTooltip(figure) {
    updateInfoTooltip(figure, null);
    metadataForInfo(figure)
      .then((metadata) => updateInfoTooltip(figure, metadata))
      .catch(() => updateInfoTooltip(figure, null));
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
    figure.dataset.filename = image.filename;
    if (image.delete_url) {
      figure.dataset.deleteUrl = image.delete_url;
    }
    if (image.immich_upload_url) {
      figure.dataset.immichUploadUrl = image.immich_upload_url;
    }
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

    link.append(img);
    const actions = document.createElement("div");
    actions.className = "gallery-actions";
    actions.setAttribute("aria-label", "Image actions");

    const infoWrap = document.createElement("span");
    infoWrap.className = "image-info-wrap";
    const infoButton = iconButton(
      "gallery-info",
      `Image information for ${image.filename}`,
      "M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm-1 8h2v7h-2zm0-3h2v2h-2z",
    );
    const tooltip = document.createElement("span");
    tooltip.className = "image-info-tooltip";
    tooltip.setAttribute("role", "tooltip");
    const tooltipLine = document.createElement("span");
    tooltipLine.className = "tooltip-line";
    tooltipLine.textContent = image.filename;
    tooltip.append(tooltipLine);
    infoWrap.append(infoButton, tooltip);

    const typeIndicator = document.createElement("span");
    typeIndicator.className = "image-type";
    const extension = image.filename.split(".").pop() || "";
    typeIndicator.textContent = extension.toUpperCase();
    typeIndicator.setAttribute(
      "aria-label",
      `${extension.toUpperCase()} image`,
    );

    let immichButton = null;
    if (image.immich_upload_url) {
      immichButton = iconButton(
        "gallery-immich",
        `Upload ${image.filename} to Immich`,
        "M7 18a5 5 0 1 1 1-9.9A6.5 6.5 0 0 1 20.5 11 3.5 3.5 0 0 1 20 18h-5v-5h3l-6-6-6 6h3v5z",
      );
    }

    const loadButton = iconButton(
      "gallery-load",
      `Load metadata from ${image.filename}`,
      "M3 6.5A2.5 2.5 0 0 1 5.5 4H10l2 2h6.5A2.5 2.5 0 0 1 21 8.5v9A2.5 2.5 0 0 1 18.5 20h-13A2.5 2.5 0 0 1 3 17.5z",
    );
    loadButton.disabled = !image.metadata_url;
    const deleteButton = iconButton(
      "gallery-delete",
      `Delete ${image.filename}`,
      "M9 3h6l1 2h4v2H4V5h4zm-3 6h12l-.7 11H6.7z",
    );
    actions.append(infoWrap, typeIndicator);
    if (immichButton) {
      actions.append(immichButton);
    }
    actions.append(loadButton, deleteButton);

    const sourceButton = document.createElement("button");
    sourceButton.className = "source-select";
    sourceButton.type = "button";
    sourceButton.setAttribute(
      "aria-label",
      `Select ${image.filename} as source image`,
    );

    caption.append(actions);
    figure.append(link, sourceButton, caption);
    return figure;
  }

  function iconButton(className, label, pathData) {
    const button = document.createElement("button");
    button.className = `gallery-action ${className}`;
    button.type = "button";
    button.setAttribute("aria-label", label);

    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("aria-hidden", "true");
    svg.setAttribute("viewBox", "0 0 24 24");
    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    path.setAttribute("d", pathData);
    svg.append(path);
    button.append(svg);
    return button;
  }

  async function refreshGallery() {
    if (!gallery || !form.dataset.apiImagesUrl) {
      return;
    }
    disarmGalleryDelete();
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
    updateSourceSelectionUi();
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
        body: JSON.stringify(collectGenerationPayload(prompt)),
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
  paletteEditorToggle?.addEventListener("click", () => {
    if (!paletteEditor) {
      return;
    }
    const nextOpen = paletteEditor.hidden;
    setPaletteEditorOpen(nextOpen);
    if (nextOpen) {
      populatePaletteEditor(
        paletteEditorPalette?.value || "",
        paletteEditorFragment?.value || "",
      );
      loadEditorFragment().catch((error) => {
        showMessage(error.message || "Palette fragment could not be loaded.", "error");
      });
    }
  });
  paletteControls?.addEventListener("change", (event) => {
    const control = event.target;
    if (!control?.dataset?.paletteName || !control.value) {
      return;
    }
    insertPaletteFragment(control.dataset.paletteName, control.value);
    control.value = "";
  });
  paletteEditorPalette?.addEventListener("change", () => {
    populatePaletteEditor(paletteEditorPalette.value, "");
    loadEditorFragment().catch((error) => {
      showMessage(error.message || "Palette fragment could not be loaded.", "error");
    });
  });
  paletteEditorFragment?.addEventListener("change", () => {
    loadEditorFragment().catch((error) => {
      showMessage(error.message || "Palette fragment could not be loaded.", "error");
    });
  });
  paletteEditorCreate?.addEventListener("click", () => {
    createPaletteFragment().catch((error) => {
      showMessage(error.message || "Palette fragment could not be created.", "error");
    });
  });
  paletteEditorUpdate?.addEventListener("click", () => {
    updatePaletteFragment().catch((error) => {
      showMessage(error.message || "Palette fragment could not be updated.", "error");
    });
  });
  paletteEditorDelete?.addEventListener("click", () => {
    deletePaletteFragment().catch((error) => {
      showMessage(error.message || "Palette fragment could not be deleted.", "error");
    });
  });
  gallery?.addEventListener("click", (event) => {
    const infoButton = event.target.closest(".gallery-info");
    if (infoButton) {
      disarmGalleryDelete();
      refreshInfoTooltip(infoButton.closest(".gallery-item"));
      return;
    }
    const loadButton = event.target.closest(".gallery-load");
    if (loadButton) {
      disarmGalleryDelete();
      const figure = loadButton.closest(".gallery-item");
      loadGalleryMetadata(figure).catch((error) => {
        showMessage(error.message || "Image metadata could not be loaded.", "error");
      });
      return;
    }
    const deleteButton = event.target.closest(".gallery-delete");
    if (deleteButton) {
      const figure = deleteButton.closest(".gallery-item");
      if (armedDeleteButton !== deleteButton) {
        armGalleryDelete(deleteButton);
        return;
      }
      deleteGalleryImage(figure).catch((error) => {
        disarmGalleryDelete();
        showMessage(error.message || "Image could not be deleted.", "error");
      });
      return;
    }
    const immichButton = event.target.closest(".gallery-immich");
    if (immichButton) {
      disarmGalleryDelete();
      const figure = immichButton.closest(".gallery-item");
      uploadGalleryImageToImmich(figure).catch((error) => {
        showMessage(error.message || "Image could not be uploaded to Immich.", "error");
      });
      return;
    }
    const button = event.target.closest(".source-select");
    if (!button) {
      return;
    }
    disarmGalleryDelete();
    const figure = button.closest(".gallery-item");
    toggleSourceImage(figure?.dataset.filename || "");
  });
  gallery?.addEventListener("mouseover", (event) => {
    const infoButton = event.target.closest(".gallery-info");
    if (!infoButton) {
      return;
    }
    refreshInfoTooltip(infoButton.closest(".gallery-item"));
  });
  gallery?.addEventListener("focusin", (event) => {
    const infoButton = event.target.closest(".gallery-info");
    if (!infoButton) {
      return;
    }
    refreshInfoTooltip(infoButton.closest(".gallery-item"));
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
  renderPricing(selectedModel());
  renderParameters(selectedModel());
  populatePaletteEditor();
  setPaletteEditorOpen(!paletteEditor?.hidden);
  updateSourceSelectionUi();
  form.addEventListener("submit", submitGeneration);
})();
