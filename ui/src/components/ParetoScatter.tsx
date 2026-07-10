"use client";
import * as React from "react";
import { CartesianGrid, Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis } from "recharts";
import type { Objective } from "@/lib/api";
import { paretoFront, type Candidate } from "@/lib/objectives";

/** Scatter of candidates over two objectives; Pareto-front points are highlighted. */
export function ParetoScatter({
  objectives,
  candidates,
  width = 420,
  height = 260,
}: {
  objectives: Objective[];
  candidates: Candidate[];
  width?: number;
  height?: number;
}) {
  const [xObj, yObj] = objectives;
  const front = paretoFront(objectives, candidates);

  if (objectives.length < 2) {
    return <p className="text-sm text-neutral-500">Add 2 objectives to see the Pareto front.</p>;
  }

  const points = candidates.map((c) => ({
    id: c.id,
    x: c.values[xObj.metric_name] ?? 0,
    y: c.values[yObj.metric_name] ?? 0,
    onFront: front.has(c.id),
  }));

  return (
    <div className="flex flex-col gap-2">
      <ScatterChart width={width} height={height} margin={{ top: 10, right: 20, bottom: 20, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis type="number" dataKey="x" name={xObj.metric_name} />
        <YAxis type="number" dataKey="y" name={yObj.metric_name} />
        <ZAxis range={[60, 60]} />
        <Tooltip cursor={{ strokeDasharray: "3 3" }} />
        <Scatter data={points.filter((p) => !p.onFront)} fill="#a3a3a3" />
        <Scatter data={points.filter((p) => p.onFront)} fill="#7c3aed" />
      </ScatterChart>

      {/* Accessible, testable mirror of the chart. */}
      <ul data-testid="pareto-list" className="flex flex-wrap gap-2 text-xs">
        {points.map((p) => (
          <li
            key={p.id}
            data-testid={`candidate-${p.id}`}
            data-pareto={p.onFront ? "true" : "false"}
            className={p.onFront ? "font-semibold text-purple-700" : "text-neutral-400"}
          >
            {p.id} ({p.x.toFixed(2)}, {p.y.toFixed(2)})
          </li>
        ))}
      </ul>
    </div>
  );
}
