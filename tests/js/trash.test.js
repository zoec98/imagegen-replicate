import { afterEach, describe, expect, test, vi } from "vitest";

import { setupTrash } from "../../src/imagegen/frontend/trash.js";

afterEach(() => {
  vi.unstubAllGlobals();
  document.body.innerHTML = "";
});

describe("setupTrash", () => {
  test("opens the trash overlay and lists trash images", async () => {
    renderTrashWorkspace();
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        jsonResponse({
          images: [
            {
              filename: "old.png",
              restore_url: "/api/trash/old.png/restore",
              url: "/trash/old.png",
            },
          ],
          trash_count: 1,
        }),
      ),
    );

    setupTrash(document, { csrfToken: "token" });
    document.querySelector(".trashcan-toggle").click();
    await vi.waitFor(() => {
      expect(document.querySelector(".trashcan-count").textContent).toBe("1");
    });

    expect(document.querySelector(".trash-overlay").hidden).toBe(false);
    expect(document.querySelector(".trash-empty-state").hidden).toBe(true);
    expect(document.querySelector(".trash-item").dataset.filename).toBe("old.png");
    expect(document.querySelector(".trash-restore").textContent).toBe("Restore");
  });

  test("shows an empty state when trash is empty", async () => {
    renderTrashWorkspace();
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => jsonResponse({ images: [], trash_count: 0 })),
    );

    setupTrash(document, { csrfToken: "token" });
    document.querySelector(".trashcan-toggle").click();
    await vi.waitFor(() => {
      expect(document.querySelector(".trash-empty-state").hidden).toBe(false);
    });

    expect(document.querySelector(".trash-gallery").children).toHaveLength(0);
  });

  test("reports list errors without closing the overlay", async () => {
    renderTrashWorkspace();
    const messages = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => jsonResponse({ error: "Trash unavailable." }, { ok: false })),
    );

    setupTrash(document, {
      csrfToken: "token",
      showMessage: (text, category) => messages.push({ category, text }),
    });
    document.querySelector(".trashcan-toggle").click();
    await vi.waitFor(() => {
      expect(messages).toEqual([{ category: "error", text: "Trash unavailable." }]);
    });

    expect(document.querySelector(".trash-overlay").hidden).toBe(false);
  });

  test("closes the trash overlay with the close button and backdrop", async () => {
    renderTrashWorkspace();
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => jsonResponse({ images: [], trash_count: 0 })),
    );

    setupTrash(document, { csrfToken: "token" });
    document.querySelector(".trashcan-toggle").click();
    await vi.waitFor(() => {
      expect(document.querySelector(".trash-empty-state").hidden).toBe(false);
    });
    document.querySelector(".trash-close").click();
    expect(document.querySelector(".trash-overlay").hidden).toBe(true);

    document.querySelector(".trashcan-toggle").click();
    await vi.waitFor(() => {
      expect(document.querySelector(".trash-empty-state").hidden).toBe(false);
    });
    document
      .querySelector(".trash-overlay")
      .dispatchEvent(new MouseEvent("click", { bubbles: true }));
    expect(document.querySelector(".trash-overlay").hidden).toBe(true);
  });

  test("restores a trash image and refreshes gallery state", async () => {
    renderTrashWorkspace();
    const messages = [];
    const refreshGallery = vi.fn(async () => {});
    const fetch = vi
      .fn()
      .mockResolvedValueOnce(
        jsonResponse({
          images: [
            {
              filename: "old.png",
              restore_url: "/api/trash/old.png/restore",
              url: "/trash/old.png",
            },
          ],
          trash_count: 1,
        }),
      )
      .mockResolvedValueOnce(jsonResponse({ filename: "old.png", trash_count: 0 }))
      .mockResolvedValueOnce(jsonResponse({ images: [], trash_count: 0 }));
    vi.stubGlobal("fetch", fetch);

    setupTrash(document, {
      csrfToken: "token",
      refreshGallery,
      showMessage: (text, category) => messages.push({ category, text }),
    });
    document.querySelector(".trashcan-toggle").click();
    await vi.waitFor(() => {
      expect(document.querySelector(".trash-restore")).not.toBeNull();
    });
    document.querySelector(".trash-restore").click();
    await vi.waitFor(() => {
      expect(messages).toContainEqual({
        category: "success",
        text: "old.png restored.",
      });
    });

    expect(fetch).toHaveBeenNthCalledWith(
      2,
      "/api/trash/old.png/restore",
      expect.objectContaining({
        body: "{}",
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": "token",
        },
        method: "POST",
      }),
    );
    expect(refreshGallery).toHaveBeenCalledOnce();
    expect(document.querySelector(".trashcan-count").textContent).toBe("0");
  });

  test("empties trash and refreshes the trash listing", async () => {
    renderTrashWorkspace();
    const messages = [];
    const fetch = vi
      .fn()
      .mockResolvedValueOnce(
        jsonResponse({ deleted: ["a.png", "b.png"], trash_count: 0 }),
      )
      .mockResolvedValueOnce(jsonResponse({ images: [], trash_count: 0 }));
    vi.stubGlobal("fetch", fetch);

    setupTrash(document, {
      csrfToken: "token",
      showMessage: (text, category) => messages.push({ category, text }),
    });
    document.querySelector(".trash-empty").click();
    await vi.waitFor(() => {
      expect(messages).toContainEqual({
        category: "success",
        text: "2 trash images deleted.",
      });
    });

    expect(fetch).toHaveBeenNthCalledWith(
      1,
      "/api/trash/empty",
      expect.objectContaining({
        body: "{}",
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": "token",
        },
        method: "POST",
      }),
    );
    expect(document.querySelector(".trashcan-count").textContent).toBe("0");
    expect(document.querySelector(".trash-empty").disabled).toBe(false);
  });
});

function renderTrashWorkspace() {
  document.body.innerHTML = `
    <button
      class="trashcan-toggle"
      data-api-trash-url="/api/trash"
      data-api-empty-trash-url="/api/trash/empty"
      type="button"
    ></button>
    <span class="trashcan-count"></span>
    <div class="trash-overlay" hidden>
      <button class="trash-close" type="button"></button>
      <button class="trash-empty" type="button"></button>
      <p class="trash-empty-state" hidden>Trash is empty.</p>
      <div class="trash-gallery"></div>
    </div>
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
