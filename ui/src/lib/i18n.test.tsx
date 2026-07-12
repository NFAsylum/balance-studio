import * as React from "react";
import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, test } from "vitest";
import { LocaleProvider, LOCALE_STORAGE_KEY, useT } from "./i18n";

afterEach(() => window.localStorage.clear());

const wrapper = ({ children }: { children: React.ReactNode }) => <LocaleProvider>{children}</LocaleProvider>;

describe("i18n", () => {
  test("defaults to English without a provider", () => {
    const { result } = renderHook(() => useT());
    expect(result.current.locale).toBe("en");
    expect(result.current.t("save")).toBe("Save");
  });

  test("interpolates named vars", () => {
    const { result } = renderHook(() => useT());
    expect(result.current.t("domainsAvailable", { n: 3 })).toBe("3 domains available");
  });

  test("falls back to the key when it is unknown", () => {
    const { result } = renderHook(() => useT());
    expect(result.current.t("does-not-exist" as never)).toBe("does-not-exist");
  });

  test("switches to Portuguese and persists the choice", () => {
    const { result } = renderHook(() => useT(), { wrapper });
    act(() => result.current.setLocale("pt"));
    expect(result.current.t("save")).toBe("Salvar");
    expect(result.current.t("domainsAvailable", { n: 2 })).toBe("2 domains disponíveis");
    expect(window.localStorage.getItem(LOCALE_STORAGE_KEY)).toBe("pt");
  });
});
