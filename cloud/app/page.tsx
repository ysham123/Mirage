import Link from "next/link";

const ROUTES = [
  {
    href: "/policies",
    title: "Policy authoring",
    description:
      "Authoring surface for policies that compile to the same YAML the runtime gateway evaluates. Stub.",
  },
  {
    href: "/fleet",
    title: "Multi-agent fleet",
    description:
      "Fleet view across many gateways: containment rate, time-to-decide, run volume, recent risky actions. Stub.",
  },
  {
    href: "/audit-log",
    title: "Audit log export",
    description:
      "Tenant-scoped audit log export with retention and SOC2/HIPAA-aligned filtering. Stub.",
  },
];

export default function ControlPlaneIndex() {
  return (
    <div>
      <h1 style={{ fontSize: "1.5rem", marginTop: 0 }}>Hosted control plane</h1>
      <p style={{ color: "#bbb", maxWidth: "60ch", lineHeight: 1.6 }}>
        Early-stage commercial scaffolding for Mirage Cloud. The OSS
        runtime gateway is the source of truth for policy decisions; this
        control plane is the multi-tenant management surface that ships
        on top of it. None of these routes are wired to a backend yet.
      </p>
      <ul
        style={{
          display: "grid",
          gap: "1rem",
          gridTemplateColumns: "1fr 1fr 1fr",
          listStyle: "none",
          padding: 0,
          marginTop: "2rem",
        }}
      >
        {ROUTES.map((route) => (
          <li key={route.href}>
            <Link
              href={route.href}
              style={{
                display: "block",
                padding: "1.25rem",
                border: "1px solid #2a2a2a",
                borderRadius: "0",
                color: "#f4f4f4",
                textDecoration: "none",
                background: "#111",
              }}
            >
              <strong style={{ fontSize: "1rem" }}>{route.title}</strong>
              <p
                style={{
                  marginTop: "0.5rem",
                  marginBottom: 0,
                  fontSize: "0.9rem",
                  color: "#999",
                  lineHeight: 1.5,
                }}
              >
                {route.description}
              </p>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
