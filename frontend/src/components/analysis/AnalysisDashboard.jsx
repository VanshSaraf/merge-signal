import { useState } from "react";

import { useReportFilters } from "../../hooks/useReportFilters.js";
import { ReportShell } from "../layout/ReportShell.jsx";
import { ActionsSection } from "../report/ActionsSection.jsx";
import { EvidenceSection } from "../report/EvidenceSection.jsx";
import { FilesSection } from "../report/FilesSection.jsx";
import { OverviewSection } from "../report/OverviewSection.jsx";
import { ReviewsSection } from "../report/ReviewsSection.jsx";
import { SignalsSection } from "../report/SignalsSection.jsx";

export function AnalysisDashboard({ snapshot }) {
  const [activeSection, setActiveSection] = useState("overview");
  const filters = useReportFilters(snapshot);

  return (
    <div className="dashboard report-workspace" aria-live="polite">
      <ReportShell snapshot={snapshot} activeSection={activeSection} onSectionChange={setActiveSection}>
        <div role="tabpanel" id={`report-panel-${activeSection}`} aria-labelledby={`report-tab-${activeSection}`} className="report-panel" tabIndex={0}>
          {activeSection === "overview" && <OverviewSection snapshot={snapshot} onNavigate={setActiveSection} />}
          {activeSection === "files" && (
            <FilesSection
              files={snapshot.ranked_files ?? []}
              filteredFiles={filters.filteredFiles}
              filters={filters.fileFilters}
              setFilters={filters.setFileFilters}
              resetFilters={filters.resetFileFilters}
            />
          )}
          {activeSection === "reviews" && <ReviewsSection reviewContext={snapshot.review_context} />}
          {activeSection === "signals" && (
            <SignalsSection
              signals={snapshot.signals ?? []}
              filteredSignals={filters.filteredSignals}
              filters={filters.signalFilters}
              setFilters={filters.setSignalFilters}
              resetFilters={filters.resetSignalFilters}
            />
          )}
          {activeSection === "actions" && (
            <ActionsSection
              actions={snapshot.review_actions ?? []}
              filteredActions={filters.filteredActions}
              filters={filters.actionFilters}
              setFilters={filters.setActionFilters}
              resetFilters={filters.resetActionFilters}
            />
          )}
          {activeSection === "evidence" && <EvidenceSection snapshot={snapshot} />}
        </div>
      </ReportShell>
    </div>
  );
}
