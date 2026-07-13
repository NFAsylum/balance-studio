"use client";
import * as React from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";

/** First-run onboarding — a non-empty landing with two clear CTAs, so the app never opens on a
 * blank screen. "Try a sample card game" spins up a real, pre-styled scenario in seconds. */

export function Hero({ hasCardGame }: { hasCardGame: boolean }) {
  const router = useRouter();
  const qc = useQueryClient();

  const tryExample = useMutation({
    mutationFn: async () => {
      const scenario = await api.createScenario({
        domain: "card_game",
        name: "Card game example",
        brief: "a varied starter deck with distinct roles",
        n_entities: 10,
        preset_id: "modern-mana-tcg",
        visual_variant: "card_game.modern-mana",
      });
      await api.iterate(scenario.id, "design"); // instant with the deterministic dev designer
      return scenario;
    },
    onSuccess: (scenario) => {
      qc.invalidateQueries({ queryKey: ["scenarios"] });
      router.push(`/scenarios/${scenario.id}`);
    },
  });

  return (
    <section
      data-testid="hero"
      className="flex flex-col items-center gap-4 rounded-xl border border-border bg-card p-10 text-center"
    >
      <span className="text-4xl">⚖️</span>
      <h2 className="text-2xl font-bold sm:text-3xl">Balance any game, collaboratively</h2>
      <p className="max-w-xl text-sm text-muted-foreground">
        Design entities with an LLM, simulate them deterministically, and tune for balance — card
        games, RPG bestiaries, or team rosters. Same engine, swap the plugin.
      </p>
      <div className="flex flex-wrap justify-center gap-3">
        {hasCardGame && (
          <Button disabled={tryExample.isPending} onClick={() => tryExample.mutate()}>
            {tryExample.isPending ? "building example…" : "Try a sample card game"}
          </Button>
        )}
        <Button asChild variant="outline">
          <Link href="/scenarios/new">Start from scratch</Link>
        </Button>
      </div>
      {tryExample.isError && <p className="text-xs text-destructive">{String(tryExample.error)}</p>}
    </section>
  );
}
