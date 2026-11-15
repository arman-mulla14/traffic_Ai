/**
 * AI-Based Traffic Management System - Database Admin Panel (DAP) Master Controller
 * Full-featured SQLite database management, data browsing, CRUD operations,
 * schema viewer, and raw SQL console studio.
 */

// Self-healing API fallback to guarantee 100% operation under all circumstances
window.API = window.API || {};
const API_BASE = window.API_BASE || window.location.origin;
const API = window.API;

if (!window.API.getDbOverview) {
  window.API.getDbOverview = async function() {
    const res = await fetch(`${API_BASE}/api/db-admin/overview`);
    if (!res.ok) throw new Error("Failed to load database overview");
    return await res.json();
  };
}

if (!window.API.getTableSchema) {
  window.API.getTableSchema = async function(tableName) {
    const res = await fetch(`${API_BASE}/api/db-admin/tables/${encodeURIComponent(tableName)}/schema`);
    if (!res.ok) throw new Error(`Failed to load schema for ${tableName}`);
    return await res.json();
  };
}

if (!window.API.getTableData) {
  window.API.getTableData = async function(tableName, page = 1, limit = 25, search = "", sortBy = "", order = "DESC") {
    let url = `${API_BASE}/api/db-admin/tables/${encodeURIComponent(tableName)}/data?page=${page}&limit=${limit}&order=${order}`;
    if (search) url += `&search=${encodeURIComponent(search)}`;
    if (sortBy) url += `&sort_by=${encodeURIComponent(sortBy)}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`Failed to load data for ${tableName}`);
    return await res.json();
  };
}

if (!window.API.insertTableRow) {
  window.API.insertTableRow = async function(tableName, rowData) {
    const res = await fetch(`${API_BASE}/api/db-admin/tables/${encodeURIComponent(tableName)}/rows`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(rowData)
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Insert failed" }));
      throw new Error(err.detail || "Insert row failed");
    }
    return await res.json();
  };
}

if (!window.API.updateTableRow) {
  window.API.updateTableRow = async function(tableName, rowId, rowData) {
    const res = await fetch(`${API_BASE}/api/db-admin/tables/${encodeURIComponent(tableName)}/rows/${encodeURIComponent(rowId)}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(rowData)
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Update failed" }));
      throw new Error(err.detail || "Update row failed");
    }
    return await res.json();
  };
}

