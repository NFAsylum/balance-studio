import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import type { EntitySchema } from "@/lib/schema";
import DefaultListView from "./DefaultListView";

const CARD: EntitySchema = {
  name: "Unit",
  fields: [
    { name: "name", kind: "str" },
    { name: "cost", kind: "num", range: [0, 10] },
    { name: "hp", kind: "num", range: [1, 30] },
    { name: "ability_kind", kind: "cat", enum: ["burn", "heal"] },
  ],
};

const CREATURE: EntitySchema = {
  name: "Creature",
  fields: [
    { name: "name", kind: "str" },
    { name: "type", kind: "cat", enum: ["fire", "water"] },
    { name: "atk", kind: "num", range: [1, 150] },
    { name: "skills", kind: "tag_set" },
    { name: "resistances", kind: "map" },
  ],
};

const PERSON: EntitySchema = {
  name: "Person",
  fields: [
    { name: "name", kind: "str" },
    { name: "seniority", kind: "cat", enum: ["junior", "senior"] },
    { name: "skills", kind: "tag_set" },
    { name: "remote", kind: "bool" },
  ],
};

describe("DefaultListView", () => {
  test("renders a card entity with title + numbers + identifier", () => {
    render(<DefaultListView entity={{ name: "Ember", cost: 3, hp: 12, ability_kind: "burn" }} schema={CARD} />);
    expect(screen.getByText("Ember")).toBeInTheDocument();
    expect(screen.getByText("12")).toBeInTheDocument(); // hp value
    expect(screen.getByText("burn")).toBeInTheDocument(); // categorical identifier
  });

  test("renders a creature with tag chips and a map table", () => {
    render(
      <DefaultListView
        entity={{ name: "Drake", type: "fire", atk: 90, skills: ["ember", "bite"], resistances: { water: 0.5 } }}
        schema={CREATURE}
      />,
    );
    expect(screen.getByText("Drake")).toBeInTheDocument();
    expect(screen.getByText("ember")).toBeInTheDocument();
    expect(screen.getByText("water")).toBeInTheDocument(); // resistance key
    expect(screen.getByText("0.50")).toBeInTheDocument(); // resistance value
  });

  test("renders a person with a boolean and no numeric fields", () => {
    render(<DefaultListView entity={{ name: "Ana", seniority: "senior", skills: ["python"], remote: true }} schema={PERSON} />);
    expect(screen.getByText("Ana")).toBeInTheDocument();
    expect(screen.getByText("python")).toBeInTheDocument();
    expect(screen.getByText("remote")).toBeInTheDocument();
  });

  test("does not crash on missing / empty fields", () => {
    render(<DefaultListView entity={{}} schema={CREATURE} />);
    expect(screen.getByText("Untitled")).toBeInTheDocument();
    expect(screen.getAllByText("—").length).toBeGreaterThan(0); // empty tag_set / map show a dash
  });
});
