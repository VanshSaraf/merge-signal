import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

import { describe, expect, it } from "vitest";

import { normalizeApiBaseUrl, resolveApiBaseUrl } from "./apiConfig.js";

describe("apiConfig", () => {
  it("falls back to localhost for local development only", () => {
    expect(resolveApiBaseUrl({ MODE: "development", DEV: true, PROD: false })).toBe("http://127.0.0.1:8000");
  });

  it("requires an API URL in production", () => {
    expect(() => resolveApiBaseUrl({ MODE: "production", PROD: true })).toThrow(/required/i);
  });

  it("normalizes trailing slashes", () => {
    expect(normalizeApiBaseUrl("https://api.example.com///")).toBe("https://api.example.com");
  });

  it("rejects malformed API base URLs safely", () => {
    expect(() => normalizeApiBaseUrl("not a url")).toThrow(/valid absolute URL/i);
    expect(() => normalizeApiBaseUrl("ftp://api.example.com")).toThrow(/http or https/i);
    expect(() => normalizeApiBaseUrl("https://user:pass@api.example.com")).toThrow(/credentials/i);
  });

  it("rejects localhost production API URLs", () => {
    expect(() =>
      resolveApiBaseUrl({
        MODE: "production",
        PROD: true,
        VITE_API_BASE_URL: "http://localhost:8000",
      }),
    ).toThrow(/localhost/i);
  });

  it("keeps the Vercel SPA fallback configured", () => {
    const currentDir = dirname(fileURLToPath(import.meta.url));
    const configPath = resolve(currentDir, "../../vercel.json");
    const config = JSON.parse(readFileSync(configPath, "utf-8"));

    expect(config.buildCommand).toBe("npm run build");
    expect(config.outputDirectory).toBe("dist");
    expect(config.rewrites).toContainEqual({ source: "/(.*)", destination: "/index.html" });
  });
});
