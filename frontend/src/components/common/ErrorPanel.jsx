import { friendlyError } from "../../utils/status.js";

export function ErrorPanel({ error, onRetry }) {
  const message = friendlyError(error);

  return (
    <section className="error-panel" aria-live="polite">
      <div>
        <p className="eyebrow">Analysis interrupted</p>
        <h2>{message.title}</h2>
        <p>{message.detail}</p>
      </div>
      {onRetry && (
        <button className="button button--secondary" type="button" onClick={onRetry}>
          Retry
        </button>
      )}
    </section>
  );
}
