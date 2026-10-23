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
  const rounded = Math.abs(value) >= 100 ? value.toFixed(0) : value.toFixed(1);
  return `${sign}${rounded.replace("-", "−")}`;
}
