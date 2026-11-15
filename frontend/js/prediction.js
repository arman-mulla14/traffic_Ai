/**
 * AI-Based Traffic Management System - Traffic Prediction Controller
 * Connects Holt's linear trend statistical forecasting, MAE evaluation, and confidence intervals.
 */

let predictionChart = null;

document.addEventListener("DOMContentLoaded", () => {
  loadPredictions();

  const recalcBtn = document.getElementById("btn-recalculate-pred");
  if (recalcBtn) {
    recalcBtn.addEventListener("click", () => {
      loadPredictions();
      showToast("Recalculating forecast model...", "info");
    });
  }

  const seedBtn = document.getElementById("btn-seed-data");
  if (seedBtn) {
    seedBtn.addEventListener("click", async () => {
      try {
        const res = await API.seedEvaluationData();
        showToast(res.message, "success");
        loadPredictions();
      } catch (e) {
        showToast(`Seeding error: ${e.message}`, "error");
      }
    });
  }
});

async function loadPredictions() {
  try {
    const res = await API.getTrafficPredictions();
    const pill = document.getElementById("pred-model-status-pill");
    const banner = document.getElementById("pred-insufficient-banner");
    const msgEl = document.getElementById("pred-insufficient-msg");

    if (res.status === "INSUFFICIENT_DATA") {
      if (pill) {
        pill.className = "status-badge warning";
        pill.textContent = "Insufficient Data";
      }
      if (banner) {
        banner.style.display = "flex";
        if (msgEl) msgEl.textContent = res.message;
      }
      document.getElementById("pred-sample-count").textContent = res.sample_count;
      document.getElementById("pred-mae-score").textContent = "N/A";
      document.getElementById("pred-freshness").textContent = "N/A";

      renderEmptyForecast();
    } else {
      if (pill) {
        pill.className = "status-badge online";
        pill.textContent = "Model Trained & Active";
      }
      if (banner) banner.style.display = "none";

      document.getElementById("pred-sample-count").textContent = res.sample_count;
      document.getElementById("pred-mae-score").textContent = res.mae_score !== null ? `${res.mae_score} veh/m` : "--";
      document.getElementById("pred-freshness").textContent = res.data_freshness_seconds !== null ? `${Math.round(res.data_freshness_seconds)}s` : "--";

      renderForecastChart(res.forecasts);
      renderForecastTable(res.forecasts);
    }
  } catch (e) {
    console.error("[Prediction] Error loading forecast:", e);
  }
}

function renderForecastChart(forecasts) {
  const ctx = document.getElementById("predictionChart");
  if (!ctx) return;

  const labels = forecasts.map(f => `+${f.horizon_minutes} Min`);
  const values = forecasts.map(f => f.predicted_flow_rate);
  const lowers = forecasts.map(f => f.confidence_lower);
  const uppers = forecasts.map(f => f.confidence_upper);

  if (predictionChart) predictionChart.destroy();

  predictionChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: labels,
      datasets: [
        {
          label: "Predicted Vehicle Flow (veh/min)",
          data: values,
          borderColor: "#8B5CF6",
          backgroundColor: "rgba(139, 92, 246, 0.2)",
          borderWidth: 2.5,
          tension: 0.25,
          pointRadius: 5
        },
        {
          label: "Upper Confidence Bound (95%)",
          data: uppers,
          borderColor: "rgba(139, 92, 246, 0.4)",
          borderDash: [5, 5],
          pointRadius: 2,
          fill: false
        },
        {
          label: "Lower Confidence Bound (95%)",
          data: lowers,
          borderColor: "rgba(139, 92, 246, 0.4)",
          borderDash: [5, 5],
          pointRadius: 2,
          fill: false
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { labels: { color: "#A1A1AA" } }
      },
      scales: {
        x: {
          ticks: { color: "#A1A1AA" },
          grid: { color: "rgba(255, 255, 255, 0.05)" }
        },
        y: {
          ticks: { color: "#71717A" },
          grid: { color: "rgba(255, 255, 255, 0.05)" },
          beginAtZero: true,
          title: { display: true, text: "Flow Rate (vehicles / min)", color: "#A1A1AA" }
        }
      }
    }
  });
}

function renderForecastTable(forecasts) {
  const tbody = document.getElementById("prediction-table-tbody");
  if (!tbody) return;

  tbody.innerHTML = "";
  forecasts.forEach(f => {
    const tr = document.createElement("tr");
    const dateStr = new Date(f.target_timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const anticipated = f.predicted_flow_rate > 20 ? "HIGH" : (f.predicted_flow_rate > 10 ? "MEDIUM" : "LOW");
    const color = anticipated === "LOW" ? "var(--color-success)" : (anticipated === "MEDIUM" ? "var(--color-warning)" : "var(--color-error)");

    tr.innerHTML = `
      <td><strong>+${f.horizon_minutes} Minutes</strong></td>
      <td style="font-family: monospace;">${dateStr} UTC</td>
      <td><strong style="color: var(--primary-accent);">${f.predicted_flow_rate}</strong></td>
      <td>${f.predicted_density}</td>
      <td style="font-family: monospace;">[ ${f.confidence_lower} - ${f.confidence_upper} ]</td>
      <td><span style="color: ${color}; font-weight: 600;">${anticipated}</span></td>
    `;
    tbody.appendChild(tr);
  });
}

function renderEmptyForecast() {
  const tbody = document.getElementById("prediction-table-tbody");
  if (tbody) {
    tbody.innerHTML = `
      <tr>
        <td colspan="6" style="text-align: center; color: var(--color-warning); padding: 24px;">
          Insufficient historical data. Please seed test logs or record live stream observations to train the model.
        </td>
      </tr>
    `;
  }
}
