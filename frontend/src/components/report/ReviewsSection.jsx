import { useState } from "react";

import { Badge } from "../common/Badge.jsx";
import { Card } from "../common/Card.jsx";
import { titleCase } from "../../utils/formatting.js";
import { plainReviewText, reviewCountLabel, safeHttpUrl } from "../../utils/report.js";
import { toneForLevel } from "../../utils/status.js";

export function ReviewsSection({ reviewContext }) {
  const context = reviewContext ?? {};
  const threads = context.threads ?? [];
  const [expandedThreadId, setExpandedThreadId] = useState(null);

  return (
    <div className="report-section">
      <Card title="Reviews" eyebrow={titleCase(context.visibility ?? "complete")}>
        <p className="section-note">Observable GitHub review state only. MergeSignal does not determine whether conversations are resolved yet.</p>
        <ReviewSummary context={context} />
        {context.warnings?.length > 0 && <DisclosureList title="Review-context warnings" items={context.warnings} />}
      </Card>

      <Card title="Inline conversations" eyebrow={reviewCountLabel(threads.length, context.visibility === "unavailable")}>
        {threads.length === 0 ? (
          <p className="empty-result">{emptyMessage(context)}</p>
        ) : (
          <div className="stack-list report-list review-thread-list">
            {threads.map((thread) => (
              <ReviewThreadRow
                expanded={expandedThreadId === thread.id}
                key={thread.id}
                onToggle={() => setExpandedThreadId(expandedThreadId === thread.id ? null : thread.id)}
                thread={thread}
              />
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}

function ReviewSummary({ context }) {
  const concern = context.concern_summary ?? {};
  const items = [
    ["Needs attention", concern.needing_attention_count ?? 0],
    ["Awaiting response", concern.awaiting_author_response_count ?? 0],
    ["Author replied", concern.author_replied_count ?? 0],
    ["Author response needs verification", concern.author_described_changes_count ?? 0],
    ["Author says addressed", concern.author_claimed_addressed_count ?? 0],
    ["Reviewer follow-up", concern.reviewer_follow_up_count ?? 0],
    ["Outdated", concern.outdated_count ?? 0],
    ["Latest change requests", concern.active_latest_change_request_count ?? context.changes_requested_count ?? 0],
  ].filter(([, value]) => value > 0);
  const visibleItems = items.length ? items : [["Inline conversations", context.thread_count ?? 0]];

  return (
    <>
      <section className="review-summary-grid" aria-label="Observable review-state summary">
        {visibleItems.map(([label, value]) => (
          <div className="metric" key={label}><span>{label}</span><strong>{value}</strong></div>
        ))}
      </section>
      {context.latest_reviewer_states?.length > 0 && (
        <div className="latest-reviewer-states" aria-label="Latest observable reviewer states">
          {context.latest_reviewer_states.map((item) => (
            <span className="reviewer-state" key={`${item.reviewer_login}-${item.review_id}`}>
              <strong>{item.reviewer_login}</strong>
              <Badge tone={reviewStateTone(item.state)}>{reviewStateLabel(item.state)}</Badge>
            </span>
          ))}
        </div>
      )}
    </>
  );
}

function ReviewThreadRow({ thread, expanded, onToggle }) {
  const root = thread.root_comment ?? {};
  const replies = thread.replies ?? [];
  const lifecycle = thread.lifecycle ?? {};
  const location = [thread.path, lineLabel(thread)].filter(Boolean).join(":");
  const githubUrl = safeHttpUrl(thread.html_url);
  const excerpt = reviewDisplayText(root.body_excerpt) || "No comment text available.";

  return (
    <article className="report-item review-thread-row">
      <div className="item-heading">
        <Badge tone={attentionTone(lifecycle.attention_state)}>{attentionLabel(lifecycle.attention_state)}</Badge>
        <Badge>{root.reviewer_login ?? "Unknown"}</Badge>
        {thread.is_orphan_reply && <Badge tone="warning">Orphan reply</Badge>}
        <span>{replies.length} {replies.length === 1 ? "reply" : "replies"}</span>
        {lifecycle.has_author_reply && <span>Author responded</span>}
        {lifecycle.has_reviewer_follow_up && <span>Reviewer followed up</span>}
      </div>
      <h3>{location || "Inline review conversation"}</h3>
      <p className="review-excerpt">{excerpt}</p>
      <button className="button-link action-details-toggle" type="button" onClick={onToggle} aria-expanded={expanded}>
        {expanded ? "Hide conversation" : "View conversation"}
      </button>
      {expanded && (
        <div className="technical-details">
          <div className="review-lifecycle-note">
            <strong>{attentionLabel(lifecycle.attention_state)}</strong>
            <p>{lifecycle.summary ?? "Lifecycle evidence is unavailable."}</p>
            <small>MergeSignal cannot verify that the code change resolves this concern.</small>
          </div>
          <div className="review-timeline" aria-label="Review conversation timeline">
            <CommentBlock comment={root} label="Root comment" />
            {replies.map((reply) => <CommentBlock comment={reply} key={reply.id} label="Reply" />)}
          </div>
          {githubUrl && <a className="button button--secondary button--compact" href={githubUrl} target="_blank" rel="noreferrer">Open on GitHub</a>}
          <DisclosureList title="Participants" items={thread.participant_logins ?? []} />
          <details className="mini-list">
            <summary>Technical details</summary>
            <ul>
              <li><code>{thread.id}</code></li>
              <li>Root comment ID: <code>{thread.root_comment_id}</code></li>
              {root.pull_request_review_id && <li>Review ID: <code>{root.pull_request_review_id}</code></li>}
              {(lifecycle.provenance ?? []).map((fact) => (
                <li key={`${fact.source}-${fact.comment_id ?? fact.review_id ?? fact.detail}`}>
                  {fact.source}: {fact.detail}
                </li>
              ))}
            </ul>
          </details>
        </div>
      )}
    </article>
  );
}

function CommentBlock({ comment, label }) {
  return (
    <div className="review-comment">
      <strong>{label} · {comment.reviewer_login ?? "Unknown"}</strong>
      <p>{reviewDisplayText(comment.body_excerpt) || "No comment text available."}</p>
      <small>{formatTimestamp(comment.created_at)}</small>
    </div>
  );
}

function reviewDisplayText(value) {
  return plainReviewText(value)
    .replace(/^Summary:\s*(?:\n\s*)+/gim, "Summary: ")
    .replace(/^Summary:\s*$/gim, "")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function DisclosureList({ title, items }) {
  if (!items?.length) return null;
  return <div className="mini-list"><strong>{title}</strong><ul>{items.map((item) => <li key={item}>{item}</li>)}</ul></div>;
}

function lineLabel(thread) {
  if (thread.start_line && thread.line && thread.start_line !== thread.line) return `${thread.start_line}-${thread.line}`;
  if (thread.line) return `L${thread.line}`;
  return null;
}

function formatTimestamp(value) {
  if (!value) return "Timestamp unavailable";
  try {
    return new Intl.DateTimeFormat("en", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
  } catch {
    return value;
  }
}

function reviewStateLabel(state) {
  return titleCase(String(state ?? "unknown").replaceAll("_", " "));
}

function reviewStateTone(state) {
  return {
    approved: "success",
    changes_requested: "danger",
    commented: "info",
    dismissed: "warning",
    pending: "warning",
  }[state] ?? toneForLevel(state);
}

function attentionLabel(state) {
  return {
    awaiting_author_response: "Needs author response",
    author_replied: "Author replied",
    author_described_changes: "Author response needs verification",
    author_claimed_addressed: "Author says addressed",
    reviewer_follow_up: "Reviewer followed up",
    outdated: "Outdated conversation",
    informational: "Informational",
    unknown: "State unknown",
  }[state] ?? "State unknown";
}

function attentionTone(state) {
  return {
    awaiting_author_response: "warning",
    author_replied: "info",
    author_described_changes: "warning",
    author_claimed_addressed: "warning",
    reviewer_follow_up: "danger",
    outdated: "neutral",
    informational: "neutral",
    unknown: "warning",
  }[state] ?? "warning";
}

function emptyMessage(context) {
  if (context.visibility === "unavailable") return "Review context was unavailable from GitHub.";
  if (context.visibility === "partial") return "No inline conversations were available in the retrieved partial review context.";
  return "No inline review conversations were observed.";
}
