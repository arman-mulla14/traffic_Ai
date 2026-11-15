/**
 * AI-Based Traffic Management System - Dashboard Master Controller
 * Connects directly to backend API (/api/dashboard/summary, /api/dashboard/charts)
 * Road-Oriented Multi-Approach Analytics, Vehicle Classification, Volume Trends, Incidents & System Health.
 */

let categoryChartInstance = null;
let volumeTrendChartInstance = null;
let dashboardRefreshTimer = null;

const ROAD_NAMES = {
  "1": "Road 1: North Approach (Nort NH4)",
  "2": "Road 2: South Approach (South NH4)",
  "3": "Road 3: East Approach (East NH4)",
  "4": "Road 4: West Approach (Wast NH4)"
};

document.addEventListener("DOMContentLoaded", () => {
  initLiveClock();
  initRoadFilter();
  loadDashboardData();

  const volumeFilter = document.getElementById("volume-range-select");
  if (volumeFilter) {
    volumeFilter.addEventListener("change", () => loadDashboardData());
  }

  // Periodic real-time update every 15 seconds
  if (dashboardRefreshTimer) clearInterval(dashboardRefreshTimer);
  dashboardRefreshTimer = setInterval(() => {
    loadDashboardData(true);
  }, 15000);
});

function initLiveClock() {
  const clockEl = document.getElementById("header-datetime-text");
  if (!clockEl) return;

  function update() {
    const now = new Date();
    const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    const month = months[now.getMonth()];
    const day = now.getDate();
    const year = now.getFullYear();
    const timeStr = now.toTimeString().split(" ")[0];
    clockEl.textContent = `${month} ${day}, ${year}  ${timeStr}`;
  }
  update();
  setInterval(update, 1000);
}

function initRoadFilter() {
  const roadFilter = document.getElementById("dashboard-road-filter");
  if (!roadFilter) return;

  roadFilter.addEventListener("change", () => {
    updateRoadViewUI(roadFilter.value);
    loadDashboardData();
  });
}

function updateRoadViewUI(selectedRoad) {
  const badge = document.getElementById("selected-road-badge");
  const camImg = document.getElementById("dashboard-live-cam");
  const camTitle = document.getElementById("dashboard-live-cam-title");
  const camBadge = document.getElementById("dashboard-live-cam-badge");

  if (selectedRoad === "all") {
    if (badge) badge.textContent = "4 Approaches Active";
    if (camTitle) camTitle.textContent = "Live Traffic Camera";
    if (camBadge) camBadge.textContent = "● Junction Live";
    if (camImg) {
      camImg.src = "/api/cameras/1/stream?t=" + Date.now();
    }
  } else {
    const roadName = ROAD_NAMES[selectedRoad] || `Road #${selectedRoad}`;
    if (badge) badge.textContent = `Road ${selectedRoad} Selected`;
    if (camTitle) camTitle.textContent = `Live Camera - ${roadName.split(' (')[0]}`;
    if (camBadge) camBadge.textContent = `● CAM #${selectedRoad} Live`;
    if (camImg) {
      camImg.src = `/api/cameras/${selectedRoad}/stream?t=${Date.now()}`;
    }
  }
}

async function loadDashboardData(isBackground = false) {
  try {
    const volumeFilter = document.getElementById("volume-range-select");
    const timeRange = volumeFilter ? volumeFilter.value : "7";

    const roadFilter = document.getElementById("dashboard-road-filter");
    const selectedRoad = roadFilter ? roadFilter.value : "all";
    const cameraId = (selectedRoad && selectedRoad !== "all") ? parseInt(selectedRoad) : null;

    const [summary, charts] = await Promise.all([
      API.getDashboardSummary(cameraId),
      API.getDashboardCharts({ camera_id: cameraId, time_range: timeRange })
    ]);

    // 1. Update KPI numbers from real database totals
    if (summary) {
      const v = document.getElementById("kpi-val-vehicles");
      const vid = document.getElementById("kpi-val-videos");
      const d = document.getElementById("kpi-val-density");
      const inc = document.getElementById("kpi-val-incidents");

      if (v) v.textContent = (summary.total_vehicles !== undefined ? summary.total_vehicles : 0).toLocaleString();
      if (vid) vid.textContent = summary.total_videos !== undefined ? summary.total_videos : 0;
      if (d) d.textContent = `${summary.avg_density !== undefined ? summary.avg_density : 0}%`;
      if (inc) inc.textContent = summary.total_incidents !== undefined ? summary.total_incidents : 0;
    }

    // 2. Render Donut Chart with authentic counts, percentages, and center total
    if (charts && charts.categories) {
      renderDonutChart(charts.categories, summary ? summary.total_vehicles : null);
    }

    // 3. Render Volume Trend Line Chart with real daily data
    if (charts && charts.volume_trend) {
      renderVolumeTrendChart(charts.volume_trend);
    }

    // 4. Render Live Recent Incidents List
    if (charts && charts.recent_incidents) {
      renderRecentIncidents(charts.recent_incidents, selectedRoad);
    }

    // 5. Render Genuine System Status Badges & Health Gauge
    if (charts && charts.system_status) {
      renderSystemStatus(charts.system_status);
    }

  } catch (err) {
    console.error("[Dashboard] Error loading live dashboard data:", err);
  }
}

