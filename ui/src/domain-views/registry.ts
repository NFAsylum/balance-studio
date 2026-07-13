/** View registry — which entity views exist and which apply to a domain.
 *
 * Discovery note: the brief suggested Vite's `import.meta.glob`, but this app is Next.js
 * (webpack/turbopack), where that Vite-only API is unavailable at build time. We use an
 * explicit registry instead: adding a view is a single self-documenting line below. The
 * DefaultListView is always available as the guaranteed fallback for any schema. */

import type { ComponentType } from "react";
import DefaultListView, { meta as defaultMeta } from "./DefaultListView";
import ModernManaStyle, { meta as modernManaMeta } from "./card_game/ModernManaStyle";
import HighScaleDuelStyle, { meta as highScaleDuelMeta } from "./card_game/HighScaleDuelStyle";
import GiantBeastStyle, { meta as giantBeastMeta } from "./creature_rpg/GiantBeastStyle";
import ElementalClassicStyle, { meta as elementalClassicMeta } from "./creature_rpg/ElementalClassicStyle";
import BadgeStyle, { meta as badgeMeta } from "./team_composition/BadgeStyle";
import RosterStyle, { meta as rosterMeta } from "./team_composition/RosterStyle";
import { customViews } from "./custom";
import type { EntityView, EntityViewProps, ViewMeta } from "./types";

function view(meta: ViewMeta, component: ComponentType<EntityViewProps>): EntityView {
  return { ...meta, component, defaultMapping: meta.defaultMapping ?? {} };
}

/** Shipped views. Add a new domain view: import it, then add one `view(meta, Component)` line.
 * User-supplied views are listed in ./custom and appended here. */
const REGISTRY: EntityView[] = [
  view(defaultMeta, DefaultListView),
  view(modernManaMeta, ModernManaStyle),
  view(highScaleDuelMeta, HighScaleDuelStyle),
  view(elementalClassicMeta, ElementalClassicStyle),
  view(giantBeastMeta, GiantBeastStyle),
  view(badgeMeta, BadgeStyle),
  view(rosterMeta, RosterStyle),
  ...customViews,
];

/** A user-supplied view (grouped separately in the editor's "Custom variants" section). */
export function isCustomView(v: EntityView): boolean {
  return v.id.startsWith("custom.");
}

/** A demo/template view shipped for the writing-a-view tutorial — registered (so old scenarios
 * that reference it still render) but hidden from the end-user layout picker. */
export function isExampleView(v: EntityView): boolean {
  return v.example === true;
}

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
