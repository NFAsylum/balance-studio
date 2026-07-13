import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import type { EntitySchema } from "@/lib/schema";
import GiantBeastStyle from "./GiantBeastStyle";
import ElementalClassicStyle from "./ElementalClassicStyle";

const SCHEMA: EntitySchema = { name: "Creature", fields: [{ name: "name", kind: "str" }] };
const CREATURE = {
  name: "Aqua Drake",
  type: "water",
  hp: 180,
  atk: 90,
  defense: 60,
  skills: ["bite", "torrent"],
  resistances: { fire: 0.5 },
};

describe("creature views", () => {
  test("ElementalClassicStyle shows name, type, stats and skills", () => {
    render(<ElementalClassicStyle entity={CREATURE} schema={SCHEMA} />);
    expect(screen.getByTestId("elemental-dex-card")).toBeInTheDocument();
    expect(screen.getByText("Aqua Drake")).toBeInTheDocument();
    expect(screen.getByText("water")).toBeInTheDocument();
    expect(screen.getByText("180")).toBeInTheDocument(); // hp
    expect(screen.getByText("bite")).toBeInTheDocument();
  });

  test("GiantBeastStyle shows stats and resistance stars", () => {
    render(<GiantBeastStyle entity={CREATURE} schema={SCHEMA} />);
    expect(screen.getByTestId("giant-beast-card")).toBeInTheDocument();
    expect(screen.getByText("Aqua Drake")).toBeInTheDocument();
    expect(screen.getByText("90")).toBeInTheDocument(); // atk
    expect(screen.getByText("fire")).toBeInTheDocument(); // resistance key
  });

  test("both tolerate an empty entity", () => {
    render(<ElementalClassicStyle entity={{}} schema={SCHEMA} />);
    render(<GiantBeastStyle entity={{}} schema={SCHEMA} />);
    expect(screen.getByTestId("elemental-dex-card")).toBeInTheDocument();
    expect(screen.getByTestId("giant-beast-card")).toBeInTheDocument();
  });
});
