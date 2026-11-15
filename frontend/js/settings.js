/**
 * AI-Based Traffic Management System - Settings Logic
 * Loads and saves persistent system configurations to FastAPI backend.
 */

document.addEventListener("DOMContentLoaded", () => {
  loadSettings();
  initSettingsForm();
});

async function loadSettings() {
  try {
    const s = await API.getSettings();

    if (document.getElementById("set-model")) document.getElementById("set-model").value = s.detection_model || "yolov8n.pt";
    if (document.getElementById("set-conf")) {
      document.getElementById("set-conf").value = s.confidence_threshold || 0.35;
      document.getElementById("set-conf-val").textContent = s.confidence_threshold || 0.35;
    }
    if (document.getElementById("set-iou")) {
      document.getElementById("set-iou").value = s.iou_threshold || 0.45;
      document.getElementById("set-iou-val").textContent = s.iou_threshold || 0.45;
    }
    if (document.getElementById("set-fps")) document.getElementById("set-fps").value = s.processing_fps || 30;
    if (document.getElementById("set-density")) {
      document.getElementById("set-density").value = s.density_threshold || 75;
      document.getElementById("set-density-val").textContent = `${s.density_threshold || 75}%`;
    }
    if (document.getElementById("set-wrong-way")) document.getElementById("set-wrong-way").value = s.wrong_way_sensitivity || "HIGH";
    if (document.getElementById("set-stopped-sec")) document.getElementById("set-stopped-sec").value = s.stopped_vehicle_seconds || 3;
    if (document.getElementById("set-purge-days")) document.getElementById("set-purge-days").value = s.auto_purge_days || 30;
    if (document.getElementById("set-notif")) document.getElementById("set-notif").checked = s.alert_notifications !== false;

  } catch (err) {
    console.warn("Could not load settings:", err);
  }
}

function initSettingsForm() {
  // Slider value displays
  const confSlider = document.getElementById("set-conf");
  const confVal = document.getElementById("set-conf-val");
  if (confSlider && confVal) {
    confSlider.addEventListener("input", () => confVal.textContent = confSlider.value);
  }

  const iouSlider = document.getElementById("set-iou");
  const iouVal = document.getElementById("set-iou-val");
  if (iouSlider && iouVal) {
    iouSlider.addEventListener("input", () => iouVal.textContent = iouSlider.value);
  }

  const densitySlider = document.getElementById("set-density");
  const densityVal = document.getElementById("set-density-val");
  if (densitySlider && densityVal) {
    densitySlider.addEventListener("input", () => densityVal.textContent = `${densitySlider.value}%`);
  }

  // Save buttons
  const saveBtn = document.getElementById("save-settings-btn");
  if (saveBtn) {
    saveBtn.addEventListener("click", async () => {
      saveBtn.disabled = true;
      saveBtn.textContent = "Saving...";

      const payload = {
        detection_model: document.getElementById("set-model")?.value || "yolov8n.pt",
        confidence_threshold: parseFloat(document.getElementById("set-conf")?.value || 0.35),
        iou_threshold: parseFloat(document.getElementById("set-iou")?.value || 0.45),
        processing_fps: parseInt(document.getElementById("set-fps")?.value || 30),
        density_threshold: parseInt(document.getElementById("set-density")?.value || 75),
        wrong_way_sensitivity: document.getElementById("set-wrong-way")?.value || "HIGH",
        stopped_vehicle_seconds: parseInt(document.getElementById("set-stopped-sec")?.value || 3),
        auto_purge_days: parseInt(document.getElementById("set-purge-days")?.value || 30),
        alert_notifications: document.getElementById("set-notif")?.checked ?? true
      };

      try {
        await API.saveSettings(payload);
        showToast("Settings saved successfully! Configuration active.");
        
        // Show green success alert box
        const successBox = document.getElementById("settings-success-alert");
        if (successBox) {
          successBox.style.display = "flex";
          setTimeout(() => successBox.style.display = "none", 5000);
        }
      } catch (err) {
        showToast("Failed to save settings: " + err.message, "error");
      } finally {
        saveBtn.disabled = false;
        saveBtn.textContent = "Save Changes";
      }
    });
  }
}
