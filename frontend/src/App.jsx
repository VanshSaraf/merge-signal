import { Route, Routes } from "react-router-dom";

import { HealthStatus } from "./components/HealthStatus.jsx";
import { useTheme } from "./hooks/useTheme.js";
import { HomePage } from "./pages/HomePage.jsx";
import { NotFoundPage } from "./pages/NotFoundPage.jsx";

export function App() {
  const { theme, toggleTheme } = useTheme();

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="brand">
          <h1>MergeSignal</h1>
          <p>Deterministic pull-request risk and merge-readiness analysis</p>
        </div>
        <div className="header-actions">
          <HealthStatus compact />
          <button className="theme-toggle" type="button" onClick={toggleTheme} aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}>
            {theme === "dark" ? "Light" : "Dark"}
          </button>
        </div>
      </header>

      <main>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </main>
    </div>
  );
}
