const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function handle(res) {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || JSON.stringify(body);
    } catch (_) {}
    throw new Error(detail);
  }
  return res.json();
}

export const api = {
  base: BASE,

  health: () => fetch(`${BASE}/api/health`).then(handle),

  kits: () => fetch(`${BASE}/api/kits`).then(handle),

  referenceCardUrl: () => `${BASE}/api/reference-card`,

  analyze: (files, { kitId, manualCorners, officerAssessment }) => {
    const form = new FormData();
    files.forEach((f) => form.append("images", f));
    form.append("kit_id", kitId);
    if (manualCorners) form.append("manual_corners", JSON.stringify(manualCorners));
    if (officerAssessment) form.append("officer_assessment", officerAssessment);
    return fetch(`${BASE}/api/analyze`, { method: "POST", body: form }).then(handle);
  },

  createRecord: (payload) =>
    fetch(`${BASE}/api/records`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }).then(handle),

  listRecords: (params = {}) => {
    const qs = new URLSearchParams(
      Object.entries(params).filter(([, v]) => v !== undefined && v !== "")
    ).toString();
    return fetch(`${BASE}/api/records${qs ? `?${qs}` : ""}`).then(handle);
  },

  getRecord: (id) => fetch(`${BASE}/api/records/${id}`).then(handle),

  getAudit: (id) => fetch(`${BASE}/api/audit/${id}`).then(handle),

  dashboardStats: () => fetch(`${BASE}/api/dashboard/stats`).then(handle),

  verify: (payload) =>
    fetch(`${BASE}/api/verify`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }).then(handle),
};
