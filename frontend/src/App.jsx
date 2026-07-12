import { NavLink, Route, Routes } from "react-router-dom";

import { HomePage } from "./pages/HomePage.jsx";
import { NotFoundPage } from "./pages/NotFoundPage.jsx";

export function App() {
  return (
    <div className="app-shell">
      <header className="app-header">
        <div>
          <p className="eyebrow">Pull-request risk intelligence</p>
          <h1>MergeSignal</h1>
        </div>
        <nav aria-label="Primary navigation">
          <NavLink to="/">Home</NavLink>
        </nav>
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
