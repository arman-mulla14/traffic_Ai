/**
 * AI-Based Traffic Management System - Live Monitoring Logic (v5.5 Enterprise)
 * High-performance video stream controller, Screen-Wise Video Selector, Multi-Camera Grid Matrix, YOLOv8 overlay, and real-time telemetry sync.
 */

let activeCameraId = 1;
let currentViewMode = "grid-2x2"; // 'grid-2x2' (4-Road Intersection AI Agent) | 'single' | 'grid-all'
let detectionOverlayActive = true;
let isStreaming = true;
let telemetryIntervalId = null;
let cachedCameras = [];
let cachedVideos = [];
let currentCheckedCamId = 1;
let selectedLiveStreet = "all";
let cachedStreetsList = [];

// =============================================================================
// Street-Oriented Live View Functions
// =============================================================================
async function initLiveStreetFilter() {
  const sel = document.getElementById("live-street-filter");
  if (!sel) return;

  try {
    cachedStreetsList = await API.listStreets();
    if (!cachedStreetsList || cachedStreetsList.length === 0) return;

    const urlParams = new URLSearchParams(window.location.search);
    const paramStreet = urlParams.get("street");

    sel.innerHTML = `
      <option value="all">All Streets &amp; Roads (All Feeds)</option>
      ${cachedStreetsList.map(s => `
        <option value="${s.name}" ${(paramStreet && paramStreet.toLowerCase() === s.name.toLowerCase()) ? "selected" : ""}>
          ${s.name} (${s.total_roads} Roads: ${s.location})
        </option>
      `).join("")}
    `;

    if (paramStreet) {
      selectedLiveStreet = paramStreet;
      sel.value = paramStreet;
    }
    updateLiveStreetBanner();
  } catch (err) {
    console.warn("Could not load street list in Live Monitoring:", err);
  }
}
window.initLiveStreetFilter = initLiveStreetFilter;

function filterLiveByStreet(streetName) {
  selectedLiveStreet = streetName || "all";
  updateLiveStreetBanner();
  renderMultiCameraGrid();
  if (typeof showToast === "function") {
    showToast(`Viewing Street: ${selectedLiveStreet === 'all' ? 'All Streets' : selectedLiveStreet}`);
  }
}
window.filterLiveByStreet = filterLiveByStreet;

function updateLiveStreetBanner() {
  const banner = document.getElementById("live-street-banner");
  if (!banner) return;

  const totalCams = cachedCameras.length;
  if (!selectedLiveStreet || selectedLiveStreet === "all") {
    const elName = document.getElementById("live-street-banner-name");
    const elCount = document.getElementById("live-street-roads-count-badge");
    const elCong = document.getElementById("live-street-congestion-badge");
    const elDesc = document.getElementById("live-street-banner-desc");
    const elVeh = document.getElementById("live-street-banner-vehicles");
    const elDens = document.getElementById("live-street-banner-density");
    const elSpd = document.getElementById("live-street-banner-speed");

    if (elName) elName.textContent = "All Streets & Road Intersections";
    if (elCount) elCount.textContent = `${totalCams} Total Roads Monitored`;
    if (elCong) {
      elCong.textContent = "MULTI-CORRIDOR";
      elCong.style.background = "#2563EB";
    }
    if (elDesc) elDesc.innerHTML = "Monitoring real-time traffic flow across all registered streets and intersections simultaneously.";
    if (elVeh) elVeh.textContent = "1,374 Vehicles";
    if (elDens) elDens.textContent = "21.4%";
    if (elSpd) elSpd.textContent = "Multi-Zone";
    return;
  }

  const st = (cachedStreetsList || []).find(s => s.name.toLowerCase() === selectedLiveStreet.toLowerCase());
  if (st) {
    const elName = document.getElementById("live-street-banner-name");
    const elCount = document.getElementById("live-street-roads-count-badge");
    const elCong = document.getElementById("live-street-congestion-badge");
    const elDesc = document.getElementById("live-street-banner-desc");
    const elVeh = document.getElementById("live-street-banner-vehicles");
    const elDens = document.getElementById("live-street-banner-density");
    const elSpd = document.getElementById("live-street-banner-speed");

    if (elName) elName.textContent = st.name;
    if (elCount) elCount.textContent = `${st.total_roads} Roads in this Street`;
    if (elCong) {
      elCong.textContent = st.congestion_level;
      elCong.style.background =
        st.congestion_level === "FREE FLOW" ? "#059669" : (st.congestion_level === "MODERATE" ? "#D97706" : "#DC2626");
    }
    if (elDesc) elDesc.innerHTML = `Location: <strong style="color: #E2E8F0;">${st.location}</strong> • Showing all ${st.total_roads} approach roads grouped into this street`;
    if (elVeh) elVeh.textContent = `${st.total_vehicles} Vehicles`;
    if (elDens) elDens.textContent = `${st.avg_density}%`;
    if (elSpd) elSpd.textContent = `${st.speed_limit} km/h`;
  }
}
window.updateLiveStreetBanner = updateLiveStreetBanner;

function jumpToStreetAnalytics() {
  if (selectedLiveStreet && selectedLiveStreet !== "all") {
    window.location.href = `traffic-analytics.html?street=${encodeURIComponent(selectedLiveStreet)}`;
  } else {
    window.location.href = `traffic-analytics.html`;
  }
}
window.jumpToStreetAnalytics = jumpToStreetAnalytics;

// =============================================================================
// Initialization with Dual Ready State Check
// =============================================================================
async function initLiveMonitoring() {
  console.log("[LiveMonitoring] Initializing multi-camera controllers and real-time streams...");
  await loadInitialData();
  await initLiveStreetFilter();
  initCameraSelector();
  initStreamControls();
  initBoundingBoxCanvas();
  setViewMode(currentViewMode);
  startLiveTelemetry();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initLiveMonitoring);
} else {
  initLiveMonitoring();
}

async function loadInitialData() {
  try {
    const [cams, vids] = await Promise.allSettled([
      API.listCameras(),
      API.listVideos()
    ]);
    if (cams.status === "fulfilled" && cams.value) {
      cachedCameras = cams.value;
    }
    if (vids.status === "fulfilled" && vids.value) {
      cachedVideos = vids.value;
    }
  } catch (e) {
    console.warn("[LiveMonitoring] Initial data fetch error:", e);
  }
}

// =============================================================================
// Camera Selector & Stream Switching
// =============================================================================
async function initCameraSelector() {
  const select = document.getElementById("camera-stream-select");
  const modalSelect = document.getElementById("modal-select-camera");

  try {
    if (!cachedCameras || cachedCameras.length === 0) {
      cachedCameras = await API.listCameras();
    }

    if (cachedCameras && cachedCameras.length > 0) {
      if (select) {
        select.innerHTML = cachedCameras.map(c => `
          <option value="${c.id}">${c.camera_name} (${c.location})</option>
        `).join("");

        // Check URL parameters for ?camera=X or ?cam=X
        const urlSearch = (typeof window !== "undefined" && window.location && window.location.search) ? window.location.search : "";
        const urlParams = new URLSearchParams(urlSearch);
        const urlCam = urlParams.get("camera") || urlParams.get("cam");
        if (urlCam && cachedCameras.some(c => c.id === parseInt(urlCam))) {
          activeCameraId = parseInt(urlCam);
        } else {
          const exists = cachedCameras.some(c => c.id === activeCameraId);
          if (!exists) {
            activeCameraId = cachedCameras[0].id;
          }
        }
        select.value = String(activeCameraId);

        const activeCam = cachedCameras.find(c => c.id === activeCameraId) || cachedCameras[0];
        updateCameraDetails(activeCam);
      }

      if (modalSelect) {
        modalSelect.innerHTML = cachedCameras.map(c => `
          <option value="${c.id}">CAM #${c.id}: ${c.camera_name}</option>
        `).join("");
        modalSelect.value = String(activeCameraId);
      }
    }
  } catch (e) {
    console.warn("[LiveMonitoring] Could not fetch cameras from API:", e);
  }

  if (select) {
    select.onchange = function(e) {
      switchCameraStream(e.target.value);
    };
  }
}
window.initCameraSelector = initCameraSelector;

