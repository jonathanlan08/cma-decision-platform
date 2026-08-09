export function money(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return value.toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  });
}

export function num(value: number | null | undefined, digits = 0): string {
  if (value === null || value === undefined) return "—";
  return value.toLocaleString("en-US", { maximumFractionDigits: digits });
}

export function pct(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined) return "—";
  const scaled = value * 100;
  return `${scaled > 0 ? "+" : ""}${scaled.toFixed(digits)}%`;
}

export function shortDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export function dateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  // Backend stores naive UTC timestamps; mark them as UTC before formatting.
  const normalized = /Z|[+-]\d\d:\d\d$/.test(iso) ? iso : `${iso}Z`;
  const date = new Date(normalized);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export function titleCase(value: string): string {
  return value
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}