function renderDonutChart(catData, totalVehiclesOverride) {
  const ctx = document.getElementById("categoryDistributionChart");
  if (!ctx) return;

  const total = (totalVehiclesOverride !== null && totalVehiclesOverride !== undefined) 
    ? totalVehiclesOverride 
    : (catData.total_vehicles !== undefined ? catData.total_vehicles : (catData.total_categorized || 0));

  // Update center total number
  const centerEl = document.getElementById("donut-center-total");
  if (centerEl) {
    centerEl.textContent = total.toLocaleString();
  }

  // Update legend counts and percentages
  const counts = catData.counts || [0, 0, 0, 0];
  const pcts = catData.percentages || [0, 0, 0, 0];

  const updateLegend = (cntId, pctId, count, pct) => {
    const cntEl = document.getElementById(cntId);
    const pctEl = document.getElementById(pctId);
    if (cntEl) cntEl.textContent = `(${Number(count).toLocaleString()})`;
    if (pctEl) pctEl.textContent = `${pct}%`;
  };

  updateLegend("dist-cnt-cars", "dist-pct-cars", counts[0] || 0, pcts[0] || 0);
  updateLegend("dist-cnt-motos", "dist-pct-motos", counts[1] || 0, pcts[1] || 0);
  updateLegend("dist-cnt-buses", "dist-pct-buses", counts[2] || 0, pcts[2] || 0);
  updateLegend("dist-cnt-trucks", "dist-pct-trucks", counts[3] || 0, pcts[3] || 0);

  if (categoryChartInstance) {
    categoryChartInstance.destroy();
  }

  // Colors: Blue (Cars), Green (Motorcycles), Orange (Buses), Purple (Trucks)
  const colors = ["#2563EB", "#22C55E", "#FB923C", "#A855F7"];
  const labels = catData.labels || ["Cars", "Motorcycles", "Buses", "Trucks"];

  // Handle case where total is 0
  const chartData = (counts.every(c => c === 0)) ? [1, 0, 0, 0] : counts;
  const chartColors = (counts.every(c => c === 0)) ? ["#E2E8F0", "#E2E8F0", "#E2E8F0", "#E2E8F0"] : colors;

  categoryChartInstance = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: labels,
      datasets: [{
        data: chartData,
        backgroundColor: chartColors,
        borderWidth: 2,
        borderColor: "#FFFFFF",
        hoverOffset: 4
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: "#0F2042",
          titleFont: { family: "Inter", size: 12 },
          bodyFont: { family: "Inter", size: 12, weight: "bold" },
          padding: 10,
          callbacks: {
            label: (item) => {
              if (counts.every(c => c === 0)) return " No vehicles recorded";
              const val = counts[item.dataIndex] || 0;
              const pct = pcts[item.dataIndex] !== undefined ? pcts[item.dataIndex] : 0;
              return ` ${item.label}: ${val.toLocaleString()} (${pct}%)`;
            }
          }
        }
      },
      cutout: "70%"
    }
  });
}

