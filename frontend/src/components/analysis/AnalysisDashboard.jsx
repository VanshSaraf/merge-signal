import { useState } from "react";

import { useReportFilters } from "../../hooks/useReportFilters.js";
import { ActionsSection } from "../report/ActionsSection.jsx";
import { EvidenceSection } from "../report/EvidenceSection.jsx";
import { FilesSection } from "../report/FilesSection.jsx";
import { OverviewSection } from "../report/OverviewSection.jsx";
import { ReportNavigation } from "../report/ReportNavigation.jsx";
import { SignalsSection } from "../report/SignalsSection.jsx";

export function AnalysisDashboard({ snapshot }) {
  const [activeSection, setActiveSection] = useState("overview");
  const filters = useReportFilters(snapshot);

  return (
    <div className="dashboard report-workspace" aria-live="polite">
      <ReportNavigation activeSection={activeSection} onSectionChange={setActiveSection} />
      <div role="tabpanel" id={`report-${activeSection}`} className="report-panel">
        {activeSection === "overview" && <OverviewSection snapshot={snapshot} />}
        {activeSection === "files" && (
          <FilesSection
            files={snapshot.ranked_files ?? []}
            filteredFiles={filters.filteredFiles}
            filters={filters.fileFilters}
            setFilters={filters.setFileFilters}
            resetFilters={filters.resetFileFilters}
          />
        )}
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
    </div>
  );
}
