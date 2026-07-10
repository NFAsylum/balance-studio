import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Button } from "./button";
import { Card, CardHeader, CardTitle, CardContent } from "./card";
import { Input } from "./input";

describe("shadcn-style components", () => {
  it("Button renders its label and variant classes", () => {
    render(<Button variant="outline">Click me</Button>);
    const btn = screen.getByRole("button", { name: "Click me" });
    expect(btn).toBeInTheDocument();
    expect(btn.className).toContain("border");
  });

  it("Card composes header/title/content", () => {
    render(
      <Card>
        <CardHeader>
          <CardTitle>Title</CardTitle>
        </CardHeader>
        <CardContent>Body</CardContent>
      </Card>
    );
    expect(screen.getByText("Title")).toBeInTheDocument();
    expect(screen.getByText("Body")).toBeInTheDocument();
  });

  it("Input reflects its value", () => {
    render(<Input defaultValue="hello" readOnly />);
    expect(screen.getByDisplayValue("hello")).toBeInTheDocument();
  });
});
