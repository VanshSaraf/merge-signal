export function SkeletonDashboard() {
  return (
    <section className="skeleton-wrap" aria-live="polite" aria-label="Analysis loading">
      <div>
        <p className="eyebrow">Analyzing snapshot</p>
        <h2>Collecting deterministic evidence...</h2>
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
