/**
 * AI-Based Traffic Management System - Application Core Shell
 * Controls Global Nav, Header, Toast Notifications, Live Clock & Active State.
 */

// Lucide SVG Icons Library (Inline SVGs for reliable offline rendering)
const ICONS = {
  dashboard: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="7" height="9" x="3" y="3" rx="1"/><rect width="7" height="5" x="14" y="3" rx="1"/><rect width="7" height="9" x="14" y="12" rx="1"/><rect width="7" height="5" x="3" y="16" rx="1"/></svg>`,
  video: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m16 13 5.223 3.482a.5.5 0 0 0 .777-.416V7.87a.5.5 0 0 0-.752-.432L16 10.5"/><rect x="2" y="6" width="14" height="12" rx="2"/></svg>`,
  monitoring: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12h20"/><path d="M20 12v8H4v-8"/><path d="m4 4 16 0"/><circle cx="12" cy="12" r="3"/><path d="M12 2v2"/><path d="M12 20v2"/></svg>`,
  analytics: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v18h18"/><path d="m19 9-5 5-4-4-3 3"/></svg>`,
  incident: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" x2="12" y1="9" y2="13"/><line x1="12" x2="12.01" y1="17" y2="17"/></svg>`,
  camera: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.5 4h-5L7 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3l-2.5-3z"/><circle cx="12" cy="13" r="3"/></svg>`,
  reports: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/><line x1="16" x2="8" y1="13" y2="13"/><line x1="16" x2="8" y1="17" y2="17"/><line x1="10" x2="8" y1="9" y2="9"/></svg>`,
  settings: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>`,
  bell: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/></svg>`,
  clock: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>`,
  refresh: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16"/><path d="M16 21h5v-5"/></svg>`,
  plus: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"/><path d="M12 5v14"/></svg>`,
  upload: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" x2="12" y1="3" y2="15"/></svg>`,
  download: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" x2="12" y1="15" y2="3"/></svg>`,
  check: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>`,
  trash: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/></svg>`,
  play: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="6 3 20 12 6 21 6 3"/></svg>`,
  menu: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="4" x2="20" y1="12" y2="12"/><line x1="4" x2="20" y1="6" y2="6"/><line x1="4" x2="20" y1="18" y2="18"/></svg>`,
  car: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 17h2c.6 0 1-.4 1-1v-3c0-.9-.7-1.7-1.5-1.9C18.7 10.6 16 10 16 10s-1.3-1.4-2.2-2.3c-.5-.4-1.1-.7-1.8-.7H5c-.6 0-1.1.4-1.4.9l-1.5 2.8C2.1 10.7 2 11 2 11.4V16c0 .6.4 1 1 1h2"/><circle cx="7" cy="17" r="2"/><path d="M9 17h6"/><circle cx="17" cy="17" r="2"/></svg>`
};

window.ICONS = ICONS;

// Navigation items definition (Strict 8 items)
const NAV_ITEMS = [
  { id: "dashboard", label: "Dashboard", href: "/frontend/index.html", icon: "dashboard" },
  { id: "videos", label: "Video Management", href: "/frontend/pages/video-management.html", icon: "video" },
  { id: "monitoring", label: "Live Monitoring", href: "/frontend/pages/live-monitoring.html", icon: "monitoring" },
  { id: "analytics", label: "Traffic Analytics", href: "/frontend/pages/traffic-analytics.html", icon: "analytics" },
  { id: "incidents", label: "Incident Management", href: "/frontend/pages/incident-management.html", icon: "incident" },
  { id: "cameras", label: "Camera Management", href: "/frontend/pages/camera-management.html", icon: "camera" },
  { id: "reports", label: "Reports", href: "/frontend/pages/reports.html", icon: "reports" },
  { id: "settings", label: "Settings", href: "/frontend/pages/settings.html", icon: "settings" }
];

document.addEventListener("DOMContentLoaded", () => {
  initLiveClock();
  initDropdowns();
  initMobileToggle();
  syncNavActiveState();
  initToastContainer();
  loadHeaderHealth();
  initChatbotWidget();
});

// 1. Live Clock
function initLiveClock() {
  const clockEl = document.getElementById("header-datetime-text") || document.getElementById("header-clock");
  if (!clockEl) return;

  function update() {
    const now = new Date();
    const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    const month = months[now.getMonth()];
    const day = now.getDate();
    const year = now.getFullYear();
    const hh = String(now.getHours()).padStart(2, "0");
    const mm = String(now.getMinutes()).padStart(2, "0");
    const ss = String(now.getSeconds()).padStart(2, "0");
    clockEl.textContent = `${month} ${day}, ${year}  ${hh}:${mm}:${ss}`;
  }
  update();
  setInterval(update, 1000);
}

