"use client";
import * as React from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Pencil } from "lucide-react";
import { api } from "@/lib/api";
import { useT } from "@/lib/i18n";
import type { EntitySchema, EntityValue } from "@/lib/schema";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EntityEditor } from "@/components/EntityEditor";
import { MetricsPanel, type Freshness, type MetricResult } from "@/components/MetricsPanel";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { getDefaultViewForDomain, getViewById } from "@/domain-views/registry";
import { SafeView } from "@/domain-views/SafeView";

const PHASES = ["design", "simulate", "judge", "iterate"] as const;
type Phase = (typeof PHASES)[number];

const PHASE_HINT: Record<Phase, string> = {
  design: "LLM designer materialises entities from the brief",
  simulate: "Run the deterministic (LLM-free) simulation and recompute metrics",
  judge: "LLM judge scores the set on subjective criteria (variety, cohesion)",
  iterate: "LLM iterator proposes balance changes — never overwrites your edits",
};

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
  const { t } = useT();
  const scenario = useQuery({ queryKey: ["scenario", id], queryFn: () => api.getScenario(id) });
  const metrics = useMetrics(id, scenario.data?.head_seq ?? 0);

  const iterate = usePhaseMutation(id);

  if (scenario.isLoading) return <p className="text-sm text-muted-foreground">{t("loading")}</p>;
  if (scenario.isError) return <p className="text-sm text-destructive">{t("loadError")}</p>;

  const data = scenario.data!;
  const entities = Object.entries(data.entities);
  // The backend already returns the scenario's *effective* schema (plugin + overrides) and the
  // chosen visual_variant — render each entity as its design, not raw JSON.
  const schema = data.schema as EntitySchema;
  const variant = data.scenario.visual_variant ?? null;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">{data.scenario.name}</h1>
          <p className="text-sm text-muted-foreground">
            {data.scenario.domain} · {data.head_seq} {t("events")} · {entities.length} {t("entities")}
          </p>
        </div>
        <div className="flex gap-2">
          <Button asChild variant="outline">
            <Link href={`/scenarios/${id}/history`}>{t("history")}</Link>
          </Button>
          <Button asChild variant="outline">
            <Link href={`/scenarios/${id}/branches`}>{t("branches")}</Link>
          </Button>
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        {PHASES.map((phase) => (
          <Button
            key={phase}
            variant="outline"
            title={PHASE_HINT[phase]}
            disabled={iterate.isPending}
            onClick={() => iterate.mutate(phase)}
          >
            {t(`phase_${phase}`)}
          </Button>
        ))}
      </div>

      <ErrorBoundary label="This scenario view hit an error.">
        {metrics.results.length > 0 && (
          <MetricsPanel
            results={metrics.results}
            freshness={iterate.isPending ? "computing" : metrics.freshness}
            onRunFull={() => iterate.mutate("simulate")}
          />
        )}

        {entities.length === 0 ? (
          <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed border-border p-10 text-center">
            <span className="text-3xl">🃏</span>
            <p className="text-sm text-muted-foreground">{t("noEntities")}</p>
            <Button size="sm" disabled={iterate.isPending} onClick={() => iterate.mutate("design")}>
              {iterate.isPending ? "…" : t("phase_design")}
            </Button>
          </div>
        ) : (
          <section className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {entities.map(([eid, entity]) => (
              <EntityCard key={eid} scenarioId={id} entityId={eid} entity={entity} schema={schema} variant={variant} domain={data.scenario.domain} />
            ))}
          </section>
        )}
      </ErrorBoundary>
    </div>
  );
}

function usePhaseMutation(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (phase: Phase) => api.iterate(id, phase),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["scenario", id] });
      qc.invalidateQueries({ queryKey: ["history", id] });
    },
  });
}

/** One entity: rendered as its domain view (falls back to the default list view), with a raw-JSON
 * toggle, flipping into the schema-driven EntityEditor on demand. */
function EntityCard({
  scenarioId,
  entityId,
  entity,
  schema,
  variant,
  domain,
}: {
  scenarioId: string;
  entityId: string;
  entity: Record<string, unknown>;
  schema?: EntitySchema;
  variant?: string | null;
  domain: string;
}) {
  const { t } = useT();
  const qc = useQueryClient();
  const [editing, setEditing] = React.useState(false);
  const [showRaw, setShowRaw] = React.useState(false);
  const [draft, setDraft] = React.useState<EntityValue>(entity);

  const save = useMutation({
    mutationFn: (value: EntityValue) => api.editEntity(scenarioId, entityId, value),
    onSuccess: () => {
      setEditing(false);
      qc.invalidateQueries({ queryKey: ["scenario", scenarioId] });
      qc.invalidateQueries({ queryKey: ["history", scenarioId] });
    },
  });

  const startEdit = () => {
    setDraft(entity);
    setEditing(true);
  };

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between gap-2">
        <CardTitle className="text-sm">{entityId}</CardTitle>
        {schema && !editing && (
          <Button size="sm" variant="ghost" onClick={startEdit} title={t("editHint")} aria-label={`${t("edit")} ${entityId}`}>
            <Pencil className="h-3.5 w-3.5" />
          </Button>
        )}
      </CardHeader>
      <CardContent>
        {editing && schema ? (
          <div className="flex flex-col gap-3">
            <EntityEditor schema={schema} value={draft} onChange={setDraft} />
            {save.isError && <p className="text-xs text-destructive">{String(save.error)}</p>}
            <div className="flex gap-2">
              <Button size="sm" disabled={save.isPending} onClick={() => save.mutate(draft)}>
                {save.isPending ? t("saving") : t("save")}
              </Button>
              <Button size="sm" variant="ghost" disabled={save.isPending} onClick={() => setEditing(false)}>
                {t("cancel")}
              </Button>
            </div>
          </div>
        ) : (
          <div className="flex flex-col gap-2">
            {schema ? (
              <SafeView view={getViewById(variant ?? "") ?? getDefaultViewForDomain(domain)} entity={entity} schema={schema} />
            ) : (
              <pre className="overflow-x-auto text-xs text-muted-foreground">{JSON.stringify(entity, null, 1)}</pre>
            )}
            <button
              type="button"
              onClick={() => setShowRaw((v) => !v)}
              className="self-start text-[10px] uppercase tracking-wide text-muted-foreground hover:text-foreground"
            >
              {showRaw ? t("hideRaw") : t("rawJson")}
            </button>
            {showRaw && (
              <pre className="overflow-x-auto text-xs text-muted-foreground">{JSON.stringify(entity, null, 1)}</pre>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
