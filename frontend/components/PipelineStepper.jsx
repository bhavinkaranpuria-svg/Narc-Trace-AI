"use client";

const STEPS = [
  { key: "see", label: "See", hint: "Capture + quality check" },
  { key: "correct", label: "Correct", hint: "Card calibration" },
  { key: "decide", label: "Decide", hint: "Classification" },
  { key: "prove", label: "Prove", hint: "Sign + hash chain" },
  { key: "trace", label: "Trace", hint: "Record filed" },
];

export default function PipelineStepper({ activeKey, doneKeys = [] }) {
  return (
    <div className="stepper">
      {STEPS.map((s, i) => {
        const done = doneKeys.includes(s.key);
        const active = s.key === activeKey;
        return (
          <div key={s.key} className={`step${done ? " done" : ""}${active ? " active" : ""}`}>
            <div className="step-index">{String(i + 1).padStart(2, "0")}</div>
            <div className="step-label">{s.label}</div>
            <div className="step-hint" style={{ fontSize: 11.5, color: "var(--text-faint)", marginTop: 2 }}>
              {s.hint}
            </div>
          </div>
        );
      })}
    </div>
  );
}
