/** Build a plausible sample entity from a schema — used for the editor's live preview. */

import type { EntitySchema } from "./schema";

export function sampleEntity(schema: EntitySchema): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const f of schema.fields) {
    switch (f.kind) {
      case "num": {
        const [lo, hi] = f.range ?? [0, 10];
        out[f.name] = Math.round((lo + hi) / 2);
        break;
      }
      case "cat":
        out[f.name] = f.enum?.[0] ?? "";
        break;
      case "bool":
        out[f.name] = true;
        break;
      case "str":
        out[f.name] = f.name === "name" ? "Sample Entity" : "…";
        break;
      case "tag_set":
        out[f.name] = ["alpha", "beta"];
        break;
      case "map":
        out[f.name] = {};
        break;
    }
  }
  if (!("name" in out)) out.name = "Sample Entity";
  return out;
}
