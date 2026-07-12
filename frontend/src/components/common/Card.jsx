export function Card({ title, eyebrow, action, children, className = "" }) {
  return (
    <section className={["card", className].filter(Boolean).join(" ")}>
      {(title || eyebrow || action) && (
        <div className="card__header">
          <div>
            {eyebrow && <p className="eyebrow">{eyebrow}</p>}
            {title && <h2>{title}</h2>}
          </div>
          {action}
        </div>
      )}
      {children}
    </section>
  );
}
