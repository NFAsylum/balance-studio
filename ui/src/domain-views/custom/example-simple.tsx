"use client";
import * as React from "react";
import type { EntityViewProps, ViewMeta } from "../types";
import { show } from "../_shared";

/** Minimal custom view example — copy this file to start your own.
 *
 * A view is: a `meta` export (id, name, domain) + a default component taking EntityViewProps.
 * Register it by adding a line to ../custom/index.ts. */

export const meta: ViewMeta = {
  id: "custom.simple",
  name: "Simple (example)",
  domain: "*", // "*" = works for any domain; use a domain id to scope it
};

export default function SimpleExample({ entity, schema }: EntityViewProps) {
  const nameField = schema.fields.find((f) => f.name === "name" || f.kind === "str")?.name;
  return (
    <div className="rounded-lg border border-dashed border-border bg-card p-4 text-card-foreground">
      <h3 className="text-sm font-semibold">{show(nameField ? entity[nameField] : "Untitled")}</h3>
      <p className="text-xs text-muted-foreground">{schema.fields.length} fields · custom view</p>
    </div>
  );
}
