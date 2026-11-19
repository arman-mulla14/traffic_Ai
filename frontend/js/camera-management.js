/**
 * AI-Based Traffic Management System - Camera & Street Management Logic (v7.5 Enterprise)
 * Handles street/road corridor creation, camera registration, live preview, video attachment,
 * and direct one-click traffic analysis by street.
 */

let cachedCameras = [];
let cachedStreets = [];
let currentTestCamId = 1;

document.addEventListener("DOMContentLoaded", () => {
  loadCameras();
  loadStreets();
  initAddCameraModal();
});

async function loadCameras() {
  const tbody = document.getElementById("cameras-table-tbody");
  if (!tbody) return;

  try {
    const cameras = await API.listCameras();
    cachedCameras = cameras || [];

    // Update KPI counters
    const total = cachedCameras.length;
    const online = cachedCameras.filter(c => c.status === "ACTIVE" || c.status === "ONLINE").length;
    const inactive = cachedCameras.filter(c => c.status === "INACTIVE").length;
    const offline = cachedCameras.filter(c => c.status === "OFFLINE" || c.status === "ERROR").length;

    const elTotal = document.getElementById("kpi-cam-total");
    const elOnline = document.getElementById("kpi-cam-online");
    const elInactive = document.getElementById("kpi-cam-inactive");
    const elOffline = document.getElementById("kpi-cam-offline");

    if (elTotal) elTotal.textContent = total;
    if (elOnline) elOnline.textContent = online;
    if (elInactive) elInactive.textContent = inactive;
    if (elOffline) elOffline.textContent = offline;

    if (!cachedCameras || cachedCameras.length === 0) {
      tbody.innerHTML = `<tr><td colspan="8" style="text-align:center;padding:24px;color:#64748B;">No cameras registered. Click "+ Add Camera" or "+ Create Road / Street" to register.</td></tr>`;
      return;
    }

    tbody.innerHTML = cachedCameras.map(c => {
      const isOnline = c.status === "ACTIVE" || c.status === "ONLINE";
      const isOffline = c.status === "OFFLINE" || c.status === "ERROR";

      let statusBadge = `<span class="badge badge-success"><span class="badge-dot"></span> ONLINE</span>`;
      if (isOffline) {
        statusBadge = `<span class="badge badge-danger"><span class="badge-dot"></span> OFFLINE</span>`;
      } else if (c.status === "INACTIVE") {
        statusBadge = `<span class="badge badge-warning"><span class="badge-dot"></span> INACTIVE</span>`;
      }

      const streamDisplay = c.stream_url ? (c.stream_url === "0" ? "Webcam #0" : (c.stream_url.length > 35 ? '...' + c.stream_url.slice(-30) : c.stream_url)) : "Sample Loop";
      const dateStr = c.created_at ? new Date(c.created_at).toLocaleDateString() : "Recent";
      const roadDisplay = c.road_name ? c.road_name.split(" [")[0] : `Road #${c.id} Approach`;
      const dir = c.direction || "Northbound";

      return `
        <tr>
          <td>
            <div style="display:flex;align-items:center;gap:10px;">
              <div style="width:34px;height:34px;border-radius:6px;background:rgba(40,120,208,0.1);display:flex;align-items:center;justify-content:center;color:#2878D0;flex-shrink:0;">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14.5 4h-5L7 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3l-2.5-3z"/><circle cx="12" cy="13" r="3"/></svg>
              </div>
              <div>
                <strong style="color:var(--text-primary);display:block;font-size:13.5px;">${c.camera_name}</strong>
                <span style="color:var(--text-secondary);font-size:11.5px;">ID: #${c.id}</span>
              </div>
            </div>
          </td>
          <td>
            <div style="display:flex; flex-direction:column; gap:4px;">
              <span style="font-weight:600; color:#0F172A; font-size:13px; display:flex; align-items:center; gap:5px;">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#2563EB" stroke-width="2.2"><path d="M4 19L8 5"/><path d="M16 5l4 14"/><path d="M12 4v4"/><path d="M12 11v4"/><path d="M12 18v2"/></svg>
                ${roadDisplay}
              </span>
              <span style="font-size:11px; background:#EFF6FF; color:#2563EB; padding:2px 8px; border-radius:12px; width:fit-content; font-weight:600;">
                ${dir} • ${c.speed_limit || 60} km/h
              </span>
            </div>
          </td>
          <td>${c.location}</td>
          <td><code style="background:#F1F5F9;padding:2px 6px;border-radius:4px;font-size:12px;color:#12345A;">${streamDisplay}</code></td>
          <td>${c.camera_type || "CCTV"}</td>
          <td>${statusBadge}</td>
          <td>${dateStr}</td>
          <td>
            <div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;">
              <button class="btn btn-sm" style="background:#EEF2FF; color:#4F46E5; border:1px solid #C7D2FE; font-weight:600;" onclick="analyzeStreetTraffic(${c.id})" title="Analyze Traffic Flow on this Road">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 20V10"/><path d="M12 20V4"/><path d="M6 20v-6"/></svg>
                Analyze
              </button>
              <button class="btn btn-sm btn-outline" onclick="openTestFeedModal(${c.id})" title="Preview Feed on Screen">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="6 3 20 12 6 21 6 3"/></svg>
                Preview
              </button>
              <button class="btn btn-sm btn-primary" onclick="viewOnLiveScreen(${c.id})" title="View Camera on Live Monitoring Screen">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></svg>
                Live
              </button>
              <button class="btn btn-sm btn-outline" onclick="openShareModal(${c.id})" title="Attach Video or Live Stream to Camera">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m16 13 5.223 3.482a.5.5 0 0 0 .777-.416V7.87a.5.5 0 0 0-.752-.432L16 10.5"/><rect x="2" y="6" width="14" height="12" rx="2"/></svg>
                Attach
              </button>
              <button class="btn btn-sm btn-outline" style="color:var(--danger);" onclick="deleteCameraAction(${c.id})" title="Delete Camera">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/></svg>
              </button>
            </div>
          </td>
        </tr>
      `;
    }).join("");
  } catch (err) {
    console.error("Failed to load cameras:", err);
    tbody.innerHTML = `<tr><td colspan="8" style="text-align:center;padding:24px;color:var(--danger);">Error loading camera list.</td></tr>`;
  }
}
window.loadCameras = loadCameras;