// 2. Dropdowns (Notifications & User Profile)
function initDropdowns() {
  const notifBtn = document.getElementById("notif-btn");
  const notifMenu = document.getElementById("notif-dropdown");
  const profileBtn = document.getElementById("profile-btn");
  const profileMenu = document.getElementById("profile-dropdown");

  if (notifBtn && notifMenu) {
    notifBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      notifMenu.classList.toggle("show");
      if (profileMenu) profileMenu.classList.remove("show");
    });
  }

  if (profileBtn && profileMenu) {
    profileBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      profileMenu.classList.toggle("show");
      if (notifMenu) notifMenu.classList.remove("show");
    });
  }

  document.addEventListener("click", () => {
    if (notifMenu) notifMenu.classList.remove("show");
    if (profileMenu) profileMenu.classList.remove("show");
  });
}

// 3. Mobile Sidebar Toggle
function initMobileToggle() {
  const toggleBtn = document.getElementById("sidebar-toggle");
  const sidebar = document.querySelector(".app-sidebar");
  if (toggleBtn && sidebar) {
    toggleBtn.addEventListener("click", () => {
      sidebar.classList.toggle("open");
    });
  }
}

// 4. Nav Active State Sync
function syncNavActiveState() {
  const path = window.location.pathname.toLowerCase();
  const navLinks = document.querySelectorAll(".sidebar-nav .nav-link");

  navLinks.forEach((link) => {
    const href = link.getAttribute("href").toLowerCase();
    // Match exact or page filename
    const isDashboard = (path === "/" || path.endsWith("index.html")) && href.includes("index.html");
    const isMatch = href === path || (path.split("/").pop() === href.split("/").pop());

    if (isDashboard || isMatch) {
      link.classList.add("active");
    } else {
      link.classList.remove("active");
    }
  });
}

// 5. Toast Notifications
function initToastContainer() {
  if (!document.getElementById("toast-container")) {
    const container = document.createElement("div");
    container.id = "toast-container";
    container.className = "toast-container";
    document.body.appendChild(container);
  }
}

function showToast(message, type = "success") {
  initToastContainer();
  const container = document.getElementById("toast-container");
  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `
    <span style="display:flex;align-items:center;">
      ${type === "success" ? ICONS.check : (type === "error" ? ICONS.incident : ICONS.bell)}
    </span>
    <span>${message}</span>
  `;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transition = "opacity 0.3s ease";
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}
window.showToast = showToast;

// 6. Header Health Sync
async function loadHeaderHealth() {
  try {
    const health = await API.getHealth();
    const statusText = document.getElementById("system-status-text");
    if (statusText) {
      statusText.textContent = health.status === "HEALTHY" || health.status === "ONLINE" ? "System Online" : "System Alert";
    }
    const deviceBadge = document.getElementById("system-device-badge");
    if (deviceBadge && health.model_device) {
      deviceBadge.textContent = `Inference: ${health.model_device}`;
    }
  } catch (e) {
    console.warn("Health check error:", e);
  }
}


// =============================================================================
// 7. AI Traffic Copilot Chatbot Widget
// =============================================================================
function initChatbotWidget() {
  if (document.getElementById("traffic-chat-toggle-pill")) return;

  // 1. Toggle Button
  const toggleBtn = document.createElement("button");
  toggleBtn.id = "traffic-chat-toggle-pill";
  toggleBtn.className = "chat-toggle-pill";
  toggleBtn.setAttribute("aria-label", "Toggle AI Traffic Copilot");
  toggleBtn.innerHTML = `
    <span class="chat-pulse-dot"></span>
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" x2="12" y1="19" y2="22"/></svg>
    <span>AI Copilot</span>
  `;
  document.body.appendChild(toggleBtn);

  // 2. Chat Drawer
  const drawer = document.createElement("div");
  drawer.id = "traffic-chat-drawer";
  drawer.className = "chat-drawer";
  drawer.innerHTML = `
    <div class="chat-header">
      <div class="chat-header-title">
        <div class="chat-avatar bot">AI</div>
        <div>
          <h4>AI Traffic Assistant</h4>
          <p>Real-Time Intelligence &amp; Forecasts</p>
        </div>
      </div>
      <button class="chat-close-btn" id="traffic-chat-close-btn" aria-label="Close Chat">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
      </button>
    </div>
    <div class="chat-suggestions">
      <div class="suggestion-chip" data-query="How is the current traffic density?">🚦 Traffic Density</div>
      <div class="suggestion-chip" data-query="Are there any pedestrians detected or safety alerts?">🚶‍♂️ Pedestrians &amp; Safety</div>
      <div class="suggestion-chip" data-query="Predict the peak rush hour and traffic forecast.">📈 Peak Forecast</div>
      <div class="suggestion-chip" data-query="What is the status of surveillance cameras?">📹 Camera Status</div>
    </div>
    <div class="chat-messages" id="traffic-chat-messages">
      <div class="chat-message-row">
        <div class="chat-avatar bot">AI</div>
        <div class="chat-bubble bot">
          <p>👋 <strong>Welcome to AI Traffic Copilot!</strong></p>
          <p>I analyze real-time YOLOv8 detections, telemetry logs, and machine learning models. How can I assist you with traffic monitoring today?</p>
        </div>
      </div>
    </div>
    <div class="chat-input-bar">
      <input type="text" id="traffic-chat-input" class="chat-input-field" placeholder="Ask AI about traffic, incidents or forecasts..." />
      <button id="traffic-chat-send" class="chat-send-btn" aria-label="Send Message">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
      </button>
    </div>
  `;
  document.body.appendChild(drawer);

  // Events
  toggleBtn.addEventListener("click", () => {
    drawer.classList.toggle("open");
    if (drawer.classList.contains("open")) {
      setTimeout(() => document.getElementById("traffic-chat-input")?.focus(), 150);
    }
  });

  document.getElementById("traffic-chat-close-btn")?.addEventListener("click", () => {
    drawer.classList.remove("open");
  });

  drawer.querySelectorAll(".suggestion-chip").forEach(chip => {
    chip.addEventListener("click", () => {
      const query = chip.getAttribute("data-query");
      if (query) sendChatMessage(query);
    });
  });

  const inputEl = document.getElementById("traffic-chat-input");
  const sendBtn = document.getElementById("traffic-chat-send");

  function submitCurrentInput() {
    const text = inputEl.value.trim();
    if (!text) return;
    inputEl.value = "";
    sendChatMessage(text);
  }

  sendBtn?.addEventListener("click", submitCurrentInput);
  inputEl?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      submitCurrentInput();
    }
  });
}

