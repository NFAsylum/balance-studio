"use client";
import * as React from "react";
import { cn } from "@/lib/utils";
import type { EntityEvent } from "@/lib/api";

const ACTOR_STYLE: Record<string, { dot: string; label: string }> = {
  user: { dot: "bg-blue-500", label: "user" },
  "llm-designer": { dot: "bg-green-500", label: "designer" },
  "llm-judge": { dot: "bg-amber-500", label: "judge" },
  "llm-iterator": { dot: "bg-purple-500", label: "iterator" },
};

function metadataText(e: EntityEvent): string {
  const md = e.metadata ?? {};
  return (
    (md.reasoning as string) ||
    (md.rationale as string) ||
    (md.note as string) ||
    `${e.actor} · ${e.kind} · ${e.target}`
  );
}

/** Horizontal scrubber over the event log: color per actor, filter, click to restore. */
export function Timeline({
  events,
  selectedSeq,
  onSelect,
}: {
  events: EntityEvent[];
  selectedSeq?: number | null;
  onSelect?: (seq: number) => void;
}) {
  const [actor, setActor] = React.useState("all");
  const [kind, setKind] = React.useState("all");

  const actors = Array.from(new Set(events.map((e) => e.actor)));
  const kinds = Array.from(new Set(events.map((e) => e.kind)));
  const filtered = events
    .filter((e) => actor === "all" || e.actor === actor)
    .filter((e) => kind === "all" || e.kind === kind)
    .sort((a, b) => a.seq - b.seq);

  return (
    <div className="flex flex-col gap-3">
      <div className="flex gap-2 text-sm">
        <select aria-label="filter actor" className="h-8 rounded border border-neutral-300 px-2" value={actor} onChange={(e) => setActor(e.target.value)}>
          <option value="all">all actors</option>
          {actors.map((a) => (
            <option key={a} value={a}>
              {a}
            </option>
          ))}
        </select>
        <select aria-label="filter kind" className="h-8 rounded border border-neutral-300 px-2" value={kind} onChange={(e) => setKind(e.target.value)}>
          <option value="all">all kinds</option>
          {kinds.map((k) => (
            <option key={k} value={k}>
              {k}
            </option>
          ))}
        </select>
      </div>

      <ol className="flex gap-2 overflow-x-auto pb-2" data-testid="timeline">
        {filtered.map((e) => {
          const style = ACTOR_STYLE[e.actor] ?? { dot: "bg-neutral-400", label: e.actor };
          return (
            <li key={`${e.branch_id}-${e.seq}`} className="shrink-0">
              <button
                type="button"
                data-testid={`event-${e.seq}`}
                data-actor={e.actor}
                title={metadataText(e)}
                onClick={() => onSelect?.(e.seq)}
                className={cn(
                  "flex min-w-[84px] flex-col items-start gap-1 rounded border px-2 py-1 text-left text-xs",
                  selectedSeq === e.seq ? "border-neutral-900 ring-1 ring-neutral-900" : "border-neutral-200"
                )}
              >
                <span className="flex items-center gap-1">
                  <span className={cn("h-2 w-2 rounded-full", style.dot)} />
                  <span className="text-neutral-400">#{e.seq}</span>
                </span>
                <span className="font-medium">{e.kind}</span>
                <span className="text-neutral-500">{style.label}</span>
              </button>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
