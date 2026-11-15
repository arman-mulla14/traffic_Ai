/**
 * AI-Based Traffic Management System - Video Analysis Controller
 * Manages video uploads, asynchronous background analysis polling, and summary metrics.
 */

let activePollInterval = null;

document.addEventListener("DOMContentLoaded", () => {
  initUploadForm();
  loadVideosLibrary();
  loadAnalysesHistory();

  const refreshBtn = document.getElementById("btn-refresh-videos");
  if (refreshBtn) {
    refreshBtn.addEventListener("click", () => {
      loadVideosLibrary();
      loadAnalysesHistory();
      showToast("Library refreshed", "info");
    });
  }
});

function initUploadForm() {
  const form = document.getElementById("video-upload-form");
  const fileInput = document.getElementById("video-file-input");
  const uploadBox = document.getElementById("upload-status-box");
  const uploadFill = document.getElementById("upload-progress-fill");
  const uploadPct = document.getElementById("upload-progress-pct");
  const submitBtn = document.getElementById("btn-submit-upload");

  if (!form) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const file = fileInput.files[0];
    if (!file) {
      showToast("Please choose a video file first", "error");
      return;
    }

    // Size limit check (300 MB)
    if (file.size > 300 * 1024 * 1024) {
      showToast("File exceeds 300MB limit", "error");
      return;
    }

    uploadBox.style.display = "block";
    uploadFill.style.width = "40%";
    uploadPct.textContent = "Uploading...";
    submitBtn.disabled = true;

    try {
      const video = await API.uploadVideo(file);
      uploadFill.style.width = "100%";
      uploadPct.textContent = "100%";
      showToast(`Video uploaded: ${video.original_name}`, "success");

      // Reset file input
      form.reset();
      uploadBox.style.display = "none";
      submitBtn.disabled = false;

      // Automatically trigger analysis
      await triggerAnalysis(video.id);
      loadVideosLibrary();
    } catch (err) {
      showToast(`Upload failed: ${err.message}`, "error");
      uploadBox.style.display = "none";
      submitBtn.disabled = false;
    }
  });
}

async function triggerAnalysis(videoId) {
  showToast("Starting YOLOv8 analysis job...", "info");
  try {
    const analysis = await API.startAnalysis(videoId);
    startPollingAnalysis(analysis.id);
  } catch (e) {
    showToast(`Failed to start analysis: ${e.message}`, "error");
  }
}

function startPollingAnalysis(analysisId) {
  if (activePollInterval) clearInterval(activePollInterval);

  const idleBox = document.getElementById("job-idle-box");
  const activeBox = document.getElementById("job-active-box");
  const summaryBox = document.getElementById("job-summary-box");
  const title = document.getElementById("active-job-title");
  const pill = document.getElementById("job-status-pill");

  idleBox.style.display = "none";
  activeBox.style.display = "block";
  summaryBox.style.display = "none";
  pill.style.display = "inline-flex";
  pill.className = "status-badge warning";
  pill.textContent = "PROCESSING";
  title.textContent = `Analysis Job #${analysisId}`;

  activePollInterval = setInterval(async () => {
    try {
      const job = await API.getAnalysis(analysisId);
      updateJobProgress(job);

      if (job.status === "COMPLETED") {
        clearInterval(activePollInterval);
        pill.className = "status-badge online";
        pill.textContent = "COMPLETED";
        showAnalysisSummary(job);
        showToast("Video analysis finished!", "success");
        loadAnalysesHistory();
      } else if (job.status === "FAILED") {
        clearInterval(activePollInterval);
        pill.className = "status-badge offline";
        pill.textContent = "FAILED";
        showToast(`Analysis failed: ${job.error_message}`, "error");
        loadAnalysesHistory();
      }
    } catch (e) {
      console.error("[VideoAnalysis] Polling error:", e);
    }
  }, 1000);
}

function updateJobProgress(job) {
  const pct = job.progress_pct || 0.0;
  document.getElementById("job-progress-text").textContent = `${pct.toFixed(1)}%`;
  document.getElementById("job-progress-fill").style.width = `${pct}%`;
  document.getElementById("job-fps-text").textContent = (job.current_fps || 0.0).toFixed(1);
  document.getElementById("job-frames-text").textContent = `${job.processed_frames} / ${job.total_frames}`;
  document.getElementById("job-status-text").textContent = job.status;
}

function showAnalysisSummary(job) {
  const summaryBox = document.getElementById("job-summary-box");
  summaryBox.style.display = "block";

  document.getElementById("summary-unique-vehicles").textContent = job.unique_vehicles_total;
  document.getElementById("summary-congestion-level").textContent = job.congestion_level;
  document.getElementById("summary-cars").textContent = job.cars_count;
  document.getElementById("summary-bikes").textContent = job.motorcycles_count;
  document.getElementById("summary-buses").textContent = job.buses_count;
  document.getElementById("summary-trucks").textContent = job.trucks_count;
}

async function loadVideosLibrary() {
  const tbody = document.getElementById("videos-library-tbody");
  if (!tbody) return;

  try {
    const videos = await API.listVideos();
    if (!videos || videos.length === 0) return;

    tbody.innerHTML = "";
    videos.forEach(v => {
      const tr = document.createElement("tr");
      const mb = (v.file_size_bytes / (1024 * 1024)).toFixed(1);
      tr.innerHTML = `
        <td style="font-family: monospace;">#${v.id}</td>
        <td><strong>${v.original_name}</strong></td>
        <td>${mb} MB</td>
        <td>${v.duration_seconds}s</td>
        <td>${v.width}x${v.height}</td>
        <td>${v.fps.toFixed(1)}</td>
        <td>
          <button class="btn btn-primary btn-sm" onclick="triggerAnalysis(${v.id})">
            ▶ Analyze Video
          </button>
        </td>
      `;
      tbody.appendChild(tr);
    });
  } catch (e) {
    console.error("[VideoAnalysis] Error loading library:", e);
  }
}

async function loadAnalysesHistory() {
  const tbody = document.getElementById("analyses-history-tbody");
  if (!tbody) return;

  try {
    const analyses = await API.listAnalyses();
    if (!analyses || analyses.length === 0) return;

    tbody.innerHTML = "";
    analyses.forEach(a => {
      const tr = document.createElement("tr");
      const badgeClass = a.status === "COMPLETED" ? "online" : (a.status === "PROCESSING" ? "warning" : "offline");
      const dateStr = new Date(a.created_at).toLocaleString();
      tr.innerHTML = `
        <td style="font-family: monospace;">#${a.id}</td>
        <td>Video #${a.video_id || "N/A"}</td>
        <td><span class="status-badge ${badgeClass}" style="padding: 2px 8px; font-size: 11px;">${a.status}</span></td>
        <td><strong style="color: var(--primary-accent);">${a.unique_vehicles_total}</strong></td>
        <td>${a.congestion_level}</td>
        <td>${(a.current_fps || 0).toFixed(1)}</td>
        <td style="color: var(--text-dim); font-size: 12px;">${dateStr}</td>
      `;
      tbody.appendChild(tr);
    });
  } catch (e) {
    console.error("[VideoAnalysis] Error loading history:", e);
  }
}

window.triggerAnalysis = triggerAnalysis;
