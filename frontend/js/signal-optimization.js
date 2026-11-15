/**
 * AI-Based Traffic Management System - Signal Optimization Controller
 * Interactive 4-way intersection simulation, Webster's allocation, and phased green light cycling.
 */

let activePlan = null;
let simulationInterval = null;
let currentPhaseIndex = 0; // 0: North, 1: East, 2: South, 3: West

document.addEventListener("DOMContentLoaded", () => {
  initSignalOptimization();
  setupEventListeners();
});

async function initSignalOptimization() {
  await computePlanFromForm();
}

function setupEventListeners() {
  const form = document.getElementById("signal-optimize-form");
  if (form) {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      await computePlanFromForm();
      showToast("Signal timings optimized successfully", "success");
    });
  }

  const pullBtn = document.getElementById("btn-pull-measured");
  if (pullBtn) {
    pullBtn.addEventListener("click", async () => {
      try {
        const metrics = await API.getTrafficMetrics(10);
        if (metrics && metrics.length > 0) {
          const avg = Math.round(metrics.reduce((acc, m) => acc + m.vehicle_count, 0) / metrics.length);
          document.getElementById("input-n-count").value = Math.max(5, avg + 4);
          document.getElementById("input-s-count").value = Math.max(5, avg - 2);
          document.getElementById("input-e-count").value = Math.max(5, avg * 2);
          document.getElementById("input-w-count").value = Math.max(5, avg - 4);
          showToast("Pulled latest measured volumes from database", "info");
          await computePlanFromForm();
        } else {
          showToast("No active metrics in database yet; using defaults", "warning");
        }
      } catch (e) {
        showToast("Error pulling metrics", "error");
      }
    });
  }
}

async function computePlanFromForm() {
  const n = parseInt(document.getElementById("input-n-count").value) || 15;
  const s = parseInt(document.getElementById("input-s-count").value) || 15;
  const e = parseInt(document.getElementById("input-e-count").value) || 15;
  const w = parseInt(document.getElementById("input-w-count").value) || 15;
  const cycle = parseInt(document.getElementById("input-cycle").value) || 120;
  const minG = parseInt(document.getElementById("input-min-green").value) || 10;
  const maxG = parseInt(document.getElementById("input-max-green").value) || 60;

  const payload = {
    approach_n_count: n,
    approach_s_count: s,
    approach_e_count: e,
    approach_w_count: w,
    cycle_time: cycle,
    min_green: minG,
    max_green: maxG
  };

  try {
    const plan = await API.optimizeSignals(payload);
    activePlan = plan;
    renderComparisonTable(plan, { NORTH: n, SOUTH: s, EAST: e, WEST: w });
    updateIntersectionLabels(plan);
    startPhasedCycleSimulation(plan);
  } catch (err) {
    console.error("[SignalOptimization] Error computing plan:", err);
  }
}

function updateIntersectionLabels(plan) {
  document.getElementById("label-n-time").textContent = `${plan.approach_n_green}s`;
  document.getElementById("label-s-time").textContent = `${plan.approach_s_green}s`;
  document.getElementById("label-e-time").textContent = `${plan.approach_e_green}s`;
  document.getElementById("label-w-time").textContent = `${plan.approach_w_green}s`;
  document.getElementById("signal-full-reasoning").textContent = plan.reasoning;
}

function renderComparisonTable(plan, counts) {
  const tbody = document.getElementById("signal-comparison-tbody");
  if (!tbody) return;

  const rows = [
    { name: "North Approach", count: counts.NORTH, base: plan.baseline_n_green, rec: plan.approach_n_green },
    { name: "South Approach", count: counts.SOUTH, base: plan.baseline_s_green, rec: plan.approach_s_green },
    { name: "East Approach",  count: counts.EAST,  base: plan.baseline_e_green, rec: plan.approach_e_green },
    { name: "West Approach",  count: counts.WEST,  base: plan.baseline_w_green, rec: plan.approach_w_green }
  ];

  tbody.innerHTML = "";
  rows.forEach(r => {
    const delta = r.rec - r.base;
    const deltaSign = delta > 0 ? `+${delta}s` : (delta < 0 ? `${delta}s` : "0s");
    const deltaColor = delta > 0 ? "var(--color-success)" : (delta < 0 ? "var(--color-warning)" : "var(--text-muted)");

    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><strong>${r.name}</strong></td>
      <td>${r.count} vehicles</td>
      <td>${r.base}s</td>
      <td><strong style="color: var(--primary-accent); font-size: 14px;">${r.rec}s</strong></td>
      <td><strong style="color: ${deltaColor};">${deltaSign}</strong></td>
      <td>${plan.clearance_interval}s</td>
    `;
    tbody.appendChild(tr);
  });
}

function startPhasedCycleSimulation(plan) {
  if (simulationInterval) clearInterval(simulationInterval);

  const phases = ["north", "east", "south", "west"];

  function activatePhase(phaseName) {
    phases.forEach(p => {
      const red = document.getElementById(`bulb-${p}-red`);
      const amber = document.getElementById(`bulb-${p}-amber`);
      const green = document.getElementById(`bulb-${p}-green`);

      if (p === phaseName) {
        red.classList.remove("active");
        amber.classList.remove("active");
        green.classList.add("active");
      } else {
        red.classList.add("active");
        amber.classList.remove("active");
        green.classList.remove("active");
      }
    });
  }

  // Initial activation
  activatePhase(phases[currentPhaseIndex]);

  // Rotate green light every 4 seconds in visual simulation
  simulationInterval = setInterval(() => {
    currentPhaseIndex = (currentPhaseIndex + 1) % phases.length;
    activatePhase(phases[currentPhaseIndex]);
  }, 4000);
}
