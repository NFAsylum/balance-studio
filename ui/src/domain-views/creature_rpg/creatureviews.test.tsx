import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import type { EntitySchema } from "@/lib/schema";
import MonsterHunterStyle from "./MonsterHunterStyle";
import PokedexStyle from "./PokedexStyle";

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
  test("PokedexStyle shows name, type, stats and skills", () => {
    render(<PokedexStyle entity={CREATURE} schema={SCHEMA} />);
    expect(screen.getByTestId("pokedex-card")).toBeInTheDocument();
    expect(screen.getByText("Aqua Drake")).toBeInTheDocument();
    expect(screen.getByText("water")).toBeInTheDocument();
    expect(screen.getByText("180")).toBeInTheDocument(); // hp
    expect(screen.getByText("bite")).toBeInTheDocument();
  });

  test("MonsterHunterStyle shows stats and resistance stars", () => {
    render(<MonsterHunterStyle entity={CREATURE} schema={SCHEMA} />);
    expect(screen.getByTestId("monster-hunter-card")).toBeInTheDocument();
    expect(screen.getByText("Aqua Drake")).toBeInTheDocument();
    expect(screen.getByText("90")).toBeInTheDocument(); // atk
    expect(screen.getByText("fire")).toBeInTheDocument(); // resistance key
  });

  test("both tolerate an empty entity", () => {
    render(<PokedexStyle entity={{}} schema={SCHEMA} />);
    render(<MonsterHunterStyle entity={{}} schema={SCHEMA} />);
    expect(screen.getByTestId("pokedex-card")).toBeInTheDocument();
    expect(screen.getByTestId("monster-hunter-card")).toBeInTheDocument();
  });
});
