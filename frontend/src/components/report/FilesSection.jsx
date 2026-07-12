import { useRef, useState } from "react";

import { Badge } from "../common/Badge.jsx";
import { Card } from "../common/Card.jsx";
import { compactList, formatNumber, titleCase } from "../../utils/formatting.js";
import { optionValues } from "../../utils/report.js";
import { toneForLevel } from "../../utils/status.js";
import { FileDetails } from "./FileDetails.jsx";
import { FilterBar, SelectFilter, TextFilter } from "./FilterBar.jsx";

export function FilesSection({ files, filteredFiles, filters, setFilters, resetFilters }) {
  const [selectedFile, setSelectedFile] = useState(null);
  const triggerRef = useRef(null);
  const levels = optionValues(files, (file) => [file.level]);
  const kinds = optionValues(files, (file) => [file.primary_kind]);
  const areas = optionValues(files, (file) => file.areas ?? []);
  const statuses = optionValues(files, (file) => [file.status]);

  function openFile(file, event) {
    triggerRef.current = event.currentTarget;
    setSelectedFile(file);
  }

  function closeFile() {
    setSelectedFile(null);
    triggerRef.current?.focus();
  }

  return (
    <Card title="Ranked files" eyebrow={`${filteredFiles.length} of ${files.length}`}>
      <FilterBar onClear={resetFilters}>
        <TextFilter id="file-search" label="Search path" value={filters.query} onChange={(query) => setFilters({ ...filters, query })} placeholder="backend/app" />
        <SelectFilter id="file-level" label="Priority" value={filters.level} onChange={(level) => setFilters({ ...filters, level })} options={levels} />
        <SelectFilter id="file-kind" label="Kind" value={filters.kind} onChange={(kind) => setFilters({ ...filters, kind })} options={kinds} />
        <SelectFilter id="file-area" label="Area" value={filters.area} onChange={(area) => setFilters({ ...filters, area })} options={areas} />
        <SelectFilter id="file-status" label="Status" value={filters.status} onChange={(status) => setFilters({ ...filters, status })} options={statuses} />
        <SelectFilter id="file-sort" label="Sort" value={filters.sort} onChange={(sort) => setFilters({ ...filters, sort })} options={["rank", "score", "changes", "path"]} />
      </FilterBar>

      {filteredFiles.length === 0 ? (
        <p className="empty-result">No files match the current filters.</p>
      ) : (
        <div className="report-table file-table">
          {filteredFiles.map((file) => (
            <article className="report-row file-report-row" key={file.path}>
              <span className="rank">#{file.rank}</span>
              <div className="row-main">
                <strong>{file.path}</strong>
                {file.previous_path && <small>Renamed from {file.previous_path}</small>}
                <small>{titleCase(file.status)} · {titleCase(file.primary_kind)} · {titleCase(file.language)} · {compactList(file.areas ?? [], 3) || "No area"}</small>
              </div>
              <Badge tone={toneForLevel(file.level)}>{file.score} · {titleCase(file.level)}</Badge>
              <span className="diff-stat">
                <span className="diff-stat__add">+{formatNumber(file.additions)}</span>
                <span className="diff-stat__delete">-{formatNumber(file.deletions)}</span>
                <span>{formatNumber(file.changes)} total</span>
              </span>
              <span>{(file.related_signal_ids ?? []).length} signals</span>
              <button className="button button--secondary" type="button" onClick={(event) => openFile(file, event)}>Details</button>
            </article>
          ))}
        </div>
      )}

      <FileDetails file={selectedFile} onClose={closeFile} returnFocusRef={triggerRef} />
    </Card>
  );
}
