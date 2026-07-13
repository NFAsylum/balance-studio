import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, expect, test, vi } from "vitest";
import { Hero } from "./Hero";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));

function renderHero(hasCardGame: boolean) {
  const qc = new QueryClient();
  return render(
    <QueryClientProvider client={qc}>
      <Hero hasCardGame={hasCardGame} />
    </QueryClientProvider>,
  );
}

describe("Hero", () => {
  test("shows both CTAs when card_game is available", () => {
    renderHero(true);
    expect(screen.getByTestId("hero")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /hearthstone example/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /start from scratch/i })).toBeInTheDocument();
  });

  test("hides the example CTA when card_game is absent", () => {
    renderHero(false);
    expect(screen.queryByRole("button", { name: /hearthstone example/i })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: /start from scratch/i })).toBeInTheDocument();
  });
});
