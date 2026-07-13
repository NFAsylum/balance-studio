/** Client mirror of the 5 ConstraintEngine checks — used to flag violations on the sample
 * entity live in the editor. `unique_across_set` is a set-level rule (skipped for one entity). */

import type { Constraint } from "./api";

function num(v: unknown): number {
  return typeof v === "number" ? v : Number(v);
}
function tags(v: unknown): string[] {
  return Array.isArray(v) ? v.map(String) : [];
}

export function checkConstraints(entity: Record<string, unknown>, constraints: Constraint[]): string[] {
  const out: string[] = [];
  for (const c of constraints) {
    const p = c.params ?? {};
    if (c.kind === "range") {
      const v = num(entity[String(p.field)]);
      if (Number.isFinite(v) && (v < num(p.min) || v > num(p.max))) {
        out.push(`range: ${p.field}=${v} outside [${p.min}, ${p.max}]`);
      }
    } else if (c.kind === "sum_of_fields") {
      const fields = tags(p.fields);
      const total = fields.reduce((s, f) => s + num(entity[f]), 0);
      if (p.min != null && total < num(p.min)) out.push(`sum_of_fields: sum=${total} below ${p.min}`);
      if (p.max != null && total > num(p.max)) out.push(`sum_of_fields: sum=${total} above ${p.max}`);
    } else if (c.kind === "forbidden_combo") {
      const has = new Set(tags(entity[String(p.field)]));
      const forbidden = tags(p.tags);
      if (forbidden.length > 0 && forbidden.every((t) => has.has(t))) {
        out.push(`forbidden_combo: ${p.field} has all of {${forbidden.join(", ")}}`);
      }
    } else if (c.kind === "required_tag") {
      const has = new Set(tags(entity[String(p.field)]));
      const anyOf = tags(p.any_of);
      if (anyOf.length > 0 && !anyOf.some((t) => has.has(t))) {
        out.push(`required_tag: ${p.field} has none of {${anyOf.join(", ")}}`);
      }
    }
    // unique_across_set is a whole-set rule — not checkable on a single sample entity.
  }
  return out;
}
