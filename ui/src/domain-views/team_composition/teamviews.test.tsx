import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import type { EntitySchema } from "@/lib/schema";
import BadgeStyle from "./BadgeStyle";
import RosterStyle from "./RosterStyle";

const SCHEMA: EntitySchema = { name: "Person", fields: [{ name: "name", kind: "str" }] };
const PERSON = { name: "Ana Souza", seniority: "senior", skills: ["python", "sql"], preferred_task_types: ["backend"] };

describe("team views", () => {
  test("BadgeStyle shows name, seniority chip and skills", () => {
    render(<BadgeStyle entity={PERSON} schema={SCHEMA} />);
    expect(screen.getByTestId("badge-card")).toBeInTheDocument();
    expect(screen.getByText("Ana Souza")).toBeInTheDocument();
    expect(screen.getByText("senior")).toBeInTheDocument();
    expect(screen.getByText("python")).toBeInTheDocument();
  });

  test("RosterStyle shows name and a skills summary", () => {
    render(<RosterStyle entity={PERSON} schema={SCHEMA} />);
    expect(screen.getByTestId("roster-card")).toBeInTheDocument();
    expect(screen.getByText("Ana Souza")).toBeInTheDocument();
    expect(screen.getByText(/2 skills/)).toBeInTheDocument();
  });

  test("both tolerate an empty entity", () => {
    render(<BadgeStyle entity={{}} schema={SCHEMA} />);
    render(<RosterStyle entity={{}} schema={SCHEMA} />);
    expect(screen.getByTestId("badge-card")).toBeInTheDocument();
    expect(screen.getByTestId("roster-card")).toBeInTheDocument();
  });
});
