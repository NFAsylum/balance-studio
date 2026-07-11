"use client";
import * as React from "react";
import type { DiffReport } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

/** Presentational branch diff: entities added/removed/changed + metric deltas + fork. */
export function DiffView({ diff, onForkA }: { diff: DiffReport; onForkA?: () => void }) {
  const { entities, metrics_diff } = diff;
  const metricRows = Object.entries(metrics_diff);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">
          {diff.branch_a} <span className="text-muted-foreground">vs</span> {diff.branch_b}
        </h2>
        {onForkA && (
          <Button size="sm" variant="outline" onClick={onForkA}>
            Fork from {diff.branch_a}
          </Button>
        )}
      </div>

      <p className="text-sm text-muted-foreground">
        {diff.exclusive_events_a} events only in {diff.branch_a} · {diff.exclusive_events_b} only in {diff.branch_b}
      </p>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Entities</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-2 text-sm">
          <DiffLine label={`added in ${diff.branch_b}`} testid="added" color="text-green-700" ids={entities.only_in_b} />
          <DiffLine label={`removed in ${diff.branch_b}`} testid="removed" color="text-red-700" ids={entities.only_in_a} />
          <DiffLine label="changed" testid="changed" color="text-amber-700" ids={entities.changed} />
        </CardContent>
      </Card>

      {metricRows.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Metrics</CardTitle>
          </CardHeader>
          <CardContent>
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-muted-foreground">
                  <th className="py-1">entity</th>
                  <th>{diff.branch_a}</th>
                  <th>{diff.branch_b}</th>
                </tr>
              </thead>
              <tbody>
                {metricRows.map(([entity, v]) => (
                  <tr key={entity} data-testid={`metric-diff-${entity}`}>
                    <td className="py-1">{entity}</td>
                    <td>{v.a ?? "—"}</td>
                    <td>{v.b ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function DiffLine({ label, testid, color, ids }: { label: string; testid: string; color: string; ids: string[] }) {
  return (
    <div data-testid={`diff-${testid}`} className="flex flex-wrap items-center gap-2">
      <span className="w-40 shrink-0 text-muted-foreground">{label}</span>
      {ids.length === 0 ? (
        <span className="text-muted-foreground/60">none</span>
      ) : (
        ids.map((id) => (
          <span key={id} className={`rounded bg-muted px-2 py-0.5 text-xs ${color}`}>
            {id}
          </span>
        ))
      )}
    </div>
  );
}
