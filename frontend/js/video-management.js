/**
 * AI-Based Traffic Management System - Video Management Logic (v5.0 Enterprise)
 * Handles video file uploads, processing queue, library table, preview modal, and streaming video to live camera screen.
 */

let cachedVideos = [];
let currentPreviewVideoId = null;

document.addEventListener("DOMContentLoaded", () => {
  loadVideos();
  initUploadForm();
});

async function loadVideos() {
  const tbody = document.getElementById("videos-table-tbody");
  if (!tbody) return;

  try {
    const videos = await API.listVideos();
    cachedVideos = videos || [];
    window.allVideos = cachedVideos;

    if (!cachedVideos || cachedVideos.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align:center;padding:24px;color:#64748B;">No video files found. Upload a video above to begin AI analysis.</td></tr>`;
      return;
    }

    tbody.innerHTML = cachedVideos.map(v => {
      const sizeMb = (v.file_size / (1024 * 1024)).toFixed(1);
      const durationSec = Math.round(v.duration || 0);
      const uploadDate = v.uploaded_at ? new Date(v.uploaded_at).toLocaleDateString() : "Recent";
      
      let badgeClass = "badge-secondary";
      if (v.status === "COMPLETED") badgeClass = "badge-success";
      else if (v.status === "PROCESSING") badgeClass = "badge-info";
      else if (v.status === "FAILED") badgeClass = "badge-danger";

      return `
        <tr>
          <td>
            <div style="display:flex;align-items:center;gap:12px;">
              <div style="width:36px;height:36px;border-radius:6px;background:#F1F5F9;display:flex;align-items:center;justify-content:center;color:#2878D0;flex-shrink:0;">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m16 13 5.223 3.482a.5.5 0 0 0 .777-.416V7.87a.5.5 0 0 0-.752-.432L16 10.5"/><rect x="2" y="6" width="14" height="12" rx="2"/></svg>
              </div>
              <div>
                <strong style="color:var(--text-primary);display:block;font-size:13.5px;">${v.video_name}</strong>
                <span style="color:var(--text-secondary);font-size:11.5px;">ID: #${v.id}</span>
              </div>
            </div>
          </td>
          <td>${durationSec}s</td>
          <td>${sizeMb} MB</td>
          <td>${uploadDate}</td>
          <td>
            <span class="badge ${badgeClass}">
              <span class="badge-dot"></span>
              ${v.status}
            </span>
          </td>
          <td>
            <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;">
              <button class="btn btn-sm btn-outline" onclick="openVideoModal(${v.id})" title="Preview video">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/></svg>
                Preview
              </button>

              <button class="btn btn-sm btn-primary" onclick="openStreamToScreenModal(${v.id})" title="Stream this video on Live Surveillance Screen">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></svg>
                Stream to Screen
              </button>

              ${v.status !== 'COMPLETED' && v.status !== 'PROCESSING' ? `
                <button class="btn btn-sm btn-outline" onclick="triggerProcessVideo(${v.id})">
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="6 3 20 12 6 21 6 3"/></svg>
                  Process
                </button>
              ` : ''}

              <button class="btn btn-sm btn-outline" style="color:var(--danger);" onclick="deleteVideoRecord(${v.id})" title="Delete video">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/></svg>
              </button>
            </div>
          </td>
        </tr>
      `;
    }).join("");
  } catch (err) {
    console.error("Failed to load videos:", err);
    tbody.innerHTML = `<tr><td colspan="6" style="text-align:center;padding:24px;color:var(--danger);">Error loading video library.</td></tr>`;
  }
}
window.loadVideos = loadVideos;

