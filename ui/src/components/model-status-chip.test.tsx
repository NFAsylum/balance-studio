import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

vi.mock("@tanstack/react-query", () => ({ useQuery: vi.fn() }));
import { useQuery } from "@tanstack/react-query";
import { ModelStatusChip } from "./model-status-chip";

const mockUseQuery = useQuery as unknown as ReturnType<typeof vi.fn>;

describe("ModelStatusChip", () => {
  beforeEach(() => mockUseQuery.mockReset());

  test("loading state", () => {
    mockUseQuery.mockReturnValue({ isLoading: true });
    render(<ModelStatusChip />);
    expect(screen.getByTestId("model-status-chip")).toHaveTextContent(/checking/i);
  });

  test("success shows backend and model", () => {
    mockUseQuery.mockReturnValue({
      isLoading: false,
      isError: false,
      data: { status: "ok", backend_llm: "local", llm_model: "qwen2.5-coder-7b", domains_loaded: [], event_log_ready: true },
    });
    render(<ModelStatusChip />);
    expect(screen.getByTestId("model-status-chip")).toHaveTextContent("local · qwen2.5-coder-7b");
  });

  test("error shows offline", () => {
    mockUseQuery.mockReturnValue({ isLoading: false, isError: true, data: undefined });
    render(<ModelStatusChip />);
    expect(screen.getByTestId("model-status-chip")).toHaveTextContent(/offline/i);
  });
});
