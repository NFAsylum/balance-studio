"use client";
import * as React from "react";
import { Slider } from "@/components/ui/slider";

/** Generation intent: four 3-position sliders + a free-text theme brief. The values translate
 * into plain-language modifiers appended to the Designer brief (FASE 4 refines the prompt). */

export type Intent = {
  power: number; // 0 weak · 1 average · 2 strong
  variety: number; // 0 uniform · 1 mixed · 2 experimental
  complexity: number; // 0 simple · 1 moderate · 2 rich
  theme: number; // 0 loose · 1 balanced · 2 strict (theme adherence)
  brief: string;
};

export const DEFAULT_INTENT: Intent = { power: 1, variety: 1, complexity: 1, theme: 1, brief: "" };

const LABELS: Record<keyof Omit<Intent, "brief">, [string, string[]]> = {
  power: ["Power scale", ["weak", "average", "strong"]],
  variety: ["Variety", ["uniform", "mixed", "experimental"]],
  complexity: ["Complexity", ["simple", "moderate", "rich"]],
  theme: ["Theme adherence", ["loose", "balanced", "strict"]],
};

/** Human-readable modifier line the Designer receives, e.g. "Power: strong. Variety: mixed." */
export function intentModifiers(intent: Intent): string {
  return (Object.keys(LABELS) as (keyof typeof LABELS)[])
    .map((k) => `${LABELS[k][0]}: ${LABELS[k][1][intent[k]]}`)
    .join(". ");
}

/** Compose the final brief sent to the Designer (theme text + intent modifiers). */
export function composeBrief(intent: Intent): string {
  const parts = [intent.brief.trim(), intentModifiers(intent)].filter(Boolean);
  return parts.join("\n\n");
}

export function IntentPanel({ intent, onChange }: { intent: Intent; onChange: (i: Intent) => void }) {
  const set = (k: keyof Intent, v: number | string) => onChange({ ...intent, [k]: v });
  return (
    <div className="flex flex-col gap-3" data-testid="intent-panel">
      {(Object.keys(LABELS) as (keyof typeof LABELS)[]).map((k) => (
        <label key={k} className="flex flex-col gap-1 text-sm">
          <span className="flex justify-between">
            <span>{LABELS[k][0]}</span>
            <span className="text-xs text-muted-foreground">{LABELS[k][1][intent[k]]}</span>
          </span>
          <Slider aria-label={LABELS[k][0]} min={0} max={2} step={1} value={[intent[k]]} onValueChange={(v) => set(k, v[0])} />
        </label>
      ))}
      <label className="flex flex-col gap-1 text-sm">
        Theme brief
        <textarea
          aria-label="theme brief"
          className="min-h-[56px] rounded-md border border-input bg-background px-3 py-1.5 text-sm"
          value={intent.brief}
          placeholder="e.g. a cyberpunk deck of hackers and drones"
          onChange={(e) => set("brief", e.target.value)}
        />
      </label>
      <div className="rounded-md bg-muted p-2 text-xs text-muted-foreground">
        The Designer will receive: <span className="italic">{composeBrief(intent) || "(nothing yet)"}</span>
      </div>
    </div>
  );
}
