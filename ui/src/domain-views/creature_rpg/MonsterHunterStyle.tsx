"use client";
import * as React from "react";
import type { EntityViewProps, ViewMeta } from "../types";
import { show, slot, stat } from "../_shared";

/** Monster Hunter-style wiki entry (dark): a monster silhouette, a stat line, and
 * resistances rendered as star ratings. */

const DEFAULT_MAPPING = {
  name: "name",
  type: "type",
  hp: "hp",
  atk: "atk",
  def: "defense",
  resistances: "resistances",
} as const;

export const meta: ViewMeta = {
  id: "creature_rpg.monster-hunter",
  name: "Monster Hunter",
  domain: "creature_rpg",
  defaultMapping: { ...DEFAULT_MAPPING },
};

const TYPE_GLYPH: Record<string, string> = {
  fire: "🐲", water: "🐊", plant: "🦎", ice: "🦕", electric: "🦖", rock: "🦏", wind: "🦅", shadow: "🦇",
};
const SIZE = { sm: "w-64", md: "w-80", lg: "w-96" };

/** 0..1 resistance -> up to 5 stars (a resistance < 1 means it takes less damage = tanky). */
function stars(mult: number): string {
  const rating = Math.max(0, Math.min(5, Math.round((2 - mult) * 2.5)));
  return "★".repeat(rating) + "☆".repeat(5 - rating);
}

export default function MonsterHunterStyle({ entity, size = "md", mapping }: EntityViewProps) {
  const map = { ...DEFAULT_MAPPING, ...mapping };
  const type = String(slot(entity, map, "type") ?? "");
  const resist = (slot(entity, map, "resistances") as Record<string, unknown>) ?? {};

  return (
    <div
      data-testid="monster-hunter-card"
      className={`flex ${SIZE[size]} flex-col gap-2 rounded-lg border border-neutral-700 bg-neutral-900 p-3 text-neutral-100 shadow-lg`}
    >
      <div className="flex items-center gap-3">
        <span className="text-4xl">{TYPE_GLYPH[type] ?? "👹"}</span>
        <div className="min-w-0">
          <h3 className="truncate text-sm font-bold">{show(slot(entity, map, "name"))}</h3>
          <span className="text-xs uppercase tracking-wide text-neutral-400">{type || "unknown"}</span>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-2 border-y border-neutral-700 py-2 text-center text-xs">
        {(["hp", "atk", "def"] as const).map((k) => (
          <div key={k}>
            <div className="uppercase text-neutral-500">{k}</div>
            <div className="font-mono text-sm">{stat(slot(entity, map, k))}</div>
          </div>
        ))}
      </div>

      <div className="flex flex-col gap-0.5 text-xs">
        <span className="text-neutral-500">resistances</span>
        {Object.keys(resist).length === 0 ? (
          <span className="text-neutral-600">—</span>
        ) : (
          Object.entries(resist).slice(0, 6).map(([k, v]) => (
            <div key={k} className="flex justify-between gap-2">
              <span className="text-neutral-300">{k}</span>
              <span className="text-amber-400">{stars(Number(v))}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
