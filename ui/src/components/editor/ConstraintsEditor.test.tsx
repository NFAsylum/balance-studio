import * as React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test } from "vitest";
import type { Constraint } from "@/lib/api";
import { ConstraintsEditor } from "./ConstraintsEditor";

function Harness({ initial }: { initial: Constraint[] }) {
  const [c, setC] = React.useState(initial);
  return <ConstraintsEditor constraints={c} onChange={setC} violations={c.length ? ["range: cost=15 outside [0, 10]"] : []} />;
}

describe("ConstraintsEditor", () => {
  test("adds and removes constraints", async () => {
    render(<Harness initial={[]} />);
    expect(screen.queryAllByTestId(/constraint-\d/)).toHaveLength(0);
    await userEvent.click(screen.getByRole("button", { name: /add constraint/i }));
    expect(screen.getAllByTestId(/constraint-\d/)).toHaveLength(1);
    await userEvent.click(screen.getByRole("button", { name: /remove constraint 0/i }));
    expect(screen.queryAllByTestId(/constraint-\d/)).toHaveLength(0);
  });

  test("switching kind swaps the param inputs", async () => {
    render(<Harness initial={[{ kind: "range", params: { field: "", min: 0, max: 10 } }]} />);
    expect(screen.getByLabelText("min")).toBeInTheDocument();
    await userEvent.selectOptions(screen.getByLabelText("constraint 0 kind"), "required_tag");
    expect(screen.getByLabelText("any_of")).toBeInTheDocument();
  });

  test("shows violations", () => {
    render(<Harness initial={[{ kind: "range", params: { field: "cost", min: 0, max: 10 } }]} />);
    expect(screen.getByTestId("constraint-violations")).toHaveTextContent("range: cost=15");
  });
});
