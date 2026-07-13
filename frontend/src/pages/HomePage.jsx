import { useState } from "react";

import { AnalysisDashboard } from "../components/analysis/AnalysisDashboard.jsx";
import { ErrorPanel } from "../components/common/ErrorPanel.jsx";
import { SkeletonDashboard } from "../components/common/Skeleton.jsx";
import { AnalysisCommand, validatePullRequestUrl } from "../components/landing/AnalysisCommand.jsx";
import { CapabilityOverview } from "../components/landing/CapabilityOverview.jsx";
import { LandingHero } from "../components/landing/LandingHero.jsx";
import { TrustSection } from "../components/landing/TrustSection.jsx";
import { usePullRequestAnalysis } from "../hooks/usePullRequestAnalysis.js";

export function HomePage() {
  const [url, setUrl] = useState("");
  const [validationError, setValidationError] = useState("");
  const analysis = usePullRequestAnalysis();

  function submitAnalysis(event) {
    event.preventDefault();
    const error = validatePullRequestUrl(url);
    setValidationError(error);
    if (error || analysis.isLoading) {
      return;
    }
    analysis.analyze(url.trim());
  }

  function retryAnalysis() {
    if (analysis.lastUrl) {
      analysis.analyze(analysis.lastUrl);
    }
  }

  return (
    <div className="page-stack analysis-page">
      {analysis.status === "success" ? (
        <div className="report-entry-bar" aria-label="Analyze another pull request">
          <AnalysisCommand
            value={url}
            onChange={(nextValue) => {
              setUrl(nextValue);
              if (validationError) {
                setValidationError("");
              }
            }}
            onSubmit={submitAnalysis}
            onCancel={analysis.cancel}
            isLoading={analysis.isLoading}
            validationError={validationError}
            compact
          />
        </div>
      ) : (
        <>
          <LandingHero
            value={url}
            onChange={(nextValue) => {
              setUrl(nextValue);
              if (validationError) {
                setValidationError("");
              }
            }}
            onSubmit={submitAnalysis}
            onCancel={analysis.cancel}
            isLoading={analysis.isLoading}
            validationError={validationError}
          />
          {analysis.status === "idle" && (
            <>
              <CapabilityOverview />
              <TrustSection />
            </>
          )}
        </>
      )}

      {analysis.status === "loading" && <SkeletonDashboard />}
      {analysis.status === "error" && <ErrorPanel error={analysis.error} onRetry={retryAnalysis} />}
      {analysis.status === "success" && <AnalysisDashboard snapshot={analysis.snapshot} />}
    </div>
  );
}
