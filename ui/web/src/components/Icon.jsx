// Icons drawn with the same stroke paths as the design files.
const PATHS = {
  doc: ['M6 3h8l4 4v14H6z', 'M14 3v4h4', 'M9 13h6M9 17h4'],
  upload: ['M12 16V4M7 9l5-5 5 5M5 20h14'],
  check: ['M5 12l5 5 9-10'],
  trash: ['M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3'],
  chevron: ['M6 9l6 6 6-6'],
  send: ['M5 12h14M13 6l6 6-6 6'],
  close: ['M6 6l12 12M18 6L6 18'],
  copy: ['M9 9h10v11H9z', 'M5 15V4h10'],
  alert: ['M12 8v5M12 16.5v.5', 'M10.3 4L2.8 17a2 2 0 0 0 1.7 3h15a2 2 0 0 0 1.7-3L13.7 4a2 2 0 0 0-3.4 0z'],
  info: ['M12 11v5M12 8v.5', 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18z'],
};

export default function Icon({ name, size = 20, stroke = 'currentColor', width = 1.8 }) {
  if (name === 'stop') {
    return (
      <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true">
        <rect x="6" y="6" width="12" height="12" rx="2" fill="currentColor" />
      </svg>
    );
  }
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke={stroke}
      strokeWidth={width}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {(PATHS[name] ?? []).map((d, i) => (
        <path key={i} d={d} />
      ))}
    </svg>
  );
}
