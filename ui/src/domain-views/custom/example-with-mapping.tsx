"use client";
import * as React from "react";
import type { EntityViewProps, ViewMeta } from "../types";
import { show, slot } from "../_shared";

/** Custom view example that uses slot mapping — the layout names abstract "slots" and the
 * `defaultMapping` (overridable per scenario) says which schema field fills each slot. */

const DEFAULT_MAPPING = { title: "name", primary: "hp", secondary: "atk" } as const;

export const meta: ViewMeta = {
  id: "custom.stat-tile",
  name: "Stat Tile (example)",
  domain: "*",
  defaultMapping: { ...DEFAULT_MAPPING },
};

export default function StatTileExample({ entity, size = "md", mapping }: EntityViewProps) {
  const map = { ...DEFAULT_MAPPING, ...mapping };
  const big = size === "lg" ? "text-3xl" : "text-2xl";
  return (
    <div className="flex w-48 flex-col items-center gap-1 rounded-xl border border-border bg-card p-4 text-card-foreground shadow">
      <h3 className="truncate text-sm font-semibold">{show(slot(entity, map, "title"))}</h3>
      <div className={`font-bold tabular-nums ${big}`}>{show(slot(entity, map, "primary"))}</div>
      <div className="text-xs text-muted-foreground">/ {show(slot(entity, map, "secondary"))}</div>
    </div>
  );
}
