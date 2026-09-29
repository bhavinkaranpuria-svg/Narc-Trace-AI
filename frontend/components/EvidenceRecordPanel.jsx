"use client";
import ClassificationBadge from "./ClassificationBadge";

export default function EvidenceRecordPanel({ record, qrBase64 }) {
  if (!record) return null;
  return (
    <div className="grid-2">
      <div className="panel">
        <div className="panel-title">Evidence record</div>
        <div className="kv"><span className="k">Record ID</span><span className="v">{record.id}</span></div>
        <div className="kv"><span className="k">Case</span><span className="v">{record.case_id}</span></div>
        <div className="kv"><span className="k">Sample</span><span className="v">{record.sample_id}</span></div>
        <div className="kv"><span className="k">Operator</span><span className="v">{record.operator_id}</span></div>
        <div className="kv"><span className="k">Kit</span><span className="v">{record.kit_name}</span></div>
        <div className="kv"><span className="k">Captured</span><span className="v">{record.created_at}</span></div>
        <div className="kv">
          <span className="k">Location</span>
          <span className="v">
            {record.gps_lat != null ? `${record.gps_lat.toFixed(4)}, ${record.gps_lng.toFixed(4)} (±${record.gps_accuracy ?? "?"}m)` : "not recorded"}
          </span>
        </div>
        <div className="kv"><span className="k">Mode</span><span className="v">{record.capture_mode} / {record.sync_status}</span></div>
        <div className="divider" />
        <div className="row" style={{ justifyContent: "space-between", alignItems: "center" }}>
          <span className="field-label">Result</span>
          <ClassificationBadge value={record.classification} />
        </div>
        <div className="kv" style={{ marginTop: 6 }}>
          <span className="k">Confidence</span><span className="v">{Math.round(record.confidence * 100)}%</span>
        </div>
        <div className="kv"><span className="k">Quality score</span><span className="v">{record.quality_score}/100</span></div>
        {record.officer_assessment && (
          <div className="kv"><span className="k">Officer's call</span><span className="v">{record.officer_assessment}</span></div>
        )}
        <div className="kv"><span className="k">Model version</span><span className="v">{record.model_version}</span></div>

        <div className="callout" style={{ marginTop: 14 }}>
          Presumptive field-test result. Not a substitute for laboratory confirmation.
        </div>
      </div>

      <div className="panel">
        <div className="panel-title">Integrity</div>
        <div className="field-label">Image hash (SHA-256)</div>
        <div className="hash" style={{ marginBottom: 12 }}>{record.image_hash}</div>
        <div className="field-label">Record hash (SHA-256)</div>
        <div className="hash" style={{ marginBottom: 12 }}>{record.record_hash}</div>
        <div className="field-label">Previous record hash (chain link)</div>
        <div className="hash" style={{ marginBottom: 12 }}>{record.prev_hash}</div>
        <div className="field-label">Digital signature (RSA-PSS, base64)</div>
        <div className="hash" style={{ marginBottom: 4, maxHeight: 60, overflow: "hidden" }}>
          {record.signature ? `${record.signature.slice(0, 90)}…` : "—"}
        </div>
        <div className="field-label" style={{ marginTop: 8 }}>Signing key fingerprint</div>
        <div className="hash">{record.public_key_fingerprint}</div>

        {qrBase64 && (
          <>
            <div className="divider" />
            <div className="field-label" style={{ marginBottom: 8 }}>Verification QR</div>
            <img
              src={`data:image/png;base64,${qrBase64}`}
              alt="Verification QR code"
              style={{ width: 140, height: 140, background: "#fff", padding: 8, borderRadius: 6 }}
            />
          </>
        )}
      </div>
    </div>
  );
}
