import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import type { EntitySchema } from "@/lib/schema";
import ModernManaStyle from "./ModernManaStyle";
import HighScaleDuelStyle from "./HighScaleDuelStyle";

const SCHEMA: EntitySchema = { name: "Unit", fields: [{ name: "name", kind: "str" }] };
const CARD = { name: "Ember Warrior", cost: 3, hp: 5, damage: 4, ability_kind: "deal_damage", ability_value: 2 };

describe("card views", () => {
  test("ModernManaStyle shows name, mana, attack, health", () => {
    render(<ModernManaStyle entity={CARD} schema={SCHEMA} />);
    expect(screen.getByTestId("modern-mana-card")).toBeInTheDocument();
    expect(screen.getByText("Ember Warrior")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument(); // mana
    expect(screen.getByText("4")).toBeInTheDocument(); // attack
    expect(screen.getByText("5")).toBeInTheDocument(); // health
  });

  test("HighScaleDuelStyle shows name, ATK/DEF and level stars", () => {
    render(<HighScaleDuelStyle entity={CARD} schema={SCHEMA} />);
    expect(screen.getByText("Ember Warrior")).toBeInTheDocument();
    expect(screen.getByText("ATK/4")).toBeInTheDocument();
    expect(screen.getByText("DEF/5")).toBeInTheDocument();
    expect(screen.getByLabelText("level 3").textContent).toBe("★★★");
  });

  test("both tolerate a missing/empty entity without crashing", () => {
    render(<ModernManaStyle entity={{}} schema={SCHEMA} />);
    render(<HighScaleDuelStyle entity={{}} schema={SCHEMA} />);
    expect(screen.getByTestId("modern-mana-card")).toBeInTheDocument();
    expect(screen.getByTestId("high-scale-duel-card")).toBeInTheDocument();
  });
});
