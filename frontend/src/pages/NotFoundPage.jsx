import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <section className="page-stack">
      <p className="eyebrow">404</p>
      <h2>Page not found</h2>
      <p>The requested MergeSignal page does not exist.</p>
      <Link className="button-link" to="/">Return home</Link>
    </section>
  );
}
