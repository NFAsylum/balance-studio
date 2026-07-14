"use client";
import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useT } from "@/lib/i18n";

/** A small header chip showing which LLM backend + model the API is actually using.
 *
 * Status only — there is no switching UI here; the tooltip points at the .env workflow. The
 * model comes from /health, which for the local backend reports what the server has *loaded*
 * (not just the env hint). Polled every 30s with a matching staleTime, so it is close to live
 * without hammering the backend. */

const CHIP = "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium whitespace-nowrap";

const BACKEND_COLOR: Record<string, string> = {
  local: "border-amber-300 bg-amber-100 text-amber-800 dark:border-amber-800/60 dark:bg-amber-950/60 dark:text-amber-300",
  anthropic: "border-green-300 bg-green-100 text-green-800 dark:border-green-800/60 dark:bg-green-950/60 dark:text-green-300",
  fake: "border-border bg-muted text-muted-foreground",
};

export function ModelStatusChip() {
  const { t } = useT();
  const q = useQuery({
    queryKey: ["health"],
    queryFn: api.health,
    staleTime: 30_000,
    refetchInterval: 30_000,
    retry: false,
  });

  if (q.isLoading) {
    return (
      <span className={`${CHIP} ${BACKEND_COLOR.fake}`} data-testid="model-status-chip">
        {t("chipLoading")}
      </span>
    );
  }

  if (q.isError || !q.data) {
    return (
      <span
        className={`${CHIP} border-destructive/40 bg-destructive/10 text-destructive`}
        data-testid="model-status-chip"
        title={t("chipOfflineTip")}
      >
        {t("chipOffline")}
      </span>
    );
  }

  const { backend_llm: backend, llm_model: model } = q.data;
  return (
    <span
      className={`${CHIP} ${BACKEND_COLOR[backend] ?? BACKEND_COLOR.fake}`}
      data-testid="model-status-chip"
      title={t("chipTip", { backend, model })}
    >
      {backend} · {model}
    </span>
  );
}
