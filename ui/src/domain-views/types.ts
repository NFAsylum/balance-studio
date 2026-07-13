/** Domain visual system (Level 2.5) — shared types.
 *
 * An entity "view" renders one entity for a domain. Every view takes the same props, so the
 * scenario board / editor can swap layouts freely; the DefaultListView is the always-works
 * fallback for any schema. */

import type { ComponentType } from "react";
import type { EntitySchema } from "@/lib/schema";

export type ViewSize = "sm" | "md" | "lg";

export interface EntityViewProps {
  entity: Record<string, unknown>;
  schema: EntitySchema;
  size?: ViewSize;
  /** slot name -> schema field name; a view uses it to read the field for each visual slot. */
  mapping?: Record<string, string>;
}

/** What a view module exports as `meta` (its default component is the render function). */
export interface ViewMeta {
  id: string; // e.g. "card_game.hearthstone", "custom.MyCard"
  name: string; // human label for the dropdown
  domain: string | "*"; // applicable domain, or "*" for any
  defaultMapping?: Record<string, string>;
}

/** A registered view: metadata + its component. */
export interface EntityView extends ViewMeta {
  component: ComponentType<EntityViewProps>;
  defaultMapping: Record<string, string>;
}
