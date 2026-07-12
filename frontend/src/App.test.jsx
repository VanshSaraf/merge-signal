import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "./App.jsx";

const validUrl = "https://github.com/octocat/Hello-World/pull/42";

function healthResponse() {
  return Promise.resolve({
    ok: true,
    json: () =>
      Promise.resolve({
        status: "ok",
        service: "MergeSignal",
        environment: "test",
        timestamp: "2026-07-12T00:00:00Z",
      }),
  });
}

function snapshotResponse(overrides = {}) {
  return {
    reference: {
      owner: "octocat",
      repository: "Hello-World",
      pull_number: 42,
      canonical_url: validUrl,
    },
    metadata: {
      title: "Improve merge signal collection",
      state: "open",
      draft: false,
      additions: 120,
      deletions: 30,
      changed_files: 3,
      commit_count: 2,
      author: { login: "octocat" },
      base_branch: { ref: "main" },
      head_branch: { ref: "feature/analysis" },
    },
    files: [],
    ci: { state: "passing", visibility: "complete" },
    signal_summary: { total_signals: 2 },
    signals: [
      {
        id: "sig-security",
        rule_id: "security.credential_like_literal_added",
        title: "Credential-like literal pattern added",
        description: "A sanitized security signal was observed.",
        severity: "high",
        affected_files: ["backend/app/security/secrets.py"],
      },
      {
        id: "sig-config",
        rule_id: "configuration.runtime_configuration_changed",
        title: "Runtime configuration paths changed",
        description: "Runtime configuration changed.",
        severity: "medium",
        affected_files: ["backend/app/config/runtime.py"],
      },
    ],
    merge_readiness: {
      decision: "ready_with_caution",
      decisive_rule_id: "readiness.caution.patch_visibility_partial",
      limitations: ["Human review remains necessary."],
    },
    merge_risk: {
      score: 42,
      level: "moderate",
      limitations: ["Merge risk is a deterministic heuristic, not a probability."],
    },
    evidence_confidence: {
      score: 86,
      level: "high",
      limitations: ["Evidence confidence measures visibility and completeness, not code quality."],
    },
    ranked_files: [
      {
        rank: 1,
        path: "backend/app/security/secrets.py",
        score: 76,
        level: "very_high",
        primary_kind: "source",
        changes: 14,
      },
      {
        rank: 2,
        path: "backend/app/config/runtime.py",
        score: 45,
        level: "high",
        primary_kind: "configuration",
        changes: 18,
      },
    ],
    review_action_summary: { total_actions: 2 },
    review_actions: [
      {
        id: "action.verify_credential_like_literal",
        rule_id: "action.verify_credential_like_literal",
        title: "Verify credential-like literal",
        description: "Check whether the credential-like literal signal is intentional and safe.",
        priority: "high",
        category: "security",
        affected_files: ["backend/app/security/secrets.py"],
        evidence: ["Suspected values and full source lines are omitted."],
      },
      {
        id: "action.review_highest_priority_files",
        rule_id: "action.review_highest_priority_files",
        title: "Review highest-priority files",
        description: "Use the highest-ranked changed files as a review-order starting point.",
        priority: "low",
        category: "file_review",
        affected_files: ["backend/app/security/secrets.py", "backend/app/config/runtime.py"],
        evidence: ["Lower-ranked files must not be ignored."],
      },
    ],
    completeness: {
      warnings: ["One or more changed files do not include patch data from GitHub."],
    },
    ...overrides,
  };
}

function okSnapshot(payload = snapshotResponse()) {
  return Promise.resolve({
    ok: true,
    json: () => Promise.resolve({ data: payload }),
  });
}

function renderApp() {
  return render(
    <MemoryRouter initialEntries={["/"]}>
      <App />
    </MemoryRouter>,
  );
}

