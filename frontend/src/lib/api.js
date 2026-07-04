/**
 * API client for the SupplyChain Sentinel backend.
 *
 * All requests go to the FastAPI server (see ../README.md for how to start
 * it). The base URL is read from VITE_API_BASE_URL so it's configurable
 * without touching code -- defaults to localhost:8000 for local dev.
 */

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";

class ApiError extends Error {
  constructor(message, status, detail) {
    super(message);
    this.status = status;
    this.detail = detail;
  }
}

async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, options);
  } catch {
    throw new ApiError(
      "Could not reach the backend. Is the API server running?",
      0,
      null
    );
  }

  if (!response.ok) {
    let detail = null;
    try {
      const body = await response.json();
      detail = body.detail ?? body;
    } catch {
      // response had no JSON body
    }
    const message =
      typeof detail === "string"
        ? detail
        : detail?.message || `Request failed (${response.status})`;
    throw new ApiError(message, response.status, detail);
  }

  return response.json();
}

export const api = {
  health: () => request("/health"),

  dataSummary: () => request("/data/summary"),

  uploadCsv: async (entityType, file) => {
    const formData = new FormData();
    formData.append("file", file);
    return request(`/data/upload?entity_type=${entityType}`, {
      method: "POST",
      body: formData,
    });
  },

  runStressTest: (payload) =>
    request("/stress-test", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),

  listReports: () => request("/reports"),

  getReport: (slug) => request(`/reports/${slug}`),
};

export { ApiError };
