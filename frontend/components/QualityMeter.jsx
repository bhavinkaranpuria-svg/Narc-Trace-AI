"use client";

function colorFor(score) {
  if (score >= 85) return "var(--accent)";
  if (score >= 60) return "var(--warn)";
  return "var(--danger)";
}

export default function QualityMeter({ label, score, hint }) {
  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
        <span className="field-label">{label}</span>
        <span className="mono" style={{ fontSize: 12.5, color: colorFor(score) }}>{score}/100</span>
      </div>
      <div className="meter-track">
        <div className="meter-fill" style={{ width: `${score}%`, background: colorFor(score) }} />
      </div>
      {hint && <div style={{ fontSize: 12, color: "var(--text-faint)", marginTop: 5 }}>{hint}</div>}
    </div>
  );
}