describe("App", () => {
  beforeEach(() => {
    window.localStorage.clear();
    global.fetch = vi.fn((url) => {
      if (String(url).endsWith("/health")) {
        return healthResponse();
      }
      return okSnapshot();
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders the initial empty state and backend indicator", async () => {
    renderApp();

    expect(screen.getByRole("heading", { name: "MergeSignal" })).toBeInTheDocument();
    expect(screen.getByText(/Ready for a pull request/i)).toBeInTheDocument();
    expect(screen.getByText(/does not run repository code/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("Backend online")).toBeInTheDocument();
    });
  });

  it("toggles and persists the theme", async () => {
    const user = userEvent.setup();
    renderApp();

    await user.click(screen.getByRole("button", { name: /switch to dark theme/i }));

    expect(document.documentElement.dataset.theme).toBe("dark");
    expect(window.localStorage.getItem("mergesignal-theme")).toBe("dark");
  });

  it("validates empty and malformed URLs before calling the snapshot API", async () => {
    const user = userEvent.setup();
    renderApp();

    await user.click(screen.getByRole("button", { name: "Analyze" }));
    expect(screen.getByText("Enter a public GitHub pull-request URL.")).toBeInTheDocument();

    await user.type(screen.getByLabelText("GitHub PR URL"), "https://github.com/octocat/Hello-World/issues/42");
    await user.click(screen.getByRole("button", { name: "Analyze" }));

    expect(screen.getByText(/Use the format/i)).toBeInTheDocument();
    expect(global.fetch).toHaveBeenCalledTimes(1);
  });

  it("shows loading state and supports cancellation", async () => {
    const user = userEvent.setup();
    let resolveSnapshot;
    global.fetch = vi.fn((url) => {
      if (String(url).endsWith("/health")) {
        return healthResponse();
      }
      return new Promise((resolve) => {
        resolveSnapshot = () => resolve(okSnapshot());
      });
    });
    renderApp();

    await user.type(screen.getByLabelText("GitHub PR URL"), validUrl);
    await user.click(screen.getByRole("button", { name: "Analyze" }));

    expect(screen.getByText(/Collecting deterministic evidence/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Cancel" })).toBeInTheDocument();

    resolveSnapshot();
  });

  it("renders a successful analysis dashboard from the API response", async () => {
    const user = userEvent.setup();
    renderApp();

    await user.type(screen.getByLabelText("GitHub PR URL"), validUrl);
    await user.click(screen.getByRole("button", { name: "Analyze" }));

    expect(await screen.findByText("octocat/Hello-World")).toBeInTheDocument();
    expect(screen.getByText("Improve merge signal collection")).toBeInTheDocument();
    expect(screen.getByText("Ready With Caution")).toBeInTheDocument();
    expect(screen.getByText("42/100")).toBeInTheDocument();
    expect(screen.getByText("86/100")).toBeInTheDocument();
    expect(screen.getAllByText("backend/app/security/secrets.py").length).toBeGreaterThan(0);
    expect(screen.getByText("Verify credential-like literal")).toBeInTheDocument();
    expect(screen.getByText("Credential-like literal pattern added")).toBeInTheDocument();
    expect(screen.queryByText("not-a-real-secret-fixture")).not.toBeInTheDocument();
    expect(screen.queryByText(/password =/i)).not.toBeInTheDocument();
  });

  it("renders backend errors and retries with the preserved URL", async () => {
    const user = userEvent.setup();
    global.fetch = vi.fn((url) => {
      if (String(url).endsWith("/health")) {
        return healthResponse();
      }
      if (global.fetch.mock.calls.filter(([calledUrl]) => String(calledUrl).includes("/snapshot")).length === 1) {
        return Promise.resolve({
          ok: false,
          status: 422,
          json: () =>
            Promise.resolve({
              error: { code: "INVALID_PULL_REQUEST_URL", message: "Provide a valid public GitHub pull-request URL." },
            }),
        });
      }
      return okSnapshot();
    });
    renderApp();

    await user.type(screen.getByLabelText("GitHub PR URL"), validUrl);
    await user.click(screen.getByRole("button", { name: "Analyze" }));

    expect(await screen.findByText("Invalid pull-request URL")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByText("octocat/Hello-World")).toBeInTheDocument();
  });

  it("submits the form with Enter", async () => {
    const user = userEvent.setup();
    renderApp();

    await user.type(screen.getByLabelText("GitHub PR URL"), `${validUrl}{Enter}`);

    expect(await screen.findByText("octocat/Hello-World")).toBeInTheDocument();
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
