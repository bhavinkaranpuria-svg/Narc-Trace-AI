"use client";
import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { api } from "../../lib/api";
import ClassificationBadge from "../../components/ClassificationBadge";

const TAMPERABLE_FIELDS = [
  "classification", "confidence", "quality_score", "case_id",
  "sample_id", "operator_id", "gps_lat", "gps_lng", "image_hash",
];

function CheckLine({ ok, label, value }) {
  return (
    <div className="kv">
      <span className="k">
        <span style={{ color: ok ? "var(--accent)" : "var(--danger)", marginRight: 8 }}>{ok ? "✓" : "✕"}</span>
        {label}
      </span>
      <span className="v">{String(value)}</span>
    </div>
  );
}

function VerifyInner() {
  const params = useSearchParams();
  const [recordId, setRecordId] = useState(params.get("record_id") || "");
  const [record, setRecord] = useState(null);
  const [error, setError] = useState(null);
  const [field, setField] = useState("classification");
  const [value, setValue] = useState("");
  const [result, setResult] = useState(null);
  const [checking, setChecking] = useState(false);

  function loadRecord() {
    setError(null);
    setResult(null);
    api.getRecord(recordId).then(setRecord).catch((e) => setError(e.message));
  }

  useEffect(() => {
    if (recordId) loadRecord();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function runVerify(withTamper) {
    setChecking(true);
    setError(null);
    try {
      let override_fields;
      if (withTamper) {
        let parsed = value;
        if (!isNaN(Number(value)) && value.trim() !== "") parsed = Number(value);
        override_fields = { [field]: parsed };
      }
      const r = await api.verify({ record_id: recordId, override_fields });
      setResult(r);
    } catch (e) {
      setError(e.message);
    } finally {
      setChecking(false);
    }
  }

  return (
    <div>
      <div className="page-head">
        <h1 className="page-title">Verify a record</h1>
        <p className="page-sub">Recomputes the record hash, checks the digital signature, and confirms the hash-chain link to the previous record.</p>
      </div>

      <div className="panel">
        <div className="panel-title">Load record</div>
        <div className="row">
          <input style={{ flex: 1 }} value={recordId} onChange={(e) => setRecordId(e.target.value)}
                 placeholder="NCB-REC-000001" />
          <button className="btn" onClick={loadRecord}>Load</button>
        </div>
        {error && <div className="callout danger" style={{ marginTop: 12 }}>{error}</div>}
      </div>

      {record && (
        <>
          <div className="panel">
            <div className="row" style={{ justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <div style={{ fontWeight: 600 }}>{record.id}</div>
                <div style={{ fontSize: 12.5, color: "var(--text-faint)" }}>{record.case_id} / {record.sample_id}</div>
              </div>
              <ClassificationBadge value={record.classification} />
            </div>
            <div className="row" style={{ marginTop: 16, gap: 10 }}>
              <button className="btn primary" disabled={checking} onClick={() => runVerify(false)}>
                Verify as recorded
              </button>
            </div>
          </div>

          <div className="panel">
            <div className="panel-title">Tamper challenge</div>
            <p style={{ fontSize: 13, color: "var(--text-dim)", marginTop: 0 }}>
              Change one field the way a bad actor might, then verify — the signature check should fail.
            </p>
            <div className="row" style={{ gap: 10 }}>
              <select value={field} onChange={(e) => setField(e.target.value)}>
                {TAMPERABLE_FIELDS.map((f) => <option key={f} value={f}>{f}</option>)}
              </select>
              <input style={{ flex: 1 }} value={value} onChange={(e) => setValue(e.target.value)}
                     placeholder={`new value for ${field}`} />
              <button className="btn danger-outline" disabled={checking || !value} onClick={() => runVerify(true)}>
                Apply &amp; verify
              </button>
            </div>
          </div>

          {result && (
            <div className="panel">
              <div className="row" style={{ justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
                <div className="panel-title" style={{ margin: 0 }}>Result</div>
                <ClassificationBadge value={result.overall} size="lg" />
              </div>
              {result.simulated_tamper && (
                <div className="callout warn" style={{ marginBottom: 12 }}>
                  Simulated tamper applied to <span className="mono">{field}</span> — this does not modify the stored record.
                </div>
              )}
              <CheckLine ok={result.checks.hash_match} label="Record hash matches" value={result.checks.hash_match ? "match" : "MISMATCH"} />
              <CheckLine ok={result.checks.signature_valid} label="Digital signature valid" value={result.checks.signature_valid ? "valid" : "INVALID"} />
              <CheckLine ok={result.checks.chain_intact} label="Chain link to previous record" value={result.checks.chain_intact ? "intact" : "BROKEN"} />
              <div className="divider" />
              <div className="field-label">Computed hash</div>
              <div className="hash" style={{ marginBottom: 10 }}>{result.checks.computed_hash}</div>
              <div className="field-label">Stored hash</div>
              <div className="hash">{result.checks.stored_hash}</div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default function VerifyPage() {
  return (
    <Suspense fallback={<div className="skeleton" style={{ height: 200 }} />}>
      <VerifyInner />
    </Suspense>
  );
}