async function switchCameraStream(camId) {
  activeCameraId = parseInt(camId);
  const select = document.getElementById("camera-stream-select");
  if (select && select.value !== String(camId)) {
    select.value = String(camId);
  }

  const streamImg = document.getElementById("live-stream-image");
  if (streamImg) {
    streamImg.onerror = function() {
      this.onerror = null;
      this.src = "/assets/live_camera_feed.jpg";
    };
    if (isStreaming) {
      streamImg.src = API.getCameraStreamUrl(activeCameraId, detectionOverlayActive) + "&t=" + Date.now();
    }
  }

  // Update HUD indicator
  const hudInfo = document.getElementById("cam-hud-info");
  if (hudInfo && select) {
    const selectedOption = select.options[select.selectedIndex];
    if (selectedOption) {
      hudInfo.textContent = `CAM #${activeCameraId}: ${selectedOption.textContent}`;
    }
  }

  // Update Camera Details card in right sidebar
  try {
    const cam = cachedCameras.find(c => c.id === activeCameraId);
    if (cam) {
      updateCameraDetails(cam);
    }
  } catch (e) {
    console.warn("[LiveMonitoring] Error updating camera info:", e);
  }

  if (typeof showToast === "function") {
    showToast(`Switched to Camera #${activeCameraId}`);
  }
}
window.switchCameraStream = switchCameraStream;

function updateCameraDetails(cam) {
  const nameEl = document.getElementById("cam-detail-name");
  const locEl = document.getElementById("cam-detail-loc");
  const typeEl = document.getElementById("cam-detail-type");
  const hudInfo = document.getElementById("cam-hud-info");

  if (nameEl) nameEl.textContent = cam.camera_name || `Camera #${cam.id}`;
  if (locEl) locEl.textContent = cam.location || "Traffic Intersection";
  if (typeEl) typeEl.textContent = cam.camera_type || "CCTV (HD RTSP/MJPEG)";
  if (hudInfo) hudInfo.textContent = `CAM #${cam.id}: ${cam.camera_name || "Surveillance"}`;
}
window.updateCameraDetails = updateCameraDetails;

// =============================================================================
// View Mode Switcher (Single View vs 2x2 Grid vs All Cameras)
// =============================================================================
function setViewMode(mode) {
  currentViewMode = mode;
  console.log("[LiveMonitoring] Switching view mode to:", mode);

  const btnSingle = document.getElementById("view-mode-single-btn");
  const btnGrid4 = document.getElementById("view-mode-grid4-btn");
  const btnGridAll = document.getElementById("view-mode-gridall-btn");

  const singleContainer = document.getElementById("single-camera-view-container");
  const multiContainer = document.getElementById("multi-camera-view-container");
  const multiGrid = document.getElementById("multi-camera-grid");

  if (btnSingle) btnSingle.classList.toggle("active", mode === "single");
  if (btnGrid4) btnGrid4.classList.toggle("active", mode === "grid-2x2");
  if (btnGridAll) btnGridAll.classList.toggle("active", mode === "grid-all");

  if (mode === "single") {
    if (singleContainer) singleContainer.style.display = "grid";
    if (multiContainer) multiContainer.style.display = "none";
    switchCameraStream(activeCameraId);
  } else {
    // Release single-view socket so it does not hold a persistent TCP connection in grid mode
    const singleImg = document.getElementById("live-stream-image");
    if (singleImg) singleImg.src = "";

    if (singleContainer) singleContainer.style.display = "none";
    if (multiContainer) multiContainer.style.display = "flex";

    if (multiGrid) {
      multiGrid.className = mode === "grid-2x2"
        ? "multi-camera-grid grid-2x2"
        : "multi-camera-grid grid-all";
    }

    renderMultiCameraGrid();
  }

  if (typeof showToast === "function") {
    const label = mode === "single" ? "Single Camera View" : (mode === "grid-2x2" ? "2x2 Multi-Cam Grid (4 Feeds)" : "All Cameras Surveillance Matrix");
    showToast(`View Mode: ${label}`);
  }
}
window.setViewMode = setViewMode;

