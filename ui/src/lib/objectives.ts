/** Client mirror of core.objectives (score + Pareto) so the UI can preview trade-offs. */
import type { Objective } from "@/lib/api";

export type Candidate = { id: string; values: Record<string, number> };

function utility(obj: Objective, value: number): number {
  if (obj.direction === "maximize") return value;
  if (obj.direction === "minimize") return -value;
  return -Math.abs(value - (obj.target_value ?? 0)); // "target": closer is better
}

/** Weighted sum of per-objective utilities (weight 0 or missing metric ignored). */
export function scoreObjectives(objectives: Objective[], values: Record<string, number>): number {
  let total = 0;
  for (const obj of objectives) {
    if (obj.weight === 0 || !(obj.metric_name in values)) continue;
    total += obj.weight * utility(obj, values[obj.metric_name]);
  }
  return total;
}

function dominates(a: number[], b: number[]): boolean {
  return a.every((x, i) => x >= b[i]) && a.some((x, i) => x > b[i]);
}

/** Ids of the non-dominated candidates (the Pareto front) across all objectives. */
export function paretoFront(objectives: Objective[], candidates: Candidate[]): Set<string> {
  const utils = candidates.map((c) => objectives.map((o) => utility(o, c.values[o.metric_name] ?? 0)));
  const front = new Set<string>();
  candidates.forEach((c, i) => {
    const dominated = utils.some((u, j) => j !== i && dominates(u, utils[i]));
    if (!dominated) front.add(c.id);
  });
  return front;
}
