import * as React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, within } from "@testing-library/react";
import { Timeline } from "./Timeline";
import type { EntityEvent } from "@/lib/api";

function ev(seq: number, actor: EntityEvent["actor"], kind: string, metadata: Record<string, unknown> = {}): EntityEvent {
  return { seq, parent_seq: seq - 1 || null, branch_id: "main", timestamp: "", actor, kind, target: "scenario", before: null, after: null, metadata };
}

const events: EntityEvent[] = [
  ev(1, "llm-designer", "create_entity"),
  ev(2, "user", "edit_entity", { note: "buffed hp" }),
  ev(3, "llm-judge", "evaluate_subjective", { rationale: "variety ok" }),
  ev(4, "llm-iterator", "note", { reasoning: "nerf top card" }),
];

describe("Timeline", () => {
  it("renders one marker per event, ordered by seq", () => {
    render(<Timeline events={[...events].reverse()} />);
    const markers = within(screen.getByTestId("timeline")).getAllByRole("button");
    expect(markers).toHaveLength(4);
    expect(markers.map((m) => m.getAttribute("data-testid"))).toEqual(["event-1", "event-2", "event-3", "event-4"]);
  });

  it("tags each marker with its actor (for color coding) and hover metadata", () => {
    render(<Timeline events={events} />);
    expect(screen.getByTestId("event-2").getAttribute("data-actor")).toBe("user");
    expect(screen.getByTestId("event-4").getAttribute("title")).toContain("nerf top card");
  });

  it("filters by actor", () => {
    render(<Timeline events={events} />);
    fireEvent.change(screen.getByLabelText("filter actor"), { target: { value: "user" } });
    const markers = within(screen.getByTestId("timeline")).getAllByRole("button");
    expect(markers).toHaveLength(1);
    expect(markers[0]).toHaveAttribute("data-testid", "event-2");
  });

  it("calls onSelect with the event seq on click", () => {
    const onSelect = vi.fn();
    render(<Timeline events={events} onSelect={onSelect} />);
    fireEvent.click(screen.getByTestId("event-3"));
    expect(onSelect).toHaveBeenCalledWith(3);
  });
});
