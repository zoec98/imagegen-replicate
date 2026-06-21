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
