const LOCAL_API_BASE_URL = "http://127.0.0.1:8000";

export function resolveApiBaseUrl(env = import.meta.env) {
  const rawValue = env.VITE_API_BASE_URL?.trim();
  const isProduction = env.PROD === true || env.MODE === "production";

  if (!rawValue) {
    if (isProduction) {
      throw new Error("VITE_API_BASE_URL is required for production builds.");
    }
    return LOCAL_API_BASE_URL;
  }

  const normalized = normalizeApiBaseUrl(rawValue);
  if (isProduction && isLocalhostUrl(normalized)) {
    throw new Error("VITE_API_BASE_URL must not point to localhost in production.");
  }
  return normalized;
}

export function normalizeApiBaseUrl(value) {
  let url;
  try {
    url = new URL(value);
  } catch {
    throw new Error("VITE_API_BASE_URL must be a valid absolute URL.");
  }

  if (!["http:", "https:"].includes(url.protocol)) {
    throw new Error("VITE_API_BASE_URL must use http or https.");
  }
  if (url.username || url.password) {
    throw new Error("VITE_API_BASE_URL must not include credentials.");
  }
  url.hash = "";
  url.search = "";
  return url.toString().replace(/\/+$/, "");
}

function isLocalhostUrl(value) {
  const { hostname } = new URL(value);
  return hostname === "localhost" || hostname === "127.0.0.1" || hostname === "::1";
}

export const API_BASE_URL = resolveApiBaseUrl();
