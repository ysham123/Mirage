export default function AuditLogStub() {
  return (
    <section>
      <h1 style={{ fontSize: "1.4rem", marginTop: 0 }}>Audit log export</h1>
      <p style={{ color: "#bbb", maxWidth: "60ch", lineHeight: 1.6 }}>
        Stub. Tenant-scoped audit log export. Pulls from the same
        trace store the gateway writes to, filtered to a tenant and a
        retention window. Output formats are CSV and JSON, with a
        SOC2/HIPAA-aligned schema that includes run id, timestamp,
        action, policy decisions, outcome, and operator identity.
      </p>
      <ul
        style={{
          color: "#bbb",
          maxWidth: "60ch",
          lineHeight: 1.7,
          paddingLeft: "1.25rem",
        }}
      >
        <li>Tenant + environment filter.</li>
        <li>Start / end timestamps with retention enforcement.</li>
        <li>Outcome filter (allowed, blocked, flagged, error).</li>
        <li>Async export job submission with email notification on completion.</li>
      </ul>
    </section>
  );
}
