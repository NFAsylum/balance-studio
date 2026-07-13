# Writing a domain view (Level 2.5)

Balance Studio renders each entity through a **view** — a small React component. Cards,
creatures and people should look like cards, creatures and people, not raw JSON. This guide
gets you from zero to a working custom layout in about 10 minutes.

## Why Level 2.5

- **Level 1** — the `DefaultListView` renders *any* schema (grouped fields). Always works, zero
  effort, but generic.
- **Level 2** — the shipped variants (`HearthstoneStyle`, `PokedexStyle`, `BadgeStyle`, …) are
  hand-designed per domain.
- **Level 2.5 — you are here.** Drop your own `.tsx` in `ui/src/domain-views/custom/` and it
  shows up in the editor's *Custom variants* group. No core changes, no visual designer to build.

## The contract

Every view is one file that exports `meta` and a default component:

```tsx
import type { EntityViewProps, ViewMeta } from "../types";

export const meta: ViewMeta = {
  id: "custom.my-card",   // must start with "custom." for user views
  name: "My Card",        // label shown in the dropdown
  domain: "*",            // "*" = any domain, or "card_game" | "creature_rpg" | "team_composition"
  defaultMapping: {},     // optional: slot name -> schema field name (see "Slot mapping")
};

export default function MyCard({ entity, schema, size, mapping }: EntityViewProps) {
  return <div>…</div>;
}
```

`EntityViewProps`:

| prop | type | what |
|---|---|---|
| `entity` | `Record<string, unknown>` | the entity's field values |
| `schema` | `EntitySchema` | the effective schema (fields, kinds, ranges) |
| `size` | `"sm" \| "md" \| "lg"` | render size hint (optional) |
| `mapping` | `Record<string,string>` | per-scenario slot→field overrides (optional) |

## Quickstart (≈10 min)

1. Copy `ui/src/domain-views/custom/example-simple.tsx` to `custom/my-card.tsx`.
2. Edit `meta` (give it a unique `custom.` id) and the JSX.
3. Register it: in `custom/index.ts`, import it and add one `custom(meta, Component)` entry.
4. `pnpm test` (or open the app) — it appears in the *Custom variants* dropdown.

## Slot mapping

Hard-coding field names couples a view to one schema. Instead, name abstract **slots** and let
`defaultMapping` say which field fills each — the user can remap per scenario.

```tsx
const DEFAULT_MAPPING = { title: "name", primary: "hp", secondary: "atk" } as const;
export const meta = { id: "custom.tile", name: "Tile", domain: "*", defaultMapping: { ...DEFAULT_MAPPING } };

export default function Tile({ entity, mapping }: EntityViewProps) {
  const map = { ...DEFAULT_MAPPING, ...mapping };
  return <big>{String(slot(entity, map, "primary") ?? "—")}</big>;
}
```

## Best practices

- **Handle missing fields.** An entity may omit any field. Use the `_shared` helpers — `show(v)`
  (value or em-dash), `slot(entity, map, name)`, `stat(v)` (number or 0) — so nothing NaNs or
  throws. If your view *does* throw, `SafeView` catches it and falls back to `DefaultListView`
  with a warning — but a clean view is nicer.
- **Responsive + theme-aware.** Use Tailwind with semantic tokens (`bg-card`,
  `text-muted-foreground`, `border-border`) so light/dark both work. Avoid fixed pixel widths
  that overflow small screens.
- **Keep it pure.** A view is presentational — no data fetching, no mutations.

## Security / sandboxing

Custom views are arbitrary React code running in the app. On a **self-hosted** install that is
your own trusted code — fine. A future **hosted/SaaS** mode would need to sandbox third-party
views (iframe or a restricted runtime); until then, only add views you trust.

See also `ui/src/domain-views/custom/README.md` (short version) and `docs/architecture.md`.
