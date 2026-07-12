import { reportSections } from "../../utils/report.js";

export function ReportNavigation({ activeSection, onSectionChange }) {
  return (
    <nav className="report-tabs" aria-label="Analysis report sections">
      {reportSections.map((section) => (
        <button
          aria-selected={activeSection === section.id}
          className="report-tab"
          key={section.id}
          onClick={() => onSectionChange(section.id)}
          role="tab"
          type="button"
        >
          {section.label}
        </button>
      ))}
    </nav>
  );
}