// =============================================================================
// Streets & Road Corridors Section
// =============================================================================

async function loadStreets() {
  const container = document.getElementById("streets-cards-grid");
  if (!container) return;

  try {
    const streets = await API.listStreets();
    cachedStreets = streets || [];

    if (!streets || streets.length === 0) {
      container.innerHTML = `
        <div style="grid-column: 1 / -1; text-align: center; padding: 30px; color: #64748B; background: #F8FAFC; border-radius: 8px; border: 1px dashed #CBD5E1;">
          No streets registered yet. Click <strong>"+ Create Road / Street"</strong> to set up your first approach corridor.
        </div>
      `;
      return;
    }

    container.innerHTML = streets.map(s => {
      const congClass = s.congestion_level === "FREE FLOW" ? "color:#16A34A; background:#DCFCE7;" : 
                        (s.congestion_level === "MODERATE" ? "color:#D97706; background:#FEF3C7;" : "color:#DC2626; background:#FEE2E2;");

      const roadsList = (s.roads && s.roads.length > 0) ? s.roads : [];

      const roadsHtml = roadsList.map(r => `
        <div style="display:flex; align-items:center; justify-content:space-between; font-size:12px; background:#FFFFFF; padding:8px 12px; border-radius:6px; border:1px solid #E2E8F0; gap:8px;">
          <div style="display:flex; align-items:center; gap:8px; min-width:0;">
            <span style="width:8px; height:8px; border-radius:50%; background:#00BA63; flex-shrink:0;"></span>
            <div style="white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">
              <strong style="color:#0F172A;">${r.road_name || r.display_name}</strong>
              <span style="font-size:11px; color:#64748B; margin-left:4px;">(${r.direction})</span>
            </div>
          </div>
          <div style="display:flex; align-items:center; gap:8px; flex-shrink:0;">
            <span style="font-size:11px; color:#2563EB; font-weight:700; background:#EFF6FF; padding:2px 7px; border-radius:4px; border:1px solid #DBEAFE;">Cam #${r.camera_id}</span>
            <span style="font-size:11px; color:#475569; font-weight:600;">${r.total_vehicles || 0} veh</span>
          </div>
        </div>
      `).join("");

      return `
        <div class="street-card" style="background:#FFFFFF; border:1.5px solid #E2E8F0; border-radius:12px; padding:18px; box-shadow:0 2px 5px rgba(0,0,0,0.04); display:flex; flex-direction:column; justify-content:space-between; gap:12px;">
          <div>
            <!-- CLICKABLE STREET TITLE / HEADER (TAP TO EXPAND/COLLAPSE ROADS) -->
            <div onclick="toggleStreetRoads('${s.id}')" style="cursor:pointer; user-select:none; padding:4px 6px; margin:-4px -6px 8px -6px; border-radius:8px; transition:background 0.15s ease;" onmouseover="this.style.background='#F8FAFC'" onmouseout="this.style.background='transparent'" title="Tap to expand / collapse all roads inside ${s.name}">
              <div style="display:flex; align-items:flex-start; justify-content:space-between; gap:10px;">
                <div style="flex:1;">
                  <h4 style="margin:0; font-size:15px; font-weight:800; color:#0F172A; display:flex; align-items:center; gap:7px;">
                    <span style="width:9px; height:9px; border-radius:50%; background:#2563EB; flex-shrink:0;"></span>
                    <span>Street: ${s.name}</span>
                    <svg id="street-chevron-${s.id}" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#2563EB" stroke-width="2.5" style="transition:transform 0.25s ease; flex-shrink:0;"><polyline points="6 9 12 15 18 9"/></svg>
                  </h4>
                  <div style="font-size:12px; color:#64748B; margin-top:3px; display:flex; align-items:center; gap:6px;">
                    <span>📍 Location: <strong style="color:#334155;">${s.location || 'Intersection'}</strong></span>
                  </div>
                </div>
                <div style="display:flex; flex-direction:column; align-items:flex-end; gap:4px; flex-shrink:0;">
                  <span style="font-size:11px; font-weight:700; padding:3px 8px; border-radius:12px; ${congClass}">
                    ${s.congestion_level}
                  </span>
                  <span id="street-expand-badge-${s.id}" style="font-size:11px; font-weight:700; color:#2563EB; background:#EFF6FF; border:1px solid #BFDBFE; padding:3px 8px; border-radius:12px; display:flex; align-items:center; gap:4px;">
                    ${s.total_roads} Roads Grouped ▾
                  </span>
                </div>
              </div>
            </div>

            <!-- COLLAPSIBLE ROADS CONTAINER (EXPANDS WHEN USER TAPS STREET NAME) -->
            <div id="street-roads-container-${s.id}" style="display:none; margin:10px 0 12px 0; background:#F8FAFC; border:1.5px solid #DBEAFE; border-radius:10px; padding:12px; animation:fadeIn 0.2s ease;">
              <div style="font-size:11px; font-weight:700; color:#1E40AF; text-transform:uppercase; margin-bottom:8px; display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid #E2E8F0; padding-bottom:6px;">
                <span style="display:flex; align-items:center; gap:5px;">
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M4 19L8 5"/><path d="M16 5l4 14"/><path d="M12 4v4"/><path d="M12 11v4"/><path d="M12 18v2"/></svg>
                  Total Roads in this Street (${roadsList.length})
                </span>
                <span style="color:#2563EB; font-weight:700;">Speed Limit: ${s.speed_limit} km/h</span>
              </div>
              <div style="display:flex; flex-direction:column; gap:6px;">
                ${roadsHtml}
              </div>
            </div>

            <!-- Quick Tap-to-expand helper banner if collapsed -->
            <div id="street-roads-hint-${s.id}" onclick="toggleStreetRoads('${s.id}')" style="cursor:pointer; display:flex; align-items:center; justify-content:space-between; background:#F8FAFC; border:1px dashed #CBD5E1; border-radius:8px; padding:7px 12px; margin-bottom:12px; font-size:11.5px; color:#475569;" onmouseover="this.style.borderColor='#2563EB'; this.style.color='#2563EB';" onmouseout="this.style.borderColor='#CBD5E1'; this.style.color='#475569';">
              <span>👉 Tap street name to view all <strong>${roadsList.length} roads</strong> inside</span>
              <span style="font-weight:700; color:#2563EB; display:flex; align-items:center; gap:3px;">Show Roads ▾</span>
            </div>

            <!-- Mini Metrics Row for Entire Street -->
            <div style="display:grid; grid-template-columns: repeat(3, 1fr); gap:8px; background:#F1F5F9; padding:10px; border-radius:8px; text-align:center;">
              <div>
                <span style="display:block; font-size:10px; color:#64748B; font-weight:700; text-transform:uppercase;">TOTAL TRAFFIC</span>
                <strong style="font-size:14px; color:#1E293B;">${Number(s.total_vehicles).toLocaleString()}</strong>
              </div>
              <div>
                <span style="display:block; font-size:10px; color:#64748B; font-weight:700; text-transform:uppercase;">AVG DENSITY</span>
                <strong style="font-size:14px; color:#1E293B;">${s.avg_density}%</strong>
              </div>
              <div>
                <span style="display:block; font-size:10px; color:#64748B; font-weight:700; text-transform:uppercase;">INCIDENTS</span>
                <strong style="font-size:14px; color:#DC2626;">${s.total_incidents}</strong>
              </div>
            </div>
          </div>

          <!-- Action buttons: Live Monitoring (All roads in street) and Analytics -->
          <div style="display:flex; gap:8px; align-items:center; border-top:1px solid #F1F5F9; padding-top:12px;">
            <button class="btn btn-sm btn-primary" style="flex:1; font-weight:600; justify-content:center; display:flex; align-items:center; gap:5px;" onclick="viewStreetOnLive('${s.name}')" title="View all roads belonging to ${s.name} on Live Monitoring">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polygon points="10 8 16 12 10 16 10 8"/></svg>
              View Roads in Live
            </button>
            <button class="btn btn-sm btn-outline" style="font-weight:600; padding:6px 10px; display:flex; align-items:center; gap:4px;" onclick="analyzeStreet('${s.name}')" title="Analyze traffic volume & trends for ${s.name}">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M18 20V10"/><path d="M12 20V4"/><path d="M6 20v-6"/></svg>
              Analytics
            </button>
          </div>
        </div>
      `;
    }).join("");
  } catch (err) {
    console.error("Failed to load streets:", err);
    container.innerHTML = `<div style="grid-column: 1 / -1; color: var(--danger); padding: 14px;">Error loading streets overview.</div>`;
  }
}
window.loadStreets = loadStreets;

