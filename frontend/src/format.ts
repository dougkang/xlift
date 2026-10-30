import type { Schemas } from "./api/client";

type Category = Schemas["CategoryInfo"];

/** Display a category value: ratios as .473 (style guide), counts as integers or one decimal. */
export function formatValue(value: number | null | undefined, cat: Category, signed = false): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "–";
  const sign = signed && value > 0 ? "+" : "";
  if (cat.decimals > 0) {
    const fixed = Math.abs(value).toFixed(cat.decimals).replace(/^0(?=\.)/, "");
    return `${value < 0 ? "−" : sign}${fixed}`;
  }
  // Counting averages always show 1 decimal so a value and its change share precision (003 R2).
  const rounded = value.toFixed(1);
  return `${sign}${rounded.replace("-", "−")}`;
}

/** Display an actual (week-to-date) value: ratios as .473, counts as whole numbers (005). */
export function formatActual(value: number | null | undefined, cat: Category): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "–";
  return cat.decimals > 0 ? formatValue(value, cat) : String(Math.round(value));
}

/** Display an xLift value: signed, two decimals (+1.27, 0.00, −0.40); "–" when missing (007). */
export function formatXlift(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "–";
  const fixed = Math.abs(value).toFixed(2);
  if (fixed === "0.00") return "0.00";
  return `${value < 0 ? "−" : "+"}${fixed}`;
}

type Expected = Schemas["ExpectedRecordModel"];

/** An expected category record to one decimal: "58.4–45.1–4.5" (010). */
export function formatRecord(r: Expected): string {
  return [r.wins, r.losses, r.ties].map((v) => v.toFixed(1)).join("–");
}

/** A standings win % (0–1) as a whole percentage: "56%". */
export function formatPct(p: number): string {
  return `${Math.round(p * 100)}%`;
}
