import { describe, expect, it } from "vitest";

import { providerDisplayName, pullRequestStateLabel, scopeLabel } from "./report.js";

describe("report formatters", () => {
  it("formats pull request state from observable merge metadata", () => {
    expect(pullRequestStateLabel({ state: "open", draft: false, merged_at: null })).toBe("Open");
    expect(pullRequestStateLabel({ state: "open", draft: true, merged_at: null })).toBe("Draft");
    expect(pullRequestStateLabel({ state: "closed", draft: false, merged_at: null })).toBe("Closed");
    expect(pullRequestStateLabel({ state: "closed", draft: false, merged_at: "2026-07-12T00:00:00Z" })).toBe("Merged");
  });

  it("formats affected scope without rendering zero affected files for global items", () => {
    expect(scopeLabel({ category: "ci", rule_id: "ci.failing", affected_files: [] })).toBe("CI-wide");
    expect(scopeLabel({ category: "change_scope", rule_id: "scope.large_file_count", affected_files: [] })).toBe("PR-wide");
    expect(scopeLabel({ category: "testing", rule_id: "testing.production_change_without_test_files", affected_files: [] })).toBe("Changed-file set");
    expect(scopeLabel({ category: "testing", affected_files: ["src/app.js"] })).toBe("1 affected file");
    expect(scopeLabel({ category: "testing", affected_files: ["src/app.js", "src/api.js"] })).toBe("2 affected files");
  });

  it("normalizes known provider display casing", () => {
    expect(providerDisplayName("github actions")).toBe("GitHub Actions");
    expect(providerDisplayName("github-actions")).toBe("GitHub Actions");
    expect(providerDisplayName("vercel")).toBe("Vercel");
    expect(providerDisplayName("internal ci")).toBe("Internal CI");
  });
});
