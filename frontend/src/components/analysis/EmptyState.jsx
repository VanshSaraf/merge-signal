import { Card } from "../common/Card.jsx";
import { MergeSignalLogo } from "../brand/MergeSignalLogo.jsx";

export function EmptyState() {
  return (
    <Card title="Ready for a pull request" eyebrow="Deterministic evidence" className="empty-state-card">
      <div className="empty-grid">
        <MergeSignalLogo size={96} decorative className="empty-mark" />
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