function toggleStreetRoads(streetId) {
  const container = document.getElementById(`street-roads-container-${streetId}`);
  const chevron = document.getElementById(`street-chevron-${streetId}`);
  const hint = document.getElementById(`street-roads-hint-${streetId}`);
  const badge = document.getElementById(`street-expand-badge-${streetId}`);

  if (!container) return;

  const isHidden = container.style.display === "none" || !container.style.display;
  if (isHidden) {
    container.style.display = "block";
    if (chevron) chevron.style.transform = "rotate(180deg)";
    if (hint) hint.style.display = "none";
    if (badge) {
      badge.innerHTML = badge.innerHTML.replace("▾", "▴");
      badge.style.background = "#2563EB";
      badge.style.color = "#FFFFFF";
    }
  } else {
    container.style.display = "none";
    if (chevron) chevron.style.transform = "rotate(0deg)";
    if (hint) hint.style.display = "flex";
    if (badge) {
      badge.innerHTML = badge.innerHTML.replace("▴", "▾");
      badge.style.background = "#EFF6FF";
      badge.style.color = "#2563EB";
    }
  }
}
window.toggleStreetRoads = toggleStreetRoads;

function viewStreetOnLive(streetName) {
  window.location.href = `/frontend/pages/live-monitoring.html?street=${encodeURIComponent(streetName)}`;
}
window.viewStreetOnLive = viewStreetOnLive;

