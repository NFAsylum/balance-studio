import * as React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ObjectivePicker } from "./ObjectivePicker";
import { ParetoScatter } from "./ParetoScatter";
import { scoreObjectives, paretoFront } from "@/lib/objectives";
import type { Objective } from "@/lib/api";

describe("objectives helpers", () => {
  it("scores weighted objectives (maximize/minimize)", () => {
    const objs: Objective[] = [
      { metric_name: "variety", direction: "maximize", weight: 1 },
      { metric_name: "std", direction: "minimize", weight: 2 },
    ];
    expect(scoreObjectives(objs, { variety: 0.8, std: 0.1 })).toBeCloseTo(0.8 - 0.2);
  });

  it("computes the Pareto front for two conflicting objectives", () => {
    const objs: Objective[] = [
      { metric_name: "a", direction: "maximize", weight: 1 },
      { metric_name: "b", direction: "maximize", weight: 1 },
    ];
    const front = paretoFront(objs, [
      { id: "c1", values: { a: 1, b: 0 } },
      { id: "c2", values: { a: 0, b: 1 } },
      { id: "c3", values: { a: 0, b: 0 } }, // dominated
    ]);
    expect(front.has("c1") && front.has("c2")).toBe(true);
    expect(front.has("c3")).toBe(false);
  });
});

describe("ObjectivePicker", () => {
  function Harness({ available, initial }: { available: string[]; initial: Objective[] }) {
    const [objs, setObjs] = React.useState(initial);
    return <ObjectivePicker available={available} value={objs} onChange={setObjs} metricValues={{ variety: 1, std: 0.2 }} />;
  }

  it("adds an objective and shows the aggregate score", () => {
    render(<Harness available={["variety", "std"]} initial={[]} />);
    expect(screen.getByTestId("aggregate-score").textContent).toContain("0.00");
    fireEvent.change(screen.getByLabelText("add objective"), { target: { value: "variety" } });
    expect(screen.getByTestId("objective-variety")).toBeInTheDocument();
    // maximize variety (value 1, weight 1) -> score 1.00
    expect(screen.getByTestId("aggregate-score").textContent).toContain("1.00");
  });

  it("removes an objective", () => {
    const onChange = vi.fn();
    render(
      <ObjectivePicker
        available={["variety"]}
        value={[{ metric_name: "variety", direction: "maximize", weight: 1 }]}
        onChange={onChange}
      />
    );
    fireEvent.click(screen.getByLabelText("remove variety"));
    expect(onChange).toHaveBeenCalledWith([]);
  });
});

describe("ParetoScatter", () => {
  it("highlights the front and marks dominated candidates", () => {
    const objs: Objective[] = [
      { metric_name: "a", direction: "maximize", weight: 1 },
      { metric_name: "b", direction: "maximize", weight: 1 },
    ];
    render(
      <ParetoScatter
        objectives={objs}
        candidates={[
          { id: "c1", values: { a: 1, b: 0 } },
          { id: "c2", values: { a: 0, b: 1 } },
          { id: "c3", values: { a: 0, b: 0 } },
        ]}
      />
    );
    expect(screen.getByTestId("candidate-c1")).toHaveAttribute("data-pareto", "true");
    expect(screen.getByTestId("candidate-c3")).toHaveAttribute("data-pareto", "false");
  });
});
