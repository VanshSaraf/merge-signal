import { reportSections } from "../../utils/report.js";

export function ReportNavigation({ activeSection, onSectionChange, snapshot }) {
  function focusTab(sectionId) {
    document.getElementById(`report-tab-${sectionId}`)?.focus();
  }

  function handleKeyDown(event, sectionId) {
    const currentIndex = reportSections.findIndex((section) => section.id === sectionId);
    const lastIndex = reportSections.length - 1;
    let nextIndex = currentIndex;

    if (event.key === "ArrowRight") nextIndex = currentIndex === lastIndex ? 0 : currentIndex + 1;
    if (event.key === "ArrowLeft") nextIndex = currentIndex === 0 ? lastIndex : currentIndex - 1;
    if (event.key === "Home") nextIndex = 0;
    if (event.key === "End") nextIndex = lastIndex;

    if (nextIndex !== currentIndex) {
      event.preventDefault();
      const nextSection = reportSections[nextIndex].id;
      onSectionChange(nextSection);
      requestAnimationFrame(() => focusTab(nextSection));
    }
  }

  return (
    <nav className="report-tabs" aria-label="Analysis report sections" role="tablist">
      {reportSections.map((section) => (
        <button
          aria-controls={`report-panel-${section.id}`}
          aria-selected={activeSection === section.id}
          className="report-tab"
          id={`report-tab-${section.id}`}
          key={section.id}
          onKeyDown={(event) => handleKeyDown(event, section.id)}
          onClick={() => onSectionChange(section.id)}
          role="tab"
          tabIndex={activeSection === section.id ? 0 : -1}
          type="button"
        >
          {sectionLabel(section, snapshot)}
        </button>
      ))}
    </nav>
  );
}

function sectionLabel(section, snapshot) {
  if (section.id !== "reviews") return section.label;
  const count = snapshot?.review_context?.thread_count ?? 0;
  return count > 0 ? `${section.label} (${count})` : section.label;
}
