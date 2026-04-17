import type { ReactNode } from "react";
import type { Metadata } from "next";
import { JetBrains_Mono, Sora } from "next/font/google";

import "./globals.css";

const sora = Sora({
  subsets: ["latin"],
  variable: "--font-sora",
});

const mono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
});

export const metadata: Metadata = {
  title: "Mirage Console",
  description: "A premium conversational interface for monitoring and suppressing agent side effects in CI.",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${sora.variable} ${mono.variable} antialiased`}>{children}</body>
    </html>
  );
}
