"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api } from "../../../lib/api";
import EvidenceRecordPanel from "../../../components/EvidenceRecordPanel";

export default function RecordPage() {
  const { id } = useParams();
  const [record, setRecord] = useState(null);
  const [qrBase64, setQrBase64] = useState(null);
  const [audit, setAudit] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.getRecord(id).then(setRecord).catch((e) => setError(e.message));
    api.getAudit(id).then((r) => setAudit(r.entries)).catch(() => {});
    fetch(`${api.base}/api/records/${id}/qr`).then((r) => r.json()).then((r) => setQrBase64(r.qr_base64)).catch(() => {});
  }, [id]);

  if (error) return <div className="callout danger">{error}</div>;
  if (!record) return <div className="skeleton" style={{ height: 240 }} />;

  return (
    <div>
      <div className="page-head">
        <h1 className="page-title">{record.id}</h1>
        <p className="page-sub">Full evidence report — presumptive result, chain-linked and signed.</p>
      </div>

      <EvidenceRecordPanel record={record} qrBase64={qrBase64} />

      <div className="panel">
        <div className="panel-title">Evidence timeline</div>
        {audit.map((e, i) => (
          <div key={e.id} style={{ display: "flex", gap: 14, paddingBottom: i === audit.length - 1 ? 0 : 14 }}>
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
              <div style={{ width: 8, height: 8, borderRadius: "50%", background: "var(--accent)", marginTop: 4 }} />
              {i !== audit.length - 1 && <div style={{ flex: 1, width: 1, background: "var(--border-strong)", marginTop: 4 }} />}
            </div>
            <div>
              <div style={{ fontSize: 13.5, fontWeight: 500 }}>{e.action}</div>
              {e.detail && <div style={{ fontSize: 12.5, color: "var(--text-dim)" }}>{e.detail}</div>}
              <div className="mono" style={{ fontSize: 11, color: "var(--text-faint)", marginTop: 2 }}>
                {e.timestamp?.slice(0, 19).replace("T", " ")}
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="row" style={{ marginTop: 4 }}>
        <a className="btn primary" href={`/verify?record_id=${record.id}`}>Verify this record</a>
        <a className="btn" href="/dashboard">Back to dashboard</a>
      </div>
    </div>
  );
}
