"use client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { MetricsPanel, type Freshness, type MetricResult } from "@/components/MetricsPanel";

const PHASES = ["design", "simulate", "judge", "iterate"] as const;

/** Pull the metrics + freshness from the latest `simulate` event vs the current head. */
function useMetrics(id: string, headSeq: number) {
  const history = useQuery({ queryKey: ["history", id], queryFn: () => api.history(id) });
  const events = history.data?.events ?? [];
  const lastSim = [...events].reverse().find((e) => e.kind === "simulate");
  const raw = (lastSim?.after?.metrics ?? {}) as Record<string, MetricResult>;
  const results = Object.values(raw);
  const freshness: Freshness = !lastSim ? "stale" : headSeq > lastSim.seq ? "stale" : "full";
  return { results, freshness };
}

export default function ScenarioPage() {
  const { id } = useParams<{ id: string }>();
  const qc = useQueryClient();
  const scenario = useQuery({ queryKey: ["scenario", id], queryFn: () => api.getScenario(id) });
  const metrics = useMetrics(id, scenario.data?.head_seq ?? 0);

  const iterate = useMutation({
    mutationFn: (phase: (typeof PHASES)[number]) => api.iterate(id, phase),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["scenario", id] });
      qc.invalidateQueries({ queryKey: ["history", id] });
    },
  });

  if (scenario.isLoading) return <p className="text-sm text-neutral-500">carregando…</p>;
  if (scenario.isError) return <p className="text-sm text-red-600">erro ao carregar scenario</p>;

  const data = scenario.data!;
  const entities = Object.entries(data.entities);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">{data.scenario.name}</h1>
          <p className="text-sm text-neutral-500">
            {data.scenario.domain} · {data.head_seq} events · {entities.length} entities
          </p>
        </div>
        <div className="flex gap-2">
          <Button asChild variant="outline">
            <Link href={`/scenarios/${id}/history`}>History</Link>
          </Button>
          <Button asChild variant="outline">
            <Link href={`/scenarios/${id}/branches`}>Branches</Link>
          </Button>
        </div>
      </div>

      <div className="flex gap-2">
        {PHASES.map((phase) => (
          <Button
            key={phase}
            variant="outline"
            disabled={iterate.isPending}
            onClick={() => iterate.mutate(phase)}
          >
            {phase}
          </Button>
        ))}
      </div>

      {metrics.results.length > 0 && (
        <MetricsPanel
          results={metrics.results}
          freshness={iterate.isPending ? "computing" : metrics.freshness}
          onRunFull={() => iterate.mutate("simulate")}
        />
      )}

      <section className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {entities.length === 0 && (
          <p className="text-sm text-neutral-500">Nenhuma entidade — rode a fase &quot;design&quot;.</p>
        )}
        {entities.map(([eid, entity]) => (
          <Card key={eid}>
            <CardHeader>
              <CardTitle className="text-sm">{eid}</CardTitle>
            </CardHeader>
            <CardContent>
              <pre className="overflow-x-auto text-xs text-neutral-600">
                {JSON.stringify(entity, null, 1)}
              </pre>
            </CardContent>
          </Card>
        ))}
      </section>
    </div>
  );
}
