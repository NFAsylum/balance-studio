import * as React from "react";
import { describe, it, expect } from "vitest";
import { render, screen, fireEvent, within } from "@testing-library/react";
import { EntityEditor } from "./EntityEditor";
import type { EntitySchema, EntityValue } from "@/lib/schema";

const cardSchema: EntitySchema = {
  name: "Unit",
  fields: [
    { name: "name", kind: "str", min_len: 2, max_len: 40, required: true },
    { name: "cost", kind: "num", range: [1, 5] },
    { name: "ability_kind", kind: "cat", enum: ["deal_damage", "heal"] },
    { name: "legendary", kind: "bool" },
  ],
};

const creatureSchema: EntitySchema = {
  name: "Creature",
  fields: [
    { name: "type", kind: "cat", enum: ["fire", "water"] },
    { name: "skills", kind: "tag_set" },
    { name: "resistances", kind: "map" },
  ],
};

function Harness({ schema, initial }: { schema: EntitySchema; initial: EntityValue }) {
  const [value, setValue] = React.useState(initial);
  return (
    <>
      <EntityEditor schema={schema} value={value} onChange={setValue} />
      <pre data-testid="value">{JSON.stringify(value)}</pre>
    </>
  );
}

describe("EntityEditor", () => {
  it("renders one control per schema field", () => {
    render(<Harness schema={cardSchema} initial={{ name: "Ace", cost: 3, ability_kind: "heal", legendary: false }} />);
    for (const f of cardSchema.fields) {
      expect(screen.getByTestId(`field-${f.name}`)).toBeInTheDocument();
    }
  });

  it("num field renders a slider and flags out-of-range values", () => {
    render(<Harness schema={cardSchema} initial={{ name: "Ace", cost: 9, ability_kind: "heal", legendary: false }} />);
    expect(screen.getAllByRole("slider").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByRole("alert").textContent).toContain("between 1 and 5");
  });

  it("cat field is a select that updates the value", () => {
    render(<Harness schema={cardSchema} initial={{ name: "Ace", cost: 3, ability_kind: "heal", legendary: false }} />);
    const select = screen.getByLabelText("ability_kind") as HTMLSelectElement;
    fireEvent.change(select, { target: { value: "deal_damage" } });
    expect(JSON.parse(screen.getByTestId("value").textContent!).ability_kind).toBe("deal_damage");
  });

  it("str field shows a character counter and min-length error", () => {
    render(<Harness schema={cardSchema} initial={{ name: "a", cost: 3, ability_kind: "heal", legendary: false }} />);
    const field = screen.getByTestId("field-name");
    expect(within(field).getByText("1/40")).toBeInTheDocument();
    expect(within(field).getByRole("alert").textContent).toContain("min 2 chars");
  });

  it("tag_set field adds and removes tags", () => {
    render(<Harness schema={creatureSchema} initial={{ type: "fire", skills: [], resistances: {} }} />);
    const input = screen.getByLabelText("add tag");
    fireEvent.change(input, { target: { value: "fire_strike" } });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(JSON.parse(screen.getByTestId("value").textContent!).skills).toEqual(["fire_strike"]);
    fireEvent.click(screen.getByLabelText("remove fire_strike"));
    expect(JSON.parse(screen.getByTestId("value").textContent!).skills).toEqual([]);
  });

  it("renders the creature schema too (same component), incl. the map field", () => {
    render(<Harness schema={creatureSchema} initial={{ type: "fire", skills: ["fire_strike"], resistances: { shadow: 2 } }} />);
    expect(screen.getByTestId("field-resistances")).toBeInTheDocument();
    const row = screen.getByTestId("map-row-shadow");
    const input = within(row).getByLabelText("shadow value") as HTMLInputElement;
    expect(input.value).toBe("2");
    fireEvent.change(input, { target: { value: "0.5" } });
    expect(JSON.parse(screen.getByTestId("value").textContent!).resistances.shadow).toBe(0.5);
  });
});
