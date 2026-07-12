import { useEffect, useState } from "react";

import { getHealth } from "../services/healthApi.js";

export function HealthStatus({ compact = false }) {
  const [state, setState] = useState({ status: "loading", data: null, error: null });

  useEffect(() => {
    let isMounted = true;

    getHealth()
      .then((data) => {
        if (isMounted) {
          setState({ status: "success", data, error: null });
        }
      })
      .catch((error) => {
        if (isMounted) {
          setState({ status: "error", data: null, error });
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  if (state.status === "loading") {
    return <section className={`status-panel ${compact ? "status-panel--compact" : ""}`} aria-live="polite">Checking backend health...</section>;
  }

  if (state.status === "error") {
    return (
      <section className={`status-panel status-panel--error ${compact ? "status-panel--compact" : ""}`} aria-live="polite">
        Backend unavailable{compact ? "" : `: ${state.error.message}`}
      </section>
    );
  }

  return (
    <section className={`status-panel status-panel--success ${compact ? "status-panel--compact" : ""}`} aria-live="polite">
      <span className="status-dot" aria-hidden="true" />
      {compact ? "Backend online" : `Backend is ${state.data.status} for ${state.data.service} in ${state.data.environment}.`}
    </section>
  );
}
