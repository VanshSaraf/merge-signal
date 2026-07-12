import { useEffect, useState } from "react";

import { getHealth } from "../services/healthApi.js";

export function HealthStatus() {
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
    return <section className="status-panel" aria-live="polite">Checking backend health...</section>;
  }

  if (state.status === "error") {
    return (
      <section className="status-panel status-panel--error" aria-live="polite">
        Backend health unavailable: {state.error.message}
      </section>
    );
  }

  return (
    <section className="status-panel status-panel--success" aria-live="polite">
      <span className="status-dot" aria-hidden="true" />
      Backend is {state.data.status} for {state.data.service} in {state.data.environment}.
    </section>
  );
}
