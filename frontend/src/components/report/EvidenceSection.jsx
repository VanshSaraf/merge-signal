import { Badge } from "../common/Badge.jsx";
import { Card } from "../common/Card.jsx";
import { compactList, formatNumber, titleCase } from "../../utils/formatting.js";
import { dedupe } from "../../utils/report.js";
import { toneForLevel } from "../../utils/status.js";
import { ScoreBreakdown } from "./ScoreBreakdown.jsx";

export function EvidenceSection({ snapshot }) {
  const limitations = dedupe([
    ...(snapshot.merge_readiness?.limitations ?? []),
    ...(snapshot.merge_risk?.limitations ?? []),
    ...(snapshot.evidence_confidence?.limitations ?? []),
    ...(snapshot.file_priority_summary?.limitations ?? []),
    ...(snapshot.review_action_summary?.limitations ?? []),
    ...(snapshot.completeness?.warnings ?? []),
    ...(snapshot.ci?.warnings ?? []),
    ...(snapshot.classification_summary?.warnings ?? []),
  ]);

  return (
    <div className="evidence-grid">
      <Card title="Readiness reasons" eyebrow="Decision evidence">
        <div className="stack-list">
          {(snapshot.merge_readiness?.reasons ?? []).map((reason) => (
            <article className="compact-evidence" key={reason.rule_id}>
              <Badge tone={toneForLevel(reason.effect)}>{titleCase(reason.effect)}</Badge>
              <div><strong>{reason.title}</strong><p>{reason.explanation}</p><small>{reason.rule_id}</small></div>
            </article>
          ))}
        </div>
      </Card>
      <Card title="Risk contributions" eyebrow="Signals">
        <div className="stack-list">
          {(snapshot.merge_risk?.contributions ?? []).map((contribution) => (
            <article className="compact-evidence" key={contribution.signal_id}>
              <Badge tone={toneForLevel(contribution.severity)}>{titleCase(contribution.severity)}</Badge>
              <div><strong>{contribution.title}</strong><p>{contribution.explanation}</p><small>{contribution.applied_points}/{contribution.raw_points} points · {contribution.rule_id}</small></div>
            </article>
          ))}
        </div>
      </Card>
      <Card title="Confidence components" eyebrow="Visibility">
        <ScoreBreakdown title="Component breakdown" items={snapshot.evidence_confidence?.components ?? []} valueKey="awarded_points" maxKey="maximum_points" nameKey="name" />
      </Card>
      <Card title="Completeness and CI" eyebrow="Retrieval">
        <dl className="detail-grid">
          <div><dt>Files complete</dt><dd>{String(snapshot.completeness?.files_complete)}</dd></div>
          <div><dt>Commits complete</dt><dd>{String(snapshot.completeness?.commits_complete)}</dd></div>
          <div><dt>Missing patches</dt><dd>{formatNumber(snapshot.completeness?.missing_patch_count)}</dd></div>
          <div><dt>CI state</dt><dd>{titleCase(snapshot.ci?.state)}</dd></div>
          <div><dt>CI visibility</dt><dd>{titleCase(snapshot.ci?.visibility)}</dd></div>
        </dl>
      </Card>
      <Card title="Classification summary" eyebrow="Files">
        <dl className="detail-grid">
          <div><dt>Total files</dt><dd>{formatNumber(snapshot.classification_summary?.total_files)}</dd></div>
          <div><dt>Classified</dt><dd>{formatNumber(snapshot.classification_summary?.classified_files)}</dd></div>
          <div><dt>Unknown</dt><dd>{formatNumber(snapshot.classification_summary?.unknown_files)}</dd></div>
          <div><dt>Kinds</dt><dd>{compactList((snapshot.classification_summary?.counts_by_kind ?? []).map((item) => `${item.name}: ${item.count}`), 5)}</dd></div>
        </dl>
      </Card>
      <Card title="Analysis boundaries" eyebrow="Scope">
        <div className="limitation-groups">
          <LimitationGroup
            title="Analysis boundaries"
            items={[
              "MergeSignal uses deterministic GitHub-visible evidence from the current snapshot.",
              "Human review remains necessary for intent, correctness, and product judgment.",
            ]}
          />
          <LimitationGroup
            title="Score boundaries"
            items={[
              "Merge risk is a heuristic score, not a probability.",
              "Evidence confidence measures visibility and completeness, not code quality.",
            ]}
          />
          <LimitationGroup
            title="Human review"
            items={[
              "Review actions are prompts for verification, not automated fixes.",
              "Low-priority files must still be considered when reviewing the PR.",
            ]}
          />
          {limitations.length > 0 && <LimitationGroup title="Source limitations" items={limitations} compact />}
        </div>
      </Card>
    </div>
  );
}

function LimitationGroup({ title, items, compact = false }) {
  return (
    <section className={compact ? "limitation-group limitation-group--compact" : "limitation-group"}>
      <h3>{title}</h3>
      <ul className="limitation-list">
        {items.map((item) => <li key={item}>{item}</li>)}
      </ul>
    </section>
  );
}
