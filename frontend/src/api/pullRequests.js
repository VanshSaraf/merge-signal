import { API_BASE_URL } from "../services/apiConfig.js";

const SNAPSHOT_PATH = "/api/v1/pull-requests/snapshot";

export class PullRequestApiError extends Error {
  constructor(message, { code = "UNEXPECTED_RESPONSE", status = null } = {}) {
    super(message);
    this.name = "PullRequestApiError";
    this.code = code;
    this.status = status;
  }
}

export async function fetchPullRequestSnapshot(url, { signal } = {}) {
  let response;

  try {
    response = await fetch(`${API_BASE_URL}${SNAPSHOT_PATH}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
      signal,
    });
  } catch (error) {
    if (error.name === "AbortError") {
      throw error;
    }
    throw new PullRequestApiError("Backend unavailable. Check that the API server is running.", {
      code: "BACKEND_UNAVAILABLE",
    });
  }

  const payload = await readJson(response);

  if (!response.ok) {
    const apiError = payload?.error;
    throw new PullRequestApiError(apiError?.message || errorMessageForStatus(response.status), {
      code: apiError?.code || codeForStatus(response.status),
      status: response.status,
    });
  }

  if (!payload?.data || !payload.data.reference || !Array.isArray(payload.data.files)) {
    throw new PullRequestApiError("The backend returned an unexpected snapshot response.");
  }

  return payload.data;
}

async function readJson(response) {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

function codeForStatus(status) {
  if (status === 404) return "GITHUB_PULL_REQUEST_NOT_FOUND";
  if (status === 403) return "GITHUB_ACCESS_DENIED";
  if (status === 429) return "GITHUB_RATE_LIMITED";
  if (status >= 500) return "GITHUB_UNAVAILABLE";
  return "UNEXPECTED_RESPONSE";
}

function errorMessageForStatus(status) {
  if (status === 404) return "GitHub could not find that pull request.";
  if (status === 403) return "The repository may be private or inaccessible.";
  if (status === 429) return "GitHub rate limiting was detected.";
  if (status >= 500) return "GitHub or the backend is temporarily unavailable.";
  return "The backend could not analyze that pull request.";
}
