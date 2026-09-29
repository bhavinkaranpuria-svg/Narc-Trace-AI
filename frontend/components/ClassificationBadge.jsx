"use client";

const LABELS = {
  positive: "Positive",
  negative: "Negative",
  inconclusive: "Inconclusive",
  cannot_determine: "Cannot determine",
  VERIFIED: "Verified",
  "INTEGRITY FAILED": "Integrity failed",
};

export default function ClassificationBadge({ value, size = "md" }) {
  const cls =
    value === "VERIFIED" ? "verified" :
    value === "INTEGRITY FAILED" ? "failed" :
    value || "neutral";
  return (
    <span className={`badge ${cls}`} style={size === "lg" ? { fontSize: 14, padding: "6px 14px" } : undefined}>
      <span className="dot" />
      {LABELS[value] || value || "—"}
    </span>
  );
}
