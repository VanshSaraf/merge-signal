const PR_URL_PATTERN = /^https:\/\/github\.com\/[^/\s]+\/[^/\s]+\/pull\/\d+\/?$/i;

export function AnalysisForm({ value, onChange, onSubmit, onCancel, isLoading, validationError }) {
  return (
    <form className="analysis-form" onSubmit={onSubmit}>
      <div className="form-copy">
        <p className="eyebrow">Pull-request snapshot</p>
        <h2>Analyze merge readiness from observable evidence.</h2>
        <p>Paste a public GitHub pull-request URL. The backend remains the source of truth for strict validation.</p>
      </div>
      <div className="form-row">
        <label className="input-label" htmlFor="pull-request-url">
          GitHub PR URL
        </label>
        <input
          id="pull-request-url"
          name="pull-request-url"
          type="url"
          value={value}
          onChange={(event) => onChange(event.target.value)}
          placeholder="https://github.com/owner/repository/pull/123"
          aria-describedby="pull-request-help pull-request-error"
          disabled={isLoading}
        />
        <p id="pull-request-help" className="input-help">
          Example: https://github.com/owner/repository/pull/123
        </p>
        {validationError && (
          <p id="pull-request-error" className="input-error" role="alert">
            {validationError}
          </p>
        )}
      </div>
      <div className="form-actions">
        <button className="button button--primary" type="submit" disabled={isLoading}>
          {isLoading ? "Analyzing..." : "Analyze"}
        </button>
        {isLoading && (
          <button className="button button--secondary" type="button" onClick={onCancel}>
            Cancel
          </button>
        )}
      </div>
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
