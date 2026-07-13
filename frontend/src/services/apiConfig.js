export function resolveApiBaseUrl(env = import.meta.env) {
  const rawValue = env.VITE_API_BASE_URL?.trim();
  const isProduction = env.PROD === true || env.MODE === "production";

  if (!rawValue) {
    if (isProduction) {
      throw new Error("VITE_API_BASE_URL is required for production builds.");
    }
    return developmentApiBaseUrl();
  }

  const normalized = normalizeApiBaseUrl(rawValue);
  if (isProduction) {
    validateProductionApiBaseUrl(normalized);
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

function developmentApiBaseUrl() {
  return "http://127.0.0.1:8000";
}

function resolveRuntimeApiBaseUrl() {
  if (import.meta.env.PROD) {
    return resolveProductionApiBaseUrl(import.meta.env.VITE_API_BASE_URL);
  }
  return resolveApiBaseUrl(import.meta.env);
}

function resolveProductionApiBaseUrl(rawValue) {
  if (!rawValue?.trim()) {
    throw new Error("VITE_API_BASE_URL is required for production builds.");
  }
  const normalized = normalizeApiBaseUrl(rawValue);
  validateProductionApiBaseUrl(normalized);
  return normalized;
}

function validateProductionApiBaseUrl(value) {
  const url = new URL(value);
  if (isLocalhostUrl(value)) {
    throw new Error("VITE_API_BASE_URL must not point to localhost in production.");
  }
  if (url.protocol !== "https:") {
    throw new Error("VITE_API_BASE_URL must use https in production.");
  }
}

export const API_BASE_URL = resolveRuntimeApiBaseUrl();