function analyzeStreet(streetName) {
  window.location.href = `/frontend/pages/traffic-analytics.html?street=${encodeURIComponent(streetName)}`;
}
window.analyzeStreet = analyzeStreet;

function openCurrentTestOnLiveScreen() {
  if (currentTestCamId) {
    viewOnLiveScreen(currentTestCamId);
  } else {
    window.location.href = "/pages/live-monitoring.html";
  }
}
window.openCurrentTestOnLiveScreen = openCurrentTestOnLiveScreen;

// =============================================================================
// Test Feed Modal Controllers
// =============================================================================
function openTestFeedModal(camId) {
  currentTestCamId = parseInt(camId);
  const modal = document.getElementById("test-feed-modal");
  const title = document.getElementById("test-feed-title");
  const img = document.getElementById("test-feed-img");

  const cam = cachedCameras.find(c => c.id === currentTestCamId);
  const camName = cam ? cam.camera_name : `Camera #${camId}`;

  if (title) title.textContent = `Test Feed: ${camName}`;
  if (img) {
    img.onerror = function() {
      this.onerror = null;
      this.src = "/assets/live_camera_feed.jpg";
    };
    img.src = API.getCameraStreamUrl(camId) + "&t=" + Date.now();
  }

  if (modal) {
    modal.classList.add("show");
    modal.style.display = "flex";
  }
}
window.openTestFeedModal = openTestFeedModal;

