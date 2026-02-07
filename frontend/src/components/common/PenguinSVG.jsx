export default function PenguinSVG({ size = 24, className = '', style = {} }) {
  return (
    <svg width={size} height={size * 1.2} viewBox="0 0 40 48" className={className} style={style} fill="none">
      <ellipse cx="20" cy="28" rx="14" ry="18" fill="#1e293b" />
      <ellipse cx="20" cy="30" rx="9" ry="13" fill="#f8fafc" />
      <circle cx="20" cy="14" r="10" fill="#1e293b" />
      <circle cx="17" cy="12" r="2.5" fill="white" />
      <circle cx="23" cy="12" r="2.5" fill="white" />
      <circle cx="17.5" cy="12.5" r="1.2" fill="#1e293b" />
      <circle cx="23.5" cy="12.5" r="1.2" fill="#1e293b" />
      <ellipse cx="20" cy="17" rx="2.5" ry="1.5" fill="#f97316" />
      <ellipse cx="15" cy="45" rx="4" ry="2" fill="#f97316" />
      <ellipse cx="25" cy="45" rx="4" ry="2" fill="#f97316" />
    </svg>
  );
}
