import type { Metadata } from "next";

import { OpenUiProvider } from "@/components/OpenUiProvider";

import "@openuidev/react-ui/components.css";
import "@openuidev/react-ui/styles/index.css";
import "./globals.css";

export const metadata: Metadata = {
  title: "Generative UI Data Chat",
  description: "Oracle AI Database 26ai reference app for typed generative UI responses."
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <OpenUiProvider>{children}</OpenUiProvider>
      </body>
    </html>
  );
}