function closeTestFeedModal() {
  const modal = document.getElementById("test-feed-modal");
  const img = document.getElementById("test-feed-img");
  if (img) img.src = "";
  if (modal) {
    modal.classList.remove("show");
    modal.style.display = "none";
  }
}
window.closeTestFeedModal = closeTestFeedModal;

// =============================================================================
// Share Video / Live Stream Modal Controllers
// =============================================================================
async function openShareModal(camId) {
  const modal = document.getElementById("share-stream-modal");
  const hiddenCam = document.getElementById("share-modal-cam-id");
  const title = document.getElementById("share-modal-title");
  const select = document.getElementById("share-select-video");
  const inputUrl = document.getElementById("share-input-url");

  if (!modal) return;

  const cam = cachedCameras.find(c => c.id === camId);
  if (hiddenCam) hiddenCam.value = String(camId);
  if (title) title.textContent = `Attach Video to CAM #${camId}: ${cam ? cam.camera_name : ''}`;
  if (inputUrl && cam && cam.stream_url) inputUrl.value = cam.stream_url;

  // Load uploaded videos
  if (select) {
    try {
      const videos = await API.listVideos();
      if (videos && videos.length > 0) {
        select.innerHTML = `<option value="">-- Choose an uploaded video --</option>` + videos.map(v => `
          <option value="${v.id}">${v.video_name} (${(v.file_size / (1024 * 1024)).toFixed(1)} MB)</option>
        `).join("");
      } else {
        select.innerHTML = `<option value="">No recorded videos uploaded yet</option>`;
      }
    } catch (e) {
      console.warn("Could not load videos:", e);
    }
  }

  modal.classList.add("show");
  modal.style.display = "flex";
}
window.openShareModal = openShareModal;

function closeShareModal() {
  const modal = document.getElementById("share-stream-modal");
  if (modal) {
    modal.classList.remove("show");
    modal.style.display = "none";
  }
}
window.closeShareModal = closeShareModal;

async function submitShareVideoToCamera() {
  const hiddenCam = document.getElementById("share-modal-cam-id");
  const select = document.getElementById("share-select-video");
  const inputUrl = document.getElementById("share-input-url");

  const camId = hiddenCam ? parseInt(hiddenCam.value) : null;
  if (!camId) return;

  let payload = {};
  if (select && select.value) {
    payload.video_id = parseInt(select.value);
  } else if (inputUrl && inputUrl.value.trim()) {
    payload.stream_url = inputUrl.value.trim();
  } else {
    showToast("Please choose an uploaded video or enter a stream link.", "warning");
    return;
  }

  try {
    showToast("Connecting video to camera feed...");
    await API.setCameraStream(camId, payload);
    showToast("Video feed successfully attached!");
    closeShareModal();
    loadCameras();
    loadStreets();
    setTimeout(() => {
      viewOnLiveScreen(camId);
    }, 600);
  } catch (err) {
    showToast("Failed to attach video: " + err.message, "error");
  }
}
window.submitShareVideoToCamera = submitShareVideoToCamera;

