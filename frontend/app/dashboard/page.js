"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "../../lib/api";
import ClassificationBadge from "../../components/ClassificationBadge";

function StatCard({ label, value, sub }) {
  return (
    <div className="panel" style={{ flex: 1 }}>
      <div className="field-label">{label}</div>
      <div style={{ fontSize: 28, fontWeight: 600, marginTop: 6 }}>{value}</div>
      {sub && <div style={{ fontSize: 12, color: "var(--text-faint)", marginTop: 4 }}>{sub}</div>}
    </div>
  );
}

export default function DashboardPage() {
  const router = useRouter();
  const [stats, setStats] = useState(null);
  const [records, setRecords] = useState([]);
  const [kitFilter, setKitFilter] = useState("");
  const [classFilter, setClassFilter] = useState("");
  const [loading, setLoading] = useState(true);

  function load() {
    setLoading(true);
    Promise.all([
      api.dashboardStats(),
      api.listRecords({ kit_id: kitFilter || undefined, classification: classFilter || undefined }),
    ])
      .then(([s, r]) => {
        setStats(s);
        setRecords(r.records);
      })
      .finally(() => setLoading(false));
  }

  useEffect(load, [kitFilter, classFilter]);

  const maxDay = stats ? Math.max(1, ...stats.by_day.map((d) => d.n)) : 1;

  return (
    <div>
      <div className="page-head">
        <h1 className="page-title">Field intelligence dashboard</h1>
        <p className="page-sub">Aggregate view across every signed evidence record on this device.</p>
      </div>

      {stats && (
        <>
          <div className="row wrap" style={{ marginBottom: 16 }}>
            <StatCard label="Total tests" value={stats.total} />
            <StatCard label="Positive" value={stats.by_classification.positive || 0} />
            <StatCard label="Negative" value={stats.by_classification.negative || 0} />
            <StatCard label="Inconclusive" value={
              (stats.by_classification.inconclusive || 0) + (stats.by_classification.cannot_determine || 0)
            } />
            <StatCard label="Avg. confidence" value={stats.avg_confidence != null ? `${Math.round(stats.avg_confidence * 100)}%` : "—"} />
            <StatCard label="Avg. quality" value={stats.avg_quality != null ? Math.round(stats.avg_quality) : "—"} />
          </div>

          <div className="grid-2">
            <div className="panel">
              <div className="panel-title">Tests by day (last 14 days)</div>
              <div style={{ display: "flex", alignItems: "flex-end", gap: 6, height: 100 }}>
                {[...stats.by_day].reverse().map((d) => (
                  <div key={d.day} title={`${d.day}: ${d.n}`} style={{ flex: 1, textAlign: "center" }}>
                    <div style={{
                      height: `${Math.max(4, (d.n / maxDay) * 80)}px`,
                      background: "var(--accent)",
                      borderRadius: "3px 3px 0 0",
                    }} />
                  </div>
                ))}
                {stats.by_day.length === 0 && <span className="field-label">No data yet</span>}
              </div>
            </div>
            <div className="panel">
              <div className="panel-title">By kit profile</div>
              {stats.by_kit.map((k) => (
                <div className="kv" key={k.kit_id}>
                  <span className="k">{k.kit_name}</span>
                  <span className="v">{k.n}</span>
                </div>
              ))}
              {stats.by_kit.length === 0 && <span className="field-label">No data yet</span>}
            </div>
          </div>
        </>
      )}

      <div className="panel">
        <div className="row" style={{ justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
          <div className="panel-title" style={{ margin: 0 }}>Records</div>
          <div className="row" style={{ gap: 8 }}>
            <select value={classFilter} onChange={(e) => setClassFilter(e.target.value)}>
              <option value="">All results</option>
              <option value="positive">Positive</option>
              <option value="negative">Negative</option>
              <option value="inconclusive">Inconclusive</option>
            </select>
            <select value={kitFilter} onChange={(e) => setKitFilter(e.target.value)}>
              <option value="">All kits</option>
              <option value="std-narcotic">Standard Narcotic</option>
              <option value="precursor">Precursor</option>
              <option value="ketamine">Ketamine</option>
            </select>
          </div>
        </div>

        {loading ? (
          <div className="skeleton" style={{ height: 160 }} />
        ) : records.length === 0 ? (
          <div className="empty">No records yet — run a test from New Test.</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Record</th><th>Case / Sample</th><th>Kit</th><th>Result</th>
                <th>Confidence</th><th>Quality</th><th>Captured</th>
              </tr>
            </thead>
            <tbody>
              {records.map((r) => (
                <tr key={r.id} onClick={() => router.push(`/records/${r.id}`)}>
                  <td className="mono emph">{r.id}</td>
                  <td>{r.case_id} / {r.sample_id}</td>
                  <td>{r.kit_name}</td>
                  <td><ClassificationBadge value={r.classification} /></td>
                  <td>{Math.round(r.confidence * 100)}%</td>
                  <td>{r.quality_score}</td>
                  <td className="mono">{r.created_at?.slice(0, 19).replace("T", " ")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