function initUploadForm() {
  const dropzone = document.getElementById("video-dropzone");
  const fileInput = document.getElementById("video-file-input");
  const uploadBtn = document.getElementById("video-upload-btn");
  const progressWrapper = document.getElementById("upload-progress-wrapper");
  const progressBar = document.getElementById("upload-progress-bar");
  const selectedName = document.getElementById("selected-file-name");

  if (!dropzone || !fileInput) return;

  dropzone.addEventListener("click", (e) => {
    // If click is on or inside upload button, do not trigger file input again
    if (e.target && (e.target.id === "video-upload-btn" || e.target.closest("#video-upload-btn"))) {
      return;
    }
    fileInput.click();
  });

  dropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropzone.style.borderColor = "var(--primary-color)";
    dropzone.style.backgroundColor = "rgba(40,120,208,0.05)";
  });

  dropzone.addEventListener("dragleave", () => {
    dropzone.style.borderColor = "#CBD5E1";
    dropzone.style.backgroundColor = "transparent";
  });

  dropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropzone.style.borderColor = "#CBD5E1";
    dropzone.style.backgroundColor = "transparent";
    if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      fileInput.files = e.dataTransfer.files;
      handleFileSelected(fileInput.files[0]);
    }
  });

  fileInput.addEventListener("change", () => {
    if (fileInput.files && fileInput.files.length > 0) {
      handleFileSelected(fileInput.files[0]);
    }
  });

  async function handleFileSelected(file) {
    if (!file) return;
    if (selectedName) {
      selectedName.textContent = `Selected: ${file.name} (${(file.size / (1024 * 1024)).toFixed(1)} MB)`;
      selectedName.style.display = "block";
    }
    if (uploadBtn) {
      uploadBtn.disabled = false;
      uploadBtn.textContent = "Start Upload";
    }
    // Automatically perform the upload directly
    await executeUpload(file);
  }

  async function executeUpload(file) {
    if (!file) return;
    if (uploadBtn) {
      uploadBtn.disabled = true;
      uploadBtn.textContent = "Uploading (0%)...";
    }
    if (progressWrapper) progressWrapper.style.display = "block";
    if (progressBar) progressBar.style.width = "2%";

    try {
      const fileSizeMb = (file.size / (1024 * 1024)).toFixed(1);
      showToast(`Uploading "${file.name}" (${fileSizeMb} MB)...`);

      const video = await API.uploadVideo(file, (pct, loaded, total) => {
        if (progressBar) progressBar.style.width = `${pct}%`;
        const curMb = (loaded / (1024 * 1024)).toFixed(1);
        const totMb = (total / (1024 * 1024)).toFixed(1);
        if (uploadBtn) uploadBtn.textContent = `Uploading ${pct}% (${curMb}/${totMb} MB)...`;
      });

      if (progressBar) progressBar.style.width = "100%";
      if (uploadBtn) uploadBtn.textContent = "Upload Complete!";
      showToast(`Video "${video.video_name}" uploaded successfully!`, "success");

      setTimeout(() => {
        if (progressWrapper) progressWrapper.style.display = "none";
        if (progressBar) progressBar.style.width = "0%";
        if (selectedName) {
          selectedName.textContent = "";
          selectedName.style.display = "none";
        }
        fileInput.value = "";
        if (uploadBtn) {
          uploadBtn.disabled = true;
          uploadBtn.textContent = "Start Upload";
        }
        loadVideos();
      }, 700);
    } catch (err) {
      showToast("Upload failed: " + err.message, "error");
      if (uploadBtn) {
        uploadBtn.disabled = false;
        uploadBtn.textContent = "Retry Upload";
      }
      if (progressWrapper) progressWrapper.style.display = "none";
    }
  }

  if (uploadBtn) {
    uploadBtn.addEventListener("click", async (e) => {
      e.stopPropagation();
      e.preventDefault();
      if (!fileInput.files || fileInput.files.length === 0) {
        fileInput.click();
        return;
      }
      await executeUpload(fileInput.files[0]);
    });
  }
}

async function triggerProcessVideo(id) {
  try {
    showToast("Starting AI video analysis in background...");
    await API.processVideo(id);
    showToast("Analysis job queued! Processing frames with YOLOv8...");
    loadVideos();
  } catch (err) {
    showToast("Failed to queue analysis: " + err.message, "error");
  }
}
window.triggerProcessVideo = triggerProcessVideo;

async function deleteVideoRecord(id) {
  if (!confirm(`Are you sure you want to delete Video #${id} and associated files?`)) return;
  try {
    await API.deleteVideo(id);
    showToast(`Video #${id} deleted.`);
    loadVideos();
  } catch (err) {
    showToast("Failed to delete video: " + err.message, "error");
  }
}
window.deleteVideoRecord = deleteVideoRecord;

// =============================================================================
// Video Preview Modal
// =============================================================================
function openVideoModal(videoId) {
  currentPreviewVideoId = parseInt(videoId);
  const modal = document.getElementById("video-preview-modal");
  const title = document.getElementById("modal-video-title");
  const player = document.getElementById("modal-video-player");

  if (!modal || !player) return;

  const v = cachedVideos.find(vid => vid.id === currentPreviewVideoId);
  const videoName = v ? v.video_name : `Video #${videoId}`;

  if (title) title.textContent = `Video Preview: ${videoName}`;
  player.src = `/api/videos/${videoId}/file`;
  player.load();
  modal.classList.add("show");
  modal.style.display = "flex";
}
window.openVideoModal = openVideoModal;

function closeVideoModal() {
  const modal = document.getElementById("video-preview-modal");
  const player = document.getElementById("modal-video-player");
  if (modal) {
    modal.classList.remove("show");
    modal.style.display = "none";
  }
  if (player) {
    player.pause();
    player.src = "";
  }
}
window.closeVideoModal = closeVideoModal;

