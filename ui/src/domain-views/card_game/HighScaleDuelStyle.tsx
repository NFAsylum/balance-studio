"use client";
import * as React from "react";
import type { EntityViewProps, ViewMeta } from "../types";
import { show, slot, stat } from "../_shared";

/** High-scale-duel-style monster card (landscape): gold name banner, level stars top-right, a big
 * type emoji, and an ATK / DEF row at the base. Level maps to cost, ATK to damage, DEF to hp. */

const DEFAULT_MAPPING = {
  name: "name",
  level: "cost",
  atk: "damage",
  def: "hp",
  kind: "ability_kind",
} as const;

export const meta: ViewMeta = {
  id: "card_game.high-scale-duel",
  name: "High-scale Duel",
  domain: "card_game",
  defaultMapping: { ...DEFAULT_MAPPING },
};

const KIND_EMOJI: Record<string, string> = {
  deal_damage: "🐉",
  heal: "🧚",
  shield: "🛡️",
  draw: "📜",
};

const SIZE = { sm: "h-40 w-56", md: "h-56 w-80", lg: "h-64 w-96" };

export default function HighScaleDuelStyle({ entity, size = "md", mapping }: EntityViewProps) {
  const map = { ...DEFAULT_MAPPING, ...mapping };
  const level = Math.max(0, Math.min(12, Math.round(stat(slot(entity, map, "level")))));
  const kind = String(slot(entity, map, "kind") ?? "");

  return (
    <div
      data-testid="high-scale-duel-card"
      className={`flex ${SIZE[size]} flex-col overflow-hidden rounded-lg border-4 border-yellow-600 bg-gradient-to-b from-amber-200 to-yellow-100 p-2 text-neutral-900 shadow-lg`}
    >
      {/* name + level stars */}
      <div className="flex items-center justify-between gap-2 rounded bg-yellow-700/90 px-2 py-1">
        <span className="truncate font-serif text-sm font-bold text-amber-50">{show(slot(entity, map, "name"))}</span>
        <span className="shrink-0 text-xs tracking-tighter text-amber-200" aria-label={`level ${level}`}>
          {level > 0 ? "★".repeat(level) : "—"}
        </span>
      </div>

      {/* art */}
      <div className="my-1 flex flex-1 items-center justify-center rounded border border-yellow-700/50 bg-amber-50 text-5xl">
        {KIND_EMOJI[kind] ?? "✨"}
      </div>

      {/* ATK / DEF */}
      <div className="flex justify-end gap-4 rounded bg-yellow-700/10 px-2 py-1 font-mono text-sm font-bold">
        <span>ATK/{stat(slot(entity, map, "atk"))}</span>
        <span>DEF/{stat(slot(entity, map, "def"))}</span>
      </div>
    </div>
  );
}
