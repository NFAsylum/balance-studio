import { describe, expect, test } from "vitest";
import type { FieldSpec } from "./schema";
import { applyOverrides, diffFields } from "./schema-overrides";

const BASE: FieldSpec[] = [
  { name: "name", kind: "str" },
  { name: "hp", kind: "num", range: [1, 20] },
  { name: "type", kind: "cat", enum: ["fire", "water"] },
];

describe("applyOverrides", () => {
  test("edits, adds, and removes by name (order preserved, new appended)", () => {
    const out = applyOverrides(BASE, {
      fields: [
        { name: "hp", range: [1, 8000] },
        { name: "effect", kind: "str" },
        { name: "type", remove: true },
      ],
    });
    expect(out.map((f) => f.name)).toEqual(["name", "hp", "effect"]);
    expect(out.find((f) => f.name === "hp")!.range).toEqual([1, 8000]);
    expect(out.find((f) => f.name === "hp")!.origin).toBe("user");
  });

  test("empty override is identity", () => {
    expect(applyOverrides(BASE, {})).toEqual(BASE);
    expect(applyOverrides(BASE, undefined)).toEqual(BASE);
  });
});

describe("diffFields", () => {
  test("round-trips: applyOverrides(base, diff(base, target)) === target", () => {
    const target = applyOverrides(BASE, {
      fields: [{ name: "hp", range: [1, 100] }, { name: "cost", kind: "num", range: [0, 10] }, { name: "type", remove: true }],
    });
    const delta = diffFields(BASE, target);
    const rebuilt = applyOverrides(BASE, delta);
    expect(rebuilt.map((f) => ({ name: f.name, kind: f.kind, range: f.range ?? null }))).toEqual(
      target.map((f) => ({ name: f.name, kind: f.kind, range: f.range ?? null })),
    );
  });

  test("no changes -> empty delta", () => {
    expect(diffFields(BASE, BASE.map((f) => ({ ...f })))).toEqual({});
  });

  test("a removed field yields a remove op", () => {
    const delta = diffFields(BASE, BASE.filter((f) => f.name !== "hp"));
    expect(delta.fields).toContainEqual({ name: "hp", remove: true });
  });
});
