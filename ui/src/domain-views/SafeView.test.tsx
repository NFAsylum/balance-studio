import { render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";
import type { EntitySchema } from "@/lib/schema";
import { SafeView } from "./SafeView";
import { getViewById, getViewsForDomain, isCustomView } from "./registry";
import type { EntityView } from "./types";

const SCHEMA: EntitySchema = { name: "T", fields: [{ name: "name", kind: "str" }] };

const Boom: EntityView = {
  id: "custom.boom",
  name: "Boom",
  domain: "*",
  defaultMapping: {},
  component: () => {
    throw new Error("kaboom");
  },
};

describe("SafeView + custom discovery", () => {
  test("a crashing view falls back to the default view + warning", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    render(<SafeView view={Boom} entity={{ name: "X" }} schema={SCHEMA} />);
    expect(screen.getByTestId("view-fallback")).toBeInTheDocument();
    expect(screen.getByTestId("default-view")).toBeInTheDocument(); // fallback rendered
    expect(screen.getByText("X")).toBeInTheDocument();
    spy.mockRestore();
  });

  test("a healthy view renders normally through SafeView", () => {
    const ok = getViewById("card_game.hearthstone")!;
    render(<SafeView view={ok} entity={{ name: "Ok", cost: 1, hp: 1, damage: 1 }} schema={SCHEMA} />);
    expect(screen.getByTestId("hearthstone-card")).toBeInTheDocument();
  });

  test("custom example views are discovered and flagged as custom", () => {
    const simple = getViewById("custom.simple");
    expect(simple).not.toBeNull();
    expect(isCustomView(simple!)).toBe(true);
    // custom views (domain "*") appear for any domain
    expect(getViewsForDomain("card_game").map((v) => v.id)).toContain("custom.simple");
  });
});
