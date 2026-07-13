const boundaries = [
  "Deterministic, versioned rules",
  "Bounded GitHub API usage",
  "No repository execution",
  "No dependency installation",
  "Sanitized errors",
  "Credential-like values are not returned",
  "No AI-generated review commentary",
];

export function TrustSection() {
  return (
    <section className="trust-section" aria-labelledby="trust-heading">
      <div className="section-heading">
        <p className="eyebrow">Trust boundaries</p>
        <h2 id="trust-heading">Built for explainable review.</h2>
      </div>
      <ul className="boundary-list">
        {boundaries.map((boundary) => (
          <li key={boundary}>{boundary}</li>
        ))}
      </ul>
    </section>
  );
}
