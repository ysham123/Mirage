export default function FleetStub() {
  return (
    <section>
      <h1 style={{ fontSize: "1.4rem", marginTop: 0 }}>Multi-agent fleet</h1>
      <p style={{ color: "#bbb", maxWidth: "60ch", lineHeight: 1.6 }}>
        Stub. The fleet view aggregates trace metadata across many
        Mirage gateway pods and renders containment rate,
        time-to-decide, and recent risky actions per environment.
      </p>
      <ul
        style={{
          color: "#bbb",
          maxWidth: "60ch",
          lineHeight: 1.7,
          paddingLeft: "1.25rem",
        }}
      >
        <li>Environment list (no environments registered yet).</li>
        <li>Per-environment containment rate over 24h / 7d / 30d.</li>
        <li>Top 10 risky actions across the fleet, grouped by policy.</li>
        <li>Per-environment time-to-decide percentiles.</li>
      </ul>
    </section>
  );
}
