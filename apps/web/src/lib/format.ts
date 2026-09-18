/** Formatting helpers. Amounts arrive as decimal strings from the API. */

export function formatMoney(amount: string | number | null | undefined, currency = "EUR"): string {
  const value = typeof amount === "number" ? amount : Number.parseFloat(amount ?? "0");
  if (Number.isNaN(value)) return "–";
  try {
    return new Intl.NumberFormat("de-DE", { style: "currency", currency }).format(value);
  } catch {
    return `${value.toFixed(2)} ${currency}`;
  }
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "–";
  const date = new Date(iso.length === 10 ? `${iso}T00:00:00` : iso);
  if (Number.isNaN(date.getTime())) return iso;
  return new Intl.DateTimeFormat("de-DE", { day: "2-digit", month: "2-digit", year: "numeric" }).format(date);
}

export function formatMonth(yyyyMm: string): string {
  const [year, month] = yyyyMm.split("-").map(Number);
  if (!year || !month) return yyyyMm;
  return new Intl.DateTimeFormat("en", { month: "short", year: "2-digit" }).format(new Date(year, month - 1, 1));
}

export function formatPercent(value: number | null | undefined): string {
  if (value === null || value === undefined) return "–";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(1)} %`;
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function todayIso(): string {
  const now = new Date();
  const local = new Date(now.getTime() - now.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 10);
}

/** Normalises "12,34" / "12.34" / 12.34 to a two-decimal string the API accepts. */
export function normaliseAmount(input: string | number): string | null {
  const text = String(input).trim().replace(/\s/g, "").replace(",", ".");
  if (!/^\d+(\.\d{1,2})?$/.test(text)) return null;
  return Number.parseFloat(text).toFixed(2);
}
