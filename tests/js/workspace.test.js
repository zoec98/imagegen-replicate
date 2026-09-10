import { afterEach, expect, test, vi } from "vitest";

import { renderWorkspace } from "./workspace-fixture.js";

const modelRegistry = [
  {
    alias: "seedream45",
    display_name: "Seedream 4.5",
    provider: "replicate",
    parameters: [],
    pricing: [],
  },
  {
    alias: "flux-flex",
    display_name: "Flux 2 Flex",
    provider: "replicate",
    parameters: [],
    pricing: [],
  },
  {
    alias: "bria-fibo",
    display_name: "Bria Fibo",
    provider: "falai",
    parameters: [],
    pricing: [],
  },
];

const generationModelRegistry = [
  {
    alias: "seedream45",
    display_name: "Seedream 4.5",
    provider: "replicate",
    edit_capable: true,
    source_image_max: 2,
    parameters: [
      {
        name: "size",
        type: "string",
        choices: ["1K", "2K"],
        default: "2K",
      },
    ],
    pricing: [],
  },
];

afterEach(() => {
  vi.resetModules();
  document.body.innerHTML = "";
});

test("workspace shows models for the selected provider", async () => {
  renderWorkspace({ modelRegistry, selectedProvider: "replicate" });

  await import("../../src/imagegen/frontend/main.js");

  const modelSelector = document.querySelector("#model-selector");
  expect([...modelSelector.options].map((option) => option.textContent)).toEqual([
    "Seedream 4.5",
    "Flux 2 Flex",
  ]);

  document.querySelector("#provider-selector").value = "falai";
  document
    .querySelector("#provider-selector")
    .dispatchEvent(new Event("change", { bubbles: true }));

  expect([...modelSelector.options].map((option) => option.textContent)).toEqual([
    "Bria Fibo",
  ]);
  expect(modelSelector.value).toBe("bria-fibo");
});

test("workspace controller exposes the selected model", async () => {
  renderWorkspace({ modelRegistry, selectedProvider: "replicate" });

  const { setupWorkspace } = await import("../../src/imagegen/frontend/workspace.js");
  const controller = setupWorkspace(document);

  expect(controller.selectedModel().alias).toBe("seedream45");
});

test("workspace submits the selected model, parameters, and source images", async () => {
  renderWorkspace({
    modelRegistry: generationModelRegistry,
    selectedProvider: "replicate",
  });
  document.querySelector(".gallery").innerHTML = `
    <figure class="gallery-item" data-filename="source.png">
      <button class="source-select" type="button"></button>
    </figure>
  `;
  const fetcher = vi.fn().mockResolvedValue(
    new Response(
      JSON.stringify({
        poll_seconds: 60,
        request_id: "request-1",
        status_url: "/api/generation/request-1",
      }),
      { headers: { "Content-Type": "application/json" } },
    ),
  );
  vi.stubGlobal("fetch", fetcher);
  vi.stubGlobal("setTimeout", vi.fn());

  await import("../../src/imagegen/frontend/main.js");

  document.querySelector("#prompt").value = "A fox in snow";
  document.querySelector(".edit-toggle").click();
  document.querySelector(".source-select").click();
  document
    .querySelector(".prompt-form")
    .dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
  for (let index = 0; index < 5; index += 1) {
    await Promise.resolve();
  }

  expect(fetcher).toHaveBeenCalledTimes(1);
  expect(fetcher.mock.calls[0][0]).toBe("/api/generate");
  expect(JSON.parse(fetcher.mock.calls[0][1].body)).toEqual({
    edit_mode: true,
    model: "seedream45",
    parameters: { size: "2K" },
    prompt: "A fox in snow",
    provider: "replicate",
    source_images: ["source.png"],
  });
});
