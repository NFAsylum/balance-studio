# Custom entity views

Drop your own entity layouts here — they show up in the scenario editor's **Custom variants**
group and can render any domain's entities.

## Add one in 3 steps

1. Copy `example-simple.tsx` (or `example-with-mapping.tsx`) to `my-view.tsx` and edit it.
2. Register it in `index.ts` — import it and add one `custom(meta, Component)` entry.
3. It appears in the editor automatically.

> **Why the explicit `index.ts`?** This app is Next.js, where Vite's `import.meta.glob`
> folder auto-discovery isn't available at build time. The one-line registration in `index.ts`
> is the bundler-portable equivalent.

## The contract

```ts
export const meta: ViewMeta = {
  id: "custom.my-view",   // must start with "custom."
  name: "My View",        // label in the dropdown
  domain: "*",            // "*" for any domain, or "card_game" | "creature_rpg" | "team_composition"
  defaultMapping: {},     // optional: slot name -> schema field name
};

export default function MyView({ entity, schema, size, mapping }: EntityViewProps) { ... }
```

- **Handle missing fields** — an entity may not have every field. Use the `_shared` helpers
  (`show`, `slot`, `stat`) which return an em-dash / 0 instead of crashing.
- **Never assume a field exists.** If your view throws, the framework catches it (see
  `SafeView`) and falls back to the DefaultListView with a warning — but a clean view is nicer.
- **Tailwind + semantic tokens** (`bg-card`, `text-muted-foreground`, …) keep light/dark working.

## Security note

Custom views are arbitrary React code. Only add views you trust — on a self-hosted install
that's your own code. A future hosted/SaaS mode would sandbox these; today they run in-app.
See `docs/writing-a-view.md` for the full guide.
