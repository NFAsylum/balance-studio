"use client";
import * as React from "react";

/** Minimal class-based dark-mode provider — no external dependency.
 *
 * Applies a `.dark` class on <html> (matching Tailwind `darkMode: ["class"]`), persists the
 * choice in localStorage, and falls back to the OS preference. A blocking script in the
 * document head (see layout.tsx) sets the initial class before hydration to avoid a flash. */

export type Theme = "light" | "dark";

type ThemeContextValue = { theme: Theme; setTheme: (t: Theme) => void; toggle: () => void };

const ThemeContext = React.createContext<ThemeContextValue | null>(null);

export const THEME_STORAGE_KEY = "balance-studio.theme";

function resolveInitial(): Theme {
  if (typeof document !== "undefined" && document.documentElement.classList.contains("dark")) {
    return "dark";
  }
  return "light";
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = React.useState<Theme>(resolveInitial);

  const apply = React.useCallback((next: Theme) => {
    setThemeState(next);
    if (typeof document !== "undefined") {
      document.documentElement.classList.toggle("dark", next === "dark");
    }
    try {
      window.localStorage.setItem(THEME_STORAGE_KEY, next);
    } catch {
      /* storage unavailable (private mode) — theme just won't persist */
    }
  }, []);

  const value = React.useMemo<ThemeContextValue>(
    () => ({ theme, setTheme: apply, toggle: () => apply(theme === "dark" ? "light" : "dark") }),
    [theme, apply]
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  const ctx = React.useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be used within <ThemeProvider>");
  return ctx;
}

/** Inline script (runs before hydration) that sets the initial `.dark` class with no flash. */
export const themeInitScript = `(function(){try{var k='${THEME_STORAGE_KEY}';var s=localStorage.getItem(k);var d=s?s==='dark':window.matchMedia('(prefers-color-scheme: dark)').matches;if(d)document.documentElement.classList.add('dark');}catch(e){}})();`;
