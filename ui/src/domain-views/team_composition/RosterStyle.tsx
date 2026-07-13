"use client";
import * as React from "react";
import type { EntityViewProps, ViewMeta } from "../types";
import { show, slot } from "../_shared";

/** Compact LinkedIn-style roster card: emoji avatar + info rows (seniority, skills count,
 * top skills). Horizontal, dense — good for grids. */

const DEFAULT_MAPPING = {
  name: "name",
  seniority: "seniority",
  skills: "skills",
  preferred: "preferred_task_types",
} as const;

export const meta: ViewMeta = {
  id: "team_composition.roster",
  name: "Roster",
  domain: "team_composition",
  defaultMapping: { ...DEFAULT_MAPPING },
};

const SENIORITY_EMOJI: Record<string, string> = {
  junior: "🌱", mid: "🧑‍💻", senior: "🧠", lead: "🎖️", intern: "🐣", staff: "⭐", principal: "👑",
};
const SIZE = { sm: "w-64", md: "w-80", lg: "w-96" };

function asList(v: unknown): string[] {
  return Array.isArray(v) ? v.map(String) : [];
}

export default function RosterStyle({ entity, size = "md", mapping }: EntityViewProps) {
  const map = { ...DEFAULT_MAPPING, ...mapping };
  const seniority = String(slot(entity, map, "seniority") ?? "");
  const skills = asList(slot(entity, map, "skills"));

  return (
    <div
      data-testid="roster-card"
      className={`flex ${SIZE[size]} items-center gap-3 rounded-lg border border-border bg-card p-3 text-card-foreground shadow-sm`}
    >
      <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-muted text-2xl">
        {SENIORITY_EMOJI[seniority] ?? "👤"}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-baseline justify-between gap-2">
          <h3 className="truncate text-sm font-semibold">{show(slot(entity, map, "name"))}</h3>
          <span className="shrink-0 text-[11px] uppercase text-muted-foreground">{seniority || "—"}</span>
        </div>
        <p className="truncate text-xs text-muted-foreground">
          {skills.length ? `${skills.length} skills · ${skills.slice(0, 3).join(", ")}` : "no skills"}
        </p>
      </div>
    </div>
  );
}
