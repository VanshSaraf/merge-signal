import { AnalysisCommand, validatePullRequestUrl } from "../landing/AnalysisCommand.jsx";

export function AnalysisForm({ value, onChange, onSubmit, onCancel, isLoading, validationError }) {
  return (
    <AnalysisCommand
      value={value}
      onChange={onChange}
      onSubmit={onSubmit}
      onCancel={onCancel}
      isLoading={isLoading}
      validationError={validationError}
    />
  );
}

export { validatePullRequestUrl };
