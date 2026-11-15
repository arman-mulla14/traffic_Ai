/**
 * AI-Based Traffic Management System - Camera Management Logic (v5.0 Enterprise)
 * Handles camera registration, status badges, stream preview, video attachment, and live screen sharing.
 */

let cachedCameras = [];
let currentTestCamId = 1;

document.addEventListener("DOMContentLoaded", () => {
  loadCameras();
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
      tbody.innerHTML = `<tr><td colspan="7" style="text-align:center;padding:24px;color:#64748B;">No cameras registered. Click "+ Add Camera" to register a feed.</td></tr>`;
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

      const streamDisplay = c.stream_url ? (c.stream_url === "0" ? "Webcam #0" : c.stream_url) : "Sample Loop";
      const dateStr = c.created_at ? new Date(c.created_at).toLocaleDateString() : "Recent";

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
          <td>${c.location}</td>
          <td><code style="background:#F1F5F9;padding:2px 6px;border-radius:4px;font-size:12px;color:#12345A;">${streamDisplay}</code></td>
          <td>${c.camera_type || "CCTV"}</td>
          <td>${statusBadge}</td>
          <td>${dateStr}</td>
          <td>
            <div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;">
              <button class="btn btn-sm btn-outline" onclick="openTestFeedModal(${c.id})" title="Preview Feed on Screen">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="6 3 20 12 6 21 6 3"/></svg>
                Preview
              </button>
              <button class="btn btn-sm btn-primary" onclick="viewOnLiveScreen(${c.id})" title="View Camera on Live Monitoring Screen">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></svg>
                Live Screen
              </button>
              <button class="btn btn-sm btn-outline" onclick="openShareModal(${c.id})" title="Attach Video or Live Stream to Camera">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m16 13 5.223 3.482a.5.5 0 0 0 .777-.416V7.87a.5.5 0 0 0-.752-.432L16 10.5"/><rect x="2" y="6" width="14" height="12" rx="2"/></svg>
                Attach Video
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
    tbody.innerHTML = `<tr><td colspan="7" style="text-align:center;padding:24px;color:var(--danger);">Error loading camera list.</td></tr>`;
  }
}
window.loadCameras = loadCameras;

function viewOnLiveScreen(camId) {
  window.location.href = `/frontend/pages/live-monitoring.html?camera=${camId}`;
}
window.viewOnLiveScreen = viewOnLiveScreen;

function openCurrentTestOnLiveScreen() {
  if (currentTestCamId) {
    viewOnLiveScreen(currentTestCamId);
  } else {
    window.location.href = "/frontend/pages/live-monitoring.html";
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
      this.src = "/frontend/assets/live_camera_feed.jpg";
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
    // Redirect to live screen to watch immediately
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
      const loc = document.getElementById("new-cam-loc")?.value.trim();
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
          location: loc,
          camera_type: type,
          stream_url: url,
          status: status
        });
        showToast(`Camera "${name}" registered successfully!`);
        closeAddCameraModal();
        loadCameras();
      } catch (err) {
        showToast("Failed to register camera: " + err.message, "error");
      } finally {
        saveBtn.disabled = false;
      }
    });
  }
}

function closeAddCameraModal() {
  const modal = document.getElementById("add-camera-modal");
  if (modal) {
    modal.classList.remove("show");
    modal.style.display = "none";
  }
}
window.closeAddCameraModal = closeAddCameraModal;

async function deleteCameraAction(id) {
  if (!confirm(`Are you sure you want to delete Camera #${id}?`)) return;
  try {
    await API.deleteCamera(id);
    showToast(`Camera #${id} deleted.`);
    loadCameras();
  } catch (err) {
    showToast("Failed to delete camera: " + err.message, "error");
  }
}
window.deleteCameraAction = deleteCameraAction;
