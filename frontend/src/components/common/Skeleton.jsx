import { MergeSignalLogo } from "../brand/MergeSignalLogo.jsx";

export function SkeletonDashboard() {
  return (
    <section className="skeleton-wrap" aria-live="polite" aria-label="Analysis loading">
      <div className="skeleton-copy">
        <MergeSignalLogo size={40} decorative />
        <p className="eyebrow">Analyzing snapshot</p>
        <h2>Building analysis report...</h2>
        <ol className="loading-steps">
          <li>Validating pull request</li>
          <li>Fetching GitHub evidence</li>
          <li>Building analysis report</li>
        </ol>
      </div>
      <div className="skeleton-grid">
        {Array.from({ length: 8 }, (_, index) => (
          <div className="skeleton-card" key={index}>
            <span />
            <strong />
            <p />
          </div>
        ))}
      </div>
    </section>
  );
}
