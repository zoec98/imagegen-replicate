(() => {
  const form = document.querySelector(".prompt-form");
  if (!form) {
    return;
  }

  const promptInput = form.querySelector("#prompt");
  const generateButton = form.querySelector(".generate-button");
  const messages = form.querySelector(".messages");
  const csrfToken = document
    .querySelector('meta[name="csrf-token"]')
    ?.getAttribute("content");

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

  function setGenerating(isGenerating) {
    if (!generateButton) {
      return;
    }
    generateButton.disabled = isGenerating;
    generateButton.setAttribute("aria-busy", isGenerating ? "true" : "false");
    generateButton.textContent = isGenerating
      ? "Generating"
      : generateButton.dataset.defaultLabel || "Generate";
  }

  function collectParameters() {
    const parameters = {};
    const controls = form.querySelectorAll(".parameter-grid input, .parameter-grid select");
    controls.forEach((control) => {
      if (!control.name || control.disabled) {
        return;
      }
      if (control.type === "checkbox") {
        parameters[control.name] = control.checked;
        return;
      }
      parameters[control.name] = control.value;
    });
    return parameters;
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
    } catch (error) {
      setGenerating(false);
      showMessage(error.message || "Generation request failed.", "error");
    }
  }

  form.addEventListener("submit", submitGeneration);
})();