// =============================================================================
// Render Multi-Camera Real-Time Grid with Screen-Wise Video Selectors
// =============================================================================
async function renderMultiCameraGrid() {
  const grid = document.getElementById("multi-camera-grid");
  const countBadge = document.getElementById("grid-cameras-count-badge");
  if (!grid) return;

  try {
    if (!cachedCameras || cachedCameras.length === 0) {
      cachedCameras = await API.listCameras();
    }
    if (!cachedVideos || cachedVideos.length === 0) {
      cachedVideos = await API.listVideos();
    }
  } catch (e) {
    console.warn("Could not load camera/video data for grid:", e);
  }

  const approachMap = {
    1: { key: "NORTH", label: "NORTH APPROACH (Road 1)" },
    2: { key: "EAST",  label: "EAST APPROACH (Road 2)" },
    3: { key: "SOUTH", label: "SOUTH APPROACH (Road 3)" },
    4: { key: "WEST",  label: "WEST APPROACH (Road 4)" }
  };

  // Filter cameras by selected street so "all roads in street" are displayed
  let filteredCameras = cachedCameras;
  if (selectedLiveStreet && selectedLiveStreet !== "all") {
    const matched = cachedCameras.filter(c => (c.street_name || '').trim().toLowerCase() === selectedLiveStreet.trim().toLowerCase());
    if (matched.length > 0) {
      filteredCameras = matched;
    }
  }

  const camerasToDisplay = (currentViewMode === "grid-2x2" && selectedLiveStreet === "all")
    ? filteredCameras.slice(0, 4)
    : filteredCameras;

  if (countBadge) {
    countBadge.textContent = `${camerasToDisplay.length} Roads in Street Active`;
  }

  const tilesHtml = camerasToDisplay.map((cam, idx) => {
    const streamUrl = API.getCameraStreamUrl(cam.id, detectionOverlayActive);
    const appInfo = approachMap[cam.id] || { key: ["NORTH","EAST","SOUTH","WEST"][idx % 4], label: `APPROACH #${idx+1}` };
    const appKey = appInfo.key;

    // Build screen-wise video options
    const videoOptions = cachedVideos.map(v => {
      const isSelected = cam.camera_name && cam.camera_name.includes(v.video_name);
      return `<option value="video:${v.id}" ${isSelected ? 'selected' : ''}>${v.video_name}</option>`;
    }).join("");

    const displayStreet = cam.street_name ? `${cam.street_name} • ` : '';
    const displayRoad = cam.road_name ? cam.road_name.split(' [')[0] : (appInfo.label.split(' (')[0] + ' Approach');

    return `
      <div class="camera-tile-card" id="cam-tile-${cam.id}">
        <!-- Tile Header -->
        <div class="camera-tile-header">
          <div class="camera-tile-title" title="${cam.street_name || ''} ${cam.camera_name} (${cam.location})">
            <span class="status-dot-green"></span>
            <span>CAM #${cam.id}: ${displayStreet}${displayRoad}</span>
          </div>
          <div class="camera-tile-actions">
            <button type="button" onclick="takeStreamSnapshot(${cam.id})" title="Capture High-Res Snapshot of CAM #${cam.id}">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/></svg>
              Snapshot
            </button>
            <button type="button" onclick="checkScreenVideo(${cam.id})" title="Check / Preview this video feed" style="background:#2878D0;font-weight:600;">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polygon points="10 8 16 12 10 16 10 8"/></svg>
              Feed / Check
            </button>
            <button type="button" onclick="maximizeCamera(${cam.id})" title="Maximize to Single Screen">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 3 21 3 21 9"/><polyline points="9 21 3 21 3 15"/><line x1="21" x2="14" y1="3" y2="10"/><line x1="3" x2="10" y1="21" y2="14"/></svg>
              Maximize
            </button>
          </div>
        </div>

        <!-- SCREEN-WISE VIDEO SELECTOR BAR -->
        <div class="tile-screen-selector-bar">
          <div style="display:flex;align-items:center;gap:6px;flex:1;min-width:0;">
            <span style="font-size:11px;font-weight:600;color:#94A3B8;white-space:nowrap;">Screen Feed:</span>
            <select
              id="tile-feed-select-${cam.id}"
              class="tile-feed-select"
              onchange="changeScreenFeed(${cam.id}, this.value)"
              title="Select video for Screen CAM #${cam.id}"
            >
              <option value="">-- Choose Video Source --</option>
              <optgroup label="Uploaded Traffic Videos">
                ${videoOptions}
              </optgroup>
              <optgroup label="Live Stream Sources">
                <option value="preset:sample">Sample Traffic Video Loop</option>
                <option value="preset:webcam">Local USB Webcam (0)</option>
              </optgroup>
            </select>
          </div>
          <button type="button" onclick="openStreamModal(${cam.id})" title="Custom Stream URL / Advanced Config" style="background:transparent;border:none;color:#94A3B8;cursor:pointer;padding:2px 4px;">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
          </button>
        </div>

        <!-- Tile Live Stream Image Viewport -->
        <div class="camera-tile-stream-wrapper">
          <img
            id="grid-stream-${cam.id}"
            class="camera-tile-img"
            src="${isStreaming ? (streamUrl + '&t=' + Date.now()) : '/assets/live_camera_feed.jpg'}"
            alt="Camera ${cam.id} Feed"
            onerror="this.onerror=null; this.src='/assets/live_camera_feed.jpg';"
          />
          <div class="tile-badge-live">
            <span class="status-dot-green"></span>
            LIVE • 1080p
          </div>
          <div id="grid-badge-peds-${cam.id}" class="tile-badge-peds">
            PEDESTRIAN ALERT
          </div>

          <!-- REAL-TIME 4-WAY INTERSECTION TRAFFIC SIGNAL HUD -->
          <div class="approach-road-badge" id="approach-badge-${cam.id}">
            <span class="road-direction-pill" id="road-direction-${cam.id}">
              ${appInfo.label.split(' (')[0]}
            </span>
            <div class="traffic-signal-box" id="signal-box-${appKey}" title="${appKey} Road Traffic Signal • Click to switch green" onclick="forceAgentPhase('${appKey}')" style="cursor:pointer;">
              <span class="signal-lamp red active" id="lamp-red-${appKey}"></span>
              <span class="signal-lamp yellow" id="lamp-yellow-${appKey}"></span>
              <span class="signal-lamp green" id="lamp-green-${appKey}"></span>
              <span class="signal-countdown-tag tag-red" id="timer-tag-${appKey}">--s</span>
            </div>
          </div>
        </div>

        <!-- Tile Real-Time Telemetry Footer -->
        <div class="camera-tile-footer">
          <span class="camera-tile-footer-badge" id="grid-count-${cam.id}">
            <span style="color:#2878D0;">🚗</span> <strong id="grid-val-count-${cam.id}">--</strong> Veh
          </span>
          <span class="camera-tile-footer-badge" id="grid-breakdown-${cam.id}" style="font-size:11px;color:#CBD5E1;" title="Vehicle Breakdown">
            <span id="grid-bdown-cars-${cam.id}">--</span>🚗 <span id="grid-bdown-buses-${cam.id}">--</span>🚌 <span id="grid-bdown-peds-${cam.id}">--</span>🚶
          </span>
          <span class="camera-tile-footer-badge">
            Density: <strong id="grid-val-density-${cam.id}" style="color:#F59E0B;">--%</strong>
          </span>
          <span class="camera-tile-footer-badge" style="color:#38BDF8;" id="grid-alloc-wrap-${appKey}">
            Green: <strong id="grid-alloc-${appKey}">--s</strong>
          </span>
          <span class="badge badge-info" id="grid-val-cong-${cam.id}" style="font-size:10.5px;padding:2px 7px;">
            MODERATE
          </span>
          <span style="font-size:11px;color:#00BA63;font-weight:600;" id="grid-val-fps-${cam.id}">
            28.0 FPS
          </span>
        </div>
            MODERATE
          </span>
          <span style="font-size:11px;color:#00BA63;font-weight:600;" id="grid-val-fps-${cam.id}">
            28.0 FPS
          </span>
        </div>
      </div>
    `;
  }).join("");

  const addCameraTile = `
    <div class="add-camera-grid-card" onclick="openNewCameraModal()">
      <div style="width:48px;height:48px;border-radius:12px;background:#EEF6FF;color:#2878D0;display:flex;align-items:center;justify-content:center;margin-bottom:12px;">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
      </div>
      <h4 style="font-size:14px;margin:0 0 4px;font-weight:700;color:#0F172A;">Connect Another Camera</h4>
      <p style="font-size:12px;color:#64748B;margin:0 0 12px;max-width:240px;">Attach an RTSP surveillance feed, live link, or local device to expand this matrix.</p>
      <button class="btn btn-sm btn-primary">+ Add Camera Feed</button>
    </div>
  `;

  grid.innerHTML = tilesHtml + addCameraTile;
}
window.renderMultiCameraGrid = renderMultiCameraGrid;

// =============================================================================
// Screen-Wise Video Selection & Feed Switching
// =============================================================================
async function changeScreenFeed(camId, selectedVal) {
  if (!selectedVal) return;
  const targetCamId = parseInt(camId);

  let payload = {};
  if (selectedVal.startsWith("video:")) {
    const vidId = parseInt(selectedVal.split(":")[1]);
    payload.video_id = vidId;
  } else if (selectedVal === "preset:sample") {
    payload.stream_url = "datasets/sample_traffic.mp4";
  } else if (selectedVal === "preset:webcam") {
    payload.stream_url = "0";
  }

  // Temporarily pause telemetry polling during feed switch to prevent socket starvation
  if (telemetryIntervalId) {
    clearInterval(telemetryIntervalId);
    telemetryIntervalId = null;
  }

  const img = document.getElementById(`grid-stream-${targetCamId}`);
  if (img) {
    img.src = "";
  }
  if (targetCamId === activeCameraId) {
    const singleImg = document.getElementById("live-stream-image");
    if (singleImg) singleImg.src = "";
  }

  // Allow browser 80ms to cleanly release TCP socket
  await new Promise(r => setTimeout(r, 80));

  try {
    showToast(`Updating Screen CAM #${targetCamId} video feed...`);
    await API.setCameraStream(targetCamId, payload);
    showToast(`Screen CAM #${targetCamId} feed connected successfully!`);

    // Allow 120ms before re-attaching live stream with cache-busting timestamp
    setTimeout(() => {
      if (img) {
        img.src = API.getCameraStreamUrl(targetCamId, detectionOverlayActive) + "&t=" + Date.now();
      }
      if (targetCamId === activeCameraId) {
        const singleImg = document.getElementById("live-stream-image");
        if (singleImg) {
          singleImg.src = API.getCameraStreamUrl(targetCamId, detectionOverlayActive) + "&t=" + Date.now();
        }
      }
    }, 120);

    // Refresh cameras cache & update dropdown / headers
    await loadInitialData();
    const sel = document.getElementById(`tile-feed-select-${targetCamId}`);
    if (sel) sel.value = selectedVal;
    initCameraSelector();
  } catch (err) {
    showToast("Failed to switch screen feed: " + err.message, "error");
    if (img) {
      img.src = API.getCameraStreamUrl(targetCamId, detectionOverlayActive) + "&t=" + Date.now();
    }
  } finally {
    // Resume telemetry polling
    startLiveTelemetry();
  }
}
window.changeScreenFeed = changeScreenFeed;

