"use client";
import * as React from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useT } from "@/lib/i18n";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Timeline } from "@/components/Timeline";

export default function HistoryPage() {
  const { id } = useParams<{ id: string }>();
  const { t } = useT();
  const [selected, setSelected] = React.useState<number | null>(null);

  const history = useQuery({ queryKey: ["history", id], queryFn: () => api.history(id) });
  const stateAt = useQuery({
    queryKey: ["scenario", id, selected],
    queryFn: () => api.getScenario(id, selected ?? undefined),
    enabled: selected != null,
  });

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">{t("history")}</h1>
        <Button asChild variant="outline">
          <Link href={`/scenarios/${id}`}>{t("back")}</Link>
        </Button>
      </div>

      {history.data && <Timeline events={history.data.events} selectedSeq={selected} onSelect={setSelected} />}

      {selected != null && (
        <Card>
          <CardHeader className="flex-row items-center justify-between">
            <CardTitle className="text-sm">{t("readOnlyAt", { seq: selected })}</CardTitle>
            <Button size="sm" variant="ghost" onClick={() => setSelected(null)}>
              {t("backToHead")}
            </Button>
          </CardHeader>
          <CardContent>
            <pre className="overflow-x-auto text-xs text-muted-foreground">
              {JSON.stringify(stateAt.data?.entities ?? {}, null, 1)}
            </pre>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
