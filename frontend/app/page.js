"use client";
import { useEffect, useState } from "react";
import { api } from "../lib/api";
import PipelineStepper from "../components/PipelineStepper";
import ExplainabilityPanel from "../components/ExplainabilityPanel";
import EvidenceRecordPanel from "../components/EvidenceRecordPanel";

export default function CapturePage() {
  const [kits, setKits] = useState([]);
  const [kitId, setKitId] = useState("std-narcotic");
  const [caseId, setCaseId] = useState("");
  const [sampleId, setSampleId] = useState("");
  const [operatorId, setOperatorId] = useState("");
  const [captureMode, setCaptureMode] = useState("online");
  const [officerAssessment, setOfficerAssessment] = useState("");
  const [gps, setGps] = useState(null);
  const [gpsError, setGpsError] = useState(null);

  const [files, setFiles] = useState([]);
  const [previews, setPreviews] = useState([]);
  const [analyzing, setAnalyzing] = useState(false);
  const [analysis, setAnalysis] = useState(null);
  const [error, setError] = useState(null);

  const [signing, setSigning] = useState(false);
  const [record, setRecord] = useState(null);
  const [qrBase64, setQrBase64] = useState(null);

  useEffect(() => {
    api.kits().then((r) => setKits(r.kits)).catch(() => {});
  }, []);

  function handleFiles(e) {
    const list = Array.from(e.target.files || []).slice(0, 3);
    setFiles(list);
    setPreviews(list.map((f) => URL.createObjectURL(f)));
    setAnalysis(null);
    setError(null);
  }

  function useLocation() {
    if (!navigator.geolocation) {
      setGpsError("Geolocation not available in this browser.");
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setGps({
          lat: pos.coords.latitude,
          lng: pos.coords.longitude,
          accuracy: Math.round(pos.coords.accuracy),
        });
        setGpsError(null);
      },
      (err) => setGpsError(err.message)
    );
  }

  async function runAnalysis() {
    if (files.length === 0) return;
    setAnalyzing(true);
    setError(null);
    try {
      const result = await api.analyze(files, { kitId, officerAssessment: officerAssessment || undefined });
      setAnalysis(result);
    } catch (e) {
      setError(e.message);
    } finally {
      setAnalyzing(false);
    }
  }

  async function confirmAndSign() {
    if (!analysis) return;
    setSigning(true);
    setError(null);
    try {
      const result = await api.createRecord({
        analysis_id: analysis.analysis_id,
        case_id: caseId,
        sample_id: sampleId,
        operator_id: operatorId,
        gps_lat: gps?.lat,
        gps_lng: gps?.lng,
        gps_accuracy: gps?.accuracy,
        capture_mode: captureMode,
        officer_assessment: officerAssessment || undefined,
      });
      setRecord(result);
      setQrBase64(result.qr_base64);
    } catch (e) {
      setError(e.message);
    } finally {
      setSigning(false);
    }
  }

  function startNewTest() {
    setFiles([]);
    setPreviews([]);
    setAnalysis(null);
    setRecord(null);
    setQrBase64(null);
    setError(null);
    setOfficerAssessment("");
    setSampleId("");
  }

  const canAnalyze = files.length > 0 && !analyzing;
  const canSign =
    analysis?.classification &&
    analysis.classification.label !== "cannot_determine" &&
    caseId && sampleId && operatorId && !signing;

  if (record) {
    return (
      <div>
        <div className="page-head">
          <h1 className="page-title">Record signed</h1>
          <p className="page-sub">{record.id} has been written to the local evidence chain.</p>
        </div>
        <PipelineStepper activeKey="trace" doneKeys={["see", "correct", "decide", "prove", "trace"]} />
        <div style={{ height: 16 }} />
        <EvidenceRecordPanel record={record} qrBase64={qrBase64} />
        <div className="row" style={{ marginTop: 20, gap: 10 }}>
          <button className="btn primary" onClick={startNewTest}>Start new test</button>
          <a className="btn" href="/dashboard">View dashboard</a>
          <a className="btn" href="/verify">Verify this record</a>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="page-head">
        <h1 className="page-title">New field test</h1>
        <p className="page-sub">Photograph the reacted kit next to the reference card. The system checks image quality, calibrates for lighting, then classifies.</p>
      </div>

      <PipelineStepper
        activeKey={analysis ? "decide" : "see"}
        doneKeys={analysis ? ["see", "correct", "decide"] : []}
      />
      <div style={{ height: 16 }} />

      <div className="panel">
        <div className="panel-title">Case details</div>
        <div className="grid-3">
          <div className="col">
            <span className="field-label">Case ID</span>
            <input value={caseId} onChange={(e) => setCaseId(e.target.value)} placeholder="NCB-2026-0001" />
          </div>
          <div className="col">
            <span className="field-label">Sample ID</span>
            <input value={sampleId} onChange={(e) => setSampleId(e.target.value)} placeholder="S-001" />
          </div>
          <div className="col">
            <span className="field-label">Operator ID</span>
            <input value={operatorId} onChange={(e) => setOperatorId(e.target.value)} placeholder="OFF-42" />
          </div>
        </div>
        <div className="grid-3" style={{ marginTop: 14 }}>
          <div className="col">
            <span className="field-label">Kit profile</span>
            <select value={kitId} onChange={(e) => setKitId(e.target.value)}>
              {kits.map((k) => <option key={k.id} value={k.id}>{k.name}</option>)}
            </select>
          </div>
          <div className="col">
            <span className="field-label">Capture mode</span>
            <select value={captureMode} onChange={(e) => setCaptureMode(e.target.value)}>
              <option value="online">Online (sync now)</option>
              <option value="offline">Offline (sync later)</option>
            </select>
          </div>
          <div className="col">
            <span className="field-label">Location</span>
            <button type="button" className="btn" onClick={useLocation}>
              {gps ? `${gps.lat.toFixed(4)}, ${gps.lng.toFixed(4)} (±${gps.accuracy}m)` : "Capture GPS"}
            </button>
            {gpsError && <span style={{ fontSize: 11.5, color: "var(--danger)" }}>{gpsError}</span>}
          </div>
        </div>
        <div className="col" style={{ marginTop: 14 }}>
          <span className="field-label">Officer's independent call (optional — recorded before AI result is shown, for bias comparison)</span>
          <select value={officerAssessment} onChange={(e) => setOfficerAssessment(e.target.value)}>
            <option value="">Not recorded</option>
            <option value="positive">Positive</option>
            <option value="negative">Negative</option>
            <option value="inconclusive">Inconclusive</option>
          </select>
        </div>
      </div>

      <div className="panel">
        <div className="panel-title">Capture</div>
        <p style={{ fontSize: 13, color: "var(--text-dim)", marginTop: 0 }}>
          Up to 3 frames can be captured for a consensus read.{" "}
          <a href={api.referenceCardUrl()} target="_blank" rel="noreferrer" style={{ color: "var(--accent)" }}>
            Print the reference card ↗
          </a>
        </p>
        <input type="file" accept="image/*" capture="environment" multiple onChange={handleFiles} />
        {previews.length > 0 && (
          <div className="row" style={{ marginTop: 14, gap: 10 }}>
            {previews.map((src, i) => (
              <img key={i} src={src} alt={`frame ${i + 1}`}
                   style={{ width: 120, height: 90, objectFit: "cover", borderRadius: 6, border: "1px solid var(--border-strong)" }} />
            ))}
          </div>
        )}
        <div className="row" style={{ marginTop: 16 }}>
          <button className="btn primary" disabled={!canAnalyze} onClick={runAnalysis}>
            {analyzing ? "Analyzing…" : "Analyze"}
          </button>
        </div>
      </div>

      {error && <div className="callout danger">{error}</div>}

      {analysis && (
        <>
          <ExplainabilityPanel analysis={analysis} />
          <div className="panel">
            {analysis.classification?.label === "cannot_determine" ? (
              <div className="callout danger">
                The system could not reliably classify this frame. Retake the photo — check lighting, focus, and that the reference card is fully in frame.
              </div>
            ) : (
              <>
                <div className="panel-title">Confirm &amp; sign</div>
                <p style={{ fontSize: 13, color: "var(--text-dim)", marginTop: 0 }}>
                  Signing creates a permanent, hash-chained evidence record. Case, sample and operator ID are required.
                </p>
                <button className="btn primary" disabled={!canSign} onClick={confirmAndSign}>
                  {signing ? "Signing…" : "Confirm & Sign Record"}
                </button>
              </>
            )}
          </div>
        </>
      )}
    </div>
  );
}
