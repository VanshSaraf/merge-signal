import { HealthStatus } from "../HealthStatus.jsx";
import { PipelineSchematic } from "./PipelineSchematic.jsx";

const PR_URL_PATTERN = /^https:\/\/github\.com\/[^/\s]+\/[^/\s]+\/pull\/\d+\/?$/i;

export function AnalysisCommand({ value, onChange, onSubmit, onCancel, isLoading, validationError, compact = false }) {
  return (
    <form className={["analysis-command", compact ? "analysis-command--compact" : ""].filter(Boolean).join(" ")} onSubmit={onSubmit} noValidate>
      <div className="analysis-command__header">
        <div>
          <p className="eyebrow">{compact ? "Analyze another PR" : "Analyze a public pull request"}</p>
          <h2>{compact ? "Start with a new GitHub PR URL" : "Start with a GitHub PR URL"}</h2>
        </div>
        {!compact && <HealthStatus compact />}
      </div>

      <div className="form-row">
        <label className="input-label" htmlFor={compact ? "pull-request-url-compact" : "pull-request-url"}>
          GitHub PR URL
        </label>
        <div className="command-input">
          <span aria-hidden="true">pr</span>
          <input
            id={compact ? "pull-request-url-compact" : "pull-request-url"}
            name="pull-request-url"
            type="url"
            value={value}
            onChange={(event) => onChange(event.target.value)}
            placeholder="https://github.com/owner/repository/pull/123"
            aria-describedby={`${compact ? "pull-request-help-compact" : "pull-request-help"} ${compact ? "pull-request-error-compact" : "pull-request-error"}`}
            disabled={isLoading}
          />
        </div>
        <p id={compact ? "pull-request-help-compact" : "pull-request-help"} className="input-help">
          Public GitHub pull requests only.
        </p>
        {validationError && (
          <p id={compact ? "pull-request-error-compact" : "pull-request-error"} className="input-error" role="alert">
            {validationError}
          </p>
        )}
      </div>

      <div className="form-actions">
        <button className="button button--primary" type="submit" disabled={isLoading}>
          {isLoading ? "Analyzing..." : compact ? "Analyze" : "Analyze pull request"}
        </button>
        {isLoading && (
          <button className="button button--secondary" type="button" onClick={onCancel}>
            Cancel
          </button>
        )}
      </div>
      {!compact && (
        <div className="analysis-command__pipeline">
          <PipelineSchematic />
        </div>
      )}
    </form>
  );
}

export function validatePullRequestUrl(value) {
  if (!value.trim()) {
    return "Enter a public GitHub pull-request URL.";
  }
  if (!PR_URL_PATTERN.test(value.trim())) {
    return "Use the format https://github.com/owner/repository/pull/123.";
  }
  return "";
}
