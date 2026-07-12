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
    classification_summary: {
      total_files: 3,
      classified_files: 3,
      unknown_files: 0,
      counts_by_kind: [{ name: "source", count: 2 }, { name: "configuration", count: 1 }],
      warnings: ["Classification is path-based."],
    },
    files: [
      {
        filename: "backend/app/security/secrets.py",
        patch: "+password = 'not-a-real-secret-fixture'",
      },
    ],
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
      reasons: [
        {
          rule_id: "readiness.caution.patch_visibility_partial",
          title: "Patch visibility is partial",
          effect: "caution",
          explanation: "Evidence confidence reports partial patch visibility.",
        },
      ],
      limitations: ["Human review remains necessary."],
    },
    merge_risk: {
      score: 42,
      level: "moderate",
      group_scores: [
        { group: "change_scope", applied_points: 12, cap: 20 },
        { group: "sensitive_systems", applied_points: 20, cap: 25 },
      ],
      contributions: [
        {
          signal_id: "sig-security",
          rule_id: "security.credential_like_literal_added",
          title: "Credential-like literal pattern added",
          severity: "high",
          applied_points: 20,
          raw_points: 20,
          explanation: "Sanitized security contribution.",
        },
      ],
      limitations: ["Merge risk is a deterministic heuristic, not a probability."],
    },
    evidence_confidence: {
      score: 86,
      level: "high",
      components: [
        { id: "patch_visibility", name: "Patch visibility", awarded_points: 18, maximum_points: 25, status: "partial" },
        { id: "ci_visibility", name: "CI visibility", awarded_points: 15, maximum_points: 15, status: "complete" },
      ],
      limitations: ["Evidence confidence measures visibility and completeness, not code quality."],
    },
    ranked_files: [
      {
        rank: 1,
        path: "backend/app/security/secrets.py",
        score: 76,
        level: "very_high",
        primary_kind: "source",
        language: "python",
        status: "modified",
        additions: 10,
        deletions: 4,
        areas: ["security", "backend"],
        related_signal_ids: ["sig-security"],
        factors: [{ id: "signal.security.credential_like_literal_added", points: 25, description: "Credential-like literal pattern affected this file." }],
        limitations: ["Ranking does not replace human review."],
        classification: { matches: [{ rule_id: "area.security.segment", description: "Security-related path segment." }] },
        changes: 14,
      },
      {
        rank: 2,
        path: "backend/app/config/runtime.py",
        score: 45,
        level: "high",
        primary_kind: "configuration",
        language: "python",
        status: "modified",
        additions: 15,
        deletions: 3,
        areas: ["configuration", "backend"],
        related_signal_ids: ["sig-config"],
        factors: [{ id: "sensitive_area.configuration", points: 5, description: "File is classified in the configuration area." }],
        limitations: [],
        changes: 18,
      },
      {
        rank: 3,
        path: "backend/app/auth/roles.py",
        previous_path: "tests/test_roles.py",
        score: 38,
        level: "medium",
        primary_kind: "source",
        language: "python",
        status: "renamed",
        additions: 8,
        deletions: 2,
        changes: 10,
        areas: ["authentication", "backend"],
        related_signal_ids: [],
        factors: [{ id: "rename_transition.moved_into_sensitive_area", points: 5, description: "File moved into a sensitive classified area." }],
        limitations: [],
        previous_classification: { primary_kind: "test", areas: ["testing"] },
      },
    ],
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
    file_priority_summary: { limitations: ["A low-priority file must not be ignored."] },
    review_action_summary: { total_actions: 2, limitations: ["Actions are deterministic review prompts, not AI commentary."] },
    completeness: {
      files_complete: true,
      commits_complete: true,
      missing_patch_count: 1,
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

    await user.click(screen.getByRole("tab", { name: "Files" }));
    expect(screen.getAllByText("backend/app/security/secrets.py").length).toBeGreaterThan(0);

    await user.click(screen.getByRole("tab", { name: "Review actions" }));
    expect(screen.getByText("Verify credential-like literal")).toBeInTheDocument();

    await user.click(screen.getByRole("tab", { name: "Review signals" }));
    expect(screen.getByText("Credential-like literal pattern added")).toBeInTheDocument();
    expect(screen.queryByText("not-a-real-secret-fixture")).not.toBeInTheDocument();
    expect(screen.queryByText(/password =/i)).not.toBeInTheDocument();
  });

  it("navigates report sections and renders overview breakdowns", async () => {
    const user = userEvent.setup();
    renderApp();

    await user.type(screen.getByLabelText("GitHub PR URL"), validUrl);
    await user.click(screen.getByRole("button", { name: "Analyze" }));

    expect(await screen.findByText("Risk group breakdown")).toBeInTheDocument();
    expect(screen.getByText("Confidence components")).toBeInTheDocument();

    await user.click(screen.getByRole("tab", { name: "Evidence and limitations" }));
    expect(screen.getByText("Readiness reasons")).toBeInTheDocument();
    expect(screen.getByText("Risk contributions")).toBeInTheDocument();
    expect(screen.getByText("Classification summary")).toBeInTheDocument();
  });

  it("renders all ranked files with search, filters, sorting, clear filters, and details", async () => {
    const user = userEvent.setup();
    renderApp();

    await user.type(screen.getByLabelText("GitHub PR URL"), validUrl);
    await user.click(screen.getByRole("button", { name: "Analyze" }));
    await user.click(await screen.findByRole("tab", { name: "Files" }));

    expect(screen.getByText("backend/app/security/secrets.py")).toBeInTheDocument();
    expect(screen.getByText("backend/app/auth/roles.py")).toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText("Priority"), "medium");
    expect(screen.getByText("backend/app/auth/roles.py")).toBeInTheDocument();
    expect(screen.queryByText("backend/app/security/secrets.py")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Clear filters" }));
    await user.type(screen.getByLabelText("Search path"), "runtime");
    expect(screen.getByText("backend/app/config/runtime.py")).toBeInTheDocument();

    await user.clear(screen.getByLabelText("Search path"));
    await user.selectOptions(screen.getByLabelText("Kind"), "configuration");
    expect(screen.getByText("backend/app/config/runtime.py")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Clear filters" }));
    await user.selectOptions(screen.getByLabelText("Area"), "authentication");
    expect(screen.getByText("backend/app/auth/roles.py")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Clear filters" }));
    await user.selectOptions(screen.getByLabelText("Status"), "renamed");
    expect(screen.getByText(/Renamed from tests\/test_roles.py/i)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Clear filters" }));
    await user.selectOptions(screen.getByLabelText("Sort"), "path");
    expect(screen.getAllByRole("button", { name: "Details" })).toHaveLength(3);

    await user.click(screen.getAllByRole("button", { name: "Details" })[0]);
    expect(screen.getByRole("dialog", { name: /backend\/app/i })).toBeInTheDocument();
    expect(screen.getByText("Priority factors")).toBeInTheDocument();

    await user.keyboard("{Escape}");
    await waitFor(() => {
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });
  });

  it("shows empty file filter results", async () => {
    const user = userEvent.setup();
    renderApp();

    await user.type(screen.getByLabelText("GitHub PR URL"), validUrl);
    await user.click(screen.getByRole("button", { name: "Analyze" }));
    await user.click(await screen.findByRole("tab", { name: "Files" }));
    await user.type(screen.getByLabelText("Search path"), "no-match");

    expect(screen.getByText("No files match the current filters.")).toBeInTheDocument();
  });

  it("filters review signals and review actions", async () => {
    const user = userEvent.setup();
    renderApp();

    await user.type(screen.getByLabelText("GitHub PR URL"), validUrl);
    await user.click(screen.getByRole("button", { name: "Analyze" }));

    await user.click(await screen.findByRole("tab", { name: "Review signals" }));
    await user.selectOptions(screen.getByLabelText("Severity"), "medium");
    expect(screen.getByText("Runtime configuration paths changed")).toBeInTheDocument();
    expect(screen.queryByText("Credential-like literal pattern added")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Clear filters" }));
    await user.type(screen.getByLabelText("Affected file"), "secrets");
    expect(screen.getByText("Credential-like literal pattern added")).toBeInTheDocument();

    await user.click(screen.getByRole("tab", { name: "Review actions" }));
    expect(screen.getByText(/not automated fixes or reviewer assignments/i)).toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText("Priority"), "low");
    expect(screen.getByText("Review highest-priority files")).toBeInTheDocument();
    expect(screen.queryByText("Verify credential-like literal")).not.toBeInTheDocument();
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
