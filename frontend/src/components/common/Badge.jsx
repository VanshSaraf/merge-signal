import { titleCase } from "../../utils/formatting.js";

export function Badge({ children, tone = "neutral" }) {
  return <span className={`badge badge--${tone}`}>{children ?? titleCase(tone)}</span>;
}
