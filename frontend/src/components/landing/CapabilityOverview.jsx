const capabilities = [
  {
    title: "Merge readiness",
    body: "Explains whether visible evidence indicates ready, caution, not ready, or blocked.",
  },
  {
    title: "Risk and evidence confidence",
    body: "Keeps review risk separate from how complete the available evidence is.",
  },
  {
    title: "Review prioritization",
    body: "Ranks changed files and signals so reviewers know where to begin.",
  },
  {
    title: "Traceable guidance",
    body: "Links actions and conclusions back to current pull-request evidence.",
  },
];

export function CapabilityOverview() {
  return (
    <section className="capability-overview" aria-labelledby="capability-heading">
      <div className="section-heading">
        <p className="eyebrow">What the report gives you</p>
        <h2 id="capability-heading">A bounded review map, not a replacement for review.</h2>
      </div>
      <div className="capability-list">
        {capabilities.map((capability) => (
          <article className="capability-row" key={capability.title}>
            <span aria-hidden="true" />
            <div>
              <h3>{capability.title}</h3>
              <p>{capability.body}</p>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
