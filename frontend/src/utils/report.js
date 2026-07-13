import { titleCase } from "./formatting.js";

export const reportSections = [
  { id: "overview", label: "Overview" },
  { id: "files", label: "Files" },
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
      (!filters.status || file.status === filters.status)
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
