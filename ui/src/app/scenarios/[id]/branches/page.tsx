"use client";
import * as React from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useT } from "@/lib/i18n";
import { Button } from "@/components/ui/button";
import { DiffView } from "@/components/DiffView";

export default function BranchesPage() {
  const { id } = useParams<{ id: string }>();
  const { t } = useT();
  const qc = useQueryClient();
  const branches = useQuery({ queryKey: ["branches", id], queryFn: () => api.listBranches(id) });
  const scenario = useQuery({ queryKey: ["scenario", id], queryFn: () => api.getScenario(id) });

  const [a, setA] = React.useState("main");
  const [b, setB] = React.useState("");

  const diff = useQuery({
    queryKey: ["diff", id, a, b],
    queryFn: () => api.diffBranches(id, a, b),
    enabled: !!a && !!b && a !== b,
  });

  const fork = useMutation({
    mutationFn: () => api.createBranch(id, scenario.data?.head_seq ?? 0, `fork-${Date.now()}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["branches", id] }),
  });

  const options = branches.data?.branches ?? [];

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">{t("branches")}</h1>
        <Button asChild variant="outline">
          <Link href={`/scenarios/${id}`}>{t("back")}</Link>
        </Button>
      </div>

      <div className="flex items-center gap-2 text-sm">
        <span>{t("compare")}</span>
        <BranchSelect label="A" value={a} onChange={setA} options={options.map((o) => o.branch_id)} />
        <span className="text-muted-foreground">{t("vs")}</span>
        <BranchSelect label="B" value={b} onChange={setB} options={options.map((o) => o.branch_id)} />
      </div>

      {diff.data && <DiffView diff={diff.data} onForkA={() => fork.mutate()} />}
      {a && b && a === b && <p className="text-sm text-muted-foreground">{t("pickTwo")}</p>}
    </div>
  );
}

function BranchSelect({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: string[];
}) {
  return (
    <select
      aria-label={`branch ${label}`}
      className="h-8 rounded border border-input bg-background px-2"
      value={value}
      onChange={(e) => onChange(e.target.value)}
    >
      <option value="">branch {label}…</option>
      {options.map((o) => (
        <option key={o} value={o}>
          {o}
        </option>
      ))}
    </select>
  );
}
