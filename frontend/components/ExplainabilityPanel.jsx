"use client";
import ClassificationBadge from "./ClassificationBadge";
import QualityMeter from "./QualityMeter";

function CheckRow({ ok, label, detail }) {
  return (
    <div className="row" style={{ alignItems: "center", gap: 10, padding: "6px 0" }}>
      <span style={{ color: ok ? "var(--accent)" : "var(--danger)", fontSize: 15, width: 16 }}>
        {ok ? "✓" : "✕"}
      </span>
      <span style={{ fontSize: 13.5, color: "var(--text)" }}>{label}</span>
      {detail && <span style={{ fontSize: 12.5, color: "var(--text-faint)", marginLeft: "auto" }}>{detail}</span>}
    </div>
  );
}

export default function ExplainabilityPanel({ analysis }) {
  if (!analysis) return null;
  const { quality, card, calibration, classification, consensus, officer_vs_ai } = analysis;
  const q = quality;

  return (
    <div>
      <div className="panel">
        <div className="panel-title">Analysis basis</div>
        <QualityMeter label="Image quality" score={q.quality_score} hint={q.verdict} />
        <div className="divider" />
        <CheckRow ok={q.blur_ok} label="Sharpness"
          detail={`Laplacian var ${q.blur_score.toFixed(0)}`} />
        <CheckRow ok={q.glare_ok} label="No glare / blowout"
          detail={`${(q.glare_fraction * 100).toFixed(1)}% blown-out px`} />
        <CheckRow ok={q.brightness_ok} label="Lighting balanced"
          detail={`mean ${q.mean_brightness.toFixed(0)}/255`} />
        <CheckRow ok={card.found} label="Reference card detected"
          detail={card.found ? `confidence ${(card.confidence * 100).toFixed(0)}% (${card.method})` : "not found"} />
        {calibration && (
          <CheckRow ok={calibration.trustworthy} label="Calibration verified"
            detail={`check patch ΔE ${calibration.check_patch_deltae}`} />
        )}
        {q.issues.length > 0 && (
          <div className="callout warn" style={{ marginTop: 12 }}>
            {q.issues.map((issue, i) => <div key={i}>{issue}</div>)}
          </div>
        )}
      </div>

      {classification && (
        <div className="panel">
          <div className="panel-title">Classification</div>
          <div className="row" style={{ alignItems: "center", justifyContent: "space-between" }}>
            <ClassificationBadge value={classification.label} size="lg" />
            <span className="mono" style={{ fontSize: 13, color: "var(--text-dim)" }}>
              confidence {(classification.confidence * 100).toFixed(0)}%
            </span>
          </div>
          <div className="divider" />
          <div className="kv">
            <span className="k">Colour distance → negative reference (ΔE)</span>
            <span className="v">{classification.distance_to_negative}</span>
          </div>
          <div className="kv">
            <span className="k">Colour distance → positive reference (ΔE)</span>
            <span className="v">{classification.distance_to_positive}</span>
          </div>
          <div className="kv">
            <span className="k">Sample Lab (corrected)</span>
            <span className="v">
              L {classification.sample_lab[0].toFixed(1)} · a {classification.sample_lab[1].toFixed(1)} · b {classification.sample_lab[2].toFixed(1)}
            </span>
          </div>
          <div style={{ marginTop: 12, display: "flex", flexDirection: "column", gap: 6 }}>
            {classification.reasons.map((r, i) => (
              <div key={i} style={{ fontSize: 13, color: "var(--text-dim)" }}>· {r}</div>
            ))}
          </div>
        </div>
      )}

      {consensus && (
        <div className="panel">
          <div className="panel-title">Multi-frame consensus</div>
          <div className="row" style={{ alignItems: "center", gap: 12 }}>
            <ClassificationBadge value={consensus.label} />
            <span style={{ fontSize: 13, color: "var(--text-dim)" }}>
              agreement {(consensus.agreement * 100).toFixed(0)}% across {consensus.frame_labels.length} frames
            </span>
          </div>
          <div style={{ marginTop: 8, display: "flex", gap: 8, flexWrap: "wrap" }}>
            {consensus.frame_labels.map((l, i) => (
              <span key={i} className={`badge ${l}`} style={{ fontSize: 11.5 }}>
                frame {i + 1}: {l}
              </span>
            ))}
          </div>
        </div>
      )}

      {officer_vs_ai && (
        <div className="panel">
          <div className="panel-title">Officer vs AI (blind assessment)</div>
          <div className="grid-2">
            <div>
              <div className="field-label">Officer's independent call</div>
              <ClassificationBadge value={officer_vs_ai.officer} />
            </div>
            <div>
              <div className="field-label">AI classification</div>
              <ClassificationBadge value={officer_vs_ai.ai} />
            </div>
          </div>
          {!officer_vs_ai.agree && (
            <div className="callout warn" style={{ marginTop: 12 }}>
              ⚠ Officer and AI disagree — flagged for review before this record is signed.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
