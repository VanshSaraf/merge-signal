export function titleCase(value) {
  return String(value ?? "")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function formatNumber(value) {
  return new Intl.NumberFormat("en-US").format(Number(value ?? 0));
}

export function compactList(values, limit = 2) {
  const items = (values ?? []).filter(Boolean);
  if (items.length <= limit) {
    return items.join(", ");
  }
  return `${items.slice(0, limit).join(", ")} +${items.length - limit} more`;
}

export function uniqueLimit(values, limit = 6) {
  return [...new Set((values ?? []).filter(Boolean))].slice(0, limit);
}