async function sendChatMessage(text) {
  const msgContainer = document.getElementById("traffic-chat-messages");
  if (!msgContainer) return;

  // Append user bubble
  const userRow = document.createElement("div");
  userRow.className = "chat-message-row user";
  userRow.innerHTML = `
    <div class="chat-avatar user">U</div>
    <div class="chat-bubble user"><p>${escapeHtml(text)}</p></div>
  `;
  msgContainer.appendChild(userRow);
  msgContainer.scrollTop = msgContainer.scrollHeight;

  // Append typing indicator
  const loadingRow = document.createElement("div");
  loadingRow.className = "chat-message-row";
  loadingRow.id = "chat-typing-indicator";
  loadingRow.innerHTML = `
    <div class="chat-avatar bot">AI</div>
    <div class="chat-bubble bot"><p><em>Analyzing real-time traffic data...</em></p></div>
  `;
  msgContainer.appendChild(loadingRow);
  msgContainer.scrollTop = msgContainer.scrollHeight;

  try {
    const res = await API.chatWithAI(text);
    const indicator = document.getElementById("chat-typing-indicator");
    if (indicator) indicator.remove();

    const botRow = document.createElement("div");
    botRow.className = "chat-message-row";
    botRow.innerHTML = `
      <div class="chat-avatar bot">AI</div>
      <div class="chat-bubble bot">${formatBotMarkdown(res.response || "No response received.")}</div>
    `;
    msgContainer.appendChild(botRow);
  } catch (err) {
    const indicator = document.getElementById("chat-typing-indicator");
    if (indicator) indicator.remove();

    const errRow = document.createElement("div");
    errRow.className = "chat-message-row";
    errRow.innerHTML = `
      <div class="chat-avatar bot">AI</div>
      <div class="chat-bubble bot" style="border-color:#EF4444;color:#EF4444;"><p>Sorry, could not reach the AI analytics service.</p></div>
    `;
    msgContainer.appendChild(errRow);
  }

  msgContainer.scrollTop = msgContainer.scrollHeight;
}

function escapeHtml(str) {
  return String(str).replace(/[&<>'"]/g, tag => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    "'": '&#39;',
    '"': '&quot;'
  }[tag] || tag));
}

function formatBotMarkdown(text) {
  let html = escapeHtml(text);
  // Bold **text**
  html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  // Italic *text*
  html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
  // Bullet lists
  const lines = html.split('\n');
  let inList = false;
  let formatted = [];
  for (const line of lines) {
    const trimmed = line.trim();
    if (trimmed.startsWith('- ')) {
      if (!inList) {
        formatted.push('<ul>');
        inList = true;
      }
      formatted.push(`<li>${trimmed.substring(2)}</li>`);
    } else {
      if (inList) {
        formatted.push('</ul>');
        inList = false;
      }
      if (trimmed.length > 0) {
        formatted.push(`<p>${trimmed}</p>`);
      }
    }
  }
  if (inList) formatted.push('</ul>');
  return formatted.join('');
}
