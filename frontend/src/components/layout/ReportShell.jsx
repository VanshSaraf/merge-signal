import { Badge } from "../common/Badge.jsx";
import { formatNumber, titleCase } from "../../utils/formatting.js";
import { toneForLevel } from "../../utils/status.js";
import { AssessmentSummaryStrip, ReviewFocusPanel } from "../report/AssessmentRail.jsx";
import { ReportNavigation } from "../report/ReportNavigation.jsx";

export function ReportShell({ snapshot, activeSection, onSectionChange, children }) {
  const metadata = snapshot.metadata;
  const reference = snapshot.reference;
  const readiness = snapshot.merge_readiness;
  const isOverview = activeSection === "overview";

  return (
    <section className="report-shell" aria-label="Pull request analysis report">
      <div className="pull-header">
        <div className="pull-header__main">
          <p className="repo-breadcrumb">
            <span>{reference.owner}</span>
            <span aria-hidden="true">/</span>
            <span>{reference.repository}</span>
          </p>
          <div className="pull-title-row">
            <h2>
              <span className="repo-name">{reference.owner}/{reference.repository}</span>
              <span className="pull-number">#{reference.pull_number}</span>
            </h2>
            <Badge tone={toneForLevel(readiness?.decision)}>{titleCase(readiness?.decision)}</Badge>
          </div>
          <p className="pull-title">{metadata.title}</p>
        </div>
        <a className="button button--secondary" href={reference.canonical_url} target="_blank" rel="noreferrer">
          Open on GitHub
        </a>
      </div>

      <dl className="pull-meta">
        <div><dt>Author</dt><dd>{metadata.author?.login ?? "Unknown"}</dd></div>
        <div><dt>Branches</dt><dd><code>{metadata.head_branch?.ref ?? "unknown"}</code> into <code>{metadata.base_branch?.ref ?? "unknown"}</code></dd></div>
        <div><dt>State</dt><dd>{metadata.draft ? "Draft" : titleCase(metadata.state)}</dd></div>
        <div><dt>Changed files</dt><dd>{formatNumber(metadata.changed_files)}</dd></div>
      </dl>

      <div className={["report-console", isOverview ? "report-console--overview" : "report-console--compact"].join(" ")}>
        <div className="report-nav-sticky">
          <ReportNavigation activeSection={activeSection} onSectionChange={onSectionChange} />
        </div>
        <div className="report-console__main">
          {!isOverview && <AssessmentSummaryStrip snapshot={snapshot} />}
          {children}
        </div>
        {isOverview && <ReviewFocusPanel snapshot={snapshot} />}
      </div>
    </section>
  );
}
