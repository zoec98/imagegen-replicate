import { describe, expect, it, vi } from "vitest";

import {
  collectGenerationPayload,
  setupGeneration,
} from "../../src/imagegen/frontend/generation.js";

function jsonResponse(data, init = {}) {
  return new Response(JSON.stringify(data), {
    headers: { "Content-Type": "application/json" },
    status: init.status || 200,
  });
}

function renderGenerationWorkspace() {
  document.body.innerHTML = `
    <form class="prompt-form" data-api-generate-url="/api/generate">
      <textarea id="prompt"></textarea>
      <button class="generate-button" data-default-label="Generate" type="submit"></button>
      <div class="messages"></div>
    </form>
  `;
}

describe("collectGenerationPayload", () => {
  it("builds a text generation payload with parameters", () => {
    expect(
      collectGenerationPayload({
        model: "flux",
        parameters: { steps: "4" },
        prompt: "A prompt",
        provider: "replicate",
        sourceState: { editMode: false, sourceImages: [] },
      }),
    ).toEqual({
      model: "flux",
      parameters: { steps: "4" },
      prompt: "A prompt",
      provider: "replicate",
    });
  });

  it("builds an edit-mode generation payload with selected source images", () => {
    expect(
      collectGenerationPayload({
        model: "flux",
        parameters: {},
        prompt: "Edit prompt",
        provider: "replicate",
        sourceState: { editMode: true, sourceImages: ["first.png"] },
      }),
    ).toEqual({
      edit_mode: true,
      model: "flux",
      parameters: {},
      prompt: "Edit prompt",
      provider: "replicate",
      source_images: ["first.png"],
    });
  });
});

describe("setupGeneration", () => {
  it("submits a generation request and starts polling", async () => {
    renderGenerationWorkspace();
    document.querySelector("#prompt").value = "A prompt";
    const checkAppFreshness = vi.fn().mockResolvedValue(true);
    const collectParameters = vi.fn(() => ({ steps: "4" }));
    const sourceState = vi.fn(() => ({ editMode: false, sourceImages: [] }));
    const showMessage = vi.fn();
    const timeout = vi.fn();
    const fetcher = vi.fn().mockResolvedValue(
      jsonResponse({
        poll_seconds: 0.5,
        request_id: "request-1",
        status_url: "/api/status/request-1",
      }),
    );
    vi.stubGlobal("fetch", fetcher);
    vi.stubGlobal("setTimeout", timeout);

    const generation = setupGeneration(document, {
      checkAppFreshness,
      collectParameters,
      csrfToken: "csrf-token",
      getModel: () => ({ alias: "flux" }),
      getModelAlias: () => "flux",
      getProvider: () => "replicate",
      showMessage,
      sourceState,
    });
    await generation.submit(new Event("submit"));

    expect(fetcher).toHaveBeenCalledWith(
      "/api/generate",
      expect.objectContaining({ method: "POST" }),
    );
    expect(JSON.parse(fetcher.mock.calls[0][1].body)).toEqual({
      model: "flux",
      parameters: { steps: "4" },
      prompt: "A prompt",
      provider: "replicate",
    });
    expect(showMessage).toHaveBeenCalledWith("Generation is running.", "info");
    expect(timeout).toHaveBeenCalledWith(expect.any(Function), 500);
  });

  it("shows validation errors before generation requests", async () => {
    renderGenerationWorkspace();
    const showMessage = vi.fn();
    const fetcher = vi.fn();
    vi.stubGlobal("fetch", fetcher);

    const generation = setupGeneration(document, {
      csrfToken: "csrf-token",
      getModel: () => ({ alias: "flux" }),
      showMessage,
    });
    await generation.submit(new Event("submit"));

    expect(fetcher).not.toHaveBeenCalled();
    expect(showMessage).toHaveBeenCalledWith("Prompt is required.", "error");
  });

  it("refreshes the gallery after successful polling", async () => {
    renderGenerationWorkspace();
    const refreshGallery = vi.fn().mockResolvedValue(undefined);
    const showMessage = vi.fn();
    const fetcher = vi.fn().mockResolvedValue(
      jsonResponse({
        request_id: "request-1",
        status: "succeeded",
      }),
    );
    vi.stubGlobal("fetch", fetcher);
    const generation = setupGeneration(document, {
      refreshGallery,
      showMessage,
    });
    document.querySelector(".prompt-form").dataset.activeRequestId = "request-1";

    await generation.poll("/api/status/request-1");

    expect(refreshGallery).toHaveBeenCalled();
    expect(showMessage).toHaveBeenCalledWith("Generation succeeded.", "success");
  });

  it("reports polling errors and clears active generation state", async () => {
    renderGenerationWorkspace();
    const showMessage = vi.fn();
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          jsonResponse({ error: "Generation status request failed." }, { status: 500 }),
        ),
    );
    const generation = setupGeneration(document, { showMessage });
    const form = document.querySelector(".prompt-form");
    form.dataset.activeRequestId = "request-1";

    await generation.poll("/api/status/request-1");

    expect(form.dataset.activeRequestId).toBeUndefined();
    expect(showMessage).toHaveBeenCalledWith(
      "Generation status request failed.",
      "error",
    );
  });
});
