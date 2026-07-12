import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "./App.jsx";

describe("App", () => {
  beforeEach(() => {
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve({
            status: "ok",
            service: "MergeSignal",
            environment: "test",
            timestamp: "2026-07-12T00:00:00Z",
          }),
      }),
    );
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders the home page and backend health status", async () => {
    render(
      <MemoryRouter initialEntries={["/"]}>
        <App />
      </MemoryRouter>,
    );

    expect(screen.getByRole("heading", { name: "MergeSignal" })).toBeInTheDocument();
    expect(screen.getByText("Checking backend health...")).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText(/Backend is ok for MergeSignal in test/i)).toBeInTheDocument();
    });
  });

  it("renders a not-found route", () => {
    render(
      <MemoryRouter initialEntries={["/missing"]}>
        <App />
      </MemoryRouter>,
    );

    expect(screen.getByRole("heading", { name: "Page not found" })).toBeInTheDocument();
  });
});
