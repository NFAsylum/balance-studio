import { render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";
import { ErrorBoundary } from "./ErrorBoundary";

function Boom(): React.ReactNode {
  throw new Error("nope");
}

describe("ErrorBoundary", () => {
  test("catches a crashing child and offers recovery", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    render(
      <ErrorBoundary label="Couldn't load">
        <Boom />
      </ErrorBoundary>,
    );
    expect(screen.getByTestId("error-boundary")).toBeInTheDocument();
    expect(screen.getByText("Couldn't load")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /try again/i })).toBeInTheDocument();
    spy.mockRestore();
  });

  test("renders children when there is no error", () => {
    render(
      <ErrorBoundary>
        <p>all good</p>
      </ErrorBoundary>,
    );
    expect(screen.getByText("all good")).toBeInTheDocument();
    expect(screen.queryByTestId("error-boundary")).not.toBeInTheDocument();
  });
});
