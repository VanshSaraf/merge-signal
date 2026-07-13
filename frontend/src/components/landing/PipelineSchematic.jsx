const pipelineSteps = [
  "GitHub evidence",
  "Classify changes",
  "Detect signals",
  "Score readiness",
  "Prioritize review",
];

export function PipelineSchematic() {
  return (
    <section className="pipeline-schematic" aria-label="Evidence to review-order pipeline">
      <ol className="pipeline-steps">
        {pipelineSteps.map((step, index) => (
          <li key={step}>
            <span className="pipeline-node" aria-hidden="true">{index + 1}</span>
            <span>{step}</span>
          </li>
        ))}
      </ol>
    </section>
  );
}
