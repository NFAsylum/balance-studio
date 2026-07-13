import * as React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test } from "vitest";
import type { FieldSpec } from "@/lib/schema";
import { FieldBuilder, fieldError, fieldsValid } from "./FieldBuilder";

const FIELDS: FieldSpec[] = [
  { name: "name", kind: "str" },
  { name: "hp", kind: "num", range: [1, 20] },
];

function Harness({ initial }: { initial: FieldSpec[] }) {
  const [fields, setFields] = React.useState(initial);
  return <FieldBuilder fields={fields} onChange={setFields} />;
}

describe("fieldsValid / fieldError", () => {
  test("duplicate name and empty cat enum are invalid", () => {
    expect(fieldsValid(FIELDS)).toBe(true);
    expect(fieldError([{ name: "a", kind: "cat", enum: [] }], 0)).toBe("cat needs options");
    expect(fieldError([{ name: "x", kind: "num", range: [5, 1] }], 0)).toBe("min > max");
    const dup: FieldSpec[] = [{ name: "z", kind: "str" }, { name: "z", kind: "num" }];
    expect(fieldError(dup, 1)).toBe("duplicate name");
  });
});

describe("FieldBuilder interactions", () => {
  test("add appends a field", async () => {
    render(<Harness initial={FIELDS} />);
    expect(screen.getAllByTestId(/field-row-/)).toHaveLength(2);
    await userEvent.click(screen.getByRole("button", { name: /add field/i }));
    expect(screen.getAllByTestId(/field-row-/)).toHaveLength(3);
  });

  test("remove drops a field", async () => {
    render(<Harness initial={FIELDS} />);
    await userEvent.click(screen.getByRole("button", { name: /remove hp/i }));
    expect(screen.getAllByTestId(/field-row-/)).toHaveLength(1);
  });

  test("move down reorders", async () => {
    render(<Harness initial={FIELDS} />);
    const firstName = () => (screen.getByLabelText("field 0 name") as HTMLInputElement).value;
    expect(firstName()).toBe("name");
    await userEvent.click(screen.getAllByRole("button", { name: "move down" })[0]);
    expect(firstName()).toBe("hp");
  });

  test("changing kind to num shows a range editor", async () => {
    render(<Harness initial={[{ name: "x", kind: "str" }]} />);
    await userEvent.selectOptions(screen.getByLabelText("field 0 kind"), "num");
    expect(screen.getByLabelText("x min")).toBeInTheDocument();
  });
});