// =============================================================================
// Add Camera Modal
// =============================================================================
function initAddCameraModal() {
  const modal = document.getElementById("add-camera-modal");
  const openBtn = document.getElementById("open-add-camera-btn");
  const saveBtn = document.getElementById("save-camera-btn");

  if (openBtn && modal) {
    openBtn.addEventListener("click", () => {
      modal.classList.add("show");
      modal.style.display = "flex";
    });
  }

  if (saveBtn) {
    saveBtn.addEventListener("click", async () => {
      const name = document.getElementById("new-cam-name")?.value.trim();
      const road = document.getElementById("new-cam-road")?.value.trim() || null;
      const loc = document.getElementById("new-cam-loc")?.value.trim();
      const dir = document.getElementById("new-cam-direction")?.value || "Northbound";
      const type = document.getElementById("new-cam-type")?.value || "CCTV";
      const url = document.getElementById("new-cam-url")?.value.trim() || null;
      const status = document.getElementById("new-cam-status")?.value || "ACTIVE";

      if (!name || !loc) {
        showToast("Please provide Camera Name and Location.", "warning");
        return;
      }

      saveBtn.disabled = true;
      try {
        await API.createCamera({
          camera_name: name,
          road_name: road,
          direction: dir,
          location: loc,
          camera_type: type,
          stream_url: url,
          status: status
        });
        showToast(`Camera "${name}" registered successfully!`);
        closeAddCameraModal();
        loadCameras();
        loadStreets();
      } catch (err) {
        showToast("Failed to register camera: " + err.message, "error");
      } finally {
        saveBtn.disabled = false;
      }
    });
  }
}

function openAddCameraModal() {
  const modal = document.getElementById("add-camera-modal");
  if (modal) {
    modal.classList.add("show");
    modal.style.display = "flex";
  }
}
window.openAddCameraModal = openAddCameraModal;

function closeAddCameraModal() {
  const modal = document.getElementById("add-camera-modal");
  if (modal) {
    modal.classList.remove("show");
    modal.style.display = "none";
  }
}
window.closeAddCameraModal = closeAddCameraModal;

// =============================================================================
// Add Road / Street Modal Controllers ("Roads are in One")
// =============================================================================

async function openAddStreetModal() {
  const modal = document.getElementById("add-street-modal");
  const checkboxesContainer = document.getElementById("street-roads-checkboxes");
  const vidSelect = document.getElementById("new-street-video-select");

  if (!modal) return;

  if (!cachedCameras || cachedCameras.length === 0) {
    cachedCameras = await API.listCameras();
  }

  // Populate multi-road assignment checkboxes ("roads are in one")
  if (checkboxesContainer) {
    checkboxesContainer.innerHTML = cachedCameras.map(c => {
      const isFourRoadDefault = [1, 2, 3, 4].includes(c.id);
      return `
        <label style="display:flex; align-items:center; justify-content:space-between; gap:10px; font-size:12.5px; color:#1E293B; cursor:pointer; background:#FFFFFF; padding:8px 12px; border-radius:6px; border:1px solid #E2E8F0;">
          <div style="display:flex; align-items:center; gap:8px;">
            <input type="checkbox" name="street-road-assign" value="${c.id}" ${isFourRoadDefault ? "checked" : ""} style="cursor:pointer; width:16px; height:16px; accent-color:#2563EB;">
            <div>
              <strong style="color:#0F172A;">Cam #${c.id}: ${c.road_name || c.camera_name.split(' [')[0]}</strong>
              <div style="font-size:11px; color:#64748B;">Direction: ${c.direction || 'Approach'} • ${c.location}</div>
            </div>
          </div>
          <span style="font-size:11px; color:#2563EB; font-weight:700; background:#EFF6FF; padding:2px 8px; border-radius:12px;">${c.speed_limit || 60} km/h</span>
        </label>
      `;
    }).join("");
  }

  // Populate video select for optional extra road
  if (vidSelect) {
    try {
      const videos = await API.listVideos();
      if (videos && videos.length > 0) {
        vidSelect.innerHTML = `<option value="">-- Choose video feed to attach --</option>` + videos.map(v => `
          <option value="${v.file_path}">${v.video_name} (${(v.file_size / (1024 * 1024)).toFixed(1)} MB)</option>
        `).join("");
      } else {
        vidSelect.innerHTML = `<option value="">Sample traffic stream loop</option>`;
      }
    } catch (e) {
      console.warn("Could not load videos for street modal:", e);
    }
  }

  modal.classList.add("show");
  modal.style.display = "flex";
}
window.openAddStreetModal = openAddStreetModal;