// =============================================================================
// Stream / Share Video to Live Surveillance Screen
// =============================================================================
async function openStreamToScreenModal(videoId) {
  const modal = document.getElementById("stream-to-screen-modal");
  const hiddenVideo = document.getElementById("stream-screen-video-id");
  const title = document.getElementById("stream-screen-modal-title");
  const selectCam = document.getElementById("stream-screen-camera-select");

  if (!modal) return;

  const v = cachedVideos.find(vid => vid.id === parseInt(videoId));
  const vName = v ? v.video_name : `Video #${videoId}`;

  if (hiddenVideo) hiddenVideo.value = String(videoId);
  if (title) title.textContent = `Stream "${vName}" to Live Screen`;

  // Load cameras into selector
  if (selectCam) {
    try {
      const cameras = await API.listCameras();
      if (cameras && cameras.length > 0) {
        selectCam.innerHTML = cameras.map(c => `
          <option value="${c.id}">CAM #${c.id}: ${c.camera_name} (${c.location})</option>
        `).join("");
      } else {
        selectCam.innerHTML = `<option value="">No cameras registered</option>`;
      }
    } catch (e) {
      console.warn("Could not load cameras:", e);
    }
  }

  modal.classList.add("show");
  modal.style.display = "flex";
}
window.openStreamToScreenModal = openStreamToScreenModal;

function closeStreamToScreenModal() {
  const modal = document.getElementById("stream-to-screen-modal");
  if (modal) {
    modal.classList.remove("show");
    modal.style.display = "none";
  }
}
window.closeStreamToScreenModal = closeStreamToScreenModal;

async function submitStreamVideoToScreen() {
  const hiddenVideo = document.getElementById("stream-screen-video-id");
  const selectCam = document.getElementById("stream-screen-camera-select");

  const videoId = hiddenVideo ? parseInt(hiddenVideo.value) : null;
  const camId = selectCam ? parseInt(selectCam.value) : null;

  if (!videoId || !camId) {
    showToast("Please choose a target camera.", "warning");
    return;
  }

  try {
    showToast(`Connecting video to Camera #${camId}...`);
    await API.setCameraStream(camId, { video_id: videoId });
    showToast(`Video connected to Camera #${camId}! Opening Live Screen...`);
    closeStreamToScreenModal();

    setTimeout(() => {
      window.location.href = `/frontend/pages/live-monitoring.html?camera=${camId}`;
    }, 500);
  } catch (err) {
    showToast("Failed to connect video to screen: " + err.message, "error");
  }
}
window.submitStreamVideoToScreen = submitStreamVideoToScreen;

function streamCurrentPreviewToScreen() {
  if (currentPreviewVideoId) {
    closeVideoModal();
    openStreamToScreenModal(currentPreviewVideoId);
  }
}
window.streamCurrentPreviewToScreen = streamCurrentPreviewToScreen;

// =============================================================================
// Live Link & Stream Ingestion
// =============================================================================
function switchVideoIngestMode(mode) {
  const btnFile = document.getElementById("tab-btn-file");
  const btnLink = document.getElementById("tab-btn-link");
  const paneFile = document.getElementById("video-ingest-file-pane");
  const paneLink = document.getElementById("video-ingest-link-pane");

  if (!btnFile || !btnLink || !paneFile || !paneLink) return;

  if (mode === "file") {
    btnFile.className = "btn btn-sm btn-primary";
    btnLink.className = "btn btn-sm btn-outline";
    paneFile.style.display = "block";
    paneLink.style.display = "none";
  } else {
    btnFile.className = "btn btn-sm btn-outline";
    btnLink.className = "btn btn-sm btn-primary";
    paneFile.style.display = "none";
    paneLink.style.display = "block";
  }
}
window.switchVideoIngestMode = switchVideoIngestMode;

function fillSampleUrl(preset) {
  const urlInput = document.getElementById("input-stream-url");
  const nameInput = document.getElementById("input-stream-name");
  if (!urlInput) return;

  if (preset === "sample_traffic") {
    urlInput.value = "datasets/sample_traffic.mp4";
    if (nameInput) nameInput.value = "Sample Highway Traffic";
  } else if (preset === "pexels") {
    urlInput.value = "https://youtu.be/wqctLW0Hb_0?si=wzs6lj5Zjvcf9KUo";
    if (nameInput) nameInput.value = "Live CCTV Traffic Stream";
  }
}
window.fillSampleUrl = fillSampleUrl;

async function submitVideoUrl() {
  const urlInput = document.getElementById("input-stream-url");
  const nameInput = document.getElementById("input-stream-name");
  const downloadCheck = document.getElementById("check-download-stream");

  const url = urlInput ? urlInput.value.trim() : "";
  const name = nameInput ? nameInput.value.trim() : "";
  const downloadOffline = downloadCheck ? downloadCheck.checked : false;

  if (!url) {
    showToast("Please enter a valid video or live stream link.", "error");
    return;
  }

  const btnSubmit = document.getElementById("btn-submit-url");
  if (btnSubmit) btnSubmit.disabled = true;

  try {
    showToast("Registering live link in system...");
    const payload = {
      stream_url: url,
      video_name: name || undefined,
      download_offline: downloadOffline
    };

    const res = await API.addVideoByUrl(payload);
    showToast(`Video stream "${res.video_name}" registered!`);

    if (urlInput) urlInput.value = "";
    if (nameInput) nameInput.value = "";
    loadVideos();
  } catch (err) {
    showToast("Failed to ingest stream URL: " + err.message, "error");
  } finally {
    if (btnSubmit) btnSubmit.disabled = false;
  }
}
window.submitVideoUrl = submitVideoUrl;
