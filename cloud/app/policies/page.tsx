export default function PolicyAuthoringStub() {
  return (
    <section>
      <h1 style={{ fontSize: "1.4rem", marginTop: 0 }}>Policy authoring</h1>
      <p style={{ color: "#bbb", maxWidth: "60ch", lineHeight: 1.6 }}>
        Stub. The policy authoring surface compiles a structured policy
        editor to the same YAML the runtime gateway already consumes
        (`policies.yaml`). Nothing here is connected to a backend.
      </p>
      <ul
        style={{
          color: "#bbb",
          maxWidth: "60ch",
          lineHeight: 1.7,
          paddingLeft: "1.25rem",
        }}
      >
        <li>List of authored policies (empty).</li>
        <li>Per-policy editor with live preview against sample payloads.</li>
        <li>Versioning + diff-vs-prod review.</li>
        <li>One-click export to the gateway pod or a CI artifact.</li>
      </ul>
    </section>
  );
}
