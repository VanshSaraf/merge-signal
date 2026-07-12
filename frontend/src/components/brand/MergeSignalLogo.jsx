export function MergeSignalLogo({ size = 32, decorative = false, className = "" }) {
  const ariaProps = decorative ? { "aria-hidden": "true" } : { role: "img", "aria-label": "MergeSignal rabbit mark" };

  return (
    <svg
      className={["brand-mark", className].filter(Boolean).join(" ")}
      height={size}
      viewBox="0 0 48 48"
      width={size}
      xmlns="http://www.w3.org/2000/svg"
      {...ariaProps}
    >
      <path className="brand-mark__fill" d="M24 42c9 0 16-5.7 16-13.1 0-5.2-3.4-9.7-8.5-11.8L36 5.7 29.1 3l-5 11.2h-.2L18.9 3 12 5.7l4.5 11.4C11.4 19.2 8 23.7 8 28.9 8 36.3 15 42 24 42Z" />
      <path className="brand-mark__line" d="M17 27.5h14M18.5 32.5h11M19.8 22.5c1.1-1 2.5-1.5 4.2-1.5s3.1.5 4.2 1.5M17.2 8.6l4.1 9M30.8 8.6l-4.1 9" />
      <path className="brand-mark__accent" d="M16 13.8h7.8M24.2 13.8H32M31.6 13.8l-2.7-2.7M31.6 13.8l-2.7 2.7" />
      <circle className="brand-mark__line" cx="18.6" cy="25.8" r="1" />
      <circle className="brand-mark__line" cx="29.4" cy="25.8" r="1" />
    </svg>
  );
}
