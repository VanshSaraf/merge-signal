export function toneForLevel(level) {
  if (["blocked", "not_ready", "very_high", "high", "failing", "unavailable"].includes(level)) {
    return "danger";
  }
  if (["ready_with_caution", "moderate", "medium", "pending", "partial", "missing", "unknown"].includes(level)) {
    return "warning";
  }
  if (["ready", "low", "passing", "complete"].includes(level)) {
    return "success";
  }
  return "neutral";
}

export function friendlyError(error) {
  const code = error?.code;
  if (code === "INVALID_PULL_REQUEST_URL") {
    return {
      title: "Invalid pull-request URL",
      detail: "Use a public GitHub pull-request URL in the form https://github.com/owner/repository/pull/123.",
    };
  }
  if (code === "GITHUB_PULL_REQUEST_NOT_FOUND") {
    return { title: "Pull request not found", detail: "GitHub could not find that public pull request." };
  }
  if (code === "GITHUB_ACCESS_DENIED") {
    return { title: "Repository is inaccessible", detail: "The repository may be private or unavailable to the configured backend." };
  }
  if (code === "GITHUB_RATE_LIMITED") {
    return { title: "GitHub rate limit reached", detail: "GitHub temporarily rejected the request because the rate limit was reached. Retry when capacity is available." };
  }
  if (code === "BACKEND_UNAVAILABLE") {
    return { title: "Backend unavailable", detail: "Start the FastAPI backend and retry the analysis." };
  }
  if (code?.startsWith("GITHUB_")) {
    return { title: "GitHub temporarily unavailable", detail: "The backend could not complete the GitHub snapshot request." };
  }
  return { title: "Analysis failed", detail: error?.message || "The backend returned an unexpected response." };
}
