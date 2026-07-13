"use client";
import * as React from "react";
import { Plus, Trash2 } from "lucide-react";
import type { Constraint, ConstraintKind } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

/** Edit design-time constraints (the 5 ConstraintEngine kinds). Violations against the sample
 * entity are surfaced by the parent via `violations`. */

const KINDS: ConstraintKind[] = ["range", "sum_of_fields", "forbidden_combo", "required_tag", "unique_across_set"];

const BLANK: Record<ConstraintKind, () => Constraint> = {
  range: () => ({ kind: "range", params: { field: "", min: 0, max: 10 } }),
  sum_of_fields: () => ({ kind: "sum_of_fields", params: { fields: [], min: 0, max: 100 } }),
  forbidden_combo: () => ({ kind: "forbidden_combo", params: { field: "", tags: [] } }),
  required_tag: () => ({ kind: "required_tag", params: { field: "", any_of: [] } }),
  unique_across_set: () => ({ kind: "unique_across_set", params: { field: "" } }),
};

const csv = (v: unknown): string => (Array.isArray(v) ? v.join(", ") : "");
const toList = (s: string): string[] => s.split(",").map((x) => x.trim()).filter(Boolean);

export function ConstraintsEditor({
  constraints,
  onChange,
  violations = [],
}: {
  constraints: Constraint[];
  onChange: (c: Constraint[]) => void;
  violations?: string[];
}) {
  const setParam = (i: number, key: string, value: unknown) =>
    onChange(constraints.map((c, j) => (j === i ? { ...c, params: { ...c.params, [key]: value } } : c)));
  const setKind = (i: number, kind: ConstraintKind) => onChange(constraints.map((c, j) => (j === i ? BLANK[kind]() : c)));
  const remove = (i: number) => onChange(constraints.filter((_, j) => j !== i));

  return (
    <div className="flex flex-col gap-2" data-testid="constraints-editor">
      {constraints.map((c, i) => (
        <div key={i} className="rounded-md border border-border p-2 text-xs" data-testid={`constraint-${i}`}>
          <div className="mb-1 flex items-center gap-2">
            <select
              aria-label={`constraint ${i} kind`}
              className="h-7 rounded-md border border-input bg-background px-2"
              value={c.kind}
              onChange={(e) => setKind(i, e.target.value as ConstraintKind)}
            >
              {KINDS.map((k) => <option key={k} value={k}>{k}</option>)}
            </select>
            <button type="button" aria-label={`remove constraint ${i}`} className="ml-auto text-muted-foreground hover:text-destructive" onClick={() => remove(i)}>
              <Trash2 className="h-4 w-4" />
            </button>
          </div>
          <Params c={c} onParam={(k, v) => setParam(i, k, v)} />
        </div>
      ))}
      <Button size="sm" variant="outline" onClick={() => onChange([...constraints, BLANK.range()])}>
        <Plus className="mr-1 h-4 w-4" /> Add constraint
      </Button>
      {violations.length > 0 && (
        <div className="rounded-md bg-destructive/10 p-2 text-xs text-destructive" data-testid="constraint-violations">
          {violations.map((v, i) => <div key={i}>⚠ {v}</div>)}
        </div>
      )}
    </div>
  );
}

function Params({ c, onParam }: { c: Constraint; onParam: (key: string, value: unknown) => void }) {
  const p = c.params;
  const field = (
    <Input aria-label="field" className="h-7 w-28" placeholder="field" value={String(p.field ?? "")} onChange={(e) => onParam("field", e.target.value)} />
  );
  if (c.kind === "range") {
    return (
      <div className="flex items-center gap-1">
        {field}
        <Input aria-label="min" type="number" className="h-7 w-16" value={Number(p.min ?? 0)} onChange={(e) => onParam("min", Number(e.target.value))} />
        <Input aria-label="max" type="number" className="h-7 w-16" value={Number(p.max ?? 0)} onChange={(e) => onParam("max", Number(e.target.value))} />
      </div>
    );
  }
  if (c.kind === "sum_of_fields") {
    return (
      <div className="flex items-center gap-1">
        <Input aria-label="fields" className="h-7 flex-1" placeholder="fields (comma)" value={csv(p.fields)} onChange={(e) => onParam("fields", toList(e.target.value))} />
        <Input aria-label="min" type="number" className="h-7 w-16" value={Number(p.min ?? 0)} onChange={(e) => onParam("min", Number(e.target.value))} />
        <Input aria-label="max" type="number" className="h-7 w-16" value={Number(p.max ?? 0)} onChange={(e) => onParam("max", Number(e.target.value))} />
      </div>
    );
  }
  if (c.kind === "forbidden_combo") {
    return (
      <div className="flex items-center gap-1">
        {field}
        <Input aria-label="tags" className="h-7 flex-1" placeholder="tags (comma)" value={csv(p.tags)} onChange={(e) => onParam("tags", toList(e.target.value))} />
      </div>
    );
  }
  if (c.kind === "required_tag") {
    return (
      <div className="flex items-center gap-1">
        {field}
        <Input aria-label="any_of" className="h-7 flex-1" placeholder="any_of (comma)" value={csv(p.any_of)} onChange={(e) => onParam("any_of", toList(e.target.value))} />
      </div>
    );
  }
  return <div className="flex items-center gap-1">{field}</div>; // unique_across_set
}
