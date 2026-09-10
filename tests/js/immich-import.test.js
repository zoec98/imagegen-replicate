import { describe, expect, it, vi } from "vitest";

import { setupImmichImport } from "../../src/imagegen/frontend/immich-import.js";

function jsonResponse(data, init = {}) {
  return new Response(JSON.stringify(data), {
    headers: { "Content-Type": "application/json" },
    status: init.status || 200,
  });
}

function renderImmichBrowser() {
  document.body.innerHTML = `
    <div
      class="upload-overlay"
      data-api-immich-assets-url="/api/immich/assets"
      data-api-immich-import-url="/api/immich/import"
    >
      <div class="upload-immich-browser">
        <button class="upload-immich-prev" type="button"></button>
        <button class="upload-immich-next" type="button"></button>
        <span class="upload-immich-page"></span>
        <div class="upload-immich-empty" hidden></div>
        <div class="upload-immich-gallery"></div>
      </div>
      <div class="upload-status"></div>
    </div>
  `;
}

describe("setupImmichImport", () => {
  it("loads page one and renders eligible assets", async () => {
    renderImmichBrowser();
    const fetcher = vi.fn().mockResolvedValue(
      jsonResponse({
        assets: [
          {
            asset_id: "asset-1",
            created_at: "2026-09-09",
            height: 200,
            import_eligible: true,
            label: "Sunset",
            thumbnail_url: "/api/immich/thumb/asset-1",
            width: 300,
          },
        ],
        next_page: 2,
        page: 1,
      }),
    );
    vi.stubGlobal("fetch", fetcher);
    const setStatus = vi.fn();
    const browser = setupImmichImport(document, { setStatus });

    browser.open();

    await vi.waitFor(() => expect(fetcher).toHaveBeenCalledTimes(1));
    await vi.waitFor(() =>
      expect(document.querySelector(".upload-immich-page").textContent).toBe("Page 1"),
    );
    expect(fetcher.mock.calls[0][0]).toContain("/api/immich/assets?page=1");
    expect(document.querySelector(".upload-immich-page").textContent).toBe("Page 1");
    expect(document.querySelector(".upload-immich-item").dataset.assetId).toBe(
      "asset-1",
    );
    expect(document.querySelector(".upload-immich-prev").disabled).toBe(true);
    expect(document.querySelector(".upload-immich-next").disabled).toBe(false);
  });

  it("imports an asset and refreshes the main gallery", async () => {
    renderImmichBrowser();
    const refreshGallery = vi.fn().mockResolvedValue(undefined);
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce(
        jsonResponse({
          assets: [
            {
              asset_id: "asset-1",
              import_eligible: true,
              label: "Sunset",
              thumbnail_url: "/thumb/asset-1",
            },
          ],
          page: 1,
        }),
      )
      .mockResolvedValueOnce(jsonResponse({ image: { filename: "sunset.png" } }));
    vi.stubGlobal("fetch", fetcher);
    const setStatus = vi.fn();
    const browser = setupImmichImport(document, {
      csrfToken: "csrf-token",
      refreshGallery,
      setStatus,
    });

    browser.open();
    await vi.waitFor(() => expect(fetcher).toHaveBeenCalledTimes(1));
    await vi.waitFor(() =>
      expect(document.querySelector(".upload-immich-import")).not.toBeNull(),
    );
    expect(document.querySelector(".upload-immich-import svg")).not.toBeNull();
    document.querySelector(".upload-immich-import").click();

    await vi.waitFor(() => expect(refreshGallery).toHaveBeenCalledTimes(1));
    expect(fetcher.mock.calls[1][0]).toBe("/api/immich/import");
    expect(JSON.parse(fetcher.mock.calls[1][1].body)).toEqual({
      asset_id: "asset-1",
    });
    expect(setStatus).toHaveBeenLastCalledWith("sunset.png imported.", "success");
  });

  it("keeps the empty state visible for an empty page", async () => {
    renderImmichBrowser();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse({ assets: [], page: 1 })),
    );
    const browser = setupImmichImport(document);

    browser.open();

    await vi.waitFor(() =>
      expect(document.querySelector(".upload-immich-empty").hidden).toBe(false),
    );
    expect(document.querySelector(".upload-immich-gallery").children).toHaveLength(0);
  });
});
