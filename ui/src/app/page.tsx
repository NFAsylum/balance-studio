"use client";
import * as React from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useT } from "@/lib/i18n";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Slider } from "@/components/ui/slider";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogClose } from "@/components/ui/dialog";
import { Hero } from "@/components/Hero";
import { ErrorBoundary } from "@/components/ErrorBoundary";

export default function HomePage() {
  const qc = useQueryClient();
  const { t } = useT();
  const domains = useQuery({ queryKey: ["domains"], queryFn: api.listDomains });
  const scenarios = useQuery({ queryKey: ["scenarios"], queryFn: api.listScenarios });

  const [domain, setDomain] = React.useState<string>("");
  const [name, setName] = React.useState("New scenario");
  const [brief, setBrief] = React.useState("");
  const [n, setN] = React.useState(8);

  const create = useMutation({
    mutationFn: () => api.createScenario({ domain, name, brief, n_entities: n }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["scenarios"] }),
  });

  return (
    <div className="flex flex-col gap-8">
      <section className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">{t("scenarios")}</h1>
          <p className="text-sm text-muted-foreground">
            {domains.data ? t("domainsAvailable", { n: domains.data.domains.length }) : t("loadingDomains")}
          </p>
        </div>
        <div className="flex gap-2">
          <Button asChild variant="outline"><Link href="/scenarios/new">Editor</Link></Button>
        <Dialog>
          <DialogTrigger asChild>
            <Button>{t("newScenario")}</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>{t("createScenario")}</DialogTitle>
            </DialogHeader>
            <div className="flex flex-col gap-4">
              <label className="flex flex-col gap-1 text-sm">
                {t("domain")}
                <Select value={domain} onValueChange={setDomain}>
                  <SelectTrigger>
                    <SelectValue placeholder={t("pickDomain")} />
                  </SelectTrigger>
                  <SelectContent>
                    {domains.data?.domains.map((d) => (
                      <SelectItem key={d} value={d}>
                        {d}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </label>
              <label className="flex flex-col gap-1 text-sm">
                {t("name")}
                <Input value={name} onChange={(e) => setName(e.target.value)} />
              </label>
              <label className="flex flex-col gap-1 text-sm">
                {t("brief")}
                <Input value={brief} onChange={(e) => setBrief(e.target.value)} placeholder={t("briefPlaceholder")} />
              </label>
              <label className="flex flex-col gap-2 text-sm">
                {t("entitiesField")}: {n}
                <Slider value={[n]} min={1} max={30} step={1} onValueChange={(v) => setN(v[0])} />
              </label>
              <DialogClose asChild>
                <Button disabled={!domain || create.isPending} onClick={() => create.mutate()}>
                  {create.isPending ? t("creating") : t("create")}
                </Button>
              </DialogClose>
            </div>
          </DialogContent>
        </Dialog>
        </div>
      </section>

      <ErrorBoundary label="Couldn't load scenarios.">
        {scenarios.data?.scenarios.length === 0 ? (
          <Hero hasCardGame={!!domains.data?.domains.includes("card_game")} />
        ) : (
          <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {scenarios.data?.scenarios.map((s) => (
              <Link key={s.id} href={`/scenarios/${s.id}`}>
                <Card className="transition-shadow hover:shadow-md">
                  <CardHeader>
                    <CardTitle>{s.name}</CardTitle>
                    <CardDescription>
                      {s.domain} · {s.head_event_seq} {t("events")} · {t("branch")} {s.current_branch}
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <p className="line-clamp-2 text-sm text-muted-foreground">{s.brief || t("noBrief")}</p>
                  </CardContent>
                </Card>
              </Link>
            ))}
          </section>
        )}
      </ErrorBoundary>
    </div>
  );
}
