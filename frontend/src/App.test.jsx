import { render, screen, waitFor, within } from "@testing-library/react";
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
    ci_explanation: {
      overall_state: "passing",
      visibility: "complete",
      summary: "2 checks passed.",
      total_count: 2,
      passing_count: 2,
      failing_count: 0,
      pending_count: 0,
      neutral_count: 0,
      skipped_count: 0,
      unknown_count: 0,
      blocking_items: [],
      warnings: [],
      surfaces: [
        {
          provider: "GitHub Actions",
          source_type: "check_run",
          total_count: 2,
          passing_count: 2,
          failing_count: 0,
          pending_count: 0,
          neutral_count: 0,
          skipped_count: 0,
          unknown_count: 0,
          items: [
            {
              name: "Static checks & unit tests",
              provider: "GitHub Actions",
              source_type: "check_run",
              normalized_state: "passing",
              category: "test",
              description: "success",
              details_url: "https://github.com/octocat/Hello-World/actions/runs/1/job/2",
              is_blocking: false,
            },
            {
              name: "End-to-end tests",
              provider: "GitHub Actions",
              source_type: "check_run",
              normalized_state: "passing",
              category: "test",
              description: "success",
              details_url: "https://github.com/octocat/Hello-World/actions/runs/1/job/3",
              is_blocking: false,
            },
          ],
        },
      ],
    },
    review_context: {
      visibility: "complete",
      completeness: {
        reviews_complete: true,
        comments_complete: true,
        review_pages_fetched: 1,
        comment_pages_fetched: 1,
        warnings: [],
      },
      review_count: 2,
      comment_count: 2,
      thread_count: 1,
      approved_count: 1,
      changes_requested_count: 1,
      commented_count: 0,
      dismissed_count: 0,
      pending_count: 0,
      latest_reviewer_states: [
        { reviewer_login: "alice", state: "approved", review_id: 501, submitted_at: "2026-07-13T10:00:00Z" },
        { reviewer_login: "bob", state: "changes_requested", review_id: 502, submitted_at: "2026-07-13T10:05:00Z" },
      ],
      reviews: [
        { id: 501, reviewer_login: "alice", state: "approved", submitted_at: "2026-07-13T10:00:00Z", body_excerpt: "Looks good.", html_url: "https://github.com/octocat/Hello-World/pull/42#pullrequestreview-501", commit_sha: "head" },
        { id: 502, reviewer_login: "bob", state: "changes_requested", submitted_at: "2026-07-13T10:05:00Z", body_excerpt: "Please adjust the session handling.", html_url: "https://github.com/octocat/Hello-World/pull/42#pullrequestreview-502", commit_sha: "head" },
      ],
      threads: [
        {
          id: "review-thread-601",
          root_comment_id: 601,
          path: "backend/app/security/secrets.py",
          line: 42,
          start_line: null,
          side: "RIGHT",
          start_side: null,
          html_url: "https://github.com/octocat/Hello-World/pull/42#discussion_r601",
          is_orphan_reply: false,
          participant_logins: ["bob", "octocat"],
          root_comment: {
            id: 601,
            reviewer_login: "bob",
            body_excerpt: "Can we avoid storing password=[REDACTED] here?",
            created_at: "2026-07-13T10:06:00Z",
            updated_at: "2026-07-13T10:06:00Z",
            html_url: "https://github.com/octocat/Hello-World/pull/42#discussion_r601",
            pull_request_review_id: 502,
            in_reply_to_id: null,
            path: "backend/app/security/secrets.py",
            line: 42,
            start_line: null,
            side: "RIGHT",
            start_side: null,
            commit_sha: "head",
          },
          replies: [
            {
              id: 602,
              reviewer_login: "octocat",
              body_excerpt: "Good catch, I will revise this.",
              created_at: "2026-07-13T10:07:00Z",
              updated_at: "2026-07-13T10:07:00Z",
              html_url: "https://github.com/octocat/Hello-World/pull/42#discussion_r602",
              pull_request_review_id: 502,
              in_reply_to_id: 601,
              path: "backend/app/security/secrets.py",
              line: 42,
              start_line: null,
              side: "RIGHT",
              start_side: null,
              commit_sha: "head",
            },
          ],
        },
      ],
      warnings: [],
      limitations: ["Review comments do not automatically change merge risk or readiness."],
    },
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
        related_signal_ids: ["sig-security"],
        related_readiness_rule_ids: ["readiness.not_ready.credential_like_literal"],
        evidence: ["Suspected values and full source lines are omitted."],
        limitations: ["Actions describe what to verify next; they do not prescribe code changes."],
      },
      {
        id: "action.review_highest_priority_files",
        rule_id: "action.review_highest_priority_files",
        title: "Review highest-priority files",
        description: "Use the highest-ranked changed files as a review-order starting point.",
        priority: "low",
        category: "file_review",
        affected_files: ["backend/app/security/secrets.py", "backend/app/config/runtime.py"],
        related_signal_ids: [],
        related_readiness_rule_ids: [],
        evidence: ["Lower-ranked files must not be ignored."],
        limitations: ["Actions describe what to verify next; they do not prescribe code changes."],
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

  it("renders the landing experience, project links, and backend indicators", async () => {
    renderApp();

    expect(screen.getByText("MergeSignal")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Review the right changes before you merge." })).toBeInTheDocument();
    expect(screen.getByText(/visible GitHub pull-request evidence/i)).toBeInTheDocument();
    expect(screen.getByText("No execution of analyzed code")).toBeInTheDocument();
    expect(screen.getByText("Evidence-backed decisions")).toBeInTheDocument();
    expect(screen.getByText("Deterministic review guidance")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "GitHub" })).toHaveAttribute("href", "https://github.com/VanshSaraf/merge-signal");
    expect(screen.getByRole("link", { name: "Docs" })).toHaveAttribute("href", "https://github.com/VanshSaraf/merge-signal/blob/main/docs/frontend.md");
    expect(screen.getByRole("region", { name: /Evidence to review-order pipeline/i })).toBeInTheDocument();
    expect(screen.getByText("Public GitHub pull requests only.")).toBeInTheDocument();
    expect(screen.getByText("Built for explainable review.")).toBeInTheDocument();
    expect(screen.queryByText("Blocked")).not.toBeInTheDocument();
    expect(screen.queryByText("42/100")).not.toBeInTheDocument();

    expect(await screen.findAllByText("Backend online")).toHaveLength(2);
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

    await user.click(screen.getByRole("button", { name: "Analyze pull request" }));
    expect(screen.getByText("Enter a public GitHub pull-request URL.")).toBeInTheDocument();

    await user.type(screen.getByLabelText("GitHub PR URL"), "https://github.com/octocat/Hello-World/issues/42");
    await user.click(screen.getByRole("button", { name: "Analyze pull request" }));

    expect(screen.getByText(/Use the format/i)).toBeInTheDocument();
    expect(global.fetch.mock.calls.filter(([calledUrl]) => String(calledUrl).includes("/snapshot"))).toHaveLength(0);
  });

  it("shows loading state and supports cancellation", async () => {
    const user = userEvent.setup();
    global.fetch = vi.fn((url, options = {}) => {
      if (String(url).endsWith("/health")) {
        return healthResponse();
      }
      return new Promise((resolve, reject) => {
        options.signal?.addEventListener("abort", () => {
          reject(new DOMException("The operation was aborted.", "AbortError"));
        });
      });
    });
    renderApp();

    await user.type(screen.getByLabelText("GitHub PR URL"), validUrl);
    await user.click(screen.getByRole("button", { name: "Analyze pull request" }));

    expect(screen.getByRole("heading", { name: /Building analysis report/i })).toBeInTheDocument();
    expect(screen.getByText("Validating pull request")).toBeInTheDocument();
    expect(screen.getByText("Fetching GitHub evidence")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Cancel" }));

    expect(await screen.findByRole("heading", { name: "Review the right changes before you merge." })).toBeInTheDocument();
  });

  it("renders a successful analysis dashboard from the API response", async () => {
    const user = userEvent.setup();
    renderApp();

    await user.type(screen.getByLabelText("GitHub PR URL"), validUrl);
    await user.click(screen.getByRole("button", { name: "Analyze pull request" }));

    expect(await screen.findByText("octocat/Hello-World")).toBeInTheDocument();
    expect(screen.getByText("Improve merge signal collection")).toBeInTheDocument();
    expect(screen.getByLabelText("Analyze another pull request")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Analyze" })).toBeInTheDocument();
    expect(await screen.findAllByText("Backend online")).toHaveLength(1);
    expect(screen.getByLabelText("Review focus")).toBeInTheDocument();
    expect(screen.queryByLabelText("Assessment summary")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Review focus")).toHaveTextContent("Patch visibility is partial");
    expect(screen.getByLabelText("Review focus")).toHaveTextContent("backend/app/security/secrets.py");
    expect(screen.getAllByText("Ready With Caution").length).toBeGreaterThan(0);
    expect(screen.getAllByText("42/100").length).toBeGreaterThan(0);
    expect(screen.getAllByText("86/100").length).toBeGreaterThan(0);
    expect(screen.getByText("Review next")).toBeInTheDocument();
    expect(screen.getAllByText("Verify credential-like literal").length).toBeGreaterThan(0);
    expect(screen.getByText(/Start with backend\/app\/security\/secrets.py/i)).toBeInTheDocument();
    expect(screen.queryByText("readiness.caution.patch_visibility_partial")).not.toBeInTheDocument();

    await user.click(screen.getByRole("tab", { name: "Files" }));
    expect(screen.queryByLabelText("Assessment summary")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Compact assessment summary")).toHaveTextContent("Ready With Caution");
    expect(screen.getByLabelText("Compact assessment summary")).toHaveTextContent("Risk 42");
    expect(screen.getByLabelText("Compact assessment summary")).toHaveTextContent("Confidence 86");
    expect(screen.getByLabelText("Compact assessment summary")).toHaveTextContent("CI Passing");
    expect(screen.getAllByText("backend/app/security/secrets.py").length).toBeGreaterThan(0);

    await user.click(screen.getByRole("tab", { name: "Actions" }));
    expect(screen.getByText("Verify credential-like literal")).toBeInTheDocument();
    expect(screen.queryByText("action.verify_credential_like_literal")).not.toBeInTheDocument();
    await user.click(screen.getAllByRole("button", { name: "View details" })[0]);
    expect(screen.getByText("action.verify_credential_like_literal")).toBeInTheDocument();

    await user.click(screen.getByRole("tab", { name: "Signals" }));
    expect(screen.getByText("Credential-like literal pattern added")).toBeInTheDocument();
    expect(screen.queryByText("security.credential_like_literal_added")).not.toBeInTheDocument();
    await user.click(screen.getAllByRole("button", { name: "Technical details" })[0]);
    expect(screen.getByText("security.credential_like_literal_added")).toBeInTheDocument();
    expect(screen.queryByText("not-a-real-secret-fixture")).not.toBeInTheDocument();
    expect(screen.queryByText(/password =/i)).not.toBeInTheDocument();
  });

  it("navigates report sections and renders overview breakdowns", async () => {
    const user = userEvent.setup();
    renderApp();

    await user.type(screen.getByLabelText("GitHub PR URL"), validUrl);
    await user.click(screen.getByRole("button", { name: "Analyze pull request" }));

    expect(await screen.findByText("Risk group breakdown")).toBeInTheDocument();
    expect(screen.getByText("Confidence components")).toBeInTheDocument();

    await user.click(screen.getByRole("tab", { name: "Evidence" }));
    expect(screen.getByText("Readiness reasons")).toBeInTheDocument();
    expect(screen.getByText("Risk contributions")).toBeInTheDocument();
    expect(screen.getByText("Classification summary")).toBeInTheDocument();
    expect(screen.getAllByText("Analysis boundaries").length).toBeGreaterThan(0);
    expect(screen.getByText(/Does not execute or semantically prove code behavior/i)).toBeInTheDocument();
    expect(screen.getByText("Score boundaries")).toBeInTheDocument();
    expect(screen.getByText(/not probabilities or proof of safety/i)).toBeInTheDocument();
    expect(screen.getByText("Human review")).toBeInTheDocument();
    const additionalLimitations = screen.getByText("Additional source limitations").closest("details");
    expect(additionalLimitations).not.toBeNull();
    expect(additionalLimitations).not.toHaveAttribute("open");
    expect(within(additionalLimitations).getByText(/Human review remains necessary/i)).toBeInTheDocument();
  });

  it("renders actionable CI surface intelligence for a blocked deployment status", async () => {
    const user = userEvent.setup();
    global.fetch = vi.fn((url) => {
      if (String(url).endsWith("/health")) {
        return healthResponse();
      }
      return okSnapshot(snapshotResponse({
        ci: { state: "failing", visibility: "complete" },
        ci_explanation: {
          overall_state: "failing",
          visibility: "complete",
          summary: "1 authorization/configuration check failing on Vercel; 2 checks passed.",
          total_count: 3,
          passing_count: 2,
          failing_count: 1,
          pending_count: 0,
          neutral_count: 0,
          skipped_count: 0,
          unknown_count: 0,
          warnings: [],
          blocking_items: [
            {
              name: "Vercel",
              provider: "Vercel",
              source_type: "commit_status",
              normalized_state: "failing",
              category: "authorization_or_configuration",
              description: "Authorization required to deploy.",
              details_url: "https://vercel.com/git/authorize?repo=octocat",
              is_blocking: true,
            },
          ],
          surfaces: [
            {
              provider: "GitHub Actions",
              source_type: "check_run",
              total_count: 2,
              passing_count: 2,
              failing_count: 0,
              pending_count: 0,
              neutral_count: 0,
              skipped_count: 0,
              unknown_count: 0,
              items: [
                { name: "End-to-end tests", provider: "GitHub Actions", source_type: "check_run", normalized_state: "passing", category: "test", description: "success", details_url: "https://github.com/octocat/Hello-World/actions/runs/1/job/3", is_blocking: false },
                { name: "Static checks & unit tests", provider: "GitHub Actions", source_type: "check_run", normalized_state: "passing", category: "test", description: "success", details_url: "https://github.com/octocat/Hello-World/actions/runs/1/job/2", is_blocking: false },
              ],
            },
            {
              provider: "Vercel",
              source_type: "commit_status",
              total_count: 1,
              passing_count: 0,
              failing_count: 1,
              pending_count: 0,
              neutral_count: 0,
              skipped_count: 0,
              unknown_count: 0,
              items: [
                { name: "Vercel", provider: "Vercel", source_type: "commit_status", normalized_state: "failing", category: "authorization_or_configuration", description: "Authorization required to deploy.", details_url: "https://vercel.com/git/authorize?repo=octocat", is_blocking: true },
              ],
            },
          ],
        },
        merge_readiness: {
          decision: "blocked",
          decisive_rule_id: "readiness.blocked.ci_failing",
          reasons: [
            {
              rule_id: "readiness.blocked.ci_failing",
              title: "CI is failing",
              effect: "block",
              explanation: "Blocked by a failed Vercel authorization/configuration check. 1 authorization/configuration check failing on Vercel; 2 checks passed.",
            },
          ],
          limitations: [],
        },
        review_actions: [
          {
            id: "action.inspect_failing_ci",
            rule_id: "action.inspect_failing_ci",
            title: "Inspect failing CI",
            description: "Open the failing CI surface and inspect the provider evidence before reassessing readiness.",
            priority: "high",
            category: "ci",
            affected_files: [],
            related_signal_ids: ["ci.failing:fixture"],
            related_readiness_rule_ids: ["readiness.blocked.ci_failing"],
            evidence: ["Details URL: https://vercel.com/git/authorize?repo=octocat"],
            limitations: [],
          },
        ],
        review_action_summary: { total_actions: 1, limitations: [] },
      }));
    });
    renderApp();

    await user.type(screen.getByLabelText("GitHub PR URL"), validUrl);
    await user.click(screen.getByRole("button", { name: "Analyze pull request" }));

    expect(await screen.findByRole("heading", { name: /Blocked because Vercel authorization\/configuration check is failing/i })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "CI surface summary" })).toHaveTextContent("2 checks passed");
    expect(screen.getByText("Authorization required to deploy.")).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "Open details" }).some((link) => link.getAttribute("href") === "https://vercel.com/git/authorize?repo=octocat")).toBe(true);

    await user.click(screen.getByText("View CI surface details"));
    expect(screen.getByText("Static checks & unit tests")).toBeInTheDocument();
    expect(screen.getByText("End-to-end tests")).toBeInTheDocument();

    await user.click(screen.getByRole("tab", { name: "Actions" }));
    await user.click(screen.getByRole("button", { name: "View details" }));
    expect(screen.getAllByRole("link", { name: "Open details" }).some((link) => link.getAttribute("href") === "https://vercel.com/git/authorize?repo=octocat")).toBe(true);
  });

  it("renders review context summary, conversations, safe links, and hidden technical details", async () => {
    const user = userEvent.setup();
    renderApp();

    await user.type(screen.getByLabelText("GitHub PR URL"), validUrl);
    await user.click(screen.getByRole("button", { name: "Analyze pull request" }));

    expect(await screen.findByLabelText("Review context summary")).toHaveTextContent("1 approval");
    expect(screen.getByLabelText("Review context summary")).toHaveTextContent("1 change request");
    await user.click(screen.getByRole("tab", { name: "Reviews (1)" }));

    expect(screen.getByLabelText("Observable review-state summary")).toHaveTextContent("Submitted reviews");
    expect(screen.getByLabelText("Latest observable reviewer states")).toHaveTextContent("alice");
    expect(screen.getByLabelText("Latest observable reviewer states")).toHaveTextContent("Changes Requested");
    expect(screen.getByText("backend/app/security/secrets.py:L42")).toBeInTheDocument();
    expect(screen.getByText("Can we avoid storing password=[REDACTED] here?")).toBeInTheDocument();
    expect(screen.queryByText("review-thread-601")).not.toBeInTheDocument();
    expect(screen.queryByText(/hunter2|api_key|<b>/i)).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "View conversation" }));
    expect(screen.getByText("Good catch, I will revise this.")).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "Open on GitHub" }).some((link) => link.getAttribute("href") === "https://github.com/octocat/Hello-World/pull/42#discussion_r601")).toBe(true);
    const technicalDetails = screen.getByText("Technical details").closest("details");
    expect(technicalDetails).not.toHaveAttribute("open");
    await user.click(screen.getByText("Technical details"));
    expect(technicalDetails).toHaveAttribute("open");
    expect(screen.getByText("review-thread-601")).toBeInTheDocument();
  });

  it("renders all ranked files with search, filters, sorting, clear filters, and details", async () => {
    const user = userEvent.setup();
    renderApp();

    await user.type(screen.getByLabelText("GitHub PR URL"), validUrl);
    await user.click(screen.getByRole("button", { name: "Analyze pull request" }));
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

    const firstDetailsButton = screen.getAllByRole("button", { name: "Details" })[0];
    await user.click(firstDetailsButton);
    expect(screen.getByRole("dialog", { name: /backend\/app/i })).toBeInTheDocument();
    expect(screen.getByText("Priority factors")).toBeInTheDocument();

    await user.keyboard("{Escape}");
    await waitFor(() => {
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });
    expect(document.activeElement).toBe(firstDetailsButton);
  });

  it("shows empty file filter results", async () => {
    const user = userEvent.setup();
    renderApp();

    await user.type(screen.getByLabelText("GitHub PR URL"), validUrl);
    await user.click(screen.getByRole("button", { name: "Analyze pull request" }));
    await user.click(await screen.findByRole("tab", { name: "Files" }));
    await user.type(screen.getByLabelText("Search path"), "no-match");

    expect(screen.getByText("No files match the current filters.")).toBeInTheDocument();
  });

  it("filters review signals and review actions", async () => {
    const user = userEvent.setup();
    renderApp();

    await user.type(screen.getByLabelText("GitHub PR URL"), validUrl);
    await user.click(screen.getByRole("button", { name: "Analyze pull request" }));

    await user.click(await screen.findByRole("tab", { name: "Signals" }));
    await user.selectOptions(screen.getByLabelText("Severity"), "medium");
    expect(screen.getByText("Runtime configuration paths changed")).toBeInTheDocument();
    expect(screen.queryByText("Credential-like literal pattern added")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Clear filters" }));
    await user.type(screen.getByLabelText("Affected file"), "secrets");
    expect(screen.getByText("Credential-like literal pattern added")).toBeInTheDocument();

    await user.click(screen.getByRole("tab", { name: "Actions" }));
    expect(screen.getByText(/not automated fixes or reviewer assignments/i)).toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText("Priority"), "low");
    expect(screen.getByText("Review highest-priority files")).toBeInTheDocument();
    expect(screen.queryByText("Verify credential-like literal")).not.toBeInTheDocument();
  });

  it("supports keyboard navigation across report tabs", async () => {
    const user = userEvent.setup();
    renderApp();

    await user.type(screen.getByLabelText("GitHub PR URL"), validUrl);
    await user.click(screen.getByRole("button", { name: "Analyze pull request" }));

    const overviewTab = await screen.findByRole("tab", { name: "Overview" });
    overviewTab.focus();
    await user.keyboard("{ArrowRight}");

    await waitFor(() => {
      expect(screen.getByRole("tab", { name: "Files" })).toHaveAttribute("aria-selected", "true");
    });
    expect(screen.getByText("Ranked files")).toBeInTheDocument();

    await user.keyboard("{End}");
    await waitFor(() => {
      expect(screen.getByRole("tab", { name: "Evidence" })).toHaveAttribute("aria-selected", "true");
    });
    expect(screen.getAllByText("Analysis boundaries").length).toBeGreaterThan(0);
  });

  it("replaces review actions when a new pull request analysis succeeds", async () => {
    const user = userEvent.setup();
    const secondUrl = "https://github.com/octocat/Hello-World/pull/43";
    const secondSnapshot = snapshotResponse({
      reference: {
        owner: "octocat",
        repository: "Hello-World",
        pull_number: 43,
        canonical_url: secondUrl,
      },
      metadata: {
        ...snapshotResponse().metadata,
        title: "Plain frontend cleanup",
      },
      signals: [],
      signal_summary: { total_signals: 0 },
      review_actions: [
        {
          id: "action.review_highest_priority_files",
          rule_id: "action.review_highest_priority_files",
          title: "Review highest-priority files",
          description: "Use the highest-ranked changed files as a review-order starting point.",
          priority: "low",
          category: "file_review",
          affected_files: ["frontend/src/App.jsx"],
          related_signal_ids: [],
          related_readiness_rule_ids: [],
          evidence: ["Lower-ranked files must not be ignored."],
          limitations: ["Actions describe what to verify next; they do not prescribe code changes."],
        },
      ],
      review_action_summary: { total_actions: 1, limitations: [] },
      review_context: {
        ...snapshotResponse().review_context,
        review_count: 0,
        comment_count: 0,
        thread_count: 0,
        approved_count: 0,
        changes_requested_count: 0,
        latest_reviewer_states: [],
        reviews: [],
        threads: [],
      },
      ranked_files: [
        {
          rank: 1,
          path: "frontend/src/App.jsx",
          score: 20,
          level: "low",
          primary_kind: "source",
          language: "javascript",
          status: "modified",
          additions: 4,
          deletions: 2,
          changes: 6,
          areas: ["frontend"],
          related_signal_ids: [],
          factors: [],
          limitations: [],
        },
      ],
    });
    global.fetch = vi.fn((url) => {
      if (String(url).endsWith("/health")) {
        return healthResponse();
      }
      const snapshotCalls = global.fetch.mock.calls.filter(([calledUrl]) => String(calledUrl).includes("/snapshot")).length;
      return okSnapshot(snapshotCalls === 1 ? snapshotResponse() : secondSnapshot);
    });
    renderApp();

    await user.type(screen.getByLabelText("GitHub PR URL"), validUrl);
    await user.click(screen.getByRole("button", { name: "Analyze pull request" }));
    await user.click(await screen.findByRole("tab", { name: "Actions" }));
    expect(screen.getByText("Verify credential-like literal")).toBeInTheDocument();

    await user.clear(screen.getByLabelText("GitHub PR URL"));
    await user.type(screen.getByLabelText("GitHub PR URL"), secondUrl);
    await user.click(screen.getByRole("button", { name: "Analyze" }));

    expect(await screen.findByText("Plain frontend cleanup")).toBeInTheDocument();
    await user.click(screen.getByRole("tab", { name: "Overview" }));
    expect(screen.getByLabelText("Review focus")).toHaveTextContent("frontend/src/App.jsx");
    expect(screen.getByLabelText("Review focus")).not.toHaveTextContent("backend/app/security/secrets.py");
    await user.click(screen.getByRole("tab", { name: "Reviews" }));
    expect(screen.getByText("No inline review conversations were observed.")).toBeInTheDocument();
    expect(screen.queryByText("backend/app/security/secrets.py:L42")).not.toBeInTheDocument();
    await user.click(screen.getByRole("tab", { name: "Actions" }));
    await waitFor(() => {
      expect(screen.queryByText("Verify credential-like literal")).not.toBeInTheDocument();
    });
    expect(screen.getByText("Review highest-priority files")).toBeInTheDocument();
  });

  it("renders empty report section states and unknown enum fallbacks", async () => {
    const user = userEvent.setup();
    global.fetch = vi.fn((url) => {
      if (String(url).endsWith("/health")) {
        return healthResponse();
      }
      return okSnapshot(snapshotResponse({
        ranked_files: [],
        signals: [],
        signal_summary: { total_signals: 0 },
        review_actions: [],
        review_action_summary: { total_actions: 0 },
        merge_readiness: { decision: "needs_manual_review", decisive_rule_id: "readiness.manual", limitations: [] },
        merge_risk: { score: 0, level: "unmapped_level", limitations: [] },
        evidence_confidence: { score: 0, level: "unknown_visibility", components: [], limitations: [] },
        ci: { state: "not_observed", visibility: "unknown" },
        review_context: {
          ...snapshotResponse().review_context,
          visibility: "unavailable",
          review_count: 0,
          comment_count: 0,
          thread_count: 0,
          approved_count: 0,
          changes_requested_count: 0,
          latest_reviewer_states: [],
          reviews: [],
          threads: [],
          warnings: ["Pull-request reviews could not be retrieved from GitHub."],
        },
      }));
    });
    renderApp();

    await user.type(screen.getByLabelText("GitHub PR URL"), validUrl);
    await user.click(screen.getByRole("button", { name: "Analyze pull request" }));

    await screen.findAllByText("Needs Manual Review");
    expect(screen.getAllByText("Needs Manual Review").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Unmapped Level").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Unknown Visibility").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Not Observed").length).toBeGreaterThan(0);

    await user.click(screen.getByRole("tab", { name: "Files" }));
    expect(screen.getByText("No files match the current filters.")).toBeInTheDocument();
    await user.click(screen.getByRole("tab", { name: "Reviews" }));
    expect(screen.getByText("Review context was unavailable from GitHub.")).toBeInTheDocument();
    expect(screen.getByText("Pull-request reviews could not be retrieved from GitHub.")).toBeInTheDocument();
    await user.click(screen.getByRole("tab", { name: "Signals" }));
    expect(screen.getByText("No signals match the current filters.")).toBeInTheDocument();
    await user.click(screen.getByRole("tab", { name: "Actions" }));
    expect(screen.getByText("No review actions match the current filters.")).toBeInTheDocument();
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
    await user.click(screen.getByRole("button", { name: "Analyze pull request" }));

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

  it("renders backend-unavailable health state without blocking the command input", async () => {
    global.fetch = vi.fn((url) => {
      if (String(url).endsWith("/health")) {
        return Promise.reject(new Error("Network unavailable"));
      }
      return okSnapshot();
    });
    renderApp();

    expect(await screen.findAllByText("Backend unavailable")).toHaveLength(2);
    expect(screen.getByRole("button", { name: "Analyze pull request" })).toBeEnabled();
  });

  it("renders a not-found route", async () => {
    render(
      <MemoryRouter initialEntries={["/missing"]}>
        <App />
      </MemoryRouter>,
    );

    expect(screen.getByRole("heading", { name: "Page not found" })).toBeInTheDocument();
    expect(await screen.findByText("Backend online")).toBeInTheDocument();
  });
});
