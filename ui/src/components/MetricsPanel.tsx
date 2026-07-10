"use client";
import * as React from "react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export type MetricResult = { kind: string; name: string; data: Record<string, unknown> };
export type Freshness = "full" | "quick" | "stale" | "computing";

const FRESHNESS: Record<Freshness, { icon: string; label: string }> = {
  full: { icon: "🟢", label: "full" },
  quick: { icon: "🟡", label: "quick" },
  stale: { icon: "🔴", label: "stale" },
  computing: { icon: "⏳", label: "computing" },
};

export function FreshnessBadge({ state }: { state: Freshness }) {
  const s = FRESHNESS[state];
  return (
    <span data-testid="freshness" data-state={state} title={s.label} aria-label={`freshness: ${s.label}`}>
      {s.icon}
    </span>
  );
}

/** Compact human summary of any MetricResult, keyed by its kind. */
export function summarize(result: MetricResult): string {
  const d = result.data ?? {};
  switch (result.kind) {
    case "rating": {
      const entries = Object.entries(d as Record<string, number>);
      if (!entries.length) return "no ratings";
      const [name, val] = entries.sort((a, b) => b[1] - a[1])[0];
      return `top: ${name} (${Math.round(val)})`;
    }
    case "distribution":
      return d.mean != null ? `mean ${Number(d.mean).toFixed(2)}` : "—";
    case "index":
      return d.dominance_index != null ? `dominance ${Number(d.dominance_index).toFixed(2)}` : "—";
    case "tier": {
      const tiers = (d.tiers ?? {}) as Record<string, string[]>;
      return `S:${tiers.S?.length ?? 0} A:${tiers.A?.length ?? 0}`;
    }
    case "coverage":
      return `${d.covered ?? 0}/${d.total ?? 0} used`;
    default:
      return JSON.stringify(d).slice(0, 40);
  }
}

export function MetricCard({ result, freshness }: { result: MetricResult; freshness: Freshness }) {
  return (
    <Card data-testid={`metric-${result.name}`}>
      <CardHeader className="flex-row items-center justify-between">
        <CardTitle className="text-sm">{result.name}</CardTitle>
        <FreshnessBadge state={freshness} />
      </CardHeader>
      <CardContent>
        <p className="text-sm text-neutral-700">{summarize(result)}</p>
      </CardContent>
    </Card>
  );
}

export function MetricsPanel({
  results,
  freshness,
  onRunFull,
}: {
  results: MetricResult[];
  freshness: Freshness;
  onRunFull: () => void;
}) {
  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Metrics</h2>
        <Button size="sm" onClick={onRunFull} disabled={freshness === "computing"}>
          {freshness === "computing" ? "computing…" : "Run Full Simulation"}
        </Button>
      </div>
      <div className={cn("grid grid-cols-1 gap-3 sm:grid-cols-2")}>
        {results.map((r) => (
          <MetricCard key={r.name} result={r} freshness={freshness} />
        ))}
      </div>
    </div>
  );
}

/**
 * Debounced freshness: after an edit ("touch"), a quick estimate fires at `quickMs` idle
 * and a full recompute at `fullMs` idle. Real progress (computing -> full) is pushed by
 * the backend over SSE; here the timers drive the quick/full recompute triggers.
 */
export function useFreshnessDebounce(
  onQuick: () => void,
  onFull: () => void,
  quickMs = 2000,
  fullMs = 5000
) {
  const quickRef = React.useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const fullRef = React.useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const onQuickRef = React.useRef(onQuick);
  const onFullRef = React.useRef(onFull);
  onQuickRef.current = onQuick;
  onFullRef.current = onFull;

  const touch = React.useCallback(() => {
    if (quickRef.current) clearTimeout(quickRef.current);
    if (fullRef.current) clearTimeout(fullRef.current);
    quickRef.current = setTimeout(() => onQuickRef.current(), quickMs);
    fullRef.current = setTimeout(() => onFullRef.current(), fullMs);
  }, [quickMs, fullMs]);

  React.useEffect(
    () => () => {
      if (quickRef.current) clearTimeout(quickRef.current);
      if (fullRef.current) clearTimeout(fullRef.current);
    },
    []
  );

  return touch;
}
