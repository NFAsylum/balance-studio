"use client";
import * as React from "react";
import type { EntityViewProps, ViewMeta } from "../types";
import { show, slot, stat } from "../_shared";

/** Modern-mana-style minion card (vertical): mana gem top-left, attack + health at the
 * bottom corners, an ability emoji in the art box, coloured border by ability. */

const DEFAULT_MAPPING = {
  name: "name",
  mana: "cost",
  attack: "damage",
  health: "hp",
  ability: "ability_kind",
} as const;

export const meta: ViewMeta = {
  id: "card_game.modern-mana",
  name: "Modern Mana",
  domain: "card_game",
  defaultMapping: { ...DEFAULT_MAPPING },
};

// Colour + emoji per ability primitive (works for themed names too via the emoji fallback).
const ABILITY: Record<string, { ring: string; emoji: string }> = {
  deal_damage: { ring: "border-red-500", emoji: "🔥" },
  heal: { ring: "border-green-500", emoji: "💚" },
  shield: { ring: "border-blue-500", emoji: "🛡️" },
  draw: { ring: "border-purple-500", emoji: "🃏" },
};

const SIZE = { sm: "h-56 w-40", md: "h-80 w-56", lg: "h-96 w-64" };

export default function ModernManaStyle({ entity, size = "md", mapping }: EntityViewProps) {
  const map = { ...DEFAULT_MAPPING, ...mapping };
  const ability = String(slot(entity, map, "ability") ?? "");
  const look = ABILITY[ability] ?? { ring: "border-amber-500", emoji: "✨" };

  return (
    <div
      data-testid="modern-mana-card"
      className={`relative flex ${SIZE[size]} flex-col overflow-hidden rounded-2xl border-4 ${look.ring} bg-gradient-to-b from-amber-50 to-amber-200 text-neutral-900 shadow-lg dark:from-amber-100 dark:to-amber-300`}
    >
      {/* mana gem */}
      <span className="absolute left-2 top-2 flex h-8 w-8 items-center justify-center rounded-full bg-blue-600 text-sm font-bold text-white shadow">
        {show(slot(entity, map, "mana"))}
      </span>

      {/* name banner */}
      <div className="mx-8 mt-3 truncate rounded-md bg-amber-800/90 px-2 py-1 text-center font-serif text-sm font-semibold text-amber-50">
        {show(slot(entity, map, "name"))}
      </div>

      {/* art box */}
      <div className="mx-4 mt-2 flex flex-1 items-center justify-center rounded-md border border-amber-700/40 bg-amber-100/60 text-4xl">
        {look.emoji}
      </div>

      {/* ability label */}
      <div className="mb-8 mt-1 px-3 text-center text-[11px] italic text-amber-900">
        {ability ? ability.replace(/_/g, " ") : "—"}
      </div>

      {/* attack (sword, bottom-left) + health (heart, bottom-right) */}
      <span className="absolute bottom-2 left-2 flex h-8 w-8 items-center justify-center rounded-full bg-yellow-500 text-sm font-bold text-neutral-900 shadow">
        {stat(slot(entity, map, "attack"))}
      </span>
      <span className="absolute bottom-2 right-2 flex h-8 w-8 items-center justify-center rounded-full bg-red-600 text-sm font-bold text-white shadow">
        {stat(slot(entity, map, "health"))}
      </span>
    </div>
  );
}
