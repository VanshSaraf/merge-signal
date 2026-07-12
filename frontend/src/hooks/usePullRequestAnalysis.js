import { useRef, useState } from "react";

import { fetchPullRequestSnapshot } from "../api/pullRequests.js";

export function usePullRequestAnalysis() {
  const abortControllerRef = useRef(null);
  const [state, setState] = useState({
    status: "idle",
    snapshot: null,
    error: null,
    lastUrl: "",
  });

  async function analyze(url) {
    abortControllerRef.current?.abort();
    const controller = new AbortController();
    abortControllerRef.current = controller;
    setState({ status: "loading", snapshot: null, error: null, lastUrl: url });

    try {
      const snapshot = await fetchPullRequestSnapshot(url, { signal: controller.signal });
      setState({ status: "success", snapshot, error: null, lastUrl: url });
    } catch (error) {
      if (error.name === "AbortError") {
        setState((current) => ({ ...current, status: "idle", error: null }));
        return;
      }
      setState({ status: "error", snapshot: null, error, lastUrl: url });
    } finally {
      if (abortControllerRef.current === controller) {
        abortControllerRef.current = null;
      }
    }
  }

  function cancel() {
    abortControllerRef.current?.abort();
  }

  return {
    ...state,
    analyze,
    cancel,
    isLoading: state.status === "loading",
  };
}