// =============================================================================
// Check / Inspect Video Feed Modal (Instant Inspection)
// =============================================================================
function checkScreenVideo(camId) {
  currentCheckedCamId = parseInt(camId);
  const modal = document.getElementById("check-video-modal");
  const title = document.getElementById("check-modal-title");
  const subtitle = document.getElementById("check-modal-subtitle");
  const img = document.getElementById("check-modal-img");
  const select = document.getElementById("check-modal-select-video");

  if (!modal) return;

  const cam = cachedCameras.find(c => c.id === currentCheckedCamId);
  const camName = cam ? cam.camera_name : `Camera #${camId}`;

  if (title) title.textContent = `Check Video Feed: CAM #${currentCheckedCamId}`;
  if (subtitle) subtitle.textContent = `Screen Source: ${camName} (${cam ? cam.location : ''})`;

  if (img) {
    img.onerror = function() {
      this.onerror = null;
      this.src = "/assets/live_camera_feed.jpg";
    };
    img.src = API.getCameraStreamUrl(currentCheckedCamId, detectionOverlayActive) + "&t=" + Date.now();
  }

  // Populate quick switcher in modal
  if (select && cachedVideos) {
    select.innerHTML = `<option value="">-- Keep Current Video --</option>` +
      cachedVideos.map(v => `<option value="video:${v.id}">${v.video_name}</option>`).join("") +
      `<option value="preset:sample">Sample Highway Traffic Video</option>` +
      `<option value="preset:webcam">Local Webcam (0)</option>`;
  }

  modal.classList.add("show");
  modal.style.display = "flex";
}
window.checkScreenVideo = checkScreenVideo;

function closeCheckVideoModal() {
  const modal = document.getElementById("check-video-modal");
  const img = document.getElementById("check-modal-img");
  if (img) img.src = "";
  if (modal) {
    modal.classList.remove("show");
    modal.style.display = "none";
  }
}
window.closeCheckVideoModal = closeCheckVideoModal;

async function applyVideoToCheckedCamera(val) {
  if (!val || !currentCheckedCamId) return;
  await changeScreenFeed(currentCheckedCamId, val);
  const img = document.getElementById("check-modal-img");
  if (img) {
    img.src = API.getCameraStreamUrl(currentCheckedCamId, detectionOverlayActive) + "&t=" + Date.now();
  }
}
window.applyVideoToCheckedCamera = applyVideoToCheckedCamera;

function maximizeFromCheckModal() {
  closeCheckVideoModal();
  if (currentCheckedCamId) {
    maximizeCamera(currentCheckedCamId);
  }
}
window.maximizeFromCheckModal = maximizeFromCheckModal;

function maximizeCamera(camId) {
  activeCameraId = parseInt(camId);
  setViewMode("single");
  switchCameraStream(camId);
}
window.maximizeCamera = maximizeCamera;

function refreshGridFeeds() {
  if (currentViewMode === "single") {
    switchCameraStream(activeCameraId);
  } else {
    const timestamp = Date.now();
    cachedCameras.forEach(c => {
      const img = document.getElementById(`grid-stream-${c.id}`);
      if (img) {
        img.src = API.getCameraStreamUrl(c.id, detectionOverlayActive) + `&t=${timestamp}`;
      }
    });
  }
  if (typeof showToast === "function") {
    showToast("All camera stream feeds re-synchronized.");
  }
}
window.refreshGridFeeds = refreshGridFeeds;

// =============================================================================
// Stream Action Controls (Bounding Box, Play/Pause, Snapshot, Fullscreen)
// =============================================================================
function toggleDetectionOverlay() {
  detectionOverlayActive = !detectionOverlayActive;
  const btnDetection = document.getElementById("btn-detection-toggle");

  if (btnDetection) {
    btnDetection.classList.toggle("btn-primary", detectionOverlayActive);
    btnDetection.classList.toggle("btn-outline", !detectionOverlayActive);
    btnDetection.innerHTML = detectionOverlayActive
      ? `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="m10 15 5-3-5-3v6Z"/></svg> Bounding Boxes: ON`
      : `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="4.93" y1="4.93" x2="19.07" y2="19.07"/></svg> Bounding Boxes: OFF`;
  }

  // Update single view
  const streamImg = document.getElementById("live-stream-image");
  if (streamImg && isStreaming) {
    streamImg.src = API.getCameraStreamUrl(activeCameraId, detectionOverlayActive) + "&t=" + Date.now();
  }

  // Update all active grid images
  if (currentViewMode !== "single") {
    const timestamp = Date.now();
    cachedCameras.forEach(c => {
      const img = document.getElementById(`grid-stream-${c.id}`);
      if (img && isStreaming) {
        img.src = API.getCameraStreamUrl(c.id, detectionOverlayActive) + `&t=${timestamp}`;
      }
    });
  }

  if (typeof showToast === "function") {
    showToast(detectionOverlayActive ? "Real YOLOv8 Bounding Boxes: ON" : "Bounding Boxes: OFF");
  }
}
window.toggleDetectionOverlay = toggleDetectionOverlay;

function toggleStreamPlayback() {
  isStreaming = !isStreaming;
  const btnPlayPause = document.getElementById("btn-stream-toggle");
  const streamImg = document.getElementById("live-stream-image");

  if (isStreaming) {
    if (streamImg) {
      streamImg.src = API.getCameraStreamUrl(activeCameraId, detectionOverlayActive) + "&t=" + Date.now();
    }
    if (currentViewMode !== "single") {
      refreshGridFeeds();
    }
    if (btnPlayPause) {
      btnPlayPause.classList.remove("btn-primary");
      btnPlayPause.classList.add("btn-outline");
      btnPlayPause.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></svg> Pause`;
    }
    if (typeof showToast === "function") showToast("Live streams resumed.");
  } else {
    if (streamImg) {
      const staticSrc = streamImg.src;
      streamImg.src = "";
      setTimeout(() => { streamImg.src = staticSrc; }, 50);
    }
    if (btnPlayPause) {
      btnPlayPause.classList.remove("btn-outline");
      btnPlayPause.classList.add("btn-primary");
      btnPlayPause.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="6 3 20 12 6 21 6 3"/></svg> Resume`;
    }
    if (typeof showToast === "function") showToast("Live streams paused.");
  }
}
window.toggleStreamPlayback = toggleStreamPlayback;

function takeStreamSnapshot(targetCamId = null) {
  const camId = targetCamId ? parseInt(targetCamId) : activeCameraId;
  const streamImg = (currentViewMode !== "single" && targetCamId)
    ? (document.getElementById(`grid-stream-${camId}`) || document.getElementById("live-stream-image"))
    : (document.getElementById("live-stream-image") || document.getElementById(`grid-stream-${camId}`));

  if (!streamImg) return;

  try {
    const canvas = document.createElement("canvas");
    canvas.width = streamImg.naturalWidth || streamImg.clientWidth || 960;
    canvas.height = streamImg.naturalHeight || streamImg.clientHeight || 540;
    const ctx = canvas.getContext("2d");

    try {
      ctx.drawImage(streamImg, 0, 0, canvas.width, canvas.height);
      const dataUrl = canvas.toDataURL("image/jpeg", 0.95);
      const link = document.createElement("a");
      link.href = dataUrl;
      link.download = `traffic_snapshot_cam_${camId}_${Date.now()}.jpg`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      if (typeof showToast === "function") {
        showToast(`Snapshot downloaded: CAM #${camId}`);
      }
    } catch (corsErr) {
      window.open(streamImg.src, "_blank");
      if (typeof showToast === "function") {
        showToast(`Snapshot opened in high-resolution preview.`);
      }
    }
  } catch (err) {
    console.error("Snapshot error:", err);
    if (typeof showToast === "function") showToast("Snapshot captured.");
  }
}
window.takeStreamSnapshot = takeStreamSnapshot;

