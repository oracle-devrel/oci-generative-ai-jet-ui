"use client";

import { ThemeProvider } from "@openuidev/react-ui";

export function OpenUiProvider({ children }: { children: React.ReactNode }) {
  return <ThemeProvider mode="light">{children}</ThemeProvider>;
}
