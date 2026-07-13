import { HealthStatus } from "../HealthStatus.jsx";
import { MergeSignalLogo } from "../brand/MergeSignalLogo.jsx";

export function AppHeader({ theme, onToggleTheme }) {
  const nextTheme = theme === "dark" ? "light" : "dark";

  return (
    <header className="app-header">
      <a className="app-brand" href="/" aria-label="MergeSignal home">
        <MergeSignalLogo size={34} />
        <div>
          <span className="app-brand__name">MergeSignal</span>
          <p>Pull request risk and merge readiness</p>
        </div>
      </a>
      <div className="header-actions">
        <nav className="header-nav" aria-label="Project links">
          <a href="https://github.com/VanshSaraf/merge-signal" target="_blank" rel="noreferrer">
            GitHub
          </a>
          <a href="https://github.com/VanshSaraf/merge-signal/blob/main/docs/frontend.md" target="_blank" rel="noreferrer">
            Docs
          </a>
        </nav>
        <HealthStatus compact />
        <button className="theme-toggle" type="button" onClick={onToggleTheme} aria-label={`Switch to ${nextTheme} theme`}>
          <span aria-hidden="true">{theme === "dark" ? "Light" : "Dark"}</span>
        </button>
      </div>
    </header>
  );
}
