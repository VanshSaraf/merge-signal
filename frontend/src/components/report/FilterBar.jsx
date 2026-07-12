import { titleCase } from "../../utils/formatting.js";

export function FilterBar({ children, onClear }) {
  return (
    <div className="filter-bar">
      <div className="filter-grid">{children}</div>
      <button className="button button--secondary" type="button" onClick={onClear}>
        Clear filters
      </button>
    </div>
  );
}

export function TextFilter({ id, label, value, onChange, placeholder }) {
  return (
    <label className="filter-field" htmlFor={id}>
      <span>{label}</span>
      <input id={id} value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} />
    </label>
  );
}

export function SelectFilter({ id, label, value, onChange, options }) {
  return (
    <label className="filter-field" htmlFor={id}>
      <span>{label}</span>
      <select id={id} value={value} onChange={(event) => onChange(event.target.value)}>
        <option value="">All</option>
        {options.map((option) => (
          <option value={option} key={option}>
            {titleCase(option)}
          </option>
        ))}
      </select>
    </label>
  );
}
