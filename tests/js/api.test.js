import { describe, expect, test, vi } from "vitest";

import {
  csrfFormRequest,
  csrfHeaders,
  csrfJsonRequest,
  requestJson,
} from "../../src/imagegen/frontend/api.js";

describe("requestJson", () => {
  test("returns JSON from a same-origin request", async () => {
    const fetcher = vi.fn(async () => jsonResponse({ ok: true }));

    await expect(requestJson("/api/example", { fetcher })).resolves.toEqual({
      ok: true,
    });
    expect(fetcher).toHaveBeenCalledWith("/api/example", {
      credentials: "same-origin",
    });
  });

  test("uses API error messages when JSON requests fail", async () => {
    const fetcher = vi.fn(async () =>
      jsonResponse({ error: "Prompt is required." }, { ok: false }),
    );

    await expect(
      requestJson("/api/example", {
        fallbackMessage: "Request failed.",
        fetcher,
      }),
    ).rejects.toThrow("Prompt is required.");
  });

  test("uses fallback messages when error responses have no JSON body", async () => {
    const fetcher = vi.fn(async () => emptyResponse({ ok: false }));

    await expect(
      requestJson("/api/example", {
        fallbackMessage: "Gallery refresh failed.",
        fetcher,
      }),
    ).rejects.toThrow("Gallery refresh failed.");
  });

  test("reports failed fetches", async () => {
    const fetcher = vi.fn(async () => {
      throw new Error("Network unavailable.");
    });

    await expect(
      requestJson("/api/example", {
        fallbackMessage: "Request failed.",
        fetcher,
      }),
    ).rejects.toThrow("Network unavailable.");
  });

  test("returns an empty object for successful empty responses", async () => {
    const fetcher = vi.fn(async () => emptyResponse());

    await expect(requestJson("/api/example", { fetcher })).resolves.toEqual({});
  });
});

test("csrfJsonRequest sends JSON with a CSRF header", async () => {
  const fetcher = vi.fn(async () => jsonResponse({ saved: true }));
  vi.stubGlobal("fetch", fetcher);

  await expect(
    csrfJsonRequest(
      "/api/example",
      { name: "sample" },
      { csrfToken: "token", fallbackMessage: "Save failed." },
    ),
  ).resolves.toEqual({ saved: true });
  expect(fetcher).toHaveBeenCalledWith("/api/example", {
    method: "POST",
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      "X-CSRF-Token": "token",
    },
    body: JSON.stringify({ name: "sample" }),
  });
});

test("csrfFormRequest sends form data with a CSRF header", async () => {
  const fetcher = vi.fn(async () => jsonResponse({ uploaded: true }));
  const formData = new FormData();
  formData.set("image", "sample");
  vi.stubGlobal("fetch", fetcher);

  await expect(
    csrfFormRequest("/api/upload", formData, {
      csrfToken: "token",
      fallbackMessage: "Upload failed.",
    }),
  ).resolves.toEqual({ uploaded: true });
  expect(fetcher).toHaveBeenCalledWith("/api/upload", {
    method: "POST",
    credentials: "same-origin",
    headers: {
      "X-CSRF-Token": "token",
    },
    body: formData,
  });
});

test("csrfHeaders rejects missing tokens before requests are sent", () => {
  expect(() => csrfHeaders("")).toThrow("Missing CSRF token.");
});

function jsonResponse(data, { ok = true } = {}) {
  return {
    ok,
    async json() {
      return data;
    },
  };
}

function emptyResponse({ ok = true } = {}) {
  return {
    ok,
    async json() {
      throw new Error("No JSON.");
    },
  };
}