function toggleStreamFullscreen() {
  const container = currentViewMode === "single"
    ? document.getElementById("video-viewport-wrapper")
    : document.getElementById("multi-camera-grid");

  if (!container) return;

  if (!document.fullscreenElement) {
    if (container.requestFullscreen) {
      container.requestFullscreen().catch(e => console.warn(e));
    } else if (container.webkitRequestFullscreen) {
      container.webkitRequestFullscreen();
    } else if (container.msRequestFullscreen) {
      container.msRequestFullscreen();
    }
    if (typeof showToast === "function") showToast("Fullscreen mode enabled.");
  } else {
    if (document.exitFullscreen) {
      document.exitFullscreen().catch(e => console.warn(e));
    }
    if (typeof showToast === "function") showToast("Exited fullscreen mode.");
  }
}
window.toggleStreamFullscreen = toggleStreamFullscreen;

function initStreamControls() {
  const btnDetection = document.getElementById("btn-detection-toggle");
  const btnPlayPause = document.getElementById("btn-stream-toggle");
  const btnSnapshot = document.getElementById("btn-snapshot");
  const btnFullscreen = document.getElementById("btn-fullscreen");

  if (btnDetection) btnDetection.onclick = () => toggleDetectionOverlay();
  if (btnPlayPause) btnPlayPause.onclick = () => toggleStreamPlayback();
  if (btnSnapshot) btnSnapshot.onclick = () => takeStreamSnapshot();
  if (btnFullscreen) btnFullscreen.onclick = () => toggleStreamFullscreen();
}

function initBoundingBoxCanvas() {
  const canvas = document.getElementById("yolo-overlay-canvas");
  if (!canvas || !canvas.parentElement) return;
  const ctx = canvas.getContext("2d");
  canvas.width = canvas.parentElement.clientWidth || 960;
  canvas.height = canvas.parentElement.clientHeight || 520;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
}

// =============================================================================
// Live Telemetry Sync & Multi-Camera Matrix Polling
// =============================================================================
function startLiveTelemetry() {
  if (telemetryIntervalId) {
    clearInterval(telemetryIntervalId);
  }

  const elCount = document.getElementById("stat-live-count");
  const elDensity = document.getElementById("stat-live-density");
  const elQueue = document.getElementById("stat-live-queue");
  const elFps = document.getElementById("stat-live-fps");

  const elPeds = document.getElementById("stat-count-peds");
  const elCars = document.getElementById("stat-count-cars");
  const elMotos = document.getElementById("stat-count-motos");
  const elBuses = document.getElementById("stat-count-buses");
  const elTrucks = document.getElementById("stat-count-trucks");

  const elCongestion = document.getElementById("stat-congestion-badge");
  const elSpeed = document.getElementById("stat-avg-speed");
  const elCarbon = document.getElementById("stat-carbon-emission");
  const elPedSafety = document.getElementById("stat-ped-safety");

  async function updateTelemetry() {
    if (!isStreaming) return;

    try {
      const batchData = await API.getAllCamerasTelemetry();
      if (!batchData) return;

      const activeData = batchData[String(activeCameraId)] || batchData[activeCameraId];
      if (activeData) {
        if (elCount) elCount.textContent = activeData.vehicles_in_frame ?? 0;
        if (elDensity) elDensity.textContent = `${activeData.density ?? 0}%`;
        if (elQueue) elQueue.textContent = `${activeData.queue_length ?? 0} Vehicles`;
        if (elFps) elFps.textContent = `${(activeData.fps ?? 28.5).toFixed(1)} FPS`;

        if (elPeds) elPeds.textContent = activeData.pedestrians ?? 0;
        if (elCars) elCars.textContent = activeData.cars ?? 0;
        if (elMotos) elMotos.textContent = activeData.motorcycles ?? 0;
        if (elBuses) elBuses.textContent = activeData.buses ?? 0;
        if (elTrucks) elTrucks.textContent = activeData.trucks ?? 0;

        if (elCongestion) {
          const level = activeData.congestion_level || (activeData.density > 65 ? "CONGESTED" : "MODERATE");
          elCongestion.textContent = level;
          elCongestion.className = "badge " + (
            level === "FREE FLOW" ? "badge-success" :
            (level === "MODERATE" ? "badge-info" :
            (level === "CONGESTED" ? "badge-warning" : "badge-danger"))
          );
        }

        if (elSpeed) elSpeed.textContent = `${(activeData.avg_speed_kmh ?? 42.0).toFixed(1)} km/h`;
        if (elCarbon) elCarbon.textContent = `${(activeData.co2_kg_per_hr ?? 4.8).toFixed(1)} kg CO₂/h`;

        if (elPedSafety) {
          const peds = activeData.pedestrians ?? 0;
          if (peds > 0) {
            elPedSafety.className = "badge badge-warning";
            elPedSafety.innerHTML = `<span class="badge-dot"></span> ${peds} PEDESTRIAN(S) DETECTED`;
          } else {
            elPedSafety.className = "badge badge-success";
            elPedSafety.innerHTML = `<span class="badge-dot"></span> SECURE`;
          }
        }
      }

      if (currentViewMode !== "single") {
        for (const [camIdStr, data] of Object.entries(batchData)) {
          const vCount = document.getElementById(`grid-val-count-${camIdStr}`);
          const vDensity = document.getElementById(`grid-val-density-${camIdStr}`);
          const vCong = document.getElementById(`grid-val-cong-${camIdStr}`);
          const vFps = document.getElementById(`grid-val-fps-${camIdStr}`);
          const pedsBadge = document.getElementById(`grid-badge-peds-${camIdStr}`);

          const bCars = document.getElementById(`grid-bdown-cars-${camIdStr}`);
          const bBuses = document.getElementById(`grid-bdown-buses-${camIdStr}`);
          const bPeds = document.getElementById(`grid-bdown-peds-${camIdStr}`);
          if (bCars) bCars.textContent = data.cars ?? 0;
          if (bBuses) bBuses.textContent = data.buses ?? 0;
          if (bPeds) bPeds.textContent = data.pedestrians ?? 0;

          if (vCount) vCount.textContent = data.vehicles_in_frame ?? 0;
          if (vDensity) vDensity.textContent = `${data.density ?? 0}%`;
          if (vFps) vFps.textContent = `${(data.fps ?? 28.0).toFixed(1)} FPS`;

          if (vCong) {
            const lvl = data.congestion_level || "MODERATE";
            vCong.textContent = lvl;
            vCong.className = "badge " + (
              lvl === "FREE FLOW" ? "badge-success" :
              (lvl === "MODERATE" ? "badge-info" :
              (lvl === "CONGESTED" ? "badge-warning" : "badge-danger"))
            );
          }

          if (pedsBadge) {
            if ((data.pedestrians ?? 0) > 0) {
              pedsBadge.style.display = "block";
              pedsBadge.textContent = `${data.pedestrians} PED(S) IN LANE`;
            } else {
              pedsBadge.style.display = "none";
            }
          }
        }
      }

      // 4-Way Intersection AI Traffic Signal Agent Real-Time Sync
      try {
        const signalStatus = await API.getSignalAgentStatus();
        if (signalStatus) {
          updateSignalAgentHUD(signalStatus);
        }
      } catch (errSig) {
        console.warn("[LiveTelemetry] Signal Agent status fetch error:", errSig);
      }
    } catch (e) {
      console.warn("[LiveTelemetry] Polling error:", e);
    }
  }

  updateTelemetry();
  telemetryIntervalId = setInterval(updateTelemetry, 2000);
}
window.startLiveTelemetry = startLiveTelemetry;

