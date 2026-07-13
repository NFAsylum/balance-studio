"use client";
import * as React from "react";
import { Check, X } from "lucide-react";
import type { FieldSpec } from "@/lib/schema";
import type { EntityViewProps, ViewMeta } from "./types";

/** The always-works fallback: renders ANY schema without crashing.
 *
 * Title = the `name` field (or the first `str` field, or "Untitled"). The rest are grouped by
 * kind: identifiers (str/cat) as a key/value list, numbers in a grid, tag sets as chips, maps
 * as a mini table, booleans as check/x. Neutral typography — no domain colour. */

export const meta: ViewMeta = { id: "default", name: "Default (list)", domain: "*" };

const SIZE = {
  sm: { pad: "p-3", title: "text-sm", gap: "gap-2" },
  md: { pad: "p-4", title: "text-base", gap: "gap-3" },
  lg: { pad: "p-6", title: "text-lg", gap: "gap-4" },
} as const;

function titleField(fields: FieldSpec[]): string | null {
  if (fields.some((f) => f.name === "name")) return "name";
  return fields.find((f) => f.kind === "str")?.name ?? null;
}

export default function DefaultListView({ entity, schema, size = "md" }: EntityViewProps) {
  const s = SIZE[size];
  const title = titleField(schema.fields);
  const titleValue = title ? String(entity[title] ?? "Untitled") : "Untitled";

  const of = (kinds: FieldSpec["kind"][]) =>
    schema.fields.filter((f) => kinds.includes(f.kind) && f.name !== title);

  const identifiers = of(["str", "cat"]);
  const numbers = of(["num"]);
  const tagSets = of(["tag_set"]);
  const maps = of(["map"]);
  const bools = of(["bool"]);

  return (
    <div className={`flex flex-col ${s.gap} rounded-lg border border-border bg-card text-card-foreground ${s.pad}`} data-testid="default-view">
      <h3 className={`font-semibold leading-tight ${s.title}`}>{titleValue || "Untitled"}</h3>

      {identifiers.length > 0 && (
        <dl className="flex flex-col gap-1 text-sm">
          {identifiers.map((f) => (
            <div key={f.name} className="flex justify-between gap-3">
              <dt className="text-muted-foreground">{f.name}</dt>
              <dd className="text-right font-medium">{fmt(entity[f.name])}</dd>
            </div>
          ))}
        </dl>
      )}

      {numbers.length > 0 && (
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
          {numbers.map((f) => (
            <div key={f.name} className="rounded-md bg-muted px-2 py-1">
              <div className="text-xs text-muted-foreground">{f.name}</div>
              <div className="text-sm font-semibold tabular-nums">{fmt(entity[f.name])}</div>
            </div>
          ))}
        </div>
      )}

      {bools.map((f) => (
        <div key={f.name} className="flex items-center gap-1 text-sm">
          {entity[f.name] ? <Check className="h-4 w-4 text-green-600" /> : <X className="h-4 w-4 text-muted-foreground" />}
          <span>{f.name}</span>
        </div>
      ))}

      {tagSets.map((f) => (
        <div key={f.name} className="flex flex-col gap-1">
          <span className="text-xs text-muted-foreground">{f.name}</span>
          <div className="flex flex-wrap gap-1">
            {asArray(entity[f.name]).length === 0 ? (
              <span className="text-xs text-muted-foreground/60">—</span>
            ) : (
              asArray(entity[f.name]).map((t, i) => (
                <span key={`${t}-${i}`} className="rounded bg-muted px-2 py-0.5 text-xs">{String(t)}</span>
              ))
            )}
          </div>
        </div>
      ))}

      {maps.map((f) => {
        const entries = Object.entries(asRecord(entity[f.name]));
        return (
          <div key={f.name} className="flex flex-col gap-1">
            <span className="text-xs text-muted-foreground">{f.name}</span>
            {entries.length === 0 ? (
              <span className="text-xs text-muted-foreground/60">—</span>
            ) : (
              <table className="w-full text-xs">
                <tbody>
                  {entries.map(([k, v]) => (
                    <tr key={k}>
                      <td className="py-0.5 pr-2 text-muted-foreground">{k}</td>
                      <td className="py-0.5 text-right tabular-nums">{fmt(v)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        );
      })}
    </div>
  );
}

// -- value helpers (tolerate any/missing values without crashing) ----------

function fmt(v: unknown): string {
  if (v == null) return "—";
  if (typeof v === "number") return Number.isInteger(v) ? String(v) : v.toFixed(2);
  if (typeof v === "boolean") return v ? "yes" : "no";
  if (Array.isArray(v)) return v.map(String).join(", ") || "—";
  if (typeof v === "object") return JSON.stringify(v);
  return String(v);
}

function asArray(v: unknown): unknown[] {
  return Array.isArray(v) ? v : [];
}

function asRecord(v: unknown): Record<string, unknown> {
  return v && typeof v === "object" && !Array.isArray(v) ? (v as Record<string, unknown>) : {};
}