function renderVolumeTrendChart(trendData) {
  const ctx = document.getElementById("trafficVolumeTrendChart");
  if (!ctx) return;

  if (volumeTrendChartInstance) {
    volumeTrendChartInstance.destroy();
  }

  const labels = trendData.labels || ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
  const dataPoints = trendData.volumes || [0, 0, 0, 0, 0, 0, 0];

  const maxVal = Math.max(...dataPoints, 50);
  const yMax = Math.ceil((maxVal * 1.25) / 50) * 50;
  const stepSize = Math.max(10, Math.ceil(yMax / 4 / 10) * 10);

  volumeTrendChartInstance = new Chart(ctx, {
    type: "line",
    data: {
      labels: labels,
      datasets: [{
        label: "Traffic Volume",
        data: dataPoints,
        borderColor: "#2563EB",
        backgroundColor: "rgba(37, 99, 235, 0.08)",
        borderWidth: 2.5,
        fill: true,
        tension: 0.38,
        pointBackgroundColor: "#2563EB",
        pointBorderColor: "#FFFFFF",
        pointBorderWidth: 2,
        pointRadius: 4.5,
        pointHoverRadius: 7
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: "#0F2042",
          titleFont: { family: "Inter", size: 12 },
          bodyFont: { family: "Inter", size: 12, weight: "bold" },
          padding: 8,
          callbacks: {
            label: (ctx) => ` ${ctx.parsed.y.toLocaleString()} vehicles`
          }
        }
      },
      scales: {
        x: {
          grid: { display: true, color: "#F1F5F9" },
          ticks: { font: { family: "Inter", size: 11 }, color: "#64748B" }
        },
        y: {
          min: 0,
          max: yMax,
          ticks: {
            stepSize: stepSize,
            font: { family: "Inter", size: 11 },
            color: "#64748B",
            callback: (v) => v.toLocaleString()
          },
          grid: { color: "#F1F5F9" }
        }
      }
    }
  });
}

function renderRecentIncidents(incidents, selectedRoad = "all") {
  const container = document.getElementById("dashboard-incidents-list");
  if (!container) return;

  if (!incidents || incidents.length === 0) {
    const roadNote = selectedRoad !== "all" 
      ? `on ${ROAD_NAMES[selectedRoad] ? ROAD_NAMES[selectedRoad].split(' (')[0] : 'selected road'}` 
      : "across all road approaches";
    container.innerHTML = `
      <div class="incident-row" style="padding: 18px; text-align: center; color: #64748B; font-size: 13px;">
        No active traffic incidents detected ${roadNote}.
      </div>
    `;
    return;
  }

  container.innerHTML = incidents.slice(0, 3).map(inc => {
    const sev = (inc.severity || "medium").toLowerCase();
    const isCritical = sev === "critical" || sev === "high";
    const iconColor = isCritical ? "red" : (sev === "medium" ? "orange" : "blue");
    const sevClass = isCritical ? (sev === "critical" ? "critical" : "high") : (sev === "medium" ? "medium" : "low");
    const displayTitle = inc.title || inc.type || "Traffic Alert";
    const roadTag = inc.road_name ? `<span style="font-size: 11px; color: #2563EB; font-weight: 500; margin-left: 6px;">[${inc.road_name.split('(')[0].trim()}]</span>` : "";

    return `
      <div class="incident-row">
        <div class="incident-left-meta">
          <svg class="incident-warning-icon ${iconColor}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/>
            <line x1="12" x2="12" y1="9" y2="13"/>
            <line x1="12" x2="12.01" y1="17" y2="17"/>
          </svg>
          <div class="incident-text-block">
            <h4>${displayTitle}${roadTag}</h4>
            <p title="${inc.description || ''}">${inc.description || 'Incident flagged by AI safety model.'}</p>
          </div>
        </div>
        <div class="incident-right-meta">
          <span class="incident-time">${inc.time || 'Recent'}</span>
          <span class="severity-pill ${sevClass}">${inc.severity || 'Medium'}</span>
        </div>
      </div>
    `;
  }).join("");
}

function renderSystemStatus(status) {
  if (!status) return;

  const aiEl = document.getElementById("status-ai-model");
  const dbEl = document.getElementById("status-database");
  const wsEl = document.getElementById("status-web-server");
  const qEl = document.getElementById("status-queue");
  const gaugeEl = document.getElementById("system-health-gauge");

  if (aiEl && status.ai_model) aiEl.textContent = `✔ ${status.ai_model}`;
  if (dbEl && status.database) dbEl.textContent = `✔ ${status.database}`;
  if (wsEl && status.web_server) wsEl.textContent = `✔ ${status.web_server}`;
  if (qEl && status.active_cameras) qEl.textContent = `✔ ${status.active_cameras}`;
  if (gaugeEl && status.health_percentage !== undefined) {
    gaugeEl.textContent = `${status.health_percentage}%`;
  }
}
