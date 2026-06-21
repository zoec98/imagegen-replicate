import { afterEach, describe, expect, test, vi } from "vitest";

import { setupPalettes } from "../../src/imagegen/frontend/palettes.js";

const palettes = [
  {
    display_name: "Character",
    fragments: [
      {
        content: "blue hair",
        display_name: "Zoe",
        name: "zoe",
      },
    ],
    name: "character",
  },
  {
    display_name: "Style",
    fragments: [
      {
        content: "ink wash",
        display_name: "Ink",
        name: "ink",
      },
    ],
    name: "style",
  },
];

afterEach(() => {
  vi.unstubAllGlobals();
  document.body.innerHTML = "";
});

describe("setupPalettes", () => {
  test("inserts a selected palette fragment into the prompt", () => {
    renderPaletteWorkspace();
    const messages = [];

    setupPalettes(document, {
      csrfToken: "token",
      showMessage: (text, category) => messages.push({ category, text }),
    });

    const select = document.querySelector("#palette-character");
    select.value = "zoe";
    select.dispatchEvent(new Event("change", { bubbles: true }));

    expect(document.querySelector("#prompt").value).toBe("(character: zoe blue hair)");
    expect(select.value).toBe("");
    expect(messages).toContainEqual({
      category: "success",
      text: "Zoe inserted.",
    });
  });

  test("opens the palette editor and loads the selected fragment", async () => {
    renderPaletteWorkspace();
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => jsonResponse({ fragment: { content: "updated blue hair" } })),
    );

    setupPalettes(document, { csrfToken: "token" });
    document.querySelector(".palette-editor-toggle").click();
    await vi.waitFor(() => {
      expect(document.querySelector("#palette-editor-content").value).toBe(
        "updated blue hair",
      );
    });

    expect(document.querySelector(".palette-editor").hidden).toBe(false);
    expect(
      document.querySelector(".palette-editor-toggle").getAttribute("aria-pressed"),
    ).toBe("true");
  });

  test("creates a palette fragment and refreshes editor choices", async () => {
    renderPaletteWorkspace();
    const messages = [];
    const fetch = vi
      .fn()
      .mockResolvedValueOnce(
        jsonResponse({
          fragment: { display_name: "New Zoe", name: "new_zoe" },
        }),
      )
      .mockResolvedValueOnce(
        jsonResponse({
          palettes: [
            {
              display_name: "Character",
              fragments: [
                {
                  content: "green hair",
                  display_name: "New Zoe",
                  name: "new_zoe",
                },
              ],
              name: "character",
            },
          ],
        }),
      );
    vi.stubGlobal("fetch", fetch);

    setupPalettes(document, {
      csrfToken: "token",
      showMessage: (text, category) => messages.push({ category, text }),
    });
    document.querySelector("#palette-editor-name").value = "new_zoe";
    document.querySelector("#palette-editor-content").value = "green hair";
    document.querySelector(".palette-editor-create").click();
    await vi.waitFor(() => {
      expect(messages).toContainEqual({
        category: "success",
        text: "New Zoe created.",
      });
    });

    expect(fetch).toHaveBeenNthCalledWith(
      1,
      "/api/palettes/character/fragments",
      expect.objectContaining({
        body: JSON.stringify({ name: "new_zoe", content: "green hair" }),
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": "token",
        },
        method: "POST",
      }),
    );
    expect(document.querySelector("#palette-editor-fragment").value).toBe("new_zoe");
  });

  test("updates a palette fragment", async () => {
    renderPaletteWorkspace();
    const messages = [];
    const fetch = vi
      .fn()
      .mockResolvedValueOnce(
        jsonResponse({ fragment: { display_name: "Zoe", name: "zoe" } }),
      )
      .mockResolvedValueOnce(jsonResponse({ palettes }));
    vi.stubGlobal("fetch", fetch);

    setupPalettes(document, {
      csrfToken: "token",
      showMessage: (text, category) => messages.push({ category, text }),
    });
    document.querySelector("#palette-editor-content").value = "silver hair";
    document.querySelector(".palette-editor-update").click();
    await vi.waitFor(() => {
      expect(messages).toContainEqual({
        category: "success",
        text: "Zoe updated.",
      });
    });

    expect(fetch).toHaveBeenNthCalledWith(
      1,
      "/api/palettes/character/fragments/zoe",
      expect.objectContaining({
        body: JSON.stringify({ content: "silver hair" }),
        method: "PUT",
      }),
    );
  });

  test("deletes a palette fragment", async () => {
    renderPaletteWorkspace();
    const messages = [];
    const fetch = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ deleted: "zoe" }))
      .mockResolvedValueOnce(jsonResponse({ palettes }));
    vi.stubGlobal("fetch", fetch);

    setupPalettes(document, {
      csrfToken: "token",
      showMessage: (text, category) => messages.push({ category, text }),
    });
    document.querySelector("#palette-editor-content").value = "blue hair";
    document.querySelector(".palette-editor-delete").click();
    await vi.waitFor(() => {
      expect(messages).toContainEqual({
        category: "success",
        text: "zoe deleted.",
      });
    });

    expect(fetch).toHaveBeenNthCalledWith(
      1,
      "/api/palettes/character/fragments/zoe",
      expect.objectContaining({
        body: "{}",
        method: "DELETE",
      }),
    );
    expect(document.querySelector("#palette-editor-content").value).toBe("");
  });

  test("shows palette API errors", async () => {
    renderPaletteWorkspace();
    const messages = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        jsonResponse({ error: "Palette fragment could not be loaded." }, { ok: false }),
      ),
    );

    setupPalettes(document, {
      csrfToken: "token",
      showMessage: (text, category) => messages.push({ category, text }),
    });
    document.querySelector(".palette-editor-toggle").click();
    await vi.waitFor(() => {
      expect(messages).toContainEqual({
        category: "error",
        text: "Palette fragment could not be loaded.",
      });
    });
  });
});

function renderPaletteWorkspace() {
  document.body.innerHTML = `
    <script id="palette-data" type="application/json">${JSON.stringify(palettes)}</script>
    <form class="prompt-form" data-api-palettes-url="/api/palettes">
      <textarea id="prompt"></textarea>
      <div class="palette-controls"></div>
      <button class="palette-editor-toggle" type="button"></button>
      <div class="palette-editor" hidden>
        <select id="palette-editor-palette"></select>
        <select id="palette-editor-fragment"></select>
        <input id="palette-editor-name">
        <textarea id="palette-editor-content"></textarea>
        <button class="palette-editor-create" type="button"></button>
        <button class="palette-editor-update" type="button"></button>
        <button class="palette-editor-delete" type="button"></button>
      </div>
    </form>
  `;
}

function jsonResponse(data, { ok = true } = {}) {
  return {
    ok,
    async json() {
      return data;
    },
  };
}
