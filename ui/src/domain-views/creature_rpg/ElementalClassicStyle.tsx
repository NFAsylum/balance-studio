"use client";
import * as React from "react";
import type { EntityViewProps, ViewMeta } from "../types";
import { show, slot, stat } from "../_shared";

/** Elemental-dex-style entry (horizontal split): a big type emoji + type badge on the left, name,
 * stat bars, skill chips and resistances on the right. */

const DEFAULT_MAPPING = {
  name: "name",
  type: "type",
  hp: "hp",
  atk: "atk",
  def: "defense",
  skills: "skills",
  resistances: "resistances",
} as const;

export const meta: ViewMeta = {
  id: "creature_rpg.elemental-classic",
  name: "Elemental Dex",
  domain: "creature_rpg",
  defaultMapping: { ...DEFAULT_MAPPING },
};

const TYPE_EMOJI: Record<string, string> = {
  fire: "🔥", water: "💧", plant: "🌿", ice: "❄️", electric: "⚡",
  rock: "🪨", wind: "🌪️", shadow: "🌑", grass: "🌿", dragon: "🐉",
};
const TYPE_COLOR: Record<string, string> = {
  fire: "bg-red-500", water: "bg-blue-500", plant: "bg-green-500", ice: "bg-cyan-400",
  electric: "bg-yellow-400", rock: "bg-stone-500", wind: "bg-teal-400", shadow: "bg-purple-700",
};
const STAT_MAX: Record<string, number> = { hp: 300, atk: 150, def: 150 };
const SIZE = { sm: "h-32 w-72", md: "h-44 w-96", lg: "h-52 w-[28rem]" };

function Bar({ label, value, max }: { label: string; value: number; max: number }) {
  const pct = Math.max(4, Math.min(100, (value / max) * 100));
  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="w-8 shrink-0 uppercase text-muted-foreground">{label}</span>
      <div className="h-2 flex-1 overflow-hidden rounded-full bg-muted">
        <div className="h-full rounded-full bg-foreground/70" style={{ width: `${pct}%` }} />
      </div>
      <span className="w-8 shrink-0 text-right tabular-nums">{value}</span>
    </div>
  );
}

export default function ElementalClassicStyle({ entity, size = "md", mapping }: EntityViewProps) {
  const map = { ...DEFAULT_MAPPING, ...mapping };
  const type = String(slot(entity, map, "type") ?? "");
  const skills = (slot(entity, map, "skills") as unknown[]) ?? [];
  const resist = (slot(entity, map, "resistances") as Record<string, unknown>) ?? {};

  return (
    <div
      data-testid="elemental-dex-card"
      className={`flex ${SIZE[size]} overflow-hidden rounded-xl border border-border bg-card text-card-foreground shadow`}
    >
      {/* left: type */}
      <div className={`flex w-2/5 flex-col items-center justify-center gap-2 ${TYPE_COLOR[type] ?? "bg-muted"}`}>
        <span className="text-5xl">{TYPE_EMOJI[type] ?? "❓"}</span>
        <span className="rounded-full bg-black/30 px-2 py-0.5 text-xs font-semibold uppercase text-white">
          {type || "—"}
        </span>
      </div>

      {/* right: name + stats + skills */}
      <div className="flex flex-1 flex-col gap-1 p-3">
        <h3 className="truncate text-sm font-bold">{show(slot(entity, map, "name"))}</h3>
        <div className="flex flex-col gap-1">
          <Bar label="HP" value={stat(slot(entity, map, "hp"))} max={STAT_MAX.hp} />
          <Bar label="ATK" value={stat(slot(entity, map, "atk"))} max={STAT_MAX.atk} />
          <Bar label="DEF" value={stat(slot(entity, map, "def"))} max={STAT_MAX.def} />
        </div>
        <div className="mt-1 flex flex-wrap gap-1">
          {(Array.isArray(skills) ? skills : []).slice(0, 4).map((s, i) => (
            <span key={`${s}-${i}`} className="rounded bg-muted px-1.5 py-0.5 text-[10px]">{String(s)}</span>
          ))}
          {Object.keys(resist).length > 0 && (
            <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">
              🛡 {Object.keys(resist).length}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