if (!window.API.deleteTableRow) {
  window.API.deleteTableRow = async function(tableName, rowId) {
    const res = await fetch(`${API_BASE}/api/db-admin/tables/${encodeURIComponent(tableName)}/rows/${encodeURIComponent(rowId)}`, {
      method: "DELETE"
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Delete failed" }));
      throw new Error(err.detail || "Delete row failed");
    }
    return await res.json();
  };
}

if (!window.API.executeRawQuery) {
  window.API.executeRawQuery = async function(sql) {
    const res = await fetch(`${API_BASE}/api/db-admin/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sql })
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "SQL Error" }));
      throw new Error(err.detail || "SQL Execution failed");
    }
    return await res.json();
  };
}

if (!window.API.vacuumDatabase) {
  window.API.vacuumDatabase = async function() {
    const res = await fetch(`${API_BASE}/api/db-admin/vacuum`, { method: "POST" });
    if (!res.ok) throw new Error("Database VACUUM failed");
    return await res.json();
  };
}

if (!window.API.checkDatabaseIntegrity) {
  window.API.checkDatabaseIntegrity = async function() {
    const res = await fetch(`${API_BASE}/api/db-admin/integrity-check`);
    if (!res.ok) throw new Error("Integrity check failed");
    return await res.json();
  };
}

if (!window.API.getTableExportUrl) {
  window.API.getTableExportUrl = function(tableName, format = "csv") {
    return `${API_BASE}/api/db-admin/export/${encodeURIComponent(tableName)}?format=${format}`;
  };
}

if (!window.API.getDatabaseBackupUrl) {
  window.API.getDatabaseBackupUrl = function() {
    return `${API_BASE}/api/db-admin/download-db`;
  };
}

let dapState = {
  overview: null,
  currentTable: "cameras",
  currentSchema: null,
  currentPage: 1,
  currentLimit: 25,
  currentSearch: "",
  currentSortBy: "",
  currentSortOrder: "DESC",
  currentRows: [],
  selectedRowForEdit: null
};

function safeToast(msg, type = "success") {
  if (typeof window.showToast === "function") {
    window.showToast(msg, type);
  } else {
    console.log(`[DAP ${type}]: ${msg}`);
  }
}

// Ensure initDAP runs even if DOMContentLoaded already passed
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => initDAP());
} else {
  setTimeout(() => initDAP(), 10);
}

async function initDAP() {
  try { setupTabs(); } catch (e) { console.warn("setupTabs warning:", e); }
  try { setupMaintenanceButtons(); } catch (e) { console.warn("setupMaintenanceButtons warning:", e); }
  try { setupSearchAndPagination(); } catch (e) { console.warn("setupSearchAndPagination warning:", e); }
  try { setupSqlConsole(); } catch (e) { console.warn("setupSqlConsole warning:", e); }
  try { setupExportButtons(); } catch (e) { console.warn("setupExportButtons warning:", e); }
  try { setupTableFilter(); } catch (e) { console.warn("setupTableFilter warning:", e); }

  try {
    await loadOverview();
  } catch (e) {
    console.error("loadOverview failed in initDAP:", e);
  }
}
window.initDAP = initDAP;

// -----------------------------------------------------------------------------
// 1. DATABASE OVERVIEW & TABLE DIRECTORY
// -----------------------------------------------------------------------------
async function loadOverview(preserveActiveTable = true) {
  try {
    const overview = await (API.getDbOverview ? API.getDbOverview() : fetch(`${API_BASE}/api/db-admin/overview`).then(r => r.json()));
    dapState.overview = overview;

    // Update 4 KPIs
    const kpiTables = document.getElementById("dap-kpi-tables");
    const kpiRecords = document.getElementById("dap-kpi-records");
    const kpiSize = document.getElementById("dap-kpi-size");
    const kpiVer = document.getElementById("dap-kpi-ver");
    const kpiPages = document.getElementById("dap-kpi-pages");
    const kpiJournal = document.getElementById("dap-kpi-journal");

    if (kpiTables) kpiTables.textContent = overview.total_tables || 0;
    if (kpiRecords) kpiRecords.textContent = Number(overview.total_records || 0).toLocaleString();
    if (kpiSize) kpiSize.textContent = `${overview.file_size_kb} KB`;
    if (kpiVer) kpiVer.textContent = `v${overview.sqlite_version}`;
    if (kpiPages) kpiPages.textContent = `Page Count: ${overview.page_count} (${overview.page_size}B)`;
    if (kpiJournal) kpiJournal.textContent = `Journal: ${overview.journal_mode}`;

    // Render table list
    renderTableList(overview.tables);

    // Set active table
    if (!preserveActiveTable || !dapState.currentTable) {
      if (overview.tables && overview.tables.length > 0) {
        dapState.currentTable = overview.tables[0].name;
      }
    }

    if (dapState.currentTable) {
      await switchTable(dapState.currentTable);
    }
  } catch (err) {
    console.error("Failed to load database overview:", err);
    safeToast("Failed to load database overview: " + err.message, "error");
    const kpiTables = document.getElementById("dap-kpi-tables");
    if (kpiTables && kpiTables.textContent === "--") kpiTables.textContent = "!";
    const tblList = document.getElementById("dap-tables-list");
    if (tblList) {
      tblList.innerHTML = `<div style="padding:16px;text-align:center;color:#EF4444;font-size:12px;">Failed to connect to database: ${err.message}.<br/><button class="btn btn-outline" style="margin-top:8px;padding:4px 8px;font-size:11px;" onclick="loadOverview()">Retry</button></div>`;
    }
  }
}
window.loadOverview = loadOverview;

function renderTableList(tables) {
  const container = document.getElementById("dap-tables-list");
  if (!container) return;

  if (!tables || tables.length === 0) {
    container.innerHTML = `<div style="padding:16px;text-align:center;color:#64748B;font-size:12px;">No tables found.</div>`;
    return;
  }

  container.innerHTML = tables.map(t => {
    const isActive = t.name === dapState.currentTable ? "active" : "";
    return `
      <div class="dap-table-item ${isActive}" data-table="${t.name}" onclick="switchTable('${t.name}')">
        <span style="display:flex;align-items:center;gap:7px;">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect width="18" height="18" x="3" y="3" rx="2"/><path d="M3 9h18"/><path d="M9 3v18"/></svg>
          ${t.name}
        </span>
        <span class="dap-count-badge">${Number(t.row_count || 0).toLocaleString()}</span>
      </div>
    `;
  }).join("");
}

function setupTableFilter() {
  const searchInput = document.getElementById("dap-table-search-input");
  if (!searchInput) return;

  searchInput.addEventListener("input", (e) => {
    const term = e.target.value.toLowerCase().trim();
    const items = document.querySelectorAll("#dap-tables-list .dap-table-item");
    items.forEach(el => {
      const tname = el.getAttribute("data-table").toLowerCase();
      el.style.display = tname.includes(term) ? "flex" : "none";
    });
  });

  document.getElementById("btn-refresh-tables")?.addEventListener("click", () => {
    loadOverview(true);
    safeToast("Database tables refreshed");
  });
}

// -----------------------------------------------------------------------------
// 2. SWITCH ACTIVE TABLE
// -----------------------------------------------------------------------------
async function switchTable(tableName) {
  dapState.currentTable = tableName;
  dapState.currentPage = 1;
  dapState.currentSearch = "";
  dapState.currentSortBy = "";
  dapState.currentSortOrder = "DESC";

  // Update UI sidebar active class
  document.querySelectorAll("#dap-tables-list .dap-table-item").forEach(item => {
    if (item.getAttribute("data-table") === tableName) {
      item.classList.add("active");
    } else {
      item.classList.remove("active");
    }
  });

  // Update labels
  const label = document.getElementById("dap-current-table-label");
  if (label) label.textContent = tableName;

  const insertLabel = document.getElementById("dap-insert-table-name");
  if (insertLabel) insertLabel.textContent = tableName;

  const exportTitle = document.getElementById("dap-export-table-title");
  if (exportTitle) exportTitle.textContent = tableName;

  const exportMetaTable = document.getElementById("dap-export-meta-table");
  if (exportMetaTable) exportMetaTable.textContent = tableName;

  // Clear search input
  const rowSearch = document.getElementById("dap-row-search-input");
  if (rowSearch) rowSearch.value = "";

  // Load schema & browse data concurrently with error resiliency
  try {
    const results = await Promise.allSettled([
      API.getTableSchema(tableName),
      API.getTableData(tableName, dapState.currentPage, dapState.currentLimit, "", "", "DESC")
    ]);

    const schemaRes = results[0];
    const dataRes = results[1];

    if (schemaRes.status === "fulfilled") {
      const schema = schemaRes.value;
      dapState.currentSchema = schema;
      renderSchemaView(schema);
      renderInsertForm(schema);
      const exportMetaPk = document.getElementById("dap-export-meta-pk");
      if (exportMetaPk) exportMetaPk.textContent = schema.primary_key || "id";
    } else {
      console.warn(`Schema load failed for ${tableName}:`, schemaRes.reason);
    }

    if (dataRes.status === "fulfilled") {
      const data = dataRes.value;
      renderBrowseData(data);
      const exportMetaCount = document.getElementById("dap-export-meta-count");
      if (exportMetaCount) exportMetaCount.textContent = Number(data.total_rows || 0).toLocaleString();
    } else {
      console.warn(`Data load failed for ${tableName}:`, dataRes.reason);
      const tbody = document.getElementById("dap-table-data-tbody");
      if (tbody) {
        tbody.innerHTML = `<tr><td colspan="10" style="text-align:center;color:#EF4444;padding:24px;">Failed to load rows: ${dataRes.reason?.message || "Unknown error"}</td></tr>`;
      }
    }
  } catch (err) {
    console.error(`Failed to load data for table ${tableName}:`, err);
    safeToast(`Error loading table ${tableName}: ` + err.message, "error");
  }
}
window.switchTable = switchTable;

// -----------------------------------------------------------------------------
// 3. TAB CONTROLLER
// -----------------------------------------------------------------------------
function switchDapTab(tabName) {
  const tabs = document.querySelectorAll(".dap-tab-btn");
  tabs.forEach(btn => {
    if (btn.getAttribute("data-tab") === tabName) {
      btn.classList.add("active");
    } else {
      btn.classList.remove("active");
    }
  });

  const panels = document.querySelectorAll(".dap-tab-panel");
  panels.forEach(p => p.style.display = "none");
  const target = document.getElementById(`tab-content-${tabName}`);
  if (target) target.style.display = "block";
}
window.switchDapTab = switchDapTab;

function setupTabs() {
  const tabs = document.querySelectorAll(".dap-tab-btn");
  tabs.forEach(btn => {
    btn.addEventListener("click", () => {
      const target = btn.getAttribute("data-tab");
      if (target) switchDapTab(target);
    });
  });

  document.getElementById("btn-shortcut-sql")?.addEventListener("click", () => {
    switchDapTab("sql");
  });
}

// -----------------------------------------------------------------------------
// 4. BROWSE DATA (TAB 1)
// -----------------------------------------------------------------------------
function renderBrowseData(data) {
  dapState.currentRows = data.rows || [];
  const thead = document.getElementById("dap-table-thead");
  const tbody = document.getElementById("dap-table-tbody");
  const totalLabel = document.getElementById("dap-browse-total-label");
  const pageIndicator = document.getElementById("dap-page-indicator");

  if (totalLabel) totalLabel.textContent = `${Number(data.total_rows || 0).toLocaleString()} rows`;
  if (pageIndicator) pageIndicator.textContent = `${data.page} / ${data.total_pages}`;

  const prevBtn = document.getElementById("btn-page-prev");
  const nextBtn = document.getElementById("btn-page-next");
  if (prevBtn) prevBtn.disabled = data.page <= 1;
  if (nextBtn) nextBtn.disabled = data.page >= data.total_pages;

  const cols = data.columns || [];
  const pkName = data.primary_key || "id";

  // Build thead
  if (thead) {
    let thHtml = `<tr><th style="width: 105px; text-align: center;">Actions</th>`;
    cols.forEach(col => {
      const isSorted = dapState.currentSortBy === col;
      const arrow = isSorted ? (dapState.currentSortOrder === "ASC" ? " ▲" : " ▼") : "";
      const isPk = col === pkName ? " 🔑" : "";
      thHtml += `<th class="sortable-th" data-col="${col}" style="cursor:pointer;" title="Click to sort by ${col}">
        ${col}${isPk}<span style="color:#2878D0;font-size:10px;">${arrow}</span>
      </th>`;
    });
    thHtml += `</tr>`;
    thead.innerHTML = thHtml;

    // Attach sort header listeners
    thead.querySelectorAll(".sortable-th").forEach(th => {
      th.addEventListener("click", () => {
        const col = th.getAttribute("data-col");
        if (dapState.currentSortBy === col) {
          dapState.currentSortOrder = dapState.currentSortOrder === "ASC" ? "DESC" : "ASC";
        } else {
          dapState.currentSortBy = col;
          dapState.currentSortOrder = "DESC";
        }
        refreshBrowseData();
      });
    });
  }

  // Build tbody
  if (tbody) {
    if (!data.rows || data.rows.length === 0) {
      tbody.innerHTML = `<tr><td colspan="${cols.length + 1}" style="text-align:center;padding:28px;color:#64748B;">No records found in table '${data.table_name}'.</td></tr>`;
      return;
    }

    tbody.innerHTML = data.rows.map((row, idx) => {
      const pkVal = row[pkName];
      let rowHtml = `<tr>
        <td style="text-align:center;">
          <div class="dap-action-btn-group" style="justify-content:center;">
            <button class="dap-btn-icon" title="Edit Record" onclick="openEditModal(${idx})">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 3a2.828 2.828 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z"/></svg>
            </button>
            <button class="dap-btn-icon" title="View Record JSON" onclick="openViewModal(${idx})">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" x2="12" y1="8" y2="12"/><line x1="12" x2="12.01" y1="16" y2="16"/></svg>
            </button>
            <button class="dap-btn-icon delete" title="Delete Record" onclick="confirmDeleteRow('${pkVal}')">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/></svg>
            </button>
          </div>
        </td>`;

      cols.forEach(col => {
        const val = row[col];
        rowHtml += `<td>${formatTableCellValue(val, col)}</td>`;
      });

      rowHtml += `</tr>`;
      return rowHtml;
    }).join("");
  }
}

function formatTableCellValue(val, colName) {
  if (val === null || val === undefined) {
    return `<span style="color:#94A3B8; font-style:italic;">NULL</span>`;
  }
  if (typeof val === "boolean") {
    return val ? `<span class="badge badge-success">TRUE</span>` : `<span class="badge badge-danger">FALSE</span>`;
  }
  if (colName.includes("status")) {
    const s = String(val).toUpperCase();
    if (s === "ACTIVE" || s === "CONNECTED" || s === "ONLINE" || s === "RUNNING") {
      return `<span class="badge badge-success"><span class="badge-dot"></span>${val}</span>`;
    }
    if (s === "INACTIVE" || s === "FAILED" || s === "OFFLINE") {
      return `<span class="badge badge-danger"><span class="badge-dot"></span>${val}</span>`;
    }
    return `<span class="badge badge-warning">${val}</span>`;
  }
  const str = String(val);
  if (str.length > 50) {
    return `<span title="${escapeHtml(str)}">${escapeHtml(str.substring(0, 48))}...</span>`;
  }
  return escapeHtml(str);
}

async function refreshBrowseData() {
  try {
    const data = await API.getTableData(
      dapState.currentTable,
      dapState.currentPage,
      dapState.currentLimit,
      dapState.currentSearch,
      dapState.currentSortBy,
      dapState.currentSortOrder
    );
    renderBrowseData(data);
  } catch (err) {
    console.error("Failed to refresh browse data:", err);
  }
}
window.refreshBrowseData = refreshBrowseData;

function setupSearchAndPagination() {
  const searchInput = document.getElementById("dap-row-search-input");
  let debounceTimer = null;
  if (searchInput) {
    searchInput.addEventListener("input", (e) => {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => {
        dapState.currentSearch = e.target.value.trim();
        dapState.currentPage = 1;
        refreshBrowseData();
      }, 350);
    });
  }

  const perPageSelect = document.getElementById("dap-per-page-select");
  if (perPageSelect) {
    perPageSelect.addEventListener("change", (e) => {
      dapState.currentLimit = parseInt(e.target.value, 10);
      dapState.currentPage = 1;
      refreshBrowseData();
    });
  }

  document.getElementById("btn-page-prev")?.addEventListener("click", () => {
    if (dapState.currentPage > 1) {
      dapState.currentPage--;
      refreshBrowseData();
    }
  });

  document.getElementById("btn-page-next")?.addEventListener("click", () => {
    dapState.currentPage++;
    refreshBrowseData();
  });
}

// -----------------------------------------------------------------------------
// 5. STRUCTURE / SCHEMA VIEW (TAB 2)
// -----------------------------------------------------------------------------
function renderSchemaView(schema) {
  const tbody = document.getElementById("dap-schema-tbody");
  const sqlBox = document.getElementById("dap-create-sql-box");

  if (sqlBox) {
    sqlBox.textContent = schema.create_sql || "-- No CREATE TABLE statement found";
  }

  if (tbody) {
    tbody.innerHTML = (schema.columns || []).map(c => `
      <tr>
        <td>${c.cid}</td>
        <td><strong>${c.name}</strong></td>
        <td><code style="background:#F1F5F9;padding:2px 6px;border-radius:4px;color:#0F172A;">${c.type || "ANY"}</code></td>
        <td>${c.notnull ? '<span class="badge badge-warning">NOT NULL</span>' : '<span style="color:#94A3B8;">NULLABLE</span>'}</td>
        <td>${c.dflt_value !== null ? `<code>${c.dflt_value}</code>` : '<span style="color:#94A3B8;">None</span>'}</td>
        <td>${c.pk ? '<span class="badge badge-success">PRIMARY KEY 🔑</span>' : '<span style="color:#94A3B8;">-</span>'}</td>
      </tr>
    `).join("");
  }
}

// -----------------------------------------------------------------------------
// 6. INSERT RECORD (TAB 3)
// -----------------------------------------------------------------------------
function renderInsertForm(schema) {
  const container = document.getElementById("dap-insert-fields-container");
  if (!container) return;

  const cols = schema.columns || [];
  const pkName = schema.primary_key || "id";

  container.innerHTML = cols.map(c => {
    const isPk = c.name === pkName;
    const isNum = c.type.toUpperCase().includes("INT") || c.type.toUpperCase().includes("REAL") || c.type.toUpperCase().includes("FLOAT");
    const inputType = isNum ? "number" : "text";
    const req = c.notnull && !isPk ? "required" : "";

    return `
      <div class="form-group" style="margin-bottom:0;">
        <label class="form-label" style="display:flex; justify-content:space-between;">
          <span>${c.name} <code style="font-size:11px;color:#64748B;">(${c.type})</code></span>
          ${isPk ? '<span style="color:#00BA63; font-size:11px;">(Auto-ID: Optional)</span>' : (c.notnull ? '<span style="color:#EF4444; font-size:11px;">* Required</span>' : '')}
        </label>
        <input 
          type="${inputType}" 
          name="${c.name}" 
          class="form-control" 
          placeholder="${isPk ? 'Leave empty to auto-increment' : (c.dflt_value ? `Default: ${c.dflt_value}` : `Enter ${c.name}`)}"
          ${req}
          ${isNum ? 'step="any"' : ''}
        />
      </div>
    `;
  }).join("");

  const form = document.getElementById("dap-insert-form");
  form.onsubmit = async (e) => {
    e.preventDefault();
    const formData = new FormData(form);
    const payload = {};
    formData.forEach((value, key) => {
      const valStr = value.trim();
      if (valStr !== "") {
        payload[key] = isNaN(valStr) || valStr.startsWith("0") && valStr.length > 1 ? valStr : Number(valStr);
      }
    });

    try {
      const res = await API.insertTableRow(dapState.currentTable, payload);
      safeToast(`Record #${res.row_id} inserted successfully into ${dapState.currentTable}!`);
      form.reset();

      await loadOverview(true);
      await refreshBrowseData();
      switchDapTab("browse");
    } catch (err) {
      safeToast("Insert failed: " + err.message, "error");
    }
  };
}

// -----------------------------------------------------------------------------
// 7. EDIT RECORD MODAL
// -----------------------------------------------------------------------------
function openEditModal(rowIndex) {
  const row = dapState.currentRows[rowIndex];
  if (!row) return;

  dapState.selectedRowForEdit = row;
  const modal = document.getElementById("dap-edit-modal");
  const title = document.getElementById("dap-edit-modal-title");
  const container = document.getElementById("dap-edit-fields-container");

  const pkName = dapState.currentSchema?.primary_key || "id";
  const pkVal = row[pkName];

  if (title) title.textContent = `Edit Record #${pkVal} in '${dapState.currentTable}'`;

  if (container) {
    const cols = dapState.currentSchema?.columns || Object.keys(row).map(k => ({ name: k, type: "TEXT" }));
    container.innerHTML = cols.map(c => {
      const isPk = c.name === pkName;
      const val = row[c.name] !== null && row[c.name] !== undefined ? row[c.name] : "";
      const isNum = c.type.toUpperCase().includes("INT") || c.type.toUpperCase().includes("REAL");
      const inputType = isNum ? "number" : "text";

      return `
        <div class="form-group" style="margin-bottom:0;">
          <label class="form-label">
            ${c.name} <code style="font-size:11px;color:#64748B;">(${c.type})</code>
            ${isPk ? '<span style="color:#2878D0; font-size:11px;">(Primary Key - Locked)</span>' : ''}
          </label>
          <input 
            type="${inputType}" 
            name="${c.name}" 
            class="form-control" 
            value="${escapeHtml(String(val))}"
            ${isPk ? 'disabled readonly style="background:#F1F5F9;cursor:not-allowed;"' : ''}
            ${isNum ? 'step="any"' : ''}
          />
        </div>
      `;
    }).join("");
  }

  const form = document.getElementById("dap-edit-form");
  form.onsubmit = async (e) => {
    e.preventDefault();
    const formData = new FormData(form);
    const updatePayload = {};

    formData.forEach((value, key) => {
      if (key !== pkName) {
        const valStr = value.trim();
        updatePayload[key] = isNaN(valStr) || valStr === "" ? valStr : Number(valStr);
      }
    });

    try {
      await API.updateTableRow(dapState.currentTable, pkVal, updatePayload);
      safeToast(`Record #${pkVal} updated successfully!`);
      closeEditModal();
      await refreshBrowseData();
    } catch (err) {
      safeToast("Update failed: " + err.message, "error");
    }
  };

  modal.classList.add("show");
}
window.openEditModal = openEditModal;

function closeEditModal() {
  document.getElementById("dap-edit-modal")?.classList.remove("show");
  dapState.selectedRowForEdit = null;
}
window.closeEditModal = closeEditModal;

// -----------------------------------------------------------------------------
// 8. VIEW RECORD JSON MODAL
// -----------------------------------------------------------------------------
function openViewModal(rowIndex) {
  const row = dapState.currentRows[rowIndex];
  if (!row) return;

  const modal = document.getElementById("dap-view-modal");
  const content = document.getElementById("dap-view-json-content");
  if (content) {
    content.textContent = JSON.stringify(row, null, 2);
  }
  modal.classList.add("show");
}
window.openViewModal = openViewModal;

function closeViewModal() {
  document.getElementById("dap-view-modal")?.classList.remove("show");
}
window.closeViewModal = closeViewModal;

// -----------------------------------------------------------------------------
// 9. DELETE RECORD
// -----------------------------------------------------------------------------
async function confirmDeleteRow(pkVal) {
  if (!confirm(`Are you sure you want to permanently delete record #${pkVal} from '${dapState.currentTable}'?`)) {
    return;
  }

  try {
    await API.deleteTableRow(dapState.currentTable, pkVal);
    safeToast(`Record #${pkVal} deleted successfully!`);

    await loadOverview(true);
    await refreshBrowseData();
  } catch (err) {
    safeToast("Delete failed: " + err.message, "error");
  }
}
window.confirmDeleteRow = confirmDeleteRow;

// -----------------------------------------------------------------------------
// 10. RAW SQL CONSOLE RUNNER (TAB 4)
// -----------------------------------------------------------------------------
async function handleRunSql() {
  const runBtn = document.getElementById("btn-run-sql");
  const sqlInput = document.getElementById("dap-sql-input");
  const banner = document.getElementById("dap-sql-stats-banner");
  const thead = document.getElementById("dap-sql-thead");
  const tbody = document.getElementById("dap-sql-tbody");

  const sql = sqlInput ? sqlInput.value.trim() : "";
  if (!sql) return;

  if (runBtn) {
    runBtn.disabled = true;
    runBtn.textContent = "Running...";
  }

  try {
    const res = await API.executeRawQuery(sql);

    if (banner) {
      banner.style.display = "block";
      if (res.type === "SELECT") {
        banner.innerHTML = `<strong>Execution successful</strong> in <strong>${res.execution_time_ms} ms</strong> | Returned <strong>${res.row_count} rows</strong>.`;
      } else {
        banner.innerHTML = `<strong>Query executed</strong> in <strong>${res.execution_time_ms} ms</strong> | <strong>${res.rows_affected} rows affected</strong>.`;
      }
    }

    if (res.type === "SELECT" && thead && tbody) {
      const cols = res.columns || [];
      thead.innerHTML = `<tr>${cols.map(c => `<th>${escapeHtml(c)}</th>`).join("")}</tr>`;

      if (!res.rows || res.rows.length === 0) {
        tbody.innerHTML = `<tr><td colspan="${cols.length}" style="text-align:center;padding:18px;color:#64748B;">No rows matched query.</td></tr>`;
      } else {
        tbody.innerHTML = res.rows.map(row => `
          <tr>${row.map(val => `<td>${formatTableCellValue(val, "")}</td>`).join("")}</tr>
        `).join("");
      }
    } else if (tbody) {
      if (thead) thead.innerHTML = `<tr><th>Status</th><th>Rows Affected</th></tr>`;
      tbody.innerHTML = `<tr><td style="color:#00BA63;font-weight:700;">OK</td><td>${res.rows_affected}</td></tr>`;
    }

    if (res.type === "EXECUTE") {
      loadOverview(true);
    }
  } catch (err) {
    if (banner) {
      banner.style.display = "block";
      banner.innerHTML = `<span style="color:#EF4444;font-weight:700;">Error:</span> <span style="color:#EF4444;">${escapeHtml(err.message)}</span>`;
    }
    if (tbody) {
      tbody.innerHTML = `<tr><td style="text-align:center;padding:20px;color:#EF4444;">${escapeHtml(err.message)}</td></tr>`;
    }
  } finally {
    if (runBtn) {
      runBtn.disabled = false;
      runBtn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg> Run SQL Query`;
    }
  }
}
window.handleRunSql = handleRunSql;

function setupSqlConsole() {
  document.getElementById("btn-run-sql")?.addEventListener("click", handleRunSql);

  // Snippets click
  document.querySelectorAll(".sql-snippet-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const sql = btn.getAttribute("data-sql");
      const sqlInput = document.getElementById("dap-sql-input");
      if (sql && sqlInput) {
        sqlInput.value = sql;
        sqlInput.focus();
      }
    });
  });
}

// -----------------------------------------------------------------------------
// 11. MAINTENANCE ACTIONS (VACUUM, INTEGRITY, DOWNLOAD)
// -----------------------------------------------------------------------------
async function handleVacuumDb() {
  const btn = document.getElementById("btn-vacuum-db");
  if (btn) btn.disabled = true;
  try {
    const res = await API.vacuumDatabase();
    safeToast(`Database VACUUM completed in ${res.execution_time_ms} ms! Reclaimed ${res.reclaimed_kb} KB.`);
    await loadOverview(true);
  } catch (err) {
    safeToast("VACUUM failed: " + err.message, "error");
  } finally {
    if (btn) btn.disabled = false;
  }
}
window.handleVacuumDb = handleVacuumDb;

async function handleIntegrityCheck() {
  try {
    const res = await API.checkDatabaseIntegrity();
    if (res.status === "HEALTHY") {
      safeToast("PRAGMA Integrity Check: HEALTHY (0 errors found)");
    } else {
      safeToast("PRAGMA Integrity Check: " + (res.messages || []).join(", "), "error");
    }
  } catch (err) {
    safeToast("Integrity check failed: " + err.message, "error");
  }
}
window.handleIntegrityCheck = handleIntegrityCheck;

function handleDownloadDb() {
  window.location.href = API.getDatabaseBackupUrl();
}
window.handleDownloadDb = handleDownloadDb;

function setupMaintenanceButtons() {
  document.getElementById("btn-vacuum-db")?.addEventListener("click", handleVacuumDb);
  document.getElementById("btn-integrity-check")?.addEventListener("click", handleIntegrityCheck);
  document.getElementById("btn-download-db")?.addEventListener("click", handleDownloadDb);
}

// -----------------------------------------------------------------------------
// 12. EXPORT TABLE (TAB 5)
// -----------------------------------------------------------------------------
function handleExportCsv() {
  window.location.href = API.getTableExportUrl(dapState.currentTable, "csv");
}
window.handleExportCsv = handleExportCsv;

function handleExportJson() {
  window.location.href = API.getTableExportUrl(dapState.currentTable, "json");
}
window.handleExportJson = handleExportJson;

function setupExportButtons() {
  document.getElementById("btn-export-csv")?.addEventListener("click", handleExportCsv);
  document.getElementById("btn-export-json")?.addEventListener("click", handleExportJson);
}

// -----------------------------------------------------------------------------
// UTILITIES
// -----------------------------------------------------------------------------
function escapeHtml(str) {
  return String(str).replace(/[&<>'"]/g, tag => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    "'": '&#39;',
    '"': '&quot;'
  }[tag] || tag));
}
