import type { ReactNode } from "react";

export const metadata = {
  title: "Mirage Cloud",
  description: "Mirage hosted control plane (early-stage scaffolding).",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body
        style={{
          fontFamily: "system-ui, sans-serif",
          background: "#0a0a0a",
          color: "#f4f4f4",
          margin: 0,
        }}
      >
        <header
          style={{
            display: "flex",
            alignItems: "baseline",
            gap: "1rem",
            padding: "1.25rem 2rem",
            borderBottom: "1px solid #222",
          }}
        >
          <strong style={{ fontSize: "1.1rem", letterSpacing: "-0.01em" }}>
            Mirage
          </strong>
          <span
            style={{
              fontFamily: "ui-monospace, SFMono-Regular, monospace",
              fontSize: "0.7rem",
              color: "#888",
              textTransform: "uppercase",
              letterSpacing: "0.18em",
            }}
          >
            cloud · scaffolding
          </span>
        </header>
        <main style={{ padding: "2rem", maxWidth: "1100px", margin: "0 auto" }}>
          {children}
        </main>
      </body>
    </html>
  );
}
