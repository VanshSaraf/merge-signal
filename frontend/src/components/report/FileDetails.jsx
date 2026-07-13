import { useEffect, useRef } from "react";

import { Badge } from "../common/Badge.jsx";
import { compactList, titleCase } from "../../utils/formatting.js";
import { toneForLevel } from "../../utils/status.js";

export function FileDetails({ file, onClose, returnFocusRef }) {
  const closeRef = useRef(null);

  useEffect(() => {
    closeRef.current?.focus();
    function onKeyDown(event) {
      if (event.key === "Escape") {
        onClose();
        returnFocusRef.current?.focus();
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose, returnFocusRef]);

  if (!file) return null;

  return (
    <div className="drawer-backdrop" role="presentation">
      <aside className="file-drawer" role="dialog" aria-modal="true" aria-labelledby="file-detail-title">
        <div className="drawer-header">
          <div>
            <p className="eyebrow">File detail</p>
            <h2 id="file-detail-title">{file.path}</h2>
          </div>
          <button className="button button--secondary" type="button" onClick={onClose} ref={closeRef}>
            Close
          </button>
        </div>

        <dl className="detail-grid">
          <div><dt>Priority</dt><dd><Badge tone={toneForLevel(file.level)}>{file.score} · {titleCase(file.level)}</Badge></dd></div>
          <div><dt>Status</dt><dd>{titleCase(file.status)}</dd></div>
          <div><dt>Kind</dt><dd>{titleCase(file.primary_kind)}</dd></div>
          <div><dt>Language</dt><dd>{titleCase(file.language)}</dd></div>
          <div><dt>Areas</dt><dd>{compactList(file.areas ?? [], 4) || "None"}</dd></div>
          <div><dt>Magnitude</dt><dd>{titleCase(file.change_magnitude ?? "tiny")}</dd></div>
          <div><dt>Changes</dt><dd>{file.additions} additions, {file.deletions} deletions, {file.changes} total</dd></div>
          {file.previous_path && <div><dt>Previous path</dt><dd>{file.previous_path}</dd></div>}
          <div><dt>Related signals</dt><dd>{(file.related_signal_ids ?? []).length}</dd></div>
        </dl>

        <section className="detail-section">
          <h3>Priority factors</h3>
          {(file.factors ?? []).length > 0 ? (
            <ul className="factor-list">
              {file.factors.map((factor) => (
                <li key={factor.id}>
                  <span aria-hidden="true">✓</span>
                  <div>
                    <strong>{titleCase(factor.category)}</strong>
                    <p>{factor.points} points - {factor.description}</p>
                    {(factor.evidence ?? []).map((item) => <small key={item}>{item}</small>)}
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <p className="muted">None observed.</p>
          )}
        </section>
        <ContextDetails context={file.classification?.context ?? file.context ?? {}} />
        <DetailList title="Related signal IDs" items={file.related_signal_ids ?? []} />
        <DetailList title="Related review conversations" items={relatedThreadIds(file)} />
        <details className="detail-section">
          <summary>Technical factor details</summary>
          <ul>
            {(file.factors ?? []).map((factor) => <li key={factor.id}><code>{factor.id}</code></li>)}
          </ul>
        </details>
        <DetailList title="Classification matches" items={(file.classification?.matches ?? []).map((match) => `${match.rule_id}: ${match.description}`)} />
        <DetailList title="Context evidence" items={(file.classification?.context?.evidence ?? file.context?.evidence ?? []).map((match) => `${match.rule_id}: ${match.description}`)} />
        {file.previous_classification && (
          <DetailList title="Previous classification" items={[`Kind: ${titleCase(file.previous_classification.primary_kind)}`, `Areas: ${compactList(file.previous_classification.areas ?? [], 4) || "None"}`]} />
        )}
        <DetailList title="Limitations" items={file.limitations ?? []} />
      </aside>
    </div>
  );
}

function ContextDetails({ context }) {
  const items = [
    context.framework && `Framework: ${titleCase(context.framework)}`,
    context.component_role && `Role: ${titleCase(context.component_role)}`,
    (context.route_context ?? []).length > 0 && `Route: ${compactList(context.route_context, 4)}`,
    (context.access_context ?? []).length > 0 && `Access context: ${compactList(context.access_context, 4)}`,
    (context.domains ?? []).length > 0 && `Domains: ${compactList(context.domains, 4)}`,
    (context.areas ?? []).length > 0 && `Context areas: ${compactList(context.areas, 6)}`,
    context.is_dynamic_route && "Dynamic route: yes",
    context.is_user_facing && "User-facing path convention: yes",
    context.classification_confidence && `Confidence: ${titleCase(context.classification_confidence)}`,
  ].filter(Boolean);
  return <DetailList title="File context" items={items} />;
}

function relatedThreadIds(file) {
  return [...new Set((file.factors ?? []).flatMap((factor) => factor.related_thread_ids ?? []))];
}

function DetailList({ title, items }) {
  return (
    <section className="detail-section">
      <h3>{title}</h3>
      {items.length > 0 ? (
        <ul>{items.map((item) => <li key={item}>{item}</li>)}</ul>
      ) : (
        <p className="muted">None observed.</p>
      )}
    </section>
  );
}
