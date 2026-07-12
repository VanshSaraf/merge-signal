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
      <path className="brand-mark__halo" d="M8.5 29.5c0-9.4 7.2-17 15.5-17s15.5 7.6 15.5 17S32.8 43 24 43 8.5 38.9 8.5 29.5Z" />
      <path className="brand-mark__fill" d="M24 41.5c8.1 0 14.5-5.1 14.5-12.3 0-4.6-2.6-8.5-6.6-10.7L36.3 6 31 3.4l-6.4 13h-1.2L17 3.4 11.7 6l4.4 12.5c-4 2.2-6.6 6.1-6.6 10.7 0 7.2 6.4 12.3 14.5 12.3Z" />
      <path className="brand-mark__line" d="M18.2 27.8h11.6M19.5 32.5h9M19.8 22.4c1.1-1 2.5-1.5 4.2-1.5s3.1.5 4.2 1.5M16.7 8.4l4.4 9.5M31.3 8.4l-4.4 9.5" />
      <path className="brand-mark__accent" d="M14.7 14.2h7.9M25.4 14.2h7.9M32.3 14.2l-2.7-2.8M32.3 14.2 29.6 17M17 36.5c4.4 2.4 9.6 2.4 14 0" />
      <path className="brand-mark__signal" d="M37.2 20.3c2 1.8 3.2 4.3 3.2 7s-1.2 5.2-3.2 7M10.8 20.3c-2 1.8-3.2 4.3-3.2 7s1.2 5.2 3.2 7" />
      <circle className="brand-mark__node" cx="18.8" cy="26.2" r="1.2" />
      <circle className="brand-mark__node" cx="29.2" cy="26.2" r="1.2" />
    </svg>
  );
}
