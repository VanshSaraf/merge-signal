import { HealthStatus } from "../HealthStatus.jsx";
import { MergeSignalLogo } from "../brand/MergeSignalLogo.jsx";

export function AppHeader({ theme, onToggleTheme }) {
  const nextTheme = theme === "dark" ? "light" : "dark";

  return (
    <header className="app-header">
      <a className="app-brand" href="/" aria-label="MergeSignal home">
        <MergeSignalLogo size={34} />
        <div>
          <h1>MergeSignal</h1>
          <p>Deterministic PR risk and readiness</p>
        </div>
      </a>
      <div className="header-actions">
        <HealthStatus compact />
        <button className="theme-toggle" type="button" onClick={onToggleTheme} aria-label={`Switch to ${nextTheme} theme`}>
          <span aria-hidden="true">{theme === "dark" ? "Light" : "Dark"}</span>
        </button>
      </div>
    </header>
  );
}
