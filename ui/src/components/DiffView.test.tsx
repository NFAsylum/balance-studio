import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, within } from "@testing-library/react";
import { DiffView } from "./DiffView";
import type { DiffReport } from "@/lib/api";

const diff: DiffReport = {
  branch_a: "main",
  branch_b: "alt",
  exclusive_events_a: 1,
  exclusive_events_b: 2,
  entities: { only_in_a: ["removed_one"], only_in_b: ["added_one"], changed: ["tweaked"] },
  metrics_diff: { A: { a: 0.6, b: 0.4 } },
};

describe("DiffView", () => {
  it("shows entities added/removed/changed and metric deltas", () => {
    render(<DiffView diff={diff} />);
    expect(within(screen.getByTestId("diff-added")).getByText("added_one")).toBeInTheDocument();
    expect(within(screen.getByTestId("diff-removed")).getByText("removed_one")).toBeInTheDocument();
    expect(within(screen.getByTestId("diff-changed")).getByText("tweaked")).toBeInTheDocument();
    const row = screen.getByTestId("metric-diff-A");
    expect(row.textContent).toContain("0.6");
    expect(row.textContent).toContain("0.4");
  });

  it("Fork from A triggers the callback", () => {
    const onForkA = vi.fn();
    render(<DiffView diff={diff} onForkA={onForkA} />);
    fireEvent.click(screen.getByRole("button", { name: /fork from main/i }));
    expect(onForkA).toHaveBeenCalledTimes(1);
  });
});
