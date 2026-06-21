export async function requestJson(
  url,
  { fallbackMessage, fetcher = fetch, ...init } = {},
) {
  if (!url) {
    throw new Error(fallbackMessage || "Request URL is unavailable.");
  }
  let response;
  try {
    response = await fetcher(url, {
      credentials: "same-origin",
      ...init,
    });
  } catch (error) {
    throw new Error(error.message || fallbackMessage || "Request failed.", {
      cause: error,
    });
  }

  const data = await readJsonResponse(response);
  if (!response.ok) {
    throw new Error(data.error || fallbackMessage || "Request failed.");
  }
  return data;
}

export function csrfJsonRequest(
  url,
  body,
  { csrfToken, fallbackMessage, method = "POST" },
) {
  return requestJson(url, {
    method,
    fallbackMessage,
    headers: csrfHeaders(csrfToken, {
      "Content-Type": "application/json",
    }),
    body: JSON.stringify(body),
  });
}

export function csrfFormRequest(
  url,
  formData,
  { csrfToken, fallbackMessage, method = "POST" },
) {
  return requestJson(url, {
    method,
    fallbackMessage,
    headers: csrfHeaders(csrfToken),
    body: formData,
  });
}

export function csrfHeaders(csrfToken, headers = {}) {
  if (!csrfToken) {
    throw new Error("Missing CSRF token.");
  }
  return {
    ...headers,
    "X-CSRF-Token": csrfToken,
  };
}

async function readJsonResponse(response) {
  try {
    return await response.json();
  } catch {
    return {};
  }
}
