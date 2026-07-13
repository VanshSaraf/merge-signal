import { titleCase } from "./formatting.js";

export const reportSections = [
  { id: "overview", label: "Overview" },
  { id: "files", label: "Files" },
  { id: "reviews", label: "Reviews" },
  { id: "signals", label: "Signals" },
  { id: "actions", label: "Actions" },
  { id: "evidence", label: "Evidence" },
];

export function optionValues(items, getter) {
  return [...new Set(items.flatMap((item) => getter(item) ?? []).filter(Boolean))]
    .sort((a, b) => String(a).localeCompare(String(b)));
}

export function filterFiles(files, filters) {
  return files.filter((file) => {
    const query = filters.query.trim().toLowerCase();
    return (
      (!query || `${file.path} ${file.previous_path ?? ""}`.toLowerCase().includes(query)) &&
      (!filters.level || file.level === filters.level) &&
      (!filters.kind || file.primary_kind === filters.kind) &&
      (!filters.area || (file.areas ?? []).includes(filters.area)) &&
      (!filters.status || file.status === filters.status) &&
      (!filters.magnitude || file.change_magnitude === filters.magnitude) &&
      (!filters.reviewAttention || (file.factors ?? []).some((factor) => factor.category === "review_attention"))
    );
  });
}

export function sortFiles(files, sortKey) {
  return [...files].sort((a, b) => {
    if (sortKey === "score") return (b.score ?? 0) - (a.score ?? 0) || (a.rank ?? 0) - (b.rank ?? 0);
    if (sortKey === "changes") return (b.changes ?? 0) - (a.changes ?? 0) || (a.rank ?? 0) - (b.rank ?? 0);
    if (sortKey === "path") return String(a.path).localeCompare(String(b.path));
    return (a.rank ?? 0) - (b.rank ?? 0);
  });
}

export function filterSignals(signals, filters) {
  return signals.filter((signal) => {
    const query = filters.fileQuery.trim().toLowerCase();
    return (
      (!filters.severity || signal.severity === filters.severity) &&
      (!filters.category || signal.category === filters.category) &&
      (!query || (signal.affected_files ?? []).some((file) => file.toLowerCase().includes(query)))
    );
  });
}

export function filterActions(actions, filters) {
  return actions.filter((action) => {
    const query = filters.fileQuery.trim().toLowerCase();
    return (
      (!filters.priority || action.priority === filters.priority) &&
      (!filters.category || action.category === filters.category) &&
      (!query || (action.affected_files ?? []).some((file) => file.toLowerCase().includes(query)))
    );
  });
}

export function cleanEvidence(evidence) {
  return (evidence ?? []).map((item) => ({
    kind: titleCase(item.kind ?? "evidence"),
    message: item.message ?? "",
    file: item.file ?? null,
  }));
}

export function dedupe(values) {
  return [...new Set((values ?? []).filter(Boolean))];
}

export function safeHttpUrl(value) {
  if (!value) return null;
  try {
    const url = new URL(value);
    if (url.protocol !== "https:" || !url.hostname || url.username || url.password) return null;
    return url.href;
  } catch {
    return null;
  }
}

export function extractSafeUrl(text) {
  const match = String(text ?? "").match(/https:\/\/[^\s)]+/);
  return match ? safeHttpUrl(match[0]) : null;
}

export function providerDisplayName(value) {
  const normalized = String(value ?? "").trim();
  if (!normalized) return "Unknown provider";
  const lower = normalized.toLowerCase().replaceAll("_", " ").replaceAll("-", " ");
  if (lower === "github actions") return "GitHub Actions";
  if (lower === "circleci" || lower === "circle ci") return "CircleCI";
  if (lower === "vercel") return "Vercel";
  return lower
    .split(/\s+/)
    .map((word) => (["api", "ci", "ui"].includes(word) ? word.toUpperCase() : titleCase(word)))
    .join(" ");
}

export function ciItemDisplayParts(item) {
  const provider = providerDisplayName(item?.provider);
  const name = String(item?.name ?? "").trim();
  return {
    provider,
    name: name && name.toLowerCase() !== provider.toLowerCase() ? name : "",
  };
}

export function plainReviewText(value) {
  return String(value ?? "")
    .replace(/```[\s\S]*?```/g, (match) => match.replace(/```[a-zA-Z0-9_-]*|```/g, "").trim())
    .replace(/`([^`]+)`/g, "$1")
    .replace(/!\[[^\]]*]\([^)]+\)/g, "[image omitted]")
    .replace(/\[([^\]]+)]\((https?:\/\/[^)]+)\)/g, "$1")
    .replace(/^#{1,6}\s*/gm, "")
    .replace(/[*_~]{1,3}/g, "")
    .replace(/[ \t]+/g, " ")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

export function reviewCountLabel(count, unavailable = false) {
  if (unavailable) return "Review context unavailable";
  const value = Number(count ?? 0);
  if (value <= 0) return "No inline conversations";
  return `${value} inline ${value === 1 ? "conversation" : "conversations"}`;
}

export function pullRequestStateLabel(metadata) {
  if (metadata?.draft) return "Draft";
  if (metadata?.merged_at) return "Merged";
  if (metadata?.state === "closed") return "Closed";
  if (metadata?.state === "open") return "Open";
  return titleCase(metadata?.state ?? "unknown");
}

export function scopeLabel(item) {
  const count = item?.affected_files?.length ?? 0;
  if (count === 1) return "1 affected file";
  if (count > 1) return `${count} affected files`;
  const category = String(item?.category ?? "").toLowerCase();
  const ruleId = String(item?.rule_id ?? "").toLowerCase();
  if (category === "ci" || ruleId.startsWith("ci.") || ruleId.includes(".ci_")) return "CI-wide";
  if (category === "testing" || category === "dependencies" || category === "infrastructure" || category === "configuration") return "Changed-file set";
  if (category === "file_review") return "Changed-file set";
  return "PR-wide";
}

export function snapshotIdentity(snapshot) {
  const reference = snapshot?.reference;
  if (!reference) return "";
  return `${reference.owner}/${reference.repository} #${reference.pull_number}`;
}
