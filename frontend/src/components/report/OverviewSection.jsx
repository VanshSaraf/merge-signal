import { Badge } from "../common/Badge.jsx";
import { Card } from "../common/Card.jsx";
import { formatNumber, titleCase } from "../../utils/formatting.js";
import { safeHttpUrl } from "../../utils/report.js";
import { toneForLevel } from "../../utils/status.js";
import { ScoreBreakdown } from "./ScoreBreakdown.jsx";

export function OverviewSection({ snapshot }) {
  return (
    <div className="report-section">
      <ReadinessStatement snapshot={snapshot} />
      <ReviewNext snapshot={snapshot} />
      <ReviewContextSummary snapshot={snapshot} />
      <CiSurfacePanel snapshot={snapshot} />
      <AssessmentRow snapshot={snapshot} />
      <MetricGrid snapshot={snapshot} />
      <div className="breakdown-grid">
        <Card title="Merge-risk groups" eyebrow="Not a probability">
          <ScoreBreakdown title="Risk group breakdown" items={snapshot.merge_risk?.group_scores ?? []} />
        </Card>
        <Card title="Evidence confidence" eyebrow="Visibility">
          <ScoreBreakdown title="Confidence components" items={snapshot.evidence_confidence?.components ?? []} valueKey="awarded_points" maxKey="maximum_points" nameKey="name" />
        </Card>
      </div>
    </div>
  );
}

function ReviewContextSummary({ snapshot }) {
  const context = snapshot.review_context;
  if (!context || (!context.review_count && !context.thread_count && context.visibility === "complete")) return null;
  const concern = context.concern_summary ?? {};
  const facts = [
    pluralFact(concern.needing_attention_count, "review conversation needs attention", "review conversations need attention"),
    pluralFact(concern.active_latest_change_request_count, "reviewer currently requests changes", "reviewers currently request changes"),
    pluralFact(concern.author_claimed_addressed_count, "author-said-addressed concern", "author-said-addressed concerns"),
    pluralFact(context.thread_count && !concern.needing_attention_count, "inline conversation", "inline conversations"),
  ].filter(Boolean);
  return (
    <section className="review-context-summary" aria-label="Review context summary">
      <p className="eyebrow">Reviews</p>
      <h2>{facts.length ? facts.join(" · ") : `Review context ${context.visibility ?? "available"}`}</h2>
      <p>Observable GitHub review state only; resolution is not inferred yet.</p>
    </section>
  );
}

function pluralFact(count, singular, plural) {
  if (!count) return null;
  return `${count} ${count === 1 ? singular : plural}`;
}

function ReadinessStatement({ snapshot }) {
  const decision = titleCase(snapshot.merge_readiness?.decision);
  const primaryReason = snapshot.merge_readiness?.reasons?.[0];
  const reasonText = summarizeReason(primaryReason, snapshot);

  return (
    <section className="readiness-statement" aria-label="Readiness statement">
      <p className="eyebrow">Primary assessment</p>
      <h2>{decision}{reasonText ? ` because ${reasonText}.` : "."}</h2>
      {primaryReason?.explanation && <p>{primaryReason.explanation}</p>}
    </section>
  );
}

function summarizeReason(reason, snapshot) {
  if (!reason) return "";
  const ruleId = reason.rule_id ?? "";
  if (ruleId.includes("ci_failing") || snapshot.ci?.state === "failing") return ciBlockerText(snapshot) ?? "CI is failing";
  if (ruleId.includes("merge_conflict")) return "a merge conflict is reported";
  if (reason.title) return reason.title.replace(/\.$/, "").toLowerCase();
  return ruleId.replace(/^readiness\.[^.]+\./, "").replaceAll("_", " ");
}

function ciBlockerText(snapshot) {
  const blocker = snapshot.ci_explanation?.blocking_items?.[0];
  if (!blocker) return null;
  const provider = blocker.provider || blocker.name;
  return `${provider} ${categoryLabel(blocker.category)} check is failing`;
}

function CiSurfacePanel({ snapshot }) {
  const explanation = snapshot.ci_explanation;
  if (!explanation) return null;

  return (
    <section className="ci-surface-panel" aria-label="CI surface summary">
      <div className="ci-surface-panel__header">
        <div>
          <p className="eyebrow">CI surfaces</p>
          <h2>{explanation.summary ?? "CI status was observed."}</h2>
        </div>
        <Badge tone={toneForLevel(explanation.overall_state)}>{titleCase(explanation.overall_state)}</Badge>
      </div>
      <div className="ci-surface-counts" aria-label="CI item counts">
        <CiCount label="Passed" value={explanation.passing_count} tone="success" />
        <CiCount label="Failed" value={explanation.failing_count} tone="danger" />
        <CiCount label="Pending" value={explanation.pending_count} tone="warning" />
        <CiCount label="Unknown" value={explanation.unknown_count} tone="neutral" />
      </div>
      {explanation.blocking_items?.length > 0 && (
        <div className="ci-blockers">
          {explanation.blocking_items.map((item) => (
            <CiItem item={item} key={`${item.source_type}-${item.provider}-${item.name}`} />
          ))}
        </div>
      )}
      {explanation.surfaces?.length > 0 && (
        <details className="ci-surface-details">
          <summary>View CI surface details</summary>
          <div className="ci-surface-groups">
            {explanation.surfaces.map((surface) => (
              <div className="ci-surface-group" key={`${surface.source_type}-${surface.provider}`}>
                <div className="ci-surface-group__heading">
                  <strong>{surface.provider}</strong>
                  <span>{titleCase(surface.source_type.replaceAll("_", " "))}</span>
                </div>
                <div className="ci-surface-items">
                  {surface.items.map((item) => (
                    <CiItem item={item} key={`${item.source_type}-${item.provider}-${item.name}-${item.normalized_state}`} compact />
                  ))}
                </div>
              </div>
            ))}
          </div>
        </details>
      )}
    </section>
  );
}

