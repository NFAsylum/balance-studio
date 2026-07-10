import * as React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, renderHook } from "@testing-library/react";
import { MetricsPanel, MetricCard, FreshnessBadge, summarize, useFreshnessDebounce, type MetricResult } from "./MetricsPanel";

const rating: MetricResult = { kind: "rating", name: "elo_mmr", data: { A: 1610, B: 1390 } };
const dist: MetricResult = { kind: "distribution", name: "winrate_distribution", data: { mean: 0.5, std: 0.25 } };

describe("freshness + metrics panel", () => {
  it("FreshnessBadge shows the right state icon/label", () => {
    for (const [state, icon] of [["full", "🟢"], ["quick", "🟡"], ["stale", "🔴"], ["computing", "⏳"]] as const) {
      const { unmount } = render(<FreshnessBadge state={state} />);
      const badge = screen.getByTestId("freshness");
      expect(badge).toHaveAttribute("data-state", state);
      expect(badge.textContent).toBe(icon);
      unmount();
    }
  });

  it("MetricCard shows a summarized value + freshness badge", () => {
    render(<MetricCard result={rating} freshness="stale" />);
    expect(screen.getByText("elo_mmr")).toBeInTheDocument();
    expect(screen.getByText("top: A (1610)")).toBeInTheDocument();
    expect(screen.getByTestId("freshness")).toHaveAttribute("data-state", "stale");
    expect(summarize(dist)).toBe("mean 0.50");
  });

  it("Run Full Simulation button triggers the callback (disabled while computing)", () => {
    const onRunFull = vi.fn();
    const { rerender } = render(<MetricsPanel results={[rating, dist]} freshness="quick" onRunFull={onRunFull} />);
    fireEvent.click(screen.getByRole("button", { name: /run full simulation/i }));
    expect(onRunFull).toHaveBeenCalledTimes(1);
    rerender(<MetricsPanel results={[rating, dist]} freshness="computing" onRunFull={onRunFull} />);
    expect(screen.getByRole("button", { name: /computing/i })).toBeDisabled();
  });

  describe("useFreshnessDebounce", () => {
    beforeEach(() => vi.useFakeTimers());
    afterEach(() => vi.useRealTimers());

    it("fires quick at 2s and full at 5s after an edit", () => {
      const onQuick = vi.fn();
      const onFull = vi.fn();
      const { result } = renderHook(() => useFreshnessDebounce(onQuick, onFull, 2000, 5000));
      result.current(); // touch (an edit happened)

      vi.advanceTimersByTime(2000);
      expect(onQuick).toHaveBeenCalledTimes(1);
      expect(onFull).not.toHaveBeenCalled();

      vi.advanceTimersByTime(3000); // total 5s
      expect(onFull).toHaveBeenCalledTimes(1);
    });

    it("a new edit before 2s resets the quick timer (debounce)", () => {
      const onQuick = vi.fn();
      const { result } = renderHook(() => useFreshnessDebounce(onQuick, vi.fn(), 2000, 5000));
      result.current();
      vi.advanceTimersByTime(1500);
      result.current(); // edit again -> reset
      vi.advanceTimersByTime(1500); // 1.5s since last edit
      expect(onQuick).not.toHaveBeenCalled();
      vi.advanceTimersByTime(500); // now 2s since last edit
      expect(onQuick).toHaveBeenCalledTimes(1);
    });
  });
});
