import { useRef, useState } from "react";

import { fetchPullRequestSnapshot } from "../api/pullRequests.js";

export function usePullRequestAnalysis() {
  const abortControllerRef = useRef(null);
  const [state, setState] = useState({
    status: "idle",
    snapshot: null,
    previousSnapshot: null,
    error: null,
    lastUrl: "",
  });

  async function analyze(url) {
    abortControllerRef.current?.abort();
    const controller = new AbortController();
    abortControllerRef.current = controller;
    setState((current) => ({
      status: "loading",
      snapshot: null,
      previousSnapshot: current.snapshot ?? current.previousSnapshot,
      error: null,
      lastUrl: url,
    }));

    try {
      const snapshot = await fetchPullRequestSnapshot(url, { signal: controller.signal });
      setState({ status: "success", snapshot, previousSnapshot: null, error: null, lastUrl: url });
    } catch (error) {
      if (error.name === "AbortError") {
        setState((current) => ({ ...current, status: "idle", error: null }));
        return;
      }
      setState((current) => ({ status: "error", snapshot: null, previousSnapshot: current.previousSnapshot, error, lastUrl: url }));
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
