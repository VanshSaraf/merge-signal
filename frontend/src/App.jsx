import { Route, Routes } from "react-router-dom";

import { AppHeader } from "./components/layout/AppHeader.jsx";
import { useTheme } from "./hooks/useTheme.js";
import { HomePage } from "./pages/HomePage.jsx";
import { NotFoundPage } from "./pages/NotFoundPage.jsx";

export function App() {
  const { theme, toggleTheme } = useTheme();

  return (
    <div className="app-shell">
      <AppHeader theme={theme} onToggleTheme={toggleTheme} />

      <main>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </main>
    </div>
  );
}
