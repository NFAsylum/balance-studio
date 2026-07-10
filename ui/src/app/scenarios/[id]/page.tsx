"use client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const PHASES = ["design", "simulate", "judge", "iterate"] as const;

export default function ScenarioPage() {
  const { id } = useParams<{ id: string }>();
  const qc = useQueryClient();
  const scenario = useQuery({ queryKey: ["scenario", id], queryFn: () => api.getScenario(id) });

  const iterate = useMutation({
    mutationFn: (phase: (typeof PHASES)[number]) => api.iterate(id, phase),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["scenario", id] }),
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
