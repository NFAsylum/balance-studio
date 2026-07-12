"use client";
import * as React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "@/lib/theme";
import { LocaleProvider } from "@/lib/i18n";

export function Providers({ children }: { children: React.ReactNode }) {
  const [client] = React.useState(() => new QueryClient());
  return (
    <QueryClientProvider client={client}>
      <ThemeProvider>
        <LocaleProvider>{children}</LocaleProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}
