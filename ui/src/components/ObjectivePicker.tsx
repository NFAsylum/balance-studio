"use client";
import * as React from "react";
import { X } from "lucide-react";
import type { Objective } from "@/lib/api";
import { scoreObjectives } from "@/lib/objectives";
import { Slider } from "@/components/ui/slider";

const DIRECTIONS: Objective["direction"][] = ["maximize", "minimize", "target"];

/** Compose weighted multi-objectives; shows the aggregate score over current metric values. */
export function ObjectivePicker({
  available,
  value,
  onChange,
  metricValues = {},
}: {
  available: string[];
  value: Objective[];
  onChange: (next: Objective[]) => void;
  metricValues?: Record<string, number>;
}) {
  const used = new Set(value.map((o) => o.metric_name));
  const addable = available.filter((m) => !used.has(m));
  const score = scoreObjectives(value, metricValues);

  const update = (i: number, patch: Partial<Objective>) =>
    onChange(value.map((o, idx) => (idx === i ? { ...o, ...patch } : o)));

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Objectives</h2>
        <span data-testid="aggregate-score" className="text-sm text-neutral-600">
          score: {score.toFixed(2)}
        </span>
      </div>

      <div className="flex flex-col gap-2">
        {value.map((obj, i) => (
          <div key={obj.metric_name} data-testid={`objective-${obj.metric_name}`} className="flex items-center gap-3 rounded border border-neutral-200 p-2 text-sm">
            <span className="w-40 font-medium">{obj.metric_name}</span>
            <select
              aria-label={`direction ${obj.metric_name}`}
              className="h-8 rounded border border-neutral-300 px-2"
              value={obj.direction}
              onChange={(e) => update(i, { direction: e.target.value as Objective["direction"] })}
            >
              {DIRECTIONS.map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </select>
            <div className="flex flex-1 items-center gap-2">
              <span className="text-xs text-neutral-500">weight {obj.weight.toFixed(1)}</span>
              <Slider
                className="max-w-[160px]"
                aria-label={`weight ${obj.metric_name}`}
                min={0}
                max={3}
                step={0.5}
                value={[obj.weight]}
                onValueChange={(v) => update(i, { weight: v[0] })}
              />
            </div>
            <button type="button" aria-label={`remove ${obj.metric_name}`} onClick={() => onChange(value.filter((_, idx) => idx !== i))}>
              <X className="h-4 w-4 text-neutral-400" />
            </button>
          </div>
        ))}
      </div>

      {addable.length > 0 && (
        <select
          aria-label="add objective"
          className="h-9 w-56 rounded-md border border-neutral-300 px-3 text-sm"
          value=""
          onChange={(e) => {
            if (e.target.value) {
              onChange([...value, { metric_name: e.target.value, direction: "maximize", weight: 1 }]);
            }
          }}
        >
          <option value="">+ add objective…</option>
          {addable.map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </select>
      )}
    </div>
  );
}
