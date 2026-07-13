/** Small helpers shared by the shipped domain views. */

/** Read a visual slot from the entity via the (default + user) field mapping. */
export function slot(
  entity: Record<string, unknown>,
  mapping: Record<string, string>,
  name: string,
): unknown {
  const field = mapping[name];
  return field ? entity[field] : undefined;
}

/** Display a value, or an em-dash for missing/empty — never crash on an exotic schema. */
export function show(v: unknown): string {
  if (v == null || v === "") return "—";
  if (typeof v === "number") return Number.isInteger(v) ? String(v) : v.toFixed(1);
  if (Array.isArray(v)) return v.length ? v.map(String).join(", ") : "—";
  return String(v);
}

/** A number for a stat badge, or 0 when absent (so bars/rings don't NaN). */
export function stat(v: unknown): number {
  return typeof v === "number" && Number.isFinite(v) ? v : 0;
}
