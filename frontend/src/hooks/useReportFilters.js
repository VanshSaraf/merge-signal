import { useMemo, useState } from "react";

import { filterActions, filterFiles, filterSignals, sortFiles } from "../utils/report.js";

const initialFileFilters = { query: "", level: "", kind: "", area: "", status: "", sort: "rank" };
const initialSignalFilters = { severity: "", category: "", fileQuery: "" };
const initialActionFilters = { priority: "", category: "", fileQuery: "" };

export function useReportFilters(snapshot) {
  const [fileFilters, setFileFilters] = useState(initialFileFilters);
  const [signalFilters, setSignalFilters] = useState(initialSignalFilters);
  const [actionFilters, setActionFilters] = useState(initialActionFilters);

  const files = snapshot.ranked_files ?? [];
  const signals = snapshot.signals ?? [];
  const actions = snapshot.review_actions ?? [];

  const filteredFiles = useMemo(
    () => sortFiles(filterFiles(files, fileFilters), fileFilters.sort),
    [files, fileFilters],
  );
  const filteredSignals = useMemo(
    () => filterSignals(signals, signalFilters),
    [signals, signalFilters],
  );
  const filteredActions = useMemo(
    () => filterActions(actions, actionFilters),
    [actions, actionFilters],
  );

  return {
    fileFilters,
    setFileFilters,
    resetFileFilters: () => setFileFilters(initialFileFilters),
    filteredFiles,
    signalFilters,
    setSignalFilters,
    resetSignalFilters: () => setSignalFilters(initialSignalFilters),
    filteredSignals,
    actionFilters,
    setActionFilters,
    resetActionFilters: () => setActionFilters(initialActionFilters),
    filteredActions,
  };
}