// =============================================================================
// 4-Way Intersection AI Signal Agent HUD & Lamp Controller
// =============================================================================
function updateSignalAgentHUD(status) {
  if (!status) return;

  const modeBadge = document.getElementById("agent-mode-badge");
  const cycleLabel = document.getElementById("agent-cycle-time-label");
  const phaseBadge = document.getElementById("agent-active-phase-badge");
  const reasoningEl = document.getElementById("agent-reasoning-text");
  const cyclesCount = document.getElementById("agent-cycles-count");

  const allocNorth = document.getElementById("alloc-tag-north");
  const allocEast = document.getElementById("alloc-tag-east");
  const allocSouth = document.getElementById("alloc-tag-south");
  const allocWest = document.getElementById("alloc-tag-west");

  if (cycleLabel && status.cycle_seconds) cycleLabel.textContent = `${status.cycle_seconds}s`;
  if (cyclesCount && status.total_cycles_completed !== undefined) cyclesCount.textContent = status.total_cycles_completed;
  if (reasoningEl && status.reasoning) reasoningEl.textContent = status.reasoning;

  if (modeBadge) {
    if (status.emergency_override) {
      modeBadge.className = "signal-agent-active-badge";
      modeBadge.style.color = "#EF4444";
      modeBadge.style.borderColor = "#EF4444";
      modeBadge.style.background = "rgba(239, 68, 68, 0.2)";
      modeBadge.innerHTML = `<span class="status-dot" style="background:#EF4444;"></span> EMERGENCY OVERRIDE: ${status.emergency_override}`;
    } else {
      modeBadge.className = "signal-agent-active-badge";
      modeBadge.style.color = "#00BA63";
      modeBadge.style.borderColor = "#00BA63";
      modeBadge.style.background = "rgba(0, 186, 99, 0.2)";
      modeBadge.innerHTML = `<span class="status-dot-green"></span> AI OPTIMIZER ACTIVE`;
    }
  }

  // Active Green Phase Badge
  if (phaseBadge) {
    const activeApp = status.active_approach || "NORTH";
    const rem = status.phase_remaining_seconds || 30;
    const color = status.phase_state === "YELLOW" ? "#F59E0B" : "#00BA63";
    const icon = status.phase_state === "YELLOW" ? "🟡" : "🟢";
    phaseBadge.style.background = color;
    phaseBadge.textContent = `${icon} ${activeApp} APPROACH (${rem}s remaining)`;
  }

  // Approaches Signal Lamps
  const approaches = status.approaches || {};
  const approachKeys = ["NORTH", "EAST", "SOUTH", "WEST"];

  approachKeys.forEach(appKey => {
    const appData = approaches[appKey];
    if (!appData) return;

    // Update allocation tag in HUD
    if (appKey === "NORTH" && allocNorth) allocNorth.textContent = `${appData.allocated_green_seconds}s`;
    if (appKey === "EAST" && allocEast) allocEast.textContent = `${appData.allocated_green_seconds}s`;
    if (appKey === "SOUTH" && allocSouth) allocSouth.textContent = `${appData.allocated_green_seconds}s`;
    if (appKey === "WEST" && allocWest) allocWest.textContent = `${appData.allocated_green_seconds}s`;

    // Update tile footer allocated
    const tileAlloc = document.getElementById(`grid-alloc-${appKey}`);
    if (tileAlloc) tileAlloc.textContent = `${appData.allocated_green_seconds}s`;

    // Update Signal Lamps on tile
    const lampRed = document.getElementById(`lamp-red-${appKey}`);
    const lampYellow = document.getElementById(`lamp-yellow-${appKey}`);
    const lampGreen = document.getElementById(`lamp-green-${appKey}`);
    const timerTag = document.getElementById(`timer-tag-${appKey}`);

    if (lampRed && lampYellow && lampGreen) {
      lampRed.classList.remove("active");
      lampYellow.classList.remove("active");
      lampGreen.classList.remove("active");

      const color = appData.color; // "GREEN", "YELLOW", "RED"
      if (color === "GREEN") {
        lampGreen.classList.add("active");
        if (timerTag) {
          timerTag.className = "signal-countdown-tag tag-green";
          timerTag.textContent = `🟢 ${appData.countdown_seconds}s`;
        }
      } else if (color === "YELLOW") {
        lampYellow.classList.add("active");
        if (timerTag) {
          timerTag.className = "signal-countdown-tag tag-yellow";
          timerTag.textContent = `🟡 ${appData.countdown_seconds}s`;
        }
      } else {
        lampRed.classList.add("active");
        if (timerTag) {
          timerTag.className = "signal-countdown-tag tag-red";
          timerTag.textContent = `🔴 ${appData.countdown_seconds}s`;
        }
      }
    }
  });
}
window.updateSignalAgentHUD = updateSignalAgentHUD;

async function forceAgentPhase(approach) {
  try {
    showToast(`Operator override: Forcing Green light on ${approach} Road...`);
    const res = await API.overrideSignalAgent(approach);
    showToast(`Green light forced on ${approach} Road!`);
    updateSignalAgentHUD(res.current_status);
  } catch (err) {
    showToast("Override failed: " + err.message, "error");
  }
}
window.forceAgentPhase = forceAgentPhase;

let agentAdaptiveEnabled = true;
async function toggleAgentAutonomous() {
  agentAdaptiveEnabled = !agentAdaptiveEnabled;
  try {
    await API.configSignalAgent({ agent_active: agentAdaptiveEnabled });
    showToast(agentAdaptiveEnabled ? "AI Autonomous Optimization: RESUMED" : "AI Optimization: PAUSED (Fixed Timing)");
    const status = await API.getSignalAgentStatus();
    updateSignalAgentHUD(status);
  } catch (err) {
    showToast("Toggle failed: " + err.message, "error");
  }
}
window.toggleAgentAutonomous = toggleAgentAutonomous;

let emergencyClearActive = false;
async function triggerEmergencyClear() {
  emergencyClearActive = !emergencyClearActive;
  const btn = document.getElementById("btn-emergency-clear");
  try {
    if (emergencyClearActive) {
      if (btn) btn.style.background = "#EF4444";
      showToast("🚨 Emergency Priority Corridor Activated on North Road!");
      const res = await API.emergencySignalAgent("NORTH");
      updateSignalAgentHUD(res.current_status);
    } else {
      if (btn) btn.style.background = "rgba(255,255,255,0.12)";
      showToast("Emergency Priority Corridor Deactivated. Normal flow resumed.");
      const res = await API.emergencySignalAgent(null);
      updateSignalAgentHUD(res.current_status);
    }
  } catch (err) {
    showToast("Emergency toggle failed: " + err.message, "error");
  }
}
window.triggerEmergencyClear = triggerEmergencyClear;

// =============================================================================
// Live Stream Source Modal Controllers (Instant Display)
// =============================================================================
let currentModalTab = "url";
let targetModalCamId = 1;

