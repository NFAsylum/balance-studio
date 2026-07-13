/** View registry — which entity views exist and which apply to a domain.
 *
 * Discovery note: the brief suggested Vite's `import.meta.glob`, but this app is Next.js
 * (webpack/turbopack), where that Vite-only API is unavailable at build time. We use an
 * explicit registry instead: adding a view is a single self-documenting line below. The
 * DefaultListView is always available as the guaranteed fallback for any schema. */

import type { ComponentType } from "react";
import DefaultListView, { meta as defaultMeta } from "./DefaultListView";
import HearthstoneStyle, { meta as hearthstoneMeta } from "./card_game/HearthstoneStyle";
import YuGiOhStyle, { meta as yugiohMeta } from "./card_game/YuGiOhStyle";
import type { EntityView, EntityViewProps, ViewMeta } from "./types";

function view(meta: ViewMeta, component: ComponentType<EntityViewProps>): EntityView {
  return { ...meta, component, defaultMapping: meta.defaultMapping ?? {} };
}

/** Shipped views. Add a new domain view: import it, then add one `view(meta, Component)` line. */
const REGISTRY: EntityView[] = [
  view(defaultMeta, DefaultListView),
  view(hearthstoneMeta, HearthstoneStyle),
  view(yugiohMeta, YuGiOhStyle),
  // creature_rpg / team_composition variants (T2.4–T2.5) register here.
];

export const DEFAULT_VIEW: EntityView = REGISTRY.find((v) => v.id === "default")!;

/** Views applicable to a domain (domain-specific + universal), DefaultListView always last. */
export function getViewsForDomain(domain: string): EntityView[] {
  const specific = REGISTRY.filter((v) => v.domain === domain);
  const universal = REGISTRY.filter((v) => v.domain === "*" && v.id !== "default");
  return [...specific, ...universal, DEFAULT_VIEW];
}

export function getViewById(id: string): EntityView | null {
  return REGISTRY.find((v) => v.id === id) ?? null;
}

/** Register a view at runtime (used by the custom-view loader in T2.6). Ignores duplicate ids. */
export function registerView(v: EntityView): void {
  if (!REGISTRY.some((existing) => existing.id === v.id)) REGISTRY.push(v);
}

export function allViews(): EntityView[] {
  return [...REGISTRY];
}