function toggleAllStreetCheckboxes(check) {
  const checkboxes = document.querySelectorAll("input[name='street-road-assign']");
  checkboxes.forEach(cb => cb.checked = !!check);
}
window.toggleAllStreetCheckboxes = toggleAllStreetCheckboxes;

function closeAddStreetModal() {
  const modal = document.getElementById("add-street-modal");
  if (modal) {
    modal.classList.remove("show");
    modal.style.display = "none";
  }
}
window.closeAddStreetModal = closeAddStreetModal;

async function submitCreateStreet() {
  const nameInput = document.getElementById("new-street-name");
  const locInput = document.getElementById("new-street-loc");
  const speedInput = document.getElementById("new-street-speed");
  const customRoadInput = document.getElementById("new-street-custom-road-name");
  const dirInput = document.getElementById("new-street-direction");
  const vidSelect = document.getElementById("new-street-video-select");
  const saveBtn = document.getElementById("save-street-btn");

  const streetName = nameInput ? nameInput.value.trim() : "";
  if (!streetName) {
    showToast("Please enter a Street / Intersection name.", "warning");
    return;
  }

  const location = locInput ? locInput.value.trim() || "Kodoli" : "Kodoli";
  const speedLimit = speedInput ? parseInt(speedInput.value) || 60 : 60;

  // Gather all checked roads to group into this street
  const checkedBoxes = Array.from(document.querySelectorAll("input[name='street-road-assign']:checked"));
  const cameraIds = checkedBoxes.map(cb => parseInt(cb.value));

  // Check if an optional new road is defined
  const newRoads = [];
  if (customRoadInput && customRoadInput.value.trim()) {
    newRoads.push({
      road_name: customRoadInput.value.trim(),
      direction: dirInput ? dirInput.value : "Northbound",
      stream_url: vidSelect ? vidSelect.value || null : null
    });
  }

  if (cameraIds.length === 0 && newRoads.length === 0) {
    showToast("Please check at least one road to group into this street, or create a new road.", "warning");
    return;
  }

  const payload = {
    street_name: streetName,
    location: location,
    speed_limit: speedLimit,
    camera_ids: cameraIds,
    new_roads: newRoads
  };

  if (saveBtn) saveBtn.disabled = true;

  try {
    showToast(`Configuring Street "${streetName}" & grouping roads...`);
    const res = await API.createStreet(payload);
    showToast(`Street "${streetName}" configured with ${res.total_roads || cameraIds.length} roads!`);
    closeAddStreetModal();
    if (nameInput) nameInput.value = "";
    if (locInput) locInput.value = "";
    if (customRoadInput) customRoadInput.value = "";
    await loadCameras();
    await loadStreets();
  } catch (err) {
    showToast("Failed to create street: " + err.message, "error");
  } finally {
    if (saveBtn) saveBtn.disabled = false;
  }
}
window.submitCreateStreet = submitCreateStreet;

async function deleteCameraAction(id) {
  if (!confirm(`Are you sure you want to delete Camera #${id}?`)) return;
  try {
    await API.deleteCamera(id);
    showToast(`Camera #${id} deleted.`);
    loadCameras();
    loadStreets();
  } catch (err) {
    showToast("Failed to delete camera: " + err.message, "error");
  }
}
window.deleteCameraAction = deleteCameraAction;
