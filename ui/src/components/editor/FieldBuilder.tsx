"use client";
import * as React from "react";
import { ChevronDown, ChevronUp, Plus, Trash2 } from "lucide-react";
import type { FieldKind, FieldSpec } from "@/lib/schema";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

/** Add / edit / remove / reorder the effective field list. Reorder is ↑/↓ (no drag dependency).
 * Changing a field's kind resets kind-incompatible props so the spec stays valid. */

const KINDS: FieldKind[] = ["num", "cat", "bool", "str", "tag_set", "map"];

export function fieldError(fields: FieldSpec[], i: number): string | null {
  const f = fields[i];
  if (!f.name.trim()) return "name required";
  if (fields.some((o, j) => j !== i && o.name.trim() === f.name.trim())) return "duplicate name";
  if (f.kind === "num" && f.range && f.range[0] > f.range[1]) return "min > max";
  if (f.kind === "cat" && (!f.enum || f.enum.length === 0)) return "cat needs options";
  return null;
}

export function fieldsValid(fields: FieldSpec[]): boolean {
  return fields.length > 0 && fields.every((_, i) => fieldError(fields, i) === null);
}

/** Reset props that don't belong to the new kind (backend rejects, e.g., an enum on a num). */
function coerceKind(f: FieldSpec, kind: FieldKind): FieldSpec {
  const next: FieldSpec = { name: f.name, kind, description: f.description, origin: "user" };
  if (kind === "num") next.range = f.range ?? [0, 10];
  if (kind === "cat") next.enum = f.enum ?? ["option_a", "option_b"];
  if (kind === "map") next.enum = f.enum ?? undefined;
  if (kind === "str") {
    next.min_len = f.min_len ?? undefined;
    next.max_len = f.max_len ?? undefined;
  }
  return next;
}

export function FieldBuilder({ fields, onChange }: { fields: FieldSpec[]; onChange: (fields: FieldSpec[]) => void }) {
  const patch = (i: number, p: Partial<FieldSpec>) =>
    onChange(fields.map((f, j) => (j === i ? { ...f, ...p, origin: "user" } : f)));
  const setKind = (i: number, kind: FieldKind) => onChange(fields.map((f, j) => (j === i ? coerceKind(f, kind) : f)));
  const remove = (i: number) => onChange(fields.filter((_, j) => j !== i));
  const move = (i: number, dir: -1 | 1) => {
    const j = i + dir;
    if (j < 0 || j >= fields.length) return;
    const copy = [...fields];
    [copy[i], copy[j]] = [copy[j], copy[i]];
    onChange(copy);
  };
  const add = () => {
    const names = new Set(fields.map((f) => f.name));
    let k = fields.length + 1;
    while (names.has(`field_${k}`)) k++;
    onChange([...fields, { name: `field_${k}`, kind: "num", range: [0, 10], origin: "user" }]);
  };

  return (
    <div className="flex flex-col gap-2" data-testid="field-builder">
      {fields.map((f, i) => (
        <div key={i} className="rounded-md border border-border p-2" data-testid={`field-row-${i}`}>
          <div className="flex items-center gap-2">
            <div className="flex flex-col">
              <button type="button" aria-label="move up" disabled={i === 0} onClick={() => move(i, -1)} className="text-muted-foreground disabled:opacity-30">
                <ChevronUp className="h-4 w-4" />
              </button>
              <button type="button" aria-label="move down" disabled={i === fields.length - 1} onClick={() => move(i, 1)} className="text-muted-foreground disabled:opacity-30">
                <ChevronDown className="h-4 w-4" />
              </button>
            </div>
            <Input aria-label={`field ${i} name`} className="h-8 flex-1" value={f.name} onChange={(e) => patch(i, { name: e.target.value })} />
            <select
              aria-label={`field ${i} kind`}
              className="h-8 rounded-md border border-input bg-background px-2 text-sm"
              value={f.kind}
              onChange={(e) => setKind(i, e.target.value as FieldKind)}
            >
              {KINDS.map((k) => <option key={k} value={k}>{k}</option>)}
            </select>
            <button type="button" aria-label={`remove ${f.name}`} onClick={() => remove(i)} className="text-muted-foreground hover:text-destructive">
              <Trash2 className="h-4 w-4" />
            </button>
          </div>

          <KindConfig field={f} onPatch={(p) => patch(i, p)} />
          {fieldError(fields, i) && <p className="mt-1 text-xs text-destructive">{fieldError(fields, i)}</p>}
        </div>
      ))}
      <Button size="sm" variant="outline" onClick={add}><Plus className="mr-1 h-4 w-4" /> Add field</Button>
    </div>
  );
}

function KindConfig({ field, onPatch }: { field: FieldSpec; onPatch: (p: Partial<FieldSpec>) => void }) {
  if (field.kind === "num") {
    const [lo, hi] = field.range ?? [0, 10];
    return (
      <div className="mt-1 flex items-center gap-2 text-xs">
        <span className="text-muted-foreground">range</span>
        <Input aria-label={`${field.name} min`} type="number" className="h-7 w-20" value={lo} onChange={(e) => onPatch({ range: [Number(e.target.value), hi] })} />
        <span>–</span>
        <Input aria-label={`${field.name} max`} type="number" className="h-7 w-20" value={hi} onChange={(e) => onPatch({ range: [lo, Number(e.target.value)] })} />
      </div>
    );
  }
  if (field.kind === "cat" || field.kind === "map") {
    const value = (field.enum ?? []).join(", ");
    return (
      <div className="mt-1 flex items-center gap-2 text-xs">
        <span className="text-muted-foreground">{field.kind === "cat" ? "options" : "keys"}</span>
        <Input
          aria-label={`${field.name} options`}
          className="h-7 flex-1"
          value={value}
          placeholder="comma, separated"
          onChange={(e) => onPatch({ enum: e.target.value.split(",").map((s) => s.trim()).filter(Boolean) })}
        />
      </div>
    );
  }
  if (field.kind === "str") {
    return (
      <div className="mt-1 flex items-center gap-2 text-xs">
        <span className="text-muted-foreground">len</span>
        <Input aria-label={`${field.name} min_len`} type="number" className="h-7 w-20" value={field.min_len ?? ""} placeholder="min" onChange={(e) => onPatch({ min_len: e.target.value === "" ? undefined : Number(e.target.value) })} />
        <Input aria-label={`${field.name} max_len`} type="number" className="h-7 w-20" value={field.max_len ?? ""} placeholder="max" onChange={(e) => onPatch({ max_len: e.target.value === "" ? undefined : Number(e.target.value) })} />
      </div>
    );
  }
  return null; // bool / tag_set have no extra config
}
