const LEVEL_STYLES = {
  LOW: { bg: "var(--signal-teal-soft)", fg: "var(--signal-teal)" },
  MODERATE: { bg: "var(--signal-amber-soft)", fg: "#a85d20" },
  HIGH: { bg: "var(--signal-amber-soft)", fg: "var(--signal-amber)" },
  CRITICAL: { bg: "var(--signal-rust-soft)", fg: "var(--signal-rust)" },
};

export default function RiskBadge({ level }) {
  const style = LEVEL_STYLES[level] || LEVEL_STYLES.MODERATE;
  return (
    <span
      className="risk-badge"
      style={{ background: style.bg, color: style.fg }}
    >
      {level}
    </span>
  );
}
