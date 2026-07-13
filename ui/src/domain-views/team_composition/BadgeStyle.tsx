"use client";
import * as React from "react";
import type { EntityViewProps, ViewMeta } from "../types";
import { show, slot } from "../_shared";

/** Vertical badge: colour-hashed avatar with the name initial, seniority chip, skill pills,
 * and preferred task types as smaller tags. */

const DEFAULT_MAPPING = {
  name: "name",
  seniority: "seniority",
  skills: "skills",
  preferred: "preferred_task_types",
} as const;

export const meta: ViewMeta = {
  id: "team_composition.badge",
  name: "Badge",
  domain: "team_composition",
  defaultMapping: { ...DEFAULT_MAPPING },
};

const SENIORITY_COLOR: Record<string, string> = {
  junior: "bg-emerald-500", mid: "bg-sky-500", senior: "bg-violet-500", lead: "bg-amber-500",
  intern: "bg-teal-500", staff: "bg-fuchsia-500", principal: "bg-rose-500",
};
const AVATAR = ["bg-red-500", "bg-orange-500", "bg-green-600", "bg-blue-600", "bg-purple-600", "bg-pink-600"];
const SIZE = { sm: "w-40", md: "w-52", lg: "w-60" };

function hashIndex(s: string, mod: number): number {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) % 100000;
  return h % mod;
}

function asList(v: unknown): string[] {
  return Array.isArray(v) ? v.map(String) : [];
}

export default function BadgeStyle({ entity, size = "md", mapping }: EntityViewProps) {
  const map = { ...DEFAULT_MAPPING, ...mapping };
  const name = show(slot(entity, map, "name"));
  const seniority = String(slot(entity, map, "seniority") ?? "");
  const skills = asList(slot(entity, map, "skills"));
  const preferred = asList(slot(entity, map, "preferred"));
  const initial = name && name !== "—" ? name[0]!.toUpperCase() : "?";

  return (
    <div
      data-testid="badge-card"
      className={`flex ${SIZE[size]} flex-col items-center gap-2 rounded-xl border border-border bg-card p-4 text-card-foreground shadow`}
    >
      <div className={`flex h-14 w-14 items-center justify-center rounded-full text-xl font-bold text-white ${AVATAR[hashIndex(name, AVATAR.length)]}`}>
        {initial}
      </div>
      <h3 className="truncate text-center text-sm font-semibold">{name}</h3>
      <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium uppercase text-white ${SENIORITY_COLOR[seniority] ?? "bg-neutral-500"}`}>
        {seniority || "—"}
      </span>

      <div className="flex flex-wrap justify-center gap-1">
        {skills.length === 0 ? (
          <span className="text-xs text-muted-foreground/60">no skills</span>
        ) : (
          skills.slice(0, 6).map((s, i) => (
            <span key={`${s}-${i}`} className="rounded bg-muted px-1.5 py-0.5 text-[11px]">{s}</span>
          ))
        )}
      </div>
      {preferred.length > 0 && (
        <div className="flex flex-wrap justify-center gap-1">
          {preferred.slice(0, 4).map((p, i) => (
            <span key={`${p}-${i}`} className="rounded bg-muted/60 px-1 py-0.5 text-[9px] text-muted-foreground">{p}</span>
          ))}
        </div>
      )}
    </div>
  );
}
