import { HealthStatus } from "../components/HealthStatus.jsx";

export function HomePage() {
  return (
    <div className="page-stack">
      <section className="intro">
        <p className="eyebrow">Foundation</p>
        <h2>Merge readiness starts with evidence.</h2>
        <p>
          This shell will grow into deterministic pull-request risk analysis, changed-file ranking,
          repository policy checks, and confidence reporting.
        </p>
      </section>

      <HealthStatus />
    </div>
  );
}