function CiCount({ label, value, tone }) {
  return (
    <div className={`ci-count ci-count--${tone}`}>
      <strong>{value ?? 0}</strong>
      <span>{label}</span>
    </div>
  );
}

function CiItem({ item, compact = false }) {
  const url = safeHttpUrl(item.details_url);
  return (
    <article className={compact ? "ci-item ci-item--compact" : "ci-item"}>
      <div>
        <strong>{item.provider}</strong>
        <span>{item.name}</span>
      </div>
      <div className="ci-item__meta">
        <Badge tone={toneForLevel(item.normalized_state)}>{titleCase(item.normalized_state)}</Badge>
        <Badge>{categoryLabel(item.category)}</Badge>
        {url && <a href={url} target="_blank" rel="noreferrer">Open details</a>}
      </div>
      {!compact && item.description && <p>{item.description}</p>}
    </article>
  );
}

function categoryLabel(category) {
  if (category === "authorization_or_configuration") return "authorization/configuration";
  if (category === "typecheck") return "typecheck";
  return titleCase(String(category ?? "unknown").replaceAll("_", " "));
}

function AssessmentRow({ snapshot }) {
  return (
    <section className="assessment-row" aria-label="Primary assessment">
      <AssessmentTile label="Readiness" value={titleCase(snapshot.merge_readiness?.decision)} tone={toneForLevel(snapshot.merge_readiness?.decision)} detail="Current verdict" />
      <AssessmentTile label="Merge risk" value={`${snapshot.merge_risk?.score ?? 0}/100`} tone={toneForLevel(snapshot.merge_risk?.level)} detail={titleCase(snapshot.merge_risk?.level)} meter={snapshot.merge_risk?.score ?? 0} />
      <AssessmentTile label="Evidence confidence" value={`${snapshot.evidence_confidence?.score ?? 0}/100`} tone={toneForConfidence(snapshot.evidence_confidence?.level)} detail={titleCase(snapshot.evidence_confidence?.level)} meter={snapshot.evidence_confidence?.score ?? 0} />
      <AssessmentTile label="CI" value={titleCase(snapshot.ci?.state)} tone={toneForLevel(snapshot.ci?.state)} detail={`Visibility: ${titleCase(snapshot.ci?.visibility)}`} />
    </section>
  );
}

function AssessmentTile({ label, value, tone, detail, meter }) {
  return (
    <article className="assessment-tile">
      <div className="assessment-tile__copy">
        <span>{label}</span>
        <strong>{value}</strong>
      </div>
      <Badge tone={tone}>{detail}</Badge>
      {meter != null && (
        <div className="assessment-meter" aria-label={`${label} ${meter} of 100`}>
          <span style={{ width: `${Math.min(100, Math.max(0, meter))}%` }} />
        </div>
      )}
    </article>
  );
}

function ReviewNext({ snapshot }) {
  const items = reviewNextItems(snapshot);

  if (!items.length) {
    return null;
  }

  return (
    <section className="review-next" aria-labelledby="review-next-heading">
      <div>
        <p className="eyebrow">Review next</p>
        <h2 id="review-next-heading">Start with the evidence that can change merge readiness.</h2>
      </div>
      <ol>
        {items.map((item) => (
          <li key={item.label}>
            <strong>{item.label}</strong>
            {item.detail && <span>{item.detail}</span>}
          </li>
        ))}
      </ol>
    </section>
  );
}

function reviewNextItems(snapshot) {
  const actions = (snapshot.review_actions ?? []).slice(0, 2).map((action) => ({
    label: action.title,
    detail: action.description,
  }));
  const topFile = snapshot.ranked_files?.[0];
  const fileItem = topFile?.path
    ? [{
        label: `Start with ${topFile.path}`,
        detail: `${titleCase(topFile.level)} priority changed file`,
      }]
    : [];

  return [...actions, ...fileItem].slice(0, 3);
}

function MetricGrid({ snapshot }) {
  const metrics = [
    ["Changed files", snapshot.metadata?.changed_files],
    ["Additions", snapshot.metadata?.additions],
    ["Deletions", snapshot.metadata?.deletions],
    ["Commits", snapshot.metadata?.commit_count],
    ["Review signals", snapshot.signal_summary?.total_signals],
    ["Review actions", snapshot.review_action_summary?.total_actions],
  ];
  return (
    <section className="metric-grid" aria-label="Snapshot metrics">
      {metrics.map(([label, value]) => <div className="metric" key={label}><span>{label}</span><strong>{formatNumber(value)}</strong></div>)}
    </section>
  );
}

function toneForConfidence(level) {
  return { high: "success", medium: "warning", low: "danger" }[level] ?? "neutral";
}
