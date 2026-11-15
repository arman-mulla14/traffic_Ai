/**
 * AI-Based Traffic Management System - Reports Logic
 * Handles road approach filtering, date ranges, PDF and CSV report downloads.
 */

document.addEventListener("DOMContentLoaded", () => {
  initRoadFilterListener();
  initReportDownloadButtons();
});

function getActiveRoadFilter() {
  const el = document.getElementById("report-road-filter");
  if (!el || el.value === "all") return { roadId: null, label: "All Roads (Full Intersection)" };
  const label = el.options[el.selectedIndex]?.text || "Selected Road";
  return { roadId: el.value, label };
}

function initRoadFilterListener() {
  const roadSelect = document.getElementById("report-road-filter");
  if (roadSelect) {
    roadSelect.addEventListener("change", () => {
      const { label } = getActiveRoadFilter();
      if (window.showToast) {
        window.showToast(`Active Target: ${label}. All exports will filter for this road approach.`);
      }
    });
  }
}

function getActiveDateRange() {
  const start = document.getElementById("report-start-date")?.value || null;
  const end = document.getElementById("report-end-date")?.value || null;
  return { start, end };
}

function initReportDownloadButtons() {
  const downloadBtns = document.querySelectorAll("[data-report-type]");

  downloadBtns.forEach(btn => {
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      const reportType = btn.getAttribute("data-report-type");
      const format = btn.getAttribute("data-format") || "pdf";
      const { start, end } = getActiveDateRange();
      const { roadId, label } = getActiveRoadFilter();

      const url = API.getReportDownloadUrl(reportType, format, start, end, roadId);
      if (window.showToast) {
        window.showToast(`Generating ${format.toUpperCase()} for ${label}...`);
      }
      
      // Trigger download
      window.location.href = url;
    });
  });
}
