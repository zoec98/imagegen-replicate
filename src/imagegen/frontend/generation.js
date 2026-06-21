import { csrfJsonRequest, requestJson } from "./api.js";
import { setBooleanAttribute } from "./dom.js";

export function collectGenerationPayload({
  model,
  parameters,
  prompt,
  provider,
  sourceState,
}) {
  const payload = {
    provider: provider || undefined,
    model: model || undefined,
    prompt,
    parameters,
  };
  if (sourceState?.editMode) {
    payload.edit_mode = true;
  }
  if (sourceState?.editMode && sourceState.sourceImages?.length > 0) {
    payload.source_images = Array.from(sourceState.sourceImages);
  }
  return payload;
}

export function setupGeneration(root = document, services = {}) {
  const {
    checkAppFreshness = async () => true,
    collectParameters = () => ({}),
    csrfToken = "",
    getModel = () => null,
    getModelAlias = () => undefined,
    getProvider = () => undefined,
    isPageStale = () => false,
    pollMilliseconds = 1000,
    refreshGallery = async () => {},
    showMessage = () => {},
    sourceState = () => ({ editMode: false, sourceImages: [] }),
  } = services;
  const form = root.querySelector(".prompt-form");
  const promptInput = form?.querySelector("#prompt");
  const generateButton = form?.querySelector(".generate-button");
  const terminalStatuses = new Set(["succeeded", "failed", "timeout"]);

  function setGenerating(isGenerating) {
    if (!generateButton) {
      return;
    }
    const hasProviderModel = Boolean(getModel());
    generateButton.disabled = isGenerating || isPageStale() || !hasProviderModel;
    setBooleanAttribute(generateButton, "aria-busy", isGenerating);
    generateButton.textContent = isGenerating
      ? "Generating"
      : generateButton.dataset.defaultLabel || "Generate";
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

  function finish(data) {
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

  async function poll(statusUrl) {
    if (!statusUrl || !form?.dataset.activeRequestId) {
      return;
    }
    try {
      const data = await requestJson(statusUrl, {
        fallbackMessage: "Generation status request failed.",
      });

      if (data.request_id !== form.dataset.activeRequestId) {
        return;
      }

      if (terminalStatuses.has(data.status)) {
        finish(data);
        return;
      }

      showMessage(statusMessage(data), "info");
      window.setTimeout(() => poll(data.status_url || statusUrl), pollMilliseconds);
    } catch (error) {
      delete form.dataset.activeRequestId;
      setGenerating(false);
      showMessage(error.message || "Generation status request failed.", "error");
    }
  }

  async function submit(event) {
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
      const data = await csrfJsonRequest(
        form.dataset.apiGenerateUrl,
        collectGenerationPayload({
          model: getModelAlias(),
          parameters: collectParameters(),
          prompt,
          provider: getProvider(),
          sourceState: sourceState(),
        }),
        { csrfToken, fallbackMessage: "Generation request failed." },
      );
      showMessage("Generation is running.", "info");
      form.dataset.activeRequestId = data.request_id;
      window.setTimeout(
        () => poll(data.status_url),
        Number.isFinite(data.poll_seconds)
          ? Math.max(250, data.poll_seconds * 1000)
          : pollMilliseconds,
      );
    } catch (error) {
      setGenerating(false);
      showMessage(error.message || "Generation request failed.", "error");
    }
  }

  form?.addEventListener("submit", submit);

  return {
    poll,
    setGenerating,
    statusMessage,
    submit,
  };
}