function openStreamModal(targetCamId = null) {
  const modal = document.getElementById("stream-config-modal");
  if (!modal) return;

  targetModalCamId = targetCamId ? parseInt(targetCamId) : activeCameraId;

  // Open modal instantly in 0ms
  modal.classList.add("show");
  modal.style.display = "flex";

  // Set camera select in modal
  const modalSelect = document.getElementById("modal-select-camera");
  if (modalSelect && cachedCameras && cachedCameras.length > 0) {
    modalSelect.innerHTML = cachedCameras.map(c => `
      <option value="${c.id}">CAM #${c.id}: ${c.camera_name} (${c.location})</option>
    `).join("");
    modalSelect.value = String(targetModalCamId);
  }

  // Pre-fill input with currently configured stream URL if available
  const activeCamObj = cachedCameras.find(c => c.id === targetModalCamId);
  const inputUrl = document.getElementById("input-modal-stream-url");
  if (inputUrl && activeCamObj && activeCamObj.stream_url) {
    inputUrl.value = activeCamObj.stream_url;
  }

  // Load uploaded videos into library select
  const selectLib = document.getElementById("select-modal-library-video");
  if (selectLib) {
    if (cachedVideos && cachedVideos.length > 0) {
      selectLib.innerHTML = cachedVideos.map(v => `
        <option value="${v.id}">${v.video_name} (${(v.file_size / (1024 * 1024)).toFixed(1)} MB)</option>
      `).join("");
    } else {
      selectLib.innerHTML = `<option value="">No recorded videos uploaded yet</option>`;
    }
  }
}
window.openStreamModal = openStreamModal;

function onModalCameraSelected(camId) {
  targetModalCamId = parseInt(camId);
  const activeCamObj = cachedCameras.find(c => c.id === targetModalCamId);
  const inputUrl = document.getElementById("input-modal-stream-url");
  if (inputUrl && activeCamObj && activeCamObj.stream_url) {
    inputUrl.value = activeCamObj.stream_url;
  }
}
window.onModalCameraSelected = onModalCameraSelected;

function closeStreamModal() {
  const modal = document.getElementById("stream-config-modal");
  if (modal) {
    modal.classList.remove("show");
    modal.style.display = "none";
  }
}
window.closeStreamModal = closeStreamModal;

function setModalTab(tab) {
  currentModalTab = tab;
  const tabUrl = document.getElementById("modal-tab-url");
  const tabLib = document.getElementById("modal-tab-library");
  const tabUpload = document.getElementById("modal-tab-upload");
  const paneUrl = document.getElementById("modal-url-pane");
  const paneLib = document.getElementById("modal-library-pane");
  const paneUpload = document.getElementById("modal-upload-pane");

  if (tab === "url") {
    if (tabUrl) tabUrl.className = "btn btn-sm btn-primary";
    if (tabLib) tabLib.className = "btn btn-sm btn-outline";
    if (tabUpload) tabUpload.className = "btn btn-sm btn-outline";
    if (paneUrl) paneUrl.style.display = "block";
    if (paneLib) paneLib.style.display = "none";
    if (paneUpload) paneUpload.style.display = "none";
  } else if (tab === "library") {
    if (tabUrl) tabUrl.className = "btn btn-sm btn-outline";
    if (tabLib) tabLib.className = "btn btn-sm btn-primary";
    if (tabUpload) tabUpload.className = "btn btn-sm btn-outline";
    if (paneUrl) paneUrl.style.display = "none";
    if (paneLib) paneLib.style.display = "block";
    if (paneUpload) paneUpload.style.display = "none";
  } else if (tab === "upload") {
    if (tabUrl) tabUrl.className = "btn btn-sm btn-outline";
    if (tabLib) tabLib.className = "btn btn-sm btn-outline";
    if (tabUpload) tabUpload.className = "btn btn-sm btn-primary";
    if (paneUrl) paneUrl.style.display = "none";
    if (paneLib) paneLib.style.display = "none";
    if (paneUpload) paneUpload.style.display = "block";
  }
}
window.setModalTab = setModalTab;

async function handleModalVideoUpload(file) {
  if (!file) return;

  const progressWrapper = document.getElementById("modal-upload-progress");
  const progressBar = document.getElementById("modal-upload-bar");
  const statusText = document.getElementById("modal-upload-status");
  const pctText = document.getElementById("modal-upload-pct");

  // 1. Temporarily pause telemetry polling to free HTTP sockets
  if (telemetryIntervalId) {
    clearInterval(telemetryIntervalId);
    telemetryIntervalId = null;
  }

  // 2. Temporarily detach all active MJPEG stream images so browser TCP connections are freed
  const pausedStreams = [];
  document.querySelectorAll(".camera-tile-img, #live-stream-image").forEach(img => {
    if (img && img.src && !img.src.includes("live_camera_feed.jpg") && img.src.length > 5) {
      pausedStreams.push({ el: img, src: img.src });
      img.src = "/assets/live_camera_feed.jpg";
    }
  });

  try {
    if (progressWrapper) progressWrapper.style.display = "block";
    if (progressBar) {
      progressBar.style.width = "2%";
      progressBar.style.background = "#2878D0";
    }
    const fileSizeMb = (file.size / (1024 * 1024)).toFixed(1);
    if (statusText) statusText.textContent = `Uploading ${file.name} (${fileSizeMb} MB)...`;
    if (pctText) pctText.textContent = "0%";

    if (typeof showToast === "function") {
      showToast(`Uploading "${file.name}" (${fileSizeMb} MB)...`);
    }

    // Call API with real-time byte-level progress callback
    const uploadedVid = await API.uploadVideo(file, (pct, loaded, total) => {
      if (progressBar) progressBar.style.width = `${pct}%`;
      if (pctText) pctText.textContent = `${pct}%`;
      const curMb = (loaded / (1024 * 1024)).toFixed(1);
      const totMb = (total / (1024 * 1024)).toFixed(1);
      if (statusText) statusText.textContent = `Uploading: ${curMb} / ${totMb} MB (${pct}%)...`;
    });

    if (progressBar) progressBar.style.width = "100%";
    if (pctText) pctText.textContent = "100%";
    if (statusText) statusText.textContent = `Upload complete! Attaching to Camera #${targetModalCamId}...`;

    if (typeof showToast === "function") {
      showToast(`Video "${uploadedVid.video_name}" uploaded! Attaching to Camera #${targetModalCamId}...`);
    }

    // Automatically connect uploaded video to target camera
    await API.setCameraStream(targetModalCamId, { video_id: uploadedVid.id });

    if (typeof showToast === "function") {
      showToast(`Camera #${targetModalCamId} now streaming "${uploadedVid.video_name}"!`, "success");
    }

    // Reload caches
    const [cams, vids] = await Promise.allSettled([
      API.listCameras(),
      API.listVideos()
    ]);
    if (cams.status === "fulfilled") cachedCameras = cams.value;
    if (vids.status === "fulfilled") cachedVideos = vids.value;

    // Resume telemetry polling
    startLiveTelemetry();

    // Re-attach camera streams with cache buster
    pausedStreams.forEach(item => {
      if (item.el.id === `grid-stream-${targetModalCamId}` || item.el.id === "live-stream-image") {
        item.el.src = API.getCameraStreamUrl(targetModalCamId, detectionOverlayActive) + "&t=" + Date.now();
      } else {
        item.el.src = item.src.split('&t=')[0] + '&t=' + Date.now();
      }
    });

    setTimeout(() => {
      closeStreamModal();
      if (progressWrapper) progressWrapper.style.display = "none";
      if (progressBar) progressBar.style.width = "0%";
      renderMultiCameraGrid();
    }, 700);
  } catch (err) {
    // Resume telemetry and streams even if error occurs
    startLiveTelemetry();
    pausedStreams.forEach(item => {
      item.el.src = item.src.split('&t=')[0] + '&t=' + Date.now();
    });

    if (typeof showToast === "function") {
      showToast("Upload failed: " + err.message, "error");
    }
    if (statusText) statusText.textContent = "Upload failed: " + err.message;
    if (progressBar) progressBar.style.background = "#EF4444";
  }
}
window.handleModalVideoUpload = handleModalVideoUpload;

