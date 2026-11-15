/**
 * AI-Based Traffic Management System - Incident Management Logic
 * Handles filtering, search, resolution, and detail panel for traffic safety incidents.
 */

let allIncidents = [];

document.addEventListener("DOMContentLoaded", () => {
  loadIncidents();
  initFilters();
});

async function loadIncidents() {
  const tbody = document.getElementById("incidents-table-tbody");
  if (!tbody) return;

  try {
    const status = document.getElementById("filter-status")?.value || "";
    const severity = document.getElementById("filter-severity")?.value || "";
    const type = document.getElementById("filter-type")?.value || "";
    const search = document.getElementById("filter-search")?.value.toLowerCase() || "";

    const incidents = await API.listIncidents({
      status: status || null,
      severity: severity || null,
      incident_type: type || null
    });

    allIncidents = incidents;

    // Filter by client search if text is entered
    let filtered = incidents;
    if (search) {
      filtered = incidents.filter(i => 
        i.description.toLowerCase().includes(search) || 
        i.incident_type.toLowerCase().includes(search)
      );
    }

    if (!filtered || filtered.length === 0) {
      tbody.innerHTML = `<tr><td colspan="8" style="text-align:center;padding:24px;color:#64748B;">No matching traffic incidents found.</td></tr>`;
      return;
    }

    tbody.innerHTML = filtered.map(inc => {
      const sev = inc.severity || "MEDIUM";
      let sevClass = "badge-info";
      if (sev === "CRITICAL" || sev === "HIGH") sevClass = "badge-danger";
      else if (sev === "MEDIUM") sevClass = "badge-warning";
      else if (sev === "LOW") sevClass = "badge-success";

      let statusClass = "badge-danger";
      if (inc.status === "RESOLVED") statusClass = "badge-success";
      else if (inc.status === "ACKNOWLEDGED") statusClass = "badge-warning";

      const timeStr = inc.timestamp ? new Date(inc.timestamp).toLocaleString([], { dateStyle: "short", timeStyle: "medium" }) : "Recent";

      return `
        <tr>
          <td><strong>#${inc.id}</strong></td>
          <td>
            <span class="badge ${sevClass}">
              <span class="badge-dot"></span>
              ${inc.incident_type.replace(/_/g, " ")}
            </span>
          </td>
          <td style="max-width:280px;" title="${inc.description}">${inc.description}</td>
          <td><span class="badge ${sevClass}">${inc.severity}</span></td>
          <td>Track #${inc.vehicle_track_id || "N/A"}</td>
          <td>${timeStr}</td>
          <td>
            <span class="badge ${statusClass}">
              <span class="badge-dot"></span>
              ${inc.status}
            </span>
          </td>
          <td>
            <div style="display:flex;gap:6px;">
              <button class="btn btn-sm btn-outline" onclick="openIncidentDetail(${inc.id})">Details</button>
              ${inc.status !== 'RESOLVED' ? `
                <button class="btn btn-sm btn-success" onclick="resolveIncidentAction(${inc.id})">Resolve</button>
              ` : ''}
            </div>
          </td>
        </tr>
      `;
    }).join("");
  } catch (err) {
    console.error("Failed to load incidents:", err);
    tbody.innerHTML = `<tr><td colspan="8" style="text-align:center;padding:24px;color:var(--danger);">Error loading incidents table.</td></tr>`;
  }
}

function initFilters() {
  const ids = ["filter-status", "filter-severity", "filter-type", "filter-search"];
  ids.forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      el.addEventListener("input", () => loadIncidents());
      el.addEventListener("change", () => loadIncidents());
    }
  });
}

async function resolveIncidentAction(id) {
  try {
    await API.resolveIncident(id, "RESOLVED");
    showToast(`Incident #${id} marked as RESOLVED.`);
    loadIncidents();
  } catch (err) {
    showToast("Failed to resolve incident: " + err.message, "error");
  }
}
window.resolveIncidentAction = resolveIncidentAction;

function openIncidentDetail(id) {
  const inc = allIncidents.find(i => i.id === id);
  if (!inc) return;

  const modal = document.getElementById("incident-detail-modal");
  const title = document.getElementById("incident-modal-title");
  const typeEl = document.getElementById("detail-type");
  const sevEl = document.getElementById("detail-sev");
  const descEl = document.getElementById("detail-desc");
  const trackEl = document.getElementById("detail-track");
  const timeEl = document.getElementById("detail-time");
  const statusEl = document.getElementById("detail-status");
  const resolveBtn = document.getElementById("modal-resolve-btn");

  if (title) title.textContent = `Incident Details - #${inc.id}`;
  if (typeEl) typeEl.textContent = inc.incident_type.replace(/_/g, " ");
  if (sevEl) sevEl.textContent = inc.severity;
  if (descEl) descEl.textContent = inc.description;
  if (trackEl) trackEl.textContent = inc.vehicle_track_id ? `Track #${inc.vehicle_track_id}` : "Unclassified";
  if (timeEl) timeEl.textContent = new Date(inc.timestamp).toLocaleString();
  if (statusEl) statusEl.textContent = inc.status;

  if (resolveBtn) {
    resolveBtn.style.display = inc.status === "RESOLVED" ? "none" : "inline-flex";
    resolveBtn.onclick = async () => {
      await resolveIncidentAction(inc.id);
      closeIncidentModal();
    };
  }

  if (modal) modal.classList.add("show");
}
window.openIncidentDetail = openIncidentDetail;

function closeIncidentModal() {
  const modal = document.getElementById("incident-detail-modal");
  if (modal) modal.classList.remove("show");
}
window.closeIncidentModal = closeIncidentModal;

