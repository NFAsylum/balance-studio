/** Custom views registry.
 *
 * This app is Next.js, where Vite's `import.meta.glob` auto-discovery isn't available, so
 * custom views are listed explicitly here — the one-line, bundler-portable equivalent of
 * "drop a file in the folder". To add your own:
 *   1. copy `example-simple.tsx` to `my-view.tsx` and edit it,
 *   2. import it below and add one `custom(meta, Component)` entry.
 * It then appears in the scenario editor's "Custom variants" group automatically. */

import type { ComponentType } from "react";
import type { EntityView, EntityViewProps, ViewMeta } from "../types";
import SimpleExample, { meta as simpleMeta } from "./example-simple";
import StatTileExample, { meta as statTileMeta } from "./example-with-mapping";

function custom(meta: ViewMeta, component: ComponentType<EntityViewProps>): EntityView {
  return { ...meta, component, defaultMapping: meta.defaultMapping ?? {} };
}

export const customViews: EntityView[] = [
  custom(simpleMeta, SimpleExample),
  custom(statTileMeta, StatTileExample),
];