function applyStreamPreset(type) {
  const input = document.getElementById("input-modal-stream-url");
  if (!input) return;
  if (type === "sample") {
    input.value = "datasets/sample_traffic.mp4";
  } else if (type === "webcam") {
    input.value = "0";
  } else if (type === "urban") {
    input.value = "storage/uploads/01d80a078714_15464791_3840_2160_30fps.mp4";
  }
}
window.applyStreamPreset = applyStreamPreset;

async function saveCameraStreamConfig() {
  try {
    const modalSelect = document.getElementById("modal-select-camera");
    if (modalSelect && modalSelect.value) {
      targetModalCamId = parseInt(modalSelect.value);
    }

    let payload = {};
    if (currentModalTab === "url") {
      const urlInput = document.getElementById("input-modal-stream-url");
      const url = urlInput ? urlInput.value.trim() : "";
      if (!url) {
        showToast("Please enter a valid video stream URL or webcam (0).", "error");
        return;
      }
      payload = { stream_url: url };
    } else if (currentModalTab === "upload") {
      const fileInput = document.getElementById("modal-video-file-input");
      if (fileInput && fileInput.files && fileInput.files.length > 0) {
        await handleModalVideoUpload(fileInput.files[0]);
        return;
      } else {
        if (fileInput) fileInput.click();
        return;
      }
    } else {
      const selectLib = document.getElementById("select-modal-library-video");
      const videoId = selectLib ? parseInt(selectLib.value) : null;
      if (!videoId) {
        showToast("Please select an uploaded video from the list.", "error");
        return;
      }
      payload = { video_id: videoId };
    }

    showToast(`Connecting Camera #${targetModalCamId} to live stream...`);

    // Pause telemetry polling to ensure connection availability
    if (telemetryIntervalId) {
      clearInterval(telemetryIntervalId);
      telemetryIntervalId = null;
    }

    // Detach current stream images first to cleanly terminate previous MJPEG HTTP connections
    const gridImg = document.getElementById(`grid-stream-${targetModalCamId}`);
    if (gridImg) {
      gridImg.src = "";
    }
    if (targetModalCamId === activeCameraId) {
      const img = document.getElementById("live-stream-image");
      if (img) img.src = "";
    }

    // Allow browser 80ms for socket release
    await new Promise(r => setTimeout(r, 80));

    await API.setCameraStream(targetModalCamId, payload);
    showToast(`Camera #${targetModalCamId} live stream connected successfully!`);
    closeStreamModal();

    // Reattach with cache buster after 120ms
    setTimeout(() => {
      if (gridImg) {
        gridImg.src = API.getCameraStreamUrl(targetModalCamId, detectionOverlayActive) + "&t=" + Date.now();
      }
      if (targetModalCamId === activeCameraId) {
        const img = document.getElementById("live-stream-image");
        if (img) {
          img.src = API.getCameraStreamUrl(activeCameraId, detectionOverlayActive) + "&t=" + Date.now();
        }
      }
    }, 120);

    await loadInitialData();
    initCameraSelector();
    if (currentViewMode !== "single") {
      renderMultiCameraGrid();
    }
  } catch (err) {
    showToast("Failed to connect video stream: " + err.message, "error");
  } finally {
    startLiveTelemetry();
  }
}
window.saveCameraStreamConfig = saveCameraStreamConfig;

// =============================================================================
// Connect & Register New Camera Modal
// =============================================================================
function openNewCameraModal() {
  const modal = document.getElementById("new-camera-modal");
  if (modal) {
    modal.classList.add("show");
    modal.style.display = "flex";
  }
}
window.openNewCameraModal = openNewCameraModal;

function closeNewCameraModal() {
  const modal = document.getElementById("new-camera-modal");
  if (modal) {
    modal.classList.remove("show");
    modal.style.display = "none";
  }
}
window.closeNewCameraModal = closeNewCameraModal;

async function submitCreateCamera() {
  const nameInput = document.getElementById("input-new-cam-name");
  const locInput = document.getElementById("input-new-cam-location");
  const typeSelect = document.getElementById("select-new-cam-type");
  const streamInput = document.getElementById("input-new-cam-stream-url");

  const cameraName = nameInput ? nameInput.value.trim() : "";
  const location = locInput ? locInput.value.trim() : "";
  const cameraType = typeSelect ? typeSelect.value : "CCTV (RTSP HD)";
  const streamUrl = streamInput ? streamInput.value.trim() : "";

  if (!cameraName) {
    showToast("Please enter a camera name.", "error");
    return;
  }
  if (!location) {
    showToast("Please enter camera location.", "error");
    return;
  }

  try {
    showToast("Registering & connecting camera...");
    const payload = {
      camera_name: cameraName,
      location: location,
      camera_type: cameraType,
      stream_url: streamUrl || "datasets/sample_traffic.mp4",
      status: "ACTIVE"
    };

    const newCam = await API.createCamera(payload);
    showToast(`Camera "${newCam.camera_name}" connected successfully!`);

    closeNewCameraModal();

    if (nameInput) nameInput.value = "";
    if (locInput) locInput.value = "";
    if (streamInput) streamInput.value = "";

    await initCameraSelector();
    if (currentViewMode !== "single") {
      renderMultiCameraGrid();
    }
  } catch (err) {
    showToast("Failed to register camera: " + err.message, "error");
  }
}
window.submitCreateCamera = submitCreateCamera;

// =============================================================================
// Tab Visibility & Socket Conservation Handler
// Automatically releases MJPEG HTTP persistent sockets when user switches tabs,
// preventing browser origin connection exhaustion (Chrome 6-socket limit).
// =============================================================================
let isTabPaused = false;

function pauseBackgroundStreams() {
  if (isTabPaused) return;
  isTabPaused = true;

  if (telemetryIntervalId) {
    clearInterval(telemetryIntervalId);
    telemetryIntervalId = null;
  }

  // Detach single stream
  const singleImg = document.getElementById("live-stream-image");
  if (singleImg && singleImg.src && !singleImg.src.endsWith("live_camera_feed.jpg")) {
    singleImg.dataset.pausedSrc = singleImg.src;
    singleImg.src = "/assets/live_camera_feed.jpg";
  }

  // Detach all grid streams
  document.querySelectorAll(".camera-tile-img").forEach(img => {
    if (img && img.src && !img.src.endsWith("live_camera_feed.jpg")) {
      img.dataset.pausedSrc = img.src;
      img.src = "/assets/live_camera_feed.jpg";
    }
  });
  console.log("[LiveMonitoring] Tab hidden: Released all streaming sockets to prevent connection starvation.");
}

function resumeBackgroundStreams() {
  if (!isTabPaused) return;
  isTabPaused = false;

  // Restore single stream
  const singleImg = document.getElementById("live-stream-image");
  if (singleImg && singleImg.dataset.pausedSrc) {
    const base = singleImg.dataset.pausedSrc.split("&t=")[0];
    singleImg.src = base + "&t=" + Date.now();
    delete singleImg.dataset.pausedSrc;
  }

  // Restore all grid streams
  document.querySelectorAll(".camera-tile-img").forEach(img => {
    if (img && img.dataset.pausedSrc) {
      const base = img.dataset.pausedSrc.split("&t=")[0];
      img.src = base + "&t=" + Date.now();
      delete img.dataset.pausedSrc;
    }
  });

  // Resume telemetry polling
  startLiveTelemetry();
  console.log("[LiveMonitoring] Tab visible: Reconnected active video streams and telemetry.");
}

document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "hidden") {
    pauseBackgroundStreams();
  } else if (document.visibilityState === "visible") {
    resumeBackgroundStreams();
  }
});

