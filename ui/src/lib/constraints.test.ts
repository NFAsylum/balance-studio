import { describe, expect, test } from "vitest";
import type { Constraint } from "./api";
import { checkConstraints } from "./constraints";

describe("checkConstraints (mirror of the 5 engine kinds)", () => {
  test("range flags out-of-bounds and passes in-bounds", () => {
    const c: Constraint[] = [{ kind: "range", params: { field: "cost", min: 0, max: 10 } }];
    expect(checkConstraints({ cost: 15 }, c)).toHaveLength(1);
    expect(checkConstraints({ cost: 5 }, c)).toHaveLength(0);
  });

  test("required_tag flags when none present", () => {
    const c: Constraint[] = [{ kind: "required_tag", params: { field: "skills", any_of: ["b", "c"] } }];
    expect(checkConstraints({ skills: ["a"] }, c)).toHaveLength(1);
    expect(checkConstraints({ skills: ["b"] }, c)).toHaveLength(0);
  });

  test("forbidden_combo flags when all tags present", () => {
    const c: Constraint[] = [{ kind: "forbidden_combo", params: { field: "tags", tags: ["x", "y"] } }];
    expect(checkConstraints({ tags: ["x", "y", "z"] }, c)).toHaveLength(1);
    expect(checkConstraints({ tags: ["x"] }, c)).toHaveLength(0);
  });

  test("sum_of_fields flags over max", () => {
    const c: Constraint[] = [{ kind: "sum_of_fields", params: { fields: ["a", "b"], max: 10 } }];
    expect(checkConstraints({ a: 7, b: 8 }, c)).toHaveLength(1);
  });

  test("unique_across_set is skipped for a single entity", () => {
    expect(checkConstraints({ name: "X" }, [{ kind: "unique_across_set", params: { field: "name" } }])).toHaveLength(0);
  });
});
