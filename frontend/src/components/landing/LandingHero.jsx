import { MergeSignalLogo } from "../brand/MergeSignalLogo.jsx";
import { AnalysisCommand } from "./AnalysisCommand.jsx";

const trustStatements = [
  "No execution of analyzed code",
  "Evidence-backed decisions",
  "Deterministic review guidance",
];

export function LandingHero({ value, onChange, onSubmit, onCancel, isLoading, validationError }) {
  return (
    <section className="landing-hero" aria-labelledby="landing-heading">
      <div className="landing-hero__copy">
        <div className="hero-kicker">
          <MergeSignalLogo size={28} decorative />
          <p className="eyebrow">Deterministic pull request intelligence</p>
        </div>
        <h1 id="landing-heading">
          Review the <span>right changes</span>
          <br />
          before you merge.
        </h1>
        <p className="hero-lede">
          MergeSignal turns visible GitHub pull-request evidence into clear merge readiness,
          review priorities, and traceable next steps.
        </p>
        <ul className="trust-list" aria-label="MergeSignal trust statements">
          {trustStatements.map((statement) => (
            <li key={statement}>{statement}</li>
          ))}
        </ul>
      </div>

      <div className="landing-hero__workbench">
        <AnalysisCommand
          value={value}
          onChange={onChange}
          onSubmit={onSubmit}
          onCancel={onCancel}
          isLoading={isLoading}
          validationError={validationError}
        />
      </div>
    </section>
  );
}
