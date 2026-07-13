/** Client mirror of the backend `EntitySchema.with_overrides` + the inverse (diff).
 *
 * The editor works with a full, effective field list (what the user sees and edits). To create
 * a scenario it sends a *delta* of field ops on top of a starting point (the base plugin schema,
 * or a preset's already-applied schema) — exactly what `POST /scenarios` merges server-side. */

import type { FieldSpec } from "./schema";
import type { SchemaOverrides } from "./api";

type FieldOp = Record<string, unknown> & { name?: string; remove?: boolean };

const COMPARED_KEYS: (keyof FieldSpec)[] = ["kind", "range", "enum", "min_len", "max_len", "required", "description"];

/** Apply a field-op list onto a base field list (edit/add/remove by name), preserving order. */
export function applyOverrides(base: FieldSpec[], overrides: SchemaOverrides | undefined): FieldSpec[] {
  const byName = new Map<string, FieldSpec>(base.map((f) => [f.name, { ...f }]));
  const order = base.map((f) => f.name);

  for (const op of overrides?.fields ?? []) {
    const name = (op as FieldOp).name;
    if (!name) continue;
    if ((op as FieldOp).remove) {
      byName.delete(name);
      const i = order.indexOf(name);
      if (i >= 0) order.splice(i, 1);
      continue;
    }
    const { remove: _r, ...patch } = op as FieldOp;
    if (byName.has(name)) byName.set(name, { ...byName.get(name)!, ...(patch as Partial<FieldSpec>), origin: "user" });
    else {
      byName.set(name, { ...(patch as unknown as FieldSpec), origin: "user" });
      order.push(name);
    }
  }
  return order.map((n) => byName.get(n)!);
}

/** The field ops needed to turn `from` into `to` (add / edit / remove) — the delta to submit. */
export function diffFields(from: FieldSpec[], to: FieldSpec[]): SchemaOverrides {
  const fromByName = new Map(from.map((f) => [f.name, f]));
  const toNames = new Set(to.map((f) => f.name));
  const ops: FieldOp[] = [];

  for (const field of to) {
    const prev = fromByName.get(field.name);
    if (!prev || !fieldsEqual(prev, field)) ops.push(cleanField(field)); // add or edit (full spec)
  }
  for (const field of from) {
    if (!toNames.has(field.name)) ops.push({ name: field.name, remove: true });
  }
  return ops.length ? { fields: ops } : {};
}

function fieldsEqual(a: FieldSpec, b: FieldSpec): boolean {
  return COMPARED_KEYS.every((k) => JSON.stringify(a[k] ?? null) === JSON.stringify(b[k] ?? null));
}

/** A field spec as a plain op (drop the UI-only `origin` marker; keep defined props only). */
function cleanField(field: FieldSpec): FieldOp {
  const op: FieldOp = { name: field.name, kind: field.kind };
  for (const k of ["range", "enum", "min_len", "max_len", "required", "description"] as const) {
    if (field[k] != null) op[k] = field[k];
  }
  return op;
}
