import { Card } from "../common/Card.jsx";

export function EmptyState() {
  return (
    <Card title="Ready for a pull request" eyebrow="Deterministic evidence">
      <div className="empty-grid">
        <p>
          MergeSignal collects public PR metadata, changed files, CI visibility, classifications,
          review signals, risk, confidence, readiness, ranked files, and review actions.
        </p>
        <p>
          It does not run repository code, install dependencies, assign reviewers, or generate AI
          review commentary.
        </p>
      </div>
    </Card>
  );
}
