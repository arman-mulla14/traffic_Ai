/**
 * AI-Based Traffic Management System - Alerts & Incidents Controller
 * Audits safety anomalies, handles operator review, and checks emergency model status.
 */

document.addEventListener("DOMContentLoaded", () => {
  initEmergencyModelStatus();
  loadAlerts();

  const filterType = document.getElementById("filter-type");
  const filterStatus = document.getElementById("filter-status");
  const refreshBtn = document.getElementById("btn-refresh-alerts");

  if (filterType) filterType.addEventListener("change", loadAlerts);
  if (filterStatus) filterStatus.addEventListener("change", loadAlerts);
  if (refreshBtn) refreshBtn.addEventListener("click", () => {
    loadAlerts();
    showToast("Alerts refreshed", "info");
  });
});

async function initEmergencyModelStatus() {
  try {
    const status = await API.getEmergencyStatus();
    const pill = document.getElementById("emergency-status-pill");
    const text = document.getElementById("emergency-status-text");

    if (status.is_available) {
      if (pill) {
        pill.className = "status-badge online";
        pill.textContent = "CUSTOM MODEL ACTIVE";
      }
      if (text) text.textContent = status.status_message;
    } else {
      if (pill) {
        pill.className = "status-badge offline";
        pill.textContent = "MODEL UNAVAILABLE";
      }
      if (text) text.textContent = status.status_message;
    }
  } catch (e) {
    console.error("[Alerts] Error checking emergency model:", e);
  }
}

async function loadAlerts() {
  const typeFilter = document.getElementById("filter-type")?.value || null;
  const statusFilterRaw = document.getElementById("filter-status")?.value;
  const isReviewed = statusFilterRaw !== "" ? statusFilterRaw === "true" : null;

  try {
    const alerts = await API.getAlerts(50, isReviewed, typeFilter);
    renderAlertsTable(alerts);
  } catch (e) {
    console.error("[Alerts] Error fetching alerts:", e);
  }
}

function renderAlertsTable(alerts) {
  const tbody = document.getElementById("alerts-master-tbody");
  if (!tbody) return;

  if (!alerts || alerts.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="8" style="text-align: center; color: var(--text-dim); padding: 28px;">
          No incident alerts found matching current filters.
        </td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = "";
  alerts.forEach(a => {
    const tr = document.createElement("tr");
    const dateStr = new Date(a.timestamp).toLocaleString();
    const actionBtn = a.is_reviewed
      ? `<button class="btn btn-secondary btn-sm" onclick="toggleReviewAlert(${a.id}, false)">Reopen</button>`
      : `<button class="btn btn-success btn-sm" onclick="toggleReviewAlert(${a.id}, true)">Acknowledge</button>`;

    const statusBadge = a.is_reviewed
      ? `<span class="status-badge online" style="padding: 2px 8px; font-size: 11px;">Reviewed</span>`
      : `<span class="status-badge warning" style="padding: 2px 8px; font-size: 11px;">Pending</span>`;

    tr.innerHTML = `
      <td style="font-family: monospace;">#${a.id}</td>
      <td style="font-size: 12px; color: var(--text-dim);">${dateStr}</td>
      <td><span class="badge-alert ${a.severity}">${a.alert_type}</span></td>
      <td><strong>${a.severity}</strong></td>
      <td style="font-family: monospace;">${a.track_id ? `#${a.track_id}` : "N/A"}</td>
      <td style="max-width: 320px;">${a.description}</td>
      <td>${statusBadge}</td>
      <td>${actionBtn}</td>
    `;
    tbody.appendChild(tr);
  });
}

async function toggleReviewAlert(alertId, isReviewed) {
  try {
    await API.reviewAlert(alertId, isReviewed);
    showToast(isReviewed ? `Alert #${alertId} acknowledged` : `Alert #${alertId} reopened`, "success");
    loadAlerts();
  } catch (e) {
    showToast(`Error updating alert: ${e.message}`, "error");
  }
}

window.toggleReviewAlert = toggleReviewAlert;
