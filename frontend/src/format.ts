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
