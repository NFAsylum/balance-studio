"use client";
import * as React from "react";
import { useT } from "@/lib/i18n";
import { cn } from "@/lib/utils";

/** Generation intent: four 3-choice segmented controls + a free-text theme brief. The values
 * translate into plain-language modifiers appended to the Designer brief (FASE 4 refines the
 * prompt). A segmented control reads clearer than a 3-stop slider and responds on click. */

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
  const { t } = useT();
  const set = (k: keyof Intent, v: number | string) => onChange({ ...intent, [k]: v });
  return (
    <div className="flex flex-col gap-3" data-testid="intent-panel">
      {(Object.keys(LABELS) as (keyof typeof LABELS)[]).map((k) => {
        const [label, options] = LABELS[k];
        return (
          <div key={k} className="flex flex-col gap-1 text-sm">
            <span>{label}</span>
            <div role="radiogroup" aria-label={label} className="flex rounded-md border border-input p-0.5">
              {options.map((opt, i) => (
                <button
                  key={opt}
                  type="button"
                  role="radio"
                  aria-checked={intent[k] === i}
                  aria-label={`${label}: ${opt}`}
                  onClick={() => set(k, i)}
                  className={cn(
                    "flex-1 rounded px-2 py-1 text-xs capitalize transition-colors",
                    intent[k] === i ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-muted"
                  )}
                >
                  {opt}
                </button>
              ))}
            </div>
          </div>
        );
      })}
      <label className="flex flex-col gap-1 text-sm">
        {t("themeBrief")}
        <textarea
          aria-label="theme brief"
          className="min-h-[56px] rounded-md border border-input bg-background px-3 py-1.5 text-sm"
          value={intent.brief}
          placeholder="e.g. a cyberpunk deck of hackers and drones"
          onChange={(e) => set("brief", e.target.value)}
        />
      </label>
      <div className="rounded-md bg-muted p-2 text-xs text-muted-foreground">
        {t("designerReceives")} <span className="italic">{composeBrief(intent) || t("nothingYet")}</span>
      </div>
    </div>
  );
}
