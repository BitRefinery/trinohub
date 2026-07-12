const iconPaths = {
  activity: '<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>',
  "arrow-left": '<path d="m12 19-7-7 7-7"></path><path d="M19 12H5"></path>',
  "arrow-right": '<path d="M5 12h14"></path><path d="m12 5 7 7-7 7"></path>',
  check: '<path d="M20 6 9 17l-5-5"></path>',
  cloud: '<path d="M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9Z"></path>',
  database: '<ellipse cx="12" cy="5" rx="9" ry="3"></ellipse><path d="M3 5v14c0 1.66 4.03 3 9 3s9-1.34 9-3V5"></path><path d="M3 12c0 1.66 4.03 3 9 3s9-1.34 9-3"></path>',
  download: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><path d="M7 10l5 5 5-5"></path><path d="M12 15V3"></path>',
  history: '<path d="M3 12a9 9 0 1 0 3-6.7"></path><path d="M3 3v6h6"></path><path d="M12 7v5l4 2"></path>',
  logout: '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path><polyline points="16 17 21 12 16 7"></polyline><line x1="21" x2="9" y1="12" y2="12"></line>',
  info: '<circle cx="12" cy="12" r="10"></circle><path d="M12 16v-4"></path><path d="M12 8h.01"></path>',
  copy: '<rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>',
  pause: '<path d="M14 4h4v16h-4z"></path><path d="M6 4h4v16H6z"></path>',
  play: '<polygon points="6 3 20 12 6 21 6 3"></polygon>',
  plus: '<path d="M5 12h14"></path><path d="M12 5v14"></path>',
  search: '<circle cx="11" cy="11" r="8"></circle><path d="m21 21-4.3-4.3"></path>',
  server: '<rect x="3" y="4" width="18" height="8" rx="2"></rect><rect x="3" y="12" width="18" height="8" rx="2"></rect><path d="M7 8h.01"></path><path d="M7 16h.01"></path>',
  settings: '<path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.38a2 2 0 0 0-.73-2.73l-.15-.09a2 2 0 0 1-1-1.74v-.51a2 2 0 0 1 1-1.72l.15-.1a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2Z"></path><circle cx="12" cy="12" r="3"></circle>',
  shield: '<path d="M20 13c0 5-3.5 7.5-7.7 8.9a1 1 0 0 1-.6 0C7.5 20.5 4 18 4 13V5a1 1 0 0 1 1-1c2 0 4.6-1.2 6.2-2.5a1.3 1.3 0 0 1 1.6 0C14.4 2.8 17 4 19 4a1 1 0 0 1 1 1Z"></path>',
  sliders: '<path d="M4 21v-7"></path><path d="M4 10V3"></path><path d="M12 21v-9"></path><path d="M12 8V3"></path><path d="M20 21v-5"></path><path d="M20 12V3"></path><path d="M2 14h4"></path><path d="M10 8h4"></path><path d="M18 16h4"></path>',
  terminal: '<polyline points="4 17 10 11 4 5"></polyline><line x1="12" x2="20" y1="19" y2="19"></line>',
  trash: '<path d="M3 6h18"></path><path d="M8 6V4h8v2"></path><path d="M19 6l-1 14H6L5 6"></path><path d="M10 11v6"></path><path d="M14 11v6"></path>',
  "user-plus": '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M19 8v6"></path><path d="M22 11h-6"></path>',
  users: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M22 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path>',
  visibility: '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z"></path><circle cx="12" cy="12" r="3"></circle>',
  wand: '<path d="M15 4V2"></path><path d="M15 16v-2"></path><path d="M8 9h2"></path><path d="M20 9h2"></path><path d="M17.8 6.2 19 5"></path><path d="M11 5l1.2 1.2"></path><path d="m19 13-1.2-1.2"></path><path d="M3 21l9-9"></path><path d="m12 12 3 3"></path>',
  x: '<path d="M18 6 6 18"></path><path d="m6 6 12 12"></path>',
  sun: '<circle cx="12" cy="12" r="4"></circle><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"></path>',
  moon: '<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"></path>',
  sparkles: '<path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z"></path>',
  send: '<line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>',
  table: '<rect x="4" y="4" width="16" height="16" rx="2"></rect><line x1="4" y1="10" x2="20" y2="10"></line><line x1="10" y1="10" x2="10" y2="20"></line>',
  book: '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path>',
  "help-circle": '<circle cx="12" cy="12" r="10"></circle><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path><line x1="12" y1="17" x2="12.01" y2="17"></line>',
  "bar-chart": '<line x1="12" y1="20" x2="12" y2="10"></line><line x1="18" y1="20" x2="18" y2="4"></line><line x1="6" y1="20" x2="6" y2="16"></line>',
  "chevron-down": '<polyline points="6 9 12 15 18 9"></polyline>',
  "chevron-up": '<polyline points="18 15 12 9 6 15"></polyline>',
  "chevron-left": '<polyline points="15 18 9 12 15 6"></polyline>',
  "chevron-right": '<polyline points="9 6 15 12 9 18"></polyline>',
  "external-link": '<path d="M15 3h6v6"></path><path d="M10 14 21 3"></path><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h6"></path>'
};

const clusters = [];

const users = [];

const queryHistory = [];

const queryTabs = [];

const savedQueries = [];

// Notebooks: an ordered document of SQL cells. Cells reuse the existing
// /api/query path; cellRuntime holds per-cell ephemeral run state (result,
// in-flight query, chart axes, view) keyed by cell id so each cell renders its
// own table/chart independently — unlike the SQL editor's single shared pane.
const notebooks = [];
let activeNotebookId = null;
const notebookCells = [];
const cellRuntime = new Map();
const cellSaveTimers = new Map();
const notebookFieldTimers = {};
// The notebook schema browser's insert actions target the cell the user last
// edited (falling back to the first cell).
let lastFocusedNotebookCellId = null;

// In-app Docs: a manifest (groups of topics) drives the sidebar; each
// topic's Markdown is fetched on demand and rendered by a tiny built-in renderer.
const docsManifest = { groups: [] };
let activeDocSlug = null;

const schemaBrowserState = {
  clusterId: null,
  expandedCatalogs: new Set(),
  expandedSchemas: new Set(),
  expandedTables: new Set(),
  schemasByCatalog: {},
  tablesBySchema: {},
  columnsByTable: {},
  loading: new Set(),
  errors: {},
  activeTable: ""
};

// Two schema-browser surfaces share one implementation: the SQL editor sidebar
// and the notebook canvas sidebar. Each context carries its own cached
// metadata/expansion state, search query, DOM ids, cluster source, and insert
// target; every browser function takes the context explicitly. The SQL context
// wraps the long-lived schemaBrowserState object because SQL autocomplete
// reads that cache directly.
const sqlSchemaBrowser = {
  treeId: "schemaTree",
  searchId: "schemaSearch",
  state: schemaBrowserState,
  searchQuery: "",
  emptyHint: "Select a saved cluster.",
  getCluster: () => selectedQueryCluster(),
  getClusterId: () => normalizedQueryClusterId(),
  insertText: (text) => {
    insertEditorText(text);
    const editor = document.getElementById("sqlText");
    if (editor) editor.focus();
  }
};

const notebookSchemaBrowser = {
  treeId: "notebookSchemaTree",
  searchId: "notebookSchemaSearch",
  state: {
    clusterId: null,
    expandedCatalogs: new Set(),
    expandedSchemas: new Set(),
    expandedTables: new Set(),
    schemasByCatalog: {},
    tablesBySchema: {},
    columnsByTable: {},
    loading: new Set(),
    errors: {},
    activeTable: ""
  },
  searchQuery: "",
  emptyHint: "Pick a cluster for this notebook to browse its data.",
  getCluster: () => activeNotebookCluster(),
  getClusterId: () => {
    const notebook = activeNotebook();
    return notebook && notebook.cluster_id ? Number(notebook.cluster_id) : null;
  },
  insertText: (text) => insertNotebookCellText(text)
};

const autocompleteState = {
  open: false,
  items: [],
  activeIndex: 0,
  rangeStart: 0,
  rangeEnd: 0
};

const sqlSearchState = {
  query: "",
  matches: [],
  activeIndex: -1
};

const commandPaletteState = {
  open: false,
  query: "",
  activeIndex: 0,
  commands: []
};

const nationRows = [
  [0, "ALGERIA", 0],
  [1, "ARGENTINA", 1],
  [2, "BRAZIL", 1],
  [3, "CANADA", 1],
  [4, "EGYPT", 4],
  [5, "ETHIOPIA", 0],
  [6, "FRANCE", 3],
  [7, "GERMANY", 3],
  [8, "INDIA", 2],
  [9, "INDONESIA", 2]
];

const catalogRecords = [
  {
    name: "system",
    type: "builtin",
    config: { description: "Cluster metadata" },
    enabled: true
  },
  {
    name: "tpch",
    type: "builtin",
    config: { description: "Benchmark sample data" },
    enabled: true
  },
  {
    name: "tpcds",
    type: "builtin",
    config: { description: "Decision-support sample data" },
    enabled: true
  }
];

let currentWizardStep = 0;
let currentFilter = "all";
let currentWorkerMode = "autoscale";
let selectedInstanceType = "";
let queryTimer = null;
let queryTick = 0;
let liveSetupStatus = null;
let selectedClusterDetail = null;
let activeQueryId = null;
let activeQueryResult = null;
let activeQueryTabId = null;
let queryTabSaveTimer = null;
let suppressQueryTabAutosave = false;
let draggedQueryTabId = null;
let currentRunMode = "current";
let queryBatchCancelled = false;
let queryBatchResults = [];
let activeQueryResultIndex = -1;
let activeResultView = "results";
let presetTiers = [];
// Curated instance metadata (type -> {vcpu, memory_gib, hourly_usd, available, allowed})
// and the admin-enabled allowlist, both loaded from /api/instance-types.
let instanceCatalog = {};
let allowedInstanceTypes = [];
const chartState = { type: "bar", x: "", y: "" };
let savedQueryFilter = "";
let savedQuerySort = "updated";
let historyFilter = "";
let historyStatusFilter = "";
let historyRoleFilter = "";
let historyDateFilter = "";
let selectedHistoryQueryId = null;
let editingCatalogId = null;
// Redesigned Catalogs workbench state. One view, three states (list | edit |
// pick) driven by catalogView — no separate routes. catalogGroupBy switches the
// list grouping; catalogCheckState caches the last connection-check result per
// catalog id so the list can reflect healthy/error without re-running it.
let catalogView = "list";
let catalogGroupBy = "source";
let catalogSearchTerm = "";
let editingCatalogType = "s3_glue";
let catalogEditorEnabled = true;
const catalogCheckState = {};
let currentUser = null;
const SQL_SIDEBAR_STORAGE_KEY = "trinohub-sql-closed-sidebars";
let closedSqlSidebars = new Set();

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

async function apiRequest(path, options = {}) {
  const requestOptions = Object.assign({}, options, {
    credentials: "same-origin",
    headers: Object.assign({ "Content-Type": "application/json" }, options.headers || {})
  });
  const response = await fetch(path, requestOptions);
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    // Session missing/expired: drop back to the login screen instead of leaving
    // the user on a broken authenticated view. /api/auth/login is exempt so a
    // bad-password 401 surfaces inline on the form.
    if (response.status === 401 && currentUser && path !== "/api/auth/login") {
      handleSessionExpired();
    }
    throw new Error(payload.error || payload.detail || `Request failed with ${response.status}`);
  }
  return payload;
}

function iconSvg(name) {
  const path = iconPaths[name] || "";
  return `<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${path}</svg>`;
}

function replaceIcons() {
  document.querySelectorAll("[data-icon]").forEach((slot) => {
    slot.innerHTML = iconSvg(slot.dataset.icon);
  });
}

function statusClass(status) {
  const normalized = status.toLowerCase();
  if (normalized.includes("running") || normalized.includes("finished")) return "success";
  if (
    normalized.includes("scaling") ||
    normalized.includes("creating") ||
    normalized.includes("queued") ||
    normalized.includes("starting") ||
    normalized.includes("suspending") ||
    normalized.includes("deleting") ||
    normalized.includes("updating") ||
    normalized.includes("running")
  )
    return "info";
  if (normalized.includes("failed") || normalized.includes("cancel")) return "danger";
  if (normalized.includes("suspended")) return "warning";
  return "neutral";
}

// Cold-start: a resumed/started node re-downloads the JDK + Trino on first boot,
// so "Starting" is not instant. These hints set that expectation and the UI
// auto-refreshes transitional clusters so users see the transition to Running.
const COLD_START_MINUTES = "3–5";

function isTransitionalStatus(status) {
  // Statuses that advance to a resting state on their own, so the UI should keep
  // refreshing to catch the transition (e.g. Starting/Scaling -> Running).
  return ["creating", "starting", "scaling", "suspending", "deleting", "updating"].includes(
    String(status).toLowerCase()
  );
}

function isResumableStatus(status) {
  // A suspended cluster is at rest, but it can be resumed out from under the UI —
  // by a native Trino wire query, auto-resume, or a start elsewhere — so we keep a
  // (slower) refresh alive to catch it going back to Running.
  return String(status).toLowerCase() === "suspended";
}

function progressHint(status) {
  switch (String(status).toLowerCase()) {
    case "creating":
      return "Provisioning AWS resources…";
    case "starting":
      return `Resuming — first boot downloads Java + Trino on each node, typically ${COLD_START_MINUTES} min. This page refreshes automatically.`;
    case "scaling":
      return "Adjusting worker capacity…";
    case "suspending":
      return "Suspending and cleaning up tracked AWS resources…";
    case "deleting":
      return "Deleting all tracked AWS resources…";
    case "updating":
      return "Applying configuration changes…";
    default:
      return "";
  }
}

let clusterPollTimer = null;

function scheduleClusterPolling() {
  if (clusterPollTimer !== null) {
    return;
  }
  const transitioning = clusters.some((cluster) => isTransitionalStatus(cluster.status));
  const resumable = clusters.some((cluster) => isResumableStatus(cluster.status));
  if (!transitioning && !resumable) {
    return;
  }
  // Poll quickly while something is actively transitioning; fall back to a lighter
  // cadence when we are only watching a suspended cluster for a possible resume.
  const interval = transitioning ? 15000 : 30000;
  clusterPollTimer = window.setTimeout(() => {
    clusterPollTimer = null;
    loadClustersFromApi();
  }, interval);
}

function isTerminalQueryStatus(status) {
  return ["Finished", "Failed", "Cancelled"].includes(status);
}

function formatElapsedMs(value) {
  const ms = Number(value || 0);
  return `${(ms / 1000).toFixed(1)}s`;
}

function delay(ms) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function clusterNameForId(clusterId) {
  if (clusterId == null) return "—";
  const cluster = clusters.find((item) => item.id === clusterId);
  return cluster ? cluster.name : `#${clusterId}`;
}

// Prefer the cluster name captured when the query ran (survives cluster
// deletion); fall back to a live lookup, then to an em-dash (roadmap B2).
function queryClusterLabel(query) {
  return (query && query.cluster_name) || clusterNameForId(query ? query.cluster_id : null);
}

function dismissToast() {
  const toast = document.getElementById("toast");
  if (!toast) return;
  toast.classList.remove("visible");
  window.clearTimeout(showToast.timeout);
}

// type: "info" (default) | "success" | "error". Errors get a red accent and
// linger longer so they can actually be read.
function showToast(message, options = {}) {
  const toast = document.getElementById("toast");
  const type = options.type || "info";
  toast.textContent = message;
  toast.classList.remove("toast-error", "toast-success");
  if (type === "error") toast.classList.add("toast-error");
  if (type === "success") toast.classList.add("toast-success");
  toast.classList.add("visible");
  window.clearTimeout(showToast.timeout);
  showToast.timeout = window.setTimeout(
    () => toast.classList.remove("visible"),
    type === "error" ? 5200 : 2800
  );
}

// ---------------------------------------------------------------- Dialogs
// Branded replacements for window.confirm / window.prompt. All lifecycle,
// destructive, and form-entry flows go through these so they get real
// styling, context, and keyboard handling (Enter confirms, Escape cancels).

let activeDialogResolve = null;

function closeAppDialog(result) {
  const backdrop = document.getElementById("appDialogBackdrop");
  if (backdrop) backdrop.hidden = true;
  const resolve = activeDialogResolve;
  activeDialogResolve = null;
  if (resolve) resolve(result);
}

function collectDialogValues() {
  const values = {};
  document.querySelectorAll("#appDialogForm [data-dialog-field]").forEach((el) => {
    if (el.dataset.dialogMulti) {
      values[el.dataset.dialogField] = Array.from(el.querySelectorAll("input:checked")).map((input) => input.value);
    } else {
      values[el.dataset.dialogField] = el.value;
    }
  });
  return values;
}

// Resolves with the field values object on confirm ({} when no fields), or
// null on cancel/escape/backdrop click.
function openAppDialog({ title, body, fields = [], confirmLabel = "Confirm", cancelLabel = "Cancel", danger = false }) {
  closeAppDialog(null); // only one dialog at a time
  const backdrop = document.getElementById("appDialogBackdrop");
  const bodyEl = document.getElementById("appDialogBody");
  const form = document.getElementById("appDialogForm");
  const confirm = document.getElementById("appDialogConfirm");
  const cancel = document.getElementById("appDialogCancel");
  document.getElementById("appDialogTitle").textContent = title || "";
  bodyEl.textContent = body || "";
  bodyEl.hidden = !body;
  form.innerHTML = fields
    .map((field) => {
      const id = `appDialogField-${field.name}`;
      let control;
      if (field.type === "select") {
        const options = (field.options || [])
          .map(
            (opt) =>
              `<option value="${escapeHtml(opt.value)}"${opt.value === field.value ? " selected" : ""}>${escapeHtml(opt.label)}</option>`
          )
          .join("");
        control = `<select id="${id}" data-dialog-field="${escapeHtml(field.name)}">${options}</select>`;
      } else if (field.type === "checkboxes") {
        // Multi-select checkbox group; resolves to an array of checked values.
        const selected = field.value || [];
        const options = (field.options || [])
          .map(
            (opt) => `
              <label class="app-dialog-check">
                <input type="checkbox" value="${escapeHtml(opt.value)}"${selected.includes(opt.value) ? " checked" : ""} />
                <span>${escapeHtml(opt.label)}</span>
              </label>`
          )
          .join("");
        control = `<div class="app-dialog-checks" id="${id}" data-dialog-field="${escapeHtml(field.name)}" data-dialog-multi="1">${options}</div>`;
      } else if (field.type === "textarea") {
        control = `<textarea id="${id}" data-dialog-field="${escapeHtml(field.name)}" rows="${field.rows || 4}"
          placeholder="${escapeHtml(field.placeholder || "")}" spellcheck="false">${escapeHtml(field.value == null ? "" : String(field.value))}</textarea>`;
      } else {
        control = `<input id="${id}" type="${escapeHtml(field.type || "text")}" data-dialog-field="${escapeHtml(field.name)}"
          value="${escapeHtml(field.value == null ? "" : String(field.value))}"
          placeholder="${escapeHtml(field.placeholder || "")}"${field.autocomplete ? ` autocomplete="${escapeHtml(field.autocomplete)}"` : ""} />`;
      }
      const hint = field.hint ? `<small class="app-dialog-hint">${escapeHtml(field.hint)}</small>` : "";
      return `<label class="app-dialog-field" for="${id}"><span>${escapeHtml(field.label || "")}</span>${control}${hint}</label>`;
    })
    .join("");
  form.hidden = fields.length === 0;
  confirm.textContent = confirmLabel;
  cancel.textContent = cancelLabel;
  confirm.className = danger ? "danger-button" : "primary-button";
  backdrop.hidden = false;
  const firstField = form.querySelector("input, select");
  window.setTimeout(() => (firstField || confirm).focus(), 0);
  return new Promise((resolve) => {
    activeDialogResolve = resolve;
  });
}

async function appConfirm({ title, body, confirmLabel = "Confirm", danger = false }) {
  const result = await openAppDialog({ title, body, confirmLabel, danger });
  return result !== null;
}

// Single-value prompt. Resolves with the string (may be empty) or null on cancel.
async function appPrompt({ title, body, label = "", value = "", placeholder = "", type = "text", confirmLabel = "Save" }) {
  const result = await openAppDialog({
    title,
    body,
    confirmLabel,
    fields: [{ name: "value", label, value, placeholder, type }],
  });
  return result === null ? null : result.value;
}

function wireAppDialog() {
  const backdrop = document.getElementById("appDialogBackdrop");
  if (!backdrop) return;
  document.getElementById("appDialogConfirm").addEventListener("click", () => closeAppDialog(collectDialogValues()));
  document.getElementById("appDialogCancel").addEventListener("click", () => closeAppDialog(null));
  backdrop.addEventListener("mousedown", (event) => {
    if (event.target === backdrop) closeAppDialog(null);
  });
  document.addEventListener("keydown", (event) => {
    if (backdrop.hidden) return;
    if (event.key === "Escape") {
      event.preventDefault();
      closeAppDialog(null);
    } else if (event.key === "Enter" && event.target.tagName !== "TEXTAREA") {
      event.preventDefault();
      closeAppDialog(collectDialogValues());
    }
  });
}

// Clipboard copy that also works over plain HTTP (e.g. http://<ec2-ip>:8000).
// navigator.clipboard only exists in secure contexts (HTTPS or localhost), so
// fall back to a hidden-textarea + execCommand("copy") elsewhere.
function copyText(text) {
  if (navigator.clipboard && window.isSecureContext) {
    return navigator.clipboard.writeText(text);
  }
  return new Promise((resolve, reject) => {
    const textarea = document.createElement("textarea");
    textarea.value = text;
    textarea.setAttribute("readonly", "");
    textarea.style.position = "fixed";
    textarea.style.top = "-1000px";
    textarea.style.opacity = "0";
    document.body.appendChild(textarea);
    textarea.select();
    let ok = false;
    try {
      ok = document.execCommand("copy");
    } catch (err) {
      ok = false;
    }
    document.body.removeChild(textarea);
    ok ? resolve() : reject(new Error("copy failed"));
  });
}

function splitList(value) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function ensureRegionOption(region) {
  const select = document.getElementById("setupRegion");
  if (!region || Array.from(select.options).some((option) => option.value === region || option.textContent === region)) {
    return;
  }
  const option = document.createElement("option");
  option.value = region;
  option.textContent = region;
  select.append(option);
}

function updateLiveSetupUi(status) {
  liveSetupStatus = status;
  const aws = status.aws || {};
  const metadata = aws.metadata || {};
  const checks = aws.checks || [];
  const passing = checks.filter((check) => check.ok).length;
  const region = aws.region || metadata.region || "us-east-2";

  ensureRegionOption(region);
  ensureCatalogRegionOption(region);
  const setupRegion = document.getElementById("setupRegion");
  if (setupRegion) setupRegion.value = region;
  // The catalog Glue-region field only exists while an S3/Glue form is rendered.
  const glueRegionField = catalogFieldEl("glue_region");
  if (glueRegionField) glueRegionField.value = region;
  document.getElementById("topbarRegion").textContent = region;
  document.getElementById("instanceProfileStatus").textContent = metadata.role ? "Attached" : "Missing";
  document.getElementById("instanceProfileName").textContent = metadata.role || "no instance profile";
  document.getElementById("setupControlRole").value = metadata.role || "TrinoHubControlPlaneRole";
  document.getElementById("topbarIamStatus").textContent = aws.ok ? "IAM validated" : "IAM needs attention";

  const network = aws.network || {};
  const vpcs = network.vpcs || [];
  const subnets = network.subnets || [];
  const securityGroups = network.security_groups || [];
  const vpcSelect = document.getElementById("setupVpc");
  vpcSelect.innerHTML = vpcs
    .map((vpc) => `<option value="${escapeHtml(vpc.vpc_id)}">${escapeHtml(vpc.vpc_id)} / ${escapeHtml(vpc.cidr)}</option>`)
    .join("");
  if (vpcs.length) {
    const selectedVpc = vpcs[0].vpc_id;
    vpcSelect.value = selectedVpc;
    document.getElementById("setupSubnets").value = subnets
      .filter((subnet) => subnet.vpc_id === selectedVpc)
      .map((subnet) => subnet.subnet_id)
      .join(", ");
    const defaultGroup = securityGroups.find((group) => group.vpc_id === selectedVpc && group.name === "default") || securityGroups[0];
    document.getElementById("setupSecurityGroup").value = defaultGroup ? defaultGroup.group_id : "";
  }

  document.getElementById("readinessChip").textContent = `${passing} of ${checks.length} checks passed`;
  document.getElementById("readinessChip").className = `chip ${aws.ok ? "success" : "warning"}`;
  document.getElementById("setupValidationStatus").innerHTML = aws.ok
    ? '<span data-icon="check"></span> Permissions valid'
    : '<span data-icon="info"></span> Review permissions';
  document.getElementById("readinessChecks").innerHTML = checks
    .map(
      (check) =>
        `<li><span data-icon="${check.ok ? "check" : "x"}"></span> ${escapeHtml(check.name)}: ${escapeHtml(check.detail)}</li>`
    )
    .join("");

  if (status.configured && status.setup) {
    document.getElementById("uiNetworkStatus").textContent = "Configured";
    document.getElementById("uiNetworkNote").textContent = status.setup.allowed_ui_cidrs.join(", ") || "local access";
    document.getElementById("settingsRegion").textContent = status.setup.region || region;
    document.getElementById("settingsVpc").textContent = status.setup.vpc_id || "-";
    document.getElementById("settingsNodeProfile").textContent = status.setup.node_instance_profile || "-";
    document.getElementById("settingsUiCidrs").textContent = status.setup.allowed_ui_cidrs.join(", ") || "local access";
    const uiCidrsInput = document.getElementById("settingsUiCidrsInput");
    if (uiCidrsInput && document.activeElement !== uiCidrsInput) {
      uiCidrsInput.value = status.setup.allowed_ui_cidrs.join(", ");
    }
    document.getElementById("settingsValidationChip").textContent = aws.ok ? "Validated" : "Needs review";
    document.getElementById("settingsValidationChip").className = `chip ${aws.ok ? "success" : "warning"}`;
    const baseDomain = status.setup.cluster_base_domain || "";
    const baseDomainInput = document.getElementById("settingsBaseDomain");
    if (baseDomainInput) baseDomainInput.value = baseDomain;
    const baseDomainChip = document.getElementById("baseDomainChip");
    if (baseDomainChip) {
      baseDomainChip.textContent = baseDomain || "Not set";
      baseDomainChip.className = `chip ${baseDomain ? "success" : "neutral"}`;
    }
  }

  updateWizard();
  replaceIcons();

  if (status.configured) {
    loadCatalogsFromApi();
    loadClustersFromApi();
    loadUsersFromApi();
  }
}

async function loadLiveSetupStatus() {
  try {
    const status = await apiRequest("/api/setup/status?validate=1");
    updateLiveSetupUi(status);
  } catch (error) {
    document.getElementById("topbarIamStatus").textContent = "API unavailable";
    document.getElementById("readinessChip").textContent = "Checks failed";
    document.getElementById("readinessChip").className = "chip danger";
    document.getElementById("readinessChecks").innerHTML = `<li><span data-icon="x"></span> ${escapeHtml(error.message)}</li>`;
    replaceIcons();
  }
}

async function completeSetup() {
  const password = document.getElementById("setupPassword").value;
  const confirm = document.getElementById("setupPasswordConfirm").value;
  if (password !== confirm) {
    showToast("Password confirmation does not match.");
    return;
  }

  const payload = {
    username: document.getElementById("setupAdmin").value.trim(),
    email: document.getElementById("setupEmail").value.trim(),
    password,
    setup_token: document.getElementById("setupToken").value.trim(),
    region: document.getElementById("setupRegion").value,
    vpc_id: document.getElementById("setupVpc").value,
    private_subnet_ids: splitList(document.getElementById("setupSubnets").value),
    cluster_security_group_id: document.getElementById("setupSecurityGroup").value.trim(),
    node_instance_profile: document.getElementById("setupNodeProfile").value.trim(),
    allowed_ui_cidrs: splitList(document.getElementById("setupAllowedCidrs").value)
  };

  const submit = () =>
    apiRequest("/api/setup/complete", {
      method: "POST",
      body: JSON.stringify(payload)
    });

  try {
    document.getElementById("wizardNext").disabled = true;
    let result;
    try {
      result = await submit();
    } catch (error) {
      // The server refuses an allowed-UI-CIDR list that would 403 this browser
      // right after setup; let the operator either fix the list or opt in.
      if (!/lock you out/.test(error.message)) throw error;
      const confirmed = await openAppDialog({
        title: "Allowed UI CIDRs block your own address",
        body: `${error.message} Finish setup anyway? You would need host access to reach the app afterwards.`,
        confirmLabel: "Finish and lock me out",
        danger: true
      });
      if (confirmed === null) return;
      payload.confirm_lockout = true;
      result = await submit();
    }
    showToast(`Setup saved for ${result.user.username}.`);
    // Setup created the admin and a session cookie — treat as signed in.
    onAuthenticated(result.user);
  } catch (error) {
    showToast(error.message, { type: "error" });
  } finally {
    document.getElementById("wizardNext").disabled = false;
  }
}

function clusterFromApi(cluster) {
  // Show the configured capacity honestly — live desired capacity is only
  // known on the detail page (from the ASG), so don't fake a "0 /" here.
  const workerText =
    cluster.worker_mode === "fixed"
      ? String(cluster.min_workers)
      : `${cluster.min_workers}-${cluster.max_workers}`;
  return {
    id: cluster.id,
    name: cluster.name,
    status: cluster.status,
    preset: cluster.preset,
    instance_type: cluster.instance_type || "",
    trino_version: cluster.trino_version || "",
    region: cluster.region,
    workers: workerText,
    autoscaling: cluster.worker_mode === "fixed" ? "Off" : "Trino-aware",
    suspend: cluster.auto_suspend_minutes ? `${cluster.auto_suspend_minutes} minutes` : "Never",
    owner: cluster.owner_username || "—",
    catalogs: cluster.catalogs.filter((name) => name !== "system").join(", ") || "system",
    catalogList: cluster.catalogs,
    // Raw editable fields preserved for the PATCH edit flow.
    worker_mode: cluster.worker_mode,
    min_workers: cluster.min_workers,
    max_workers: cluster.max_workers,
    auto_suspend_minutes: cluster.auto_suspend_minutes,
    accelerated: Boolean(cluster.accelerated),
    uptime_schedule: cluster.uptime_schedule || []
  };
}

const UPTIME_DAY_LABELS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"];

// [{days:[0..4], start, end}] → "mon-fri 08:00-18:00" lines for the edit dialog.
function uptimeScheduleText(windows) {
  return (windows || [])
    .map((window) => {
      const days = (window.days || []).slice().sort((a, b) => a - b);
      const contiguous = days.length > 1 && days[days.length - 1] - days[0] === days.length - 1;
      const dayText = contiguous
        ? `${UPTIME_DAY_LABELS[days[0]]}-${UPTIME_DAY_LABELS[days[days.length - 1]]}`
        : days.map((day) => UPTIME_DAY_LABELS[day]).join(",");
      return `${dayText} ${window.start}-${window.end}`;
    })
    .join("\n");
}

async function loadClustersFromApi() {
  try {
    const result = await apiRequest("/api/clusters");
    clusters.splice.apply(clusters, [0, clusters.length].concat(result.clusters.map(clusterFromApi)));
    renderClusters();
    // The catalog list shows each catalog's attached clusters, so refresh it once
    // cluster data (which carries the attachments) has loaded.
    if (catalogView === "list") renderCatalogList();
    updateQueryClusterOptions();
    populateNotebookClusterOptions();
    maybeDefaultNotebookCluster();
    populateAskClusterOptions();
    loadQueryHistoryFromApi();
  } catch (error) {
    if (/Authentication required/.test(error.message)) {
      clusters.splice(0, clusters.length);
      renderClusters();
      updateQueryClusterOptions();
    } else {
      showToast(error.message, { type: "error" });
    }
  }
}

function catalogDescription(catalog) {
  if (catalog.type === "builtin") return (catalog.config && catalog.config.description) || "Built-in catalog";
  if (GLUE_CATALOG_TYPES[catalog.type]) {
    const config = catalog.config || {};
    const mode = config.access_mode === "read_only" ? "read only" : "read and write";
    return `${GLUE_CATALOG_TYPES[catalog.type].shortLabel} / ${config.glue_region || "region unset"} / ${mode}`;
  }
  if (JDBC_CATALOG_TYPES[catalog.type]) {
    const config = catalog.config || {};
    let host = "host unset";
    // Grab the host after the last "//" so it works for jdbc:, mongodb:, and
    // Oracle's jdbc:oracle:thin:@//host form alike.
    const match = /\/\/([^/:;?@\s]+)/.exec(config.connection_url || "");
    if (match) host = match[1];
    return `${JDBC_CATALOG_TYPES[catalog.type].label} / ${host} / ${config.connection_user || "user unset"}`;
  }
  if (isSearchCatalogType(catalog.type)) {
    const config = catalog.config || {};
    const host = config.host || "host unset";
    const port = config.port || 9200;
    return `${SEARCH_CATALOG_TYPES[catalog.type].label} / ${host}:${port} / ${config.connection_user || "user unset"}`;
  }
  if (catalog.type === "bigquery") {
    const config = catalog.config || {};
    return `Google BigQuery / ${config.project_id || "project unset"} / service-account key`;
  }
  if (catalog.type === "gsheets") {
    const config = catalog.config || {};
    return `Google Sheets / metadata sheet ${config.metadata_sheet_id ? "set" : "unset"} / service-account key`;
  }
  if (isCassandraCatalogType(catalog.type)) {
    const config = catalog.config || {};
    const points = config.contact_points || "hosts unset";
    const auth = config.connection_user ? config.connection_user : "no auth";
    return `Apache Cassandra / ${points} / ${auth}`;
  }
  if (isPrometheusCatalogType(catalog.type)) {
    const config = catalog.config || {};
    const auth = config.connection_user ? config.connection_user : "no auth";
    return `Prometheus / ${config.uri || "endpoint unset"} / ${auth}`;
  }
  if (isGeneratorCatalogType(catalog.type)) {
    return GENERATOR_CATALOG_TYPES[catalog.type].description;
  }
  return catalog.type;
}

// S3/Glue-family connectors share one form (Glue region / warehouse / access
// mode) and IAM auth; they differ only in the Trino connector.name and the
// stored table_format. Mirrors the kind="s3_glue" descriptors in
// trinohub/connectors.py.
const GLUE_CATALOG_TYPES = {
  s3_glue: { label: "Iceberg", tableFormat: "ICEBERG", shortLabel: "S3 + Glue Iceberg" },
  delta_glue: { label: "Delta Lake", tableFormat: "DELTA", shortLabel: "Delta Lake on S3 + Glue" },
  hive_glue: { label: "Hive", tableFormat: "HIVE", shortLabel: "Hive on S3 + Glue" },
  hudi_glue: { label: "Hudi", tableFormat: "HUDI", shortLabel: "Hudi on S3 + Glue" }
};

function isGlueCatalogType(type) {
  return Boolean(GLUE_CATALOG_TYPES[type]);
}

// Elasticsearch and its OpenSearch fork share one host/port/user form group and
// PASSWORD auth; only the display label differs. Mirrors kind="elasticsearch".
const SEARCH_CATALOG_TYPES = {
  elasticsearch: { label: "Elasticsearch" },
  opensearch: { label: "OpenSearch" }
};

function isSearchCatalogType(type) {
  return Boolean(SEARCH_CATALOG_TYPES[type]);
}

// Cassandra: comma-separated contact points + optional auth. Setting a connection
// user turns on PASSWORD auth (a password is then required); leaving it blank
// means an unauthenticated cluster with no stored secret. Mirrors the
// kind="cassandra" descriptor + optional_secret path in trinohub/connectors.py.
const CASSANDRA_CATALOG_TYPES = {
  cassandra: { label: "Apache Cassandra" }
};

function isCassandraCatalogType(type) {
  return Boolean(CASSANDRA_CATALOG_TYPES[type]);
}

// Prometheus: one HTTP(S) endpoint + optional basic auth. A connection user turns
// on basic auth (password then required); blank means an open server with no
// stored secret. Mirrors the kind="prometheus" + optional_secret descriptor.
const PROMETHEUS_CATALOG_TYPES = {
  prometheus: { label: "Prometheus" }
};

function isPrometheusCatalogType(type) {
  return Boolean(PROMETHEUS_CATALOG_TYPES[type]);
}

// Zero-config generators (memory/blackhole/faker): name + type only, no fields.
const GENERATOR_CATALOG_TYPES = {
  memory: { label: "Memory", description: "In-memory tables (non-persistent)" },
  blackhole: { label: "Black Hole", description: "Discards writes; a data sink for testing" },
  faker: { label: "Faker", description: "Generates synthetic rows on read" }
};

function isGeneratorCatalogType(type) {
  return Boolean(GENERATOR_CATALOG_TYPES[type]);
}

// Connection-URL connectors (every JDBC database + MongoDB) share one form
// (connection URL / user / password) and one create path; only the URL scheme,
// placeholder, and display label differ. The urlPattern mirrors the per-type
// regex in trinohub/connectors.py. Elasticsearch is NOT here — it has its own
// host/port form group.
const JDBC_CATALOG_TYPES = {
  postgresql: {
    label: "PostgreSQL",
    urlPlaceholder: "jdbc:postgresql://host:5432/database",
    urlExample: "jdbc:postgresql://host:5432/database",
    urlPattern: /^jdbc:postgresql:\/\/[^/:?\s]+(?::\d+)?\/[^\s?]+(?:\?\S*)?$/
  },
  mysql: {
    label: "MySQL",
    urlPlaceholder: "jdbc:mysql://host:3306",
    urlExample: "jdbc:mysql://host:3306[/database]",
    urlPattern: /^jdbc:mysql:\/\/[^/:?\s]+(?::\d+)?(?:\/[^\s?]*)?(?:\?\S*)?$/
  },
  redshift: {
    label: "Amazon Redshift",
    urlPlaceholder: "jdbc:redshift://host:5439/database",
    urlExample: "jdbc:redshift://host:5439/database",
    urlPattern: /^jdbc:redshift:\/\/[^/:?\s]+(?::\d+)?\/[^\s?]+(?:\?\S*)?$/
  },
  sqlserver: {
    label: "SQL Server",
    urlPlaceholder: "jdbc:sqlserver://host:1433;databaseName=db",
    urlExample: "jdbc:sqlserver://host:1433[;property=value]",
    urlPattern: /^jdbc:sqlserver:\/\/[^/:;?\s]+(?::\d+)?(?:;\S*)?$/
  },
  mariadb: {
    label: "MariaDB",
    urlPlaceholder: "jdbc:mariadb://host:3306",
    urlExample: "jdbc:mariadb://host:3306[/database]",
    urlPattern: /^jdbc:mariadb:\/\/[^/:?\s]+(?::\d+)?(?:\/[^\s?]*)?(?:\?\S*)?$/
  },
  singlestore: {
    label: "SingleStore",
    urlPlaceholder: "jdbc:singlestore://host:3306",
    urlExample: "jdbc:singlestore://host:3306[/database]",
    urlPattern: /^jdbc:singlestore:\/\/[^/:?\s]+(?::\d+)?(?:\/[^\s?]*)?(?:\?\S*)?$/
  },
  clickhouse: {
    label: "ClickHouse",
    urlPlaceholder: "jdbc:clickhouse://host:8123",
    urlExample: "jdbc:clickhouse://host:8123[/database]",
    urlPattern: /^jdbc:clickhouse:\/\/[^/:?\s]+(?::\d+)?(?:\/[^\s?]*)?(?:\?\S*)?$/
  },
  oracle: {
    label: "Oracle",
    urlPlaceholder: "jdbc:oracle:thin:@//host:1521/service",
    urlExample: "jdbc:oracle:thin:@//host:1521/service",
    urlPattern: /^jdbc:oracle:thin:@\/\/[^/:?\s]+(?::\d+)?\/[^\s?]+$/
  },
  snowflake: {
    label: "Snowflake",
    urlPlaceholder: "jdbc:snowflake://account.snowflakecomputing.com",
    urlExample: "jdbc:snowflake://account.snowflakecomputing.com",
    urlPattern: /^jdbc:snowflake:\/\/[^/:?\s]+(?:\/[^\s?]*)?(?:\?\S*)?$/
  },
  druid: {
    label: "Apache Druid",
    urlPlaceholder: "jdbc:avatica:remote:url=http://broker:8082/druid/v2/sql/avatica/",
    urlExample: "jdbc:avatica:remote:url=http://broker:8082/druid/v2/sql/avatica/",
    urlPattern: /^jdbc:avatica:remote:url=https?:\/\/[^/:?\s]+(?::\d+)?\/[^\s;]*(?:;\S*)?$/
  },
  mongodb: {
    label: "MongoDB",
    urlPlaceholder: "mongodb://host:27017/database",
    urlExample: "mongodb://host:27017[/database] (no embedded credentials)",
    urlPattern: /^(?:mongodb|mongodb\+srv):\/\/[^/:?@\s]+(?::\d+)?(?:,[^/?@\s]+)*(?:\/[^\s?]*)?(?:\?\S*)?$/
  }
};

function isJdbcCatalogType(type) {
  return Boolean(JDBC_CATALOG_TYPES[type]);
}

// Every non-built-in connector type, derived so it can't drift as types are added.
const DATA_CATALOG_TYPES = [
  ...Object.keys(GLUE_CATALOG_TYPES),
  ...Object.keys(JDBC_CATALOG_TYPES),
  ...Object.keys(SEARCH_CATALOG_TYPES),
  ...Object.keys(CASSANDRA_CATALOG_TYPES),
  ...Object.keys(PROMETHEUS_CATALOG_TYPES),
  ...Object.keys(GENERATOR_CATALOG_TYPES),
  "bigquery",
  "gsheets"
];

// Connectors whose JDBC driver isn't bundled and must be uploaded by an admin.
// Mirrors DRIVER_REQUIRED_TYPES in trinohub/connectors.py.
const DRIVER_REQUIRED_TYPES = ["oracle"];
let connectorDrivers = {}; // connector_type -> uploaded driver metadata

// Registry-derived connector form schema from GET /api/connector-types. This is
// the single source of truth for the connector picker and the type dropdown, so
// adding a connector server-side surfaces in the UI without editing this file.
let connectorTypeCatalog = [];

async function loadConnectorTypes() {
  try {
    const result = await apiRequest("/api/connector-types");
    connectorTypeCatalog = Array.isArray(result.connector_types) ? result.connector_types : [];
    renderConnectorTypeOptions();
  } catch (error) {
    // Requires an authenticated user; before login the picker/dropdown stay empty.
  }
}

// Build the connector-type <select> from the fetched schema (registry order).
function renderConnectorTypeOptions() {
  const select = document.getElementById("catalogConnectorType");
  if (!select || !connectorTypeCatalog.length) return;
  const current = select.value;
  select.innerHTML = connectorTypeCatalog
    .map((c) => `<option value="${escapeHtml(c.type)}">${escapeHtml(c.label)}</option>`)
    .join("");
  if (current && connectorTypeCatalog.some((c) => c.type === current)) select.value = current;
}

function connectorSchema(type) {
  return connectorTypeCatalog.find((c) => c.type === type) || null;
}

// Address a rendered config field by its schema `name`. Only the selected type's
// fields exist inside #catalogFields at once, so names (which match the catalog
// config keys) are unambiguous; the scoped query keeps them out of the global id
// space (e.g. no clash with the login "password" field).
function catalogFieldEl(name) {
  const container = document.getElementById("catalogFields");
  return container ? container.querySelector(`[data-field="${name}"]`) : null;
}

// Base Glue/S3 regions offered in the region picker; ensureCatalogRegionOption()
// appends the live setup region on top when it isn't one of these.
const CATALOG_REGION_OPTIONS = ["us-east-2", "us-east-1", "us-west-2"];

// Render one schema field as a labelled control. `data-field` carries the config
// key; input kinds map to the same controls the form used when it was static.
function catalogFieldMarkup(field) {
  const name = escapeHtml(field.name);
  const cls = field.full_width ? ' class="span-2"' : "";
  const label = `<span>${escapeHtml(field.label)}</span>`;
  const ph = field.placeholder ? ` placeholder="${escapeHtml(String(field.placeholder))}"` : "";
  let control;
  switch (field.input) {
    case "textarea":
      control = `<textarea data-field="${name}" rows="6"${ph} autocomplete="off"></textarea>`;
      break;
    case "password":
      control = `<input data-field="${name}" type="password" placeholder="••••••••" autocomplete="new-password" />`;
      break;
    case "number": {
      const val = field.default != null ? ` value="${escapeHtml(String(field.default))}"` : "";
      control = `<input data-field="${name}" type="number" min="1" max="65535"${val} />`;
      break;
    }
    case "select": {
      control = `<select data-field="${name}">${(field.options || [])
        .map((o) => `<option${o === field.default ? " selected" : ""}>${escapeHtml(o)}</option>`)
        .join("")}</select>`;
      break;
    }
    case "region": {
      const setupRegion = (liveSetupStatus && liveSetupStatus.setup && liveSetupStatus.setup.region) || "";
      const selected = setupRegion || field.default || "us-east-2";
      const options = CATALOG_REGION_OPTIONS.includes(selected)
        ? CATALOG_REGION_OPTIONS
        : [selected, ...CATALOG_REGION_OPTIONS];
      control = `<select data-field="${name}">${options
        .map((o) => `<option${o === selected ? " selected" : ""}>${escapeHtml(o)}</option>`)
        .join("")}</select>`;
      break;
    }
    case "readonly":
      // Fixed by the connector type (e.g. table format); shown, never edited.
      control = `<select data-field="${name}" disabled><option>${escapeHtml(String(field.value || ""))}</option></select>`;
      break;
    default: {
      const val = field.default != null ? ` value="${escapeHtml(String(field.default))}"` : "";
      control = `<input data-field="${name}" type="text"${ph}${val} autocomplete="off" />`;
    }
  }
  return `<label${cls}>${label}${control}</label>`;
}

// Rebuild #catalogFields from the fetched schema for `type` (its config fields
// plus the write-only credential, if any), in schema order. Replaces the former
// hand-maintained per-type field blocks, so adding a connector server-side
// surfaces its form without editing this file.
function renderCatalogFields(type) {
  const container = document.getElementById("catalogFields");
  if (!container) return;
  const schema = connectorSchema(type);
  const fields = schema ? [...schema.fields] : [];
  if (schema && schema.credential) fields.push(schema.credential);
  container.innerHTML = fields.map(catalogFieldMarkup).join("");
}

async function loadConnectorDrivers() {
  try {
    const result = await apiRequest("/api/connector-drivers");
    connectorDrivers = {};
    for (const driver of result.drivers) connectorDrivers[driver.connector_type] = driver;
  } catch (error) {
    // Admin-only endpoint; non-admins just never see the panel.
  }
}

function renderConnectorDriverPanel(type) {
  const panel = document.getElementById("catalogDriverPanel");
  if (!panel) return;
  const needsDriver = DRIVER_REQUIRED_TYPES.includes(type);
  panel.hidden = !needsDriver;
  if (!needsDriver) return;
  const statusEl = document.getElementById("catalogDriverStatus");
  const removeBtn = document.getElementById("catalogDriverDeleteButton");
  const driver = connectorDrivers[type];
  if (driver) {
    const mb = (driver.size_bytes / (1024 * 1024)).toFixed(2);
    statusEl.textContent = `${driver.filename} · ${mb} MB · sha256 ${String(driver.sha256).slice(0, 12)}…`;
    statusEl.className = "chip success";
    if (removeBtn) removeBtn.hidden = false;
  } else {
    statusEl.textContent = "No driver uploaded — required before starting a cluster with this catalog";
    statusEl.className = "chip warning";
    if (removeBtn) removeBtn.hidden = true;
  }
}

async function uploadConnectorDriver(type, file) {
  const response = await fetch(`/api/connector-drivers/${type}?filename=${encodeURIComponent(file.name)}`, {
    method: "POST",
    credentials: "same-origin",
    body: file
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.error || payload.detail || `Upload failed (${response.status})`);
  return payload;
}

async function handleDriverUpload(type, file) {
  if (!file) return;
  try {
    await uploadConnectorDriver(type, file);
    await loadConnectorDrivers();
    renderConnectorDriverPanel(type);
    showToast(`Uploaded ${file.name} for ${type}.`);
  } catch (error) {
    showToast(error.message, { type: "error" });
  }
}

async function handleDriverDelete(type) {
  try {
    await apiRequest(`/api/connector-drivers/${type}`, { method: "DELETE" });
    await loadConnectorDrivers();
    renderConnectorDriverPanel(type);
    showToast(`Removed the ${type} driver.`);
  } catch (error) {
    showToast(error.message, { type: "error" });
  }
}

function enabledDataCatalogs() {
  return catalogRecords.filter((catalog) => catalog.enabled && DATA_CATALOG_TYPES.includes(catalog.type));
}

function selectedClusterCatalogs() {
  const selected = ["system", "tpch", "tpcds"];
  document
    .querySelectorAll("#clusterCatalogChoices input[data-cluster-catalog]:checked")
    .forEach((input) => selected.push(input.dataset.clusterCatalog));
  return selected;
}

// Render one independently-selectable toggle per saved data catalog, so a
// cluster can attach any subset of them. Preserves each catalog's checked state
// across re-renders (e.g. when the catalog list refreshes) so a user's choices
// are not silently reset.
function updateCatalogAttachmentUi() {
  const container = document.getElementById("clusterCatalogChoices");
  if (!container) return;
  const customCatalogs = enabledDataCatalogs();

  const previouslyChecked = new Set();
  let hadAny = false;
  container.querySelectorAll("input[data-cluster-catalog]").forEach((input) => {
    hadAny = true;
    if (input.checked) previouslyChecked.add(input.dataset.clusterCatalog);
  });

  if (!customCatalogs.length) {
    container.innerHTML = `
      <label class="toggle-row disabled">
        <input type="checkbox" disabled />
        <span>No data catalogs</span>
        <small>Save a catalog to attach it to a cluster</small>
      </label>`;
    return;
  }

  container.innerHTML = customCatalogs
    .map((catalog) => {
      // New catalogs default to checked; on re-render, keep the prior choice.
      const checked = hadAny ? previouslyChecked.has(catalog.name) : true;
      return `
        <label class="toggle-row">
          <input type="checkbox" data-cluster-catalog="${escapeHtml(catalog.name)}"${checked ? " checked" : ""} />
          <span>${escapeHtml(catalog.name)}</span>
          <small>${escapeHtml(catalogDescription(catalog))}</small>
        </label>`;
    })
    .join("");
}

function updateQueryCatalogOptions() {
  const select = document.getElementById("queryCatalog");
  if (!select) return;
  const previous = select.value;
  const enabled = catalogRecords.filter((catalog) => catalog.enabled);
  select.innerHTML = enabled.map((catalog) => `<option value="${catalog.name}">${escapeHtml(catalog.name)}</option>`).join("");
  if (enabled.some((catalog) => catalog.name === previous)) {
    select.value = previous;
  } else if (enabled.some((catalog) => catalog.name === "tpch")) {
    select.value = "tpch";
  }
  syncQueryContextFromActiveTab();
}

// ---------------------------------------------------------------------------
// Connector glyphs. Each catalog/connector renders a distinct icon. The path
// geometry is ported verbatim from the design handoff's iconPaths() so the
// silhouettes match pixel-for-pixel; helpers expand circles/ellipses/rects/
// lines/polygons into `d` strings. Unlike the Lucide set in `iconPaths`, these
// mix filled shapes (f:1 -> currentColor) with punch-out holes
// (f:2 -> var(--brand-subtle)), so they get their own SVG builder.
// ---------------------------------------------------------------------------
function _gc(cx, cy, r) {
  return "M" + (cx - r) + " " + cy + "a" + r + " " + r + " 0 1 0 " + 2 * r + " 0a" + r + " " + r + " 0 1 0 " + -2 * r + " 0";
}
function _ge(cx, cy, rx, ry) {
  return "M" + (cx - rx) + " " + cy + "a" + rx + " " + ry + " 0 1 0 " + 2 * rx + " 0a" + rx + " " + ry + " 0 1 0 " + -2 * rx + " 0";
}
function _grr(x, y, w, h, r) {
  r = r || 0;
  const iw = w - 2 * r;
  const ih = h - 2 * r;
  return "M" + (x + r) + " " + y + "h" + iw + "a" + r + " " + r + " 0 0 1 " + r + " " + r + "v" + ih + "a" + r + " " + r + " 0 0 1 " + -r + " " + r + "h" + -iw + "a" + r + " " + r + " 0 0 1 " + -r + " " + -r + "v" + -ih + "a" + r + " " + r + " 0 0 1 " + r + " " + -r + "z";
}
function _gln(x1, y1, x2, y2) {
  return "M" + x1 + " " + y1 + "L" + x2 + " " + y2;
}
function _gpg(pts) {
  return "M" + pts + "z";
}

let _catGlyphD = null;
function connectorGlyphPaths(key) {
  if (!_catGlyphD) {
    _catGlyphD = {
      // Group-chip + map glyphs
      cloud: [{ d: "M6.5 18a4.5 4.5 0 0 1-.5-9 6 6 0 0 1 11.6 1.5A4 4 0 0 1 17 18z" }],
      database: [{ d: _ge(12, 5, 8, 3) }, { d: "M4 5v14c0 1.7 3.6 3 8 3s8-1.3 8-3V5M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3" }],
      grid: [{ d: _grr(3, 3, 7, 7, 1.5) }, { d: _grr(14, 3, 7, 7, 1.5) }, { d: _grr(3, 14, 7, 7, 1.5) }, { d: _grr(14, 14, 7, 7, 1.5) }],
      search: [{ d: _gc(11, 11, 7) }, { d: _gln(21, 21, 16.5, 16.5) }],
      sheet: [{ d: _grr(5, 3, 14, 18, 2) }, { d: _gln(5, 9, 19, 9) }, { d: _gln(5, 15, 19, 15) }, { d: _gln(12, 9, 12, 21) }],
      flask: [{ d: "M9 3h6M10 3v5.5l-4.5 8A2 2 0 0 0 7.3 20h9.4a2 2 0 0 0 1.8-3.5L14 8.5V3" }, { d: _gln(8, 14.5, 16, 14.5) }],
      clusters: [{ d: _grr(3, 4, 18, 7, 1.5) }, { d: _grr(3, 13, 18, 7, 1.5) }],
      // Connection-check icons
      check: [{ d: "M20 6L9 17L4 12" }],
      x: [{ d: "M6 6L18 18M18 6L6 18" }],
      info: [{ d: _gc(12, 12, 9) }, { d: "M12 11v5" }, { d: _gc(12, 8, 0.9), f: 1 }],
      spin: [{ d: "M12 3a9 9 0 1 0 9 9" }],
      // Per-connector glyphs
      iceberg: [{ d: "M12 3l6.5 9.5H5.5z", f: 1 }, { d: "M12 12.5l4 7-4-1.8-4 1.8z", f: 1, op: ".4" }],
      delta: [{ d: "M12 4L3.5 19.5h17z" }, { d: _gln(8.2, 14.5, 15.8, 14.5) }, { d: _gln(9.8, 11, 14.2, 11) }],
      hive: [{ d: _gpg("12 3 19 7.5 19 16.5 12 21 5 16.5 5 7.5") }, { d: _gc(12, 12, 2.6) }],
      hudi: [{ d: _ge(12, 6, 5.5, 2.2) }, { d: "M6.5 6v8c0 1.2 2.5 2.2 5.5 2.2s5.5-1 5.5-2.2V6" }, { d: "M12 10.4v4.2m-1.8-1.9L12 14.6l1.8-1.9" }],
      postgresql: [{ d: "M16.6 4.4c-1-.4-2.3-.4-3.3.1-.6-.2-1.2-.3-1.9-.3-2.7 0-4.9 1.9-4.9 4.5 0 1.5.5 2.6 1.5 3.6.3.9 1 1.7 1.9 2.1v1.9a1.5 1.5 0 0 0 3 0v-.7c.3.1.7.1 1 .1v.6a1.5 1.5 0 0 0 3 0V15c1.2-.9 2-2.2 2-3.9 0-.5-.1-1-.3-1.5.3-1.1 0-2.4-1.3-3.2z", f: 1 }, { d: _gc(10, 9, 0.85), f: 2 }],
      mysql: [{ d: "M3.5 13.2c2.6.7 4.5-.3 5.9-2.5.6 2.5 2.2 4.3 4.8 4.9-.8 1.7-2.8 3-5.3 3-3.1 0-5.4-2-5.4-4.4z", f: 1 }, { d: "M14.5 8c1.7-.6 3.3.1 4.2 1.6-1.7-.2-3 .2-3.8 1.3z", f: 1 }, { d: _gc(6.6, 12.2, 0.7), f: 2 }],
      redshift: [{ d: _gc(12, 12, 8.5) }, { d: _gc(12, 12, 5) }, { d: _gc(12, 12, 1.8), f: 1 }],
      snowflake: [{ d: "M12 3v18M4.2 7.5l15.6 9M19.8 7.5l-15.6 9" }, { d: "M12 6.4l-1.9-1.7M12 6.4l1.9-1.7M12 17.6l-1.9 1.7M12 17.6l1.9 1.7" }, { d: "M6.9 9.2 4.6 8.9M17.1 14.8l2.3.3M6.9 14.8l-2.3.3M17.1 9.2l2.3-.3" }],
      sqlserver: [{ d: _grr(4, 5, 16, 6, 1.5) }, { d: _grr(4, 13, 16, 6, 1.5) }, { d: _gc(7.5, 8, 0.9), f: 1 }, { d: _gc(7.5, 16, 0.9), f: 1 }],
      mariadb: [{ d: _ge(12, 6, 5.5, 2.2) }, { d: "M6.5 6v12c0 1.2 2.5 2.2 5.5 2.2s5.5-1 5.5-2.2V6" }, { d: "M8 12.5c1.2 1 2.6 1 3.9 0s2.7-1 4 0" }],
      singlestore: [{ d: _gc(12, 12, 8.5) }, { d: "M13 6.5l-4.5 6.5H12l-1 4.5 4.5-6.5H12z", f: 1 }],
      clickhouse: [{ d: _grr(5, 5, 2.4, 14, 0.4), f: 1 }, { d: _grr(9.4, 5, 2.4, 14, 0.4), f: 1 }, { d: _grr(13.8, 5, 2.4, 14, 0.4), f: 1 }, { d: _grr(18.2, 5, 2.4, 7, 0.4), f: 1 }],
      oracle: [{ d: _ge(12, 12, 9, 5.8) }],
      druid: [{ d: "M12 3.5s5.5 5.5 5.5 9.5a5.5 5.5 0 0 1-11 0c0-4 5.5-9.5 5.5-9.5z" }],
      mongodb: [{ d: "M12 3c2.8 3.8 2.8 11.4 0 17.5-2.8-6.1-2.8-13.7 0-17.5z", f: 1 }],
      elasticsearch: [{ d: _gc(11, 11, 7) }, { d: _gln(21, 21, 16.5, 16.5) }],
      opensearch: [{ d: _gc(11, 11, 7) }, { d: _gln(21, 21, 16.5, 16.5) }],
      bigquery: [{ d: "M6.5 16a4 4 0 0 1-.5-8 5.5 5.5 0 0 1 10.6 1.3A3.6 3.6 0 0 1 17 16z" }, { d: _gc(11, 11.5, 2.3) }, { d: _gln(12.8, 13.3, 15, 15.5) }],
      gsheets: [{ d: _grr(5, 3, 14, 18, 2) }, { d: _gln(5, 9, 19, 9) }, { d: _gln(5, 15, 19, 15) }, { d: _gln(12, 9, 12, 21) }],
      memory: [{ d: _grr(7, 7, 10, 10, 1.5) }, { d: _grr(10, 10, 4, 4, 0), f: 1 }, { d: "M10 7V4M14 7V4M10 20v-3M14 20v-3M7 10H4M7 14H4M20 10h-3M20 14h-3" }],
      blackhole: [{ d: _gc(12, 12, 8.5) }, { d: _gc(12, 12, 3.4), f: 1 }],
      faker: [{ d: _grr(4, 4, 16, 16, 3) }, { d: _gc(9, 9, 1.1), f: 1 }, { d: _gc(15, 9, 1.1), f: 1 }, { d: _gc(12, 12, 1.1), f: 1 }, { d: _gc(9, 15, 1.1), f: 1 }, { d: _gc(15, 15, 1.1), f: 1 }],
      tpch: [{ d: "M9 3h6M10 3v5.5l-4.5 8A2 2 0 0 0 7.3 20h9.4a2 2 0 0 0 1.8-3.5L14 8.5V3" }, { d: _gln(8, 14.5, 16, 14.5) }],
      tpcds: [{ d: _gln(4, 20, 20, 20) }, { d: _grr(6, 11, 3, 8, 0.5), f: 1 }, { d: _grr(11, 7, 3, 12, 0.5), f: 1 }, { d: _grr(16, 13, 3, 6, 0.5), f: 1 }]
    };
  }
  const arr = _catGlyphD[key] || _catGlyphD.database;
  return arr.map((p) => ({
    d: p.d,
    fill: p.f === 1 ? "currentColor" : p.f === 2 ? "var(--brand-subtle)" : "none",
    stroke: p.f ? "none" : "currentColor",
    op: p.op || "1"
  }));
}

// Build an inline connector glyph SVG (own stroke-width; holes read as punch-outs).
function connectorGlyphSvg(key, size, sw) {
  size = size || 18;
  sw = sw || 1.7;
  const paths = connectorGlyphPaths(key)
    .map((p) => `<path d="${p.d}" fill="${p.fill}" stroke="${p.stroke}"${p.op !== "1" ? ` opacity="${p.op}"` : ""}></path>`)
    .join("");
  return `<svg class="cat-glyph" width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke-width="${sw}" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths}</svg>`;
}

// Trino connector.name per catalog type (differs from the type key for the
// S3/Glue family). Mirrors connector_name in trinohub/connectors.py; shown on
// the editor's live-connection map as `connector.name = <name>`.
const CONNECTOR_NAME_BY_TYPE = {
  s3_glue: "iceberg", delta_glue: "delta_lake", hive_glue: "hive", hudi_glue: "hudi",
  postgresql: "postgresql", mysql: "mysql", redshift: "redshift", sqlserver: "sqlserver",
  mariadb: "mariadb", singlestore: "singlestore", clickhouse: "clickhouse", oracle: "oracle",
  snowflake: "snowflake", druid: "druid", mongodb: "mongodb",
  elasticsearch: "elasticsearch", opensearch: "opensearch", cassandra: "cassandra",
  prometheus: "prometheus",
  bigquery: "bigquery", gsheets: "gsheets", memory: "memory", blackhole: "blackhole", faker: "faker"
};

const CATALOG_GLYPH_BY_TYPE = {
  s3_glue: "iceberg", delta_glue: "delta", hive_glue: "hive", hudi_glue: "hudi",
  postgresql: "postgresql", mysql: "mysql", redshift: "redshift", sqlserver: "sqlserver",
  mariadb: "mariadb", singlestore: "singlestore", clickhouse: "clickhouse", oracle: "oracle",
  snowflake: "snowflake", druid: "druid", mongodb: "mongodb",
  elasticsearch: "elasticsearch", opensearch: "opensearch", cassandra: "database",
  prometheus: "database",
  bigquery: "bigquery", gsheets: "gsheets", memory: "memory", blackhole: "blackhole", faker: "faker"
};

function catalogGlyphKey(catalog) {
  if (catalog.type === "builtin") {
    if (catalog.name === "tpch") return "tpch";
    if (catalog.name === "tpcds") return "tpcds";
    return "grid";
  }
  return CATALOG_GLYPH_BY_TYPE[catalog.type] || "database";
}

// List grouping "By source": one section per source family. Only families with
// at least one catalog render, so the three named ones from the design show up
// for typical data and the others appear only when such a catalog exists.
const CATALOG_SOURCE_GROUPS = [
  { key: "object", title: "Object storage & lakehouse", accent: "#3B7BDD", glyph: "cloud" },
  { key: "db", title: "Databases", accent: "#9E3FD6", glyph: "database" },
  { key: "search", title: "Document & search", accent: "#0EA5A9", glyph: "search" },
  { key: "google", title: "Google Cloud", accent: "#E0921C", glyph: "sheet" },
  { key: "test", title: "Test & sample data", accent: "#64748B", glyph: "flask" },
  { key: "builtin", title: "Built-in & sample", accent: "#16A37B", glyph: "grid" }
];

// List grouping "By status".
const CATALOG_STATUS_GROUPS = [
  { key: "error", title: "Needs attention", accent: "#DC4040", glyph: "x" },
  { key: "checking", title: "Checking", accent: "#E0921C", glyph: "spin" },
  { key: "healthy", title: "Healthy", accent: "#16A37B", glyph: "check" },
  { key: "enabled", title: "Enabled", accent: "#3B7BDD", glyph: "database" },
  { key: "disabled", title: "Disabled", accent: "#8A95AB", glyph: "grid" }
];

function catalogSourceGroup(catalog) {
  if (catalog.type === "builtin") return "builtin";
  if (isGlueCatalogType(catalog.type)) return "object";
  if (catalog.type === "bigquery" || catalog.type === "gsheets") return "google";
  if (isSearchCatalogType(catalog.type) || catalog.type === "mongodb" || isCassandraCatalogType(catalog.type)) return "search";
  if (isGeneratorCatalogType(catalog.type)) return "test";
  return "db";
}

// Derived status. The API has no status column, so status comes from what we
// truly know: built-ins are always on; a disabled flag is authoritative; and a
// live connection check (cached per id in catalogCheckState) upgrades an enabled
// catalog to healthy/error/checking. Otherwise it is simply "enabled" (untested).
function catalogStatusKey(catalog) {
  if (catalog.type === "builtin") return "healthy";
  if (!catalog.enabled) return "disabled";
  const cached = catalog.id != null ? catalogCheckState[catalog.id] : null;
  if (cached && cached.status) return cached.status;
  return "enabled";
}

const CATALOG_STATUS_LABELS = { healthy: "Healthy", enabled: "Enabled", disabled: "Disabled", error: "Error", checking: "Checking" };

function catalogTypeLabel(catalog) {
  if (catalog.type === "builtin") return "Built-in";
  if (isGlueCatalogType(catalog.type)) return "S3 + Glue · " + GLUE_CATALOG_TYPES[catalog.type].label;
  if (JDBC_CATALOG_TYPES[catalog.type]) return JDBC_CATALOG_TYPES[catalog.type].label;
  if (isSearchCatalogType(catalog.type)) return SEARCH_CATALOG_TYPES[catalog.type].label;
  if (isCassandraCatalogType(catalog.type)) return "Apache Cassandra";
  if (isPrometheusCatalogType(catalog.type)) return "Prometheus";
  if (catalog.type === "bigquery") return "Google BigQuery";
  if (catalog.type === "gsheets") return "Google Sheets";
  if (isGeneratorCatalogType(catalog.type)) return GENERATOR_CATALOG_TYPES[catalog.type].label;
  return catalog.type;
}

// The data source's host/endpoint, extracted from config for the card meta line
// and the live-connection map. Empty when the type has no endpoint (generators).
function catalogHost(catalog) {
  const config = catalog.config || {};
  if (isGlueCatalogType(catalog.type)) return config.warehouse || "AWS Glue Data Catalog · " + (config.glue_region || "region unset");
  if (JDBC_CATALOG_TYPES[catalog.type]) {
    const match = /\/\/([^/:;?@\s]+)/.exec(config.connection_url || "");
    return match ? match[1] : "host unset";
  }
  if (isSearchCatalogType(catalog.type)) return (config.host || "host unset") + ":" + (config.port || 9200);
  if (isCassandraCatalogType(catalog.type)) return config.contact_points || "hosts unset";
  if (isPrometheusCatalogType(catalog.type)) return config.uri || "endpoint unset";
  if (catalog.type === "bigquery") return config.project_id || "project unset";
  if (catalog.type === "gsheets") return config.metadata_sheet_id ? "metadata sheet set" : "metadata sheet unset";
  return "";
}

function catalogMetaDetail(catalog) {
  if (catalog.type === "builtin") return (catalog.config && catalog.config.description) || "Always available";
  if (isGeneratorCatalogType(catalog.type)) return "Zero-config test data";
  return catalogHost(catalog) || catalogTypeLabel(catalog);
}

// Cluster names this catalog is attached to (built-ins are implicitly on every
// cluster; "__all__" is the sentinel the label renders as "All clusters").
function catalogClusterNames(catalog) {
  if (catalog.type === "builtin") return clusters.length ? ["__all__"] : [];
  return clusters
    .filter((cluster) => Array.isArray(cluster.catalogList) && cluster.catalogList.includes(catalog.name))
    .map((cluster) => cluster.name);
}

function catalogClustersLabel(catalog) {
  const names = catalogClusterNames(catalog);
  if (!names.length) return "Not attached to a cluster";
  if (names[0] === "__all__") return "All clusters";
  return names.length > 1 ? names[0] + " + " + (names.length - 1) + " more" : names[0];
}

function catalogMatchesSearch(catalog) {
  if (!catalogSearchTerm) return true;
  return [catalog.name, catalogTypeLabel(catalog), catalogHost(catalog)]
    .join(" ")
    .toLowerCase()
    .includes(catalogSearchTerm);
}

function catalogCardHtml(catalog) {
  const status = catalogStatusKey(catalog);
  const selected = catalogView === "edit" && editingCatalogId != null && String(editingCatalogId) === String(catalog.id);
  return `
    <button class="cat-card${selected ? " selected" : ""}" type="button" data-edit-catalog="${escapeHtml(String(catalog.id))}">
      <span class="cat-tile">${connectorGlyphSvg(catalogGlyphKey(catalog), 17, 1.7)}</span>
      <span class="cat-body">
        <span class="cat-name-row">
          <span class="cat-name">${escapeHtml(catalog.name)}</span>
          <span class="cat-pill ${status}"><span class="cat-dot"></span>${CATALOG_STATUS_LABELS[status]}</span>
        </span>
        <span class="cat-meta">${escapeHtml(catalogTypeLabel(catalog))} · ${escapeHtml(catalogMetaDetail(catalog))}</span>
        <span class="cat-clusters">${connectorGlyphSvg("clusters", 12, 1.9)}${escapeHtml(catalogClustersLabel(catalog))}</span>
      </span>
      <span class="cat-chevron">${iconSvg("chevron-right")}</span>
    </button>`;
}

// Render the list state: source/status groups of catalog cards. `system` is
// Trino plumbing, not a managed data source, so it stays hidden.
function renderCatalogList() {
  const host = document.getElementById("catalogGroups");
  if (!host) return;
  const visible = catalogRecords.filter((catalog) => catalog.name !== "system").filter(catalogMatchesSearch);
  const byStatus = catalogGroupBy === "status";
  const defs = byStatus ? CATALOG_STATUS_GROUPS : CATALOG_SOURCE_GROUPS;
  const groupOf = byStatus ? catalogStatusKey : catalogSourceGroup;
  const html = defs
    .map((def) => {
      const cats = visible
        .filter((catalog) => groupOf(catalog) === def.key)
        .sort((a, b) => String(a.name).localeCompare(String(b.name)));
      if (!cats.length) return "";
      const count = cats.length + (cats.length === 1 ? " source" : " sources");
      return `
        <section class="cat-group">
          <div class="cat-group-head">
            <span class="cat-group-chip" style="background:${def.accent}">${connectorGlyphSvg(def.glyph, 16, 1.85)}</span>
            <span class="cat-group-title">${escapeHtml(def.title)}</span>
            <span class="cat-group-count">${count}</span>
            <span class="cat-rule"></span>
          </div>
          <div class="cat-grid">${cats.map(catalogCardHtml).join("")}</div>
        </section>`;
    })
    .join("");
  host.innerHTML =
    html ||
    `<div class="cat-empty">${
      catalogSearchTerm ? "No catalogs match “" + escapeHtml(catalogSearchTerm) + "”." : "No catalogs yet — add one to get started."
    }</div>`;
}

// Show exactly one of the three state containers and set the header title.
function syncCatalogViewVisibility() {
  const list = document.getElementById("catalogListState");
  const edit = document.getElementById("catalogEditorState");
  const pick = document.getElementById("catalogPickerState");
  if (!list || !edit || !pick) return;
  list.hidden = catalogView !== "list";
  edit.hidden = catalogView !== "edit";
  pick.hidden = catalogView !== "pick";
  const title = document.getElementById("catalogViewTitle");
  if (title) {
    title.textContent =
      catalogView === "pick"
        ? "Add catalog"
        : catalogView === "edit"
          ? editingCatalogId == null
            ? "New catalog"
            : "Edit catalog"
          : "Data sources";
  }
}

// Refresh the catalog view and everything that depends on the catalog list.
// Called on load, after save, and after the list changes. The open editor is
// NOT rebuilt here (that would clobber in-progress edits) — only the list,
// picker, and dependent selectors refresh.
function renderCatalogs() {
  renderCatalogList();
  if (catalogView === "pick") renderCatalogPicker();
  syncCatalogViewVisibility();
  replaceIcons();
  updateCatalogAttachmentUi();
  updateQueryCatalogOptions();
  updateCreateReview();
}

async function loadCatalogsFromApi() {
  try {
    const result = await apiRequest("/api/catalogs");
    catalogRecords.splice.apply(catalogRecords, [0, catalogRecords.length].concat(result.catalogs));
    await loadConnectorTypes();
    await loadConnectorDrivers();
    // If the editor is open on a catalog that no longer exists, fall back to the
    // list; otherwise leave the open editor intact.
    if (catalogView === "edit" && editingCatalogId != null && !catalogRecords.some((c) => String(c.id) === String(editingCatalogId))) {
      catalogView = "list";
    }
    renderCatalogs();
  } catch (error) {
    if (!/Authentication required/.test(error.message)) {
      showToast(error.message, { type: "error" });
    }
  }
}

async function loadUsersFromApi() {
  try {
    const result = await apiRequest("/api/users");
    users.splice.apply(users, [0, users.length].concat(result.users));
    renderUsers();
  } catch (error) {
    if (/Authentication required/.test(error.message)) {
      users.splice(0, users.length);
      renderUsers();
    } else if (!/privilege is required/.test(error.message)) {
      showToast(error.message, { type: "error" });
    }
  }
}

// Avatar initials next to each user, per the design doc (roadmap B5): up to two
// letters from the username (split on separators) or the leading characters.
function userInitials(user) {
  const name = String((user && (user.username || user.email)) || "?").trim();
  const parts = name.split(/[\s._-]+/).filter(Boolean);
  const letters = parts.length >= 2 ? parts[0][0] + parts[1][0] : name.slice(0, 2);
  return letters.toUpperCase();
}

function renderUsers() {
  const tbody = document.getElementById("userRows");
  if (!tbody) return;
  if (users.length) {
    tbody.innerHTML = users
      .map(
        (user, index) => `
        <tr>
          <td><span class="user-cell"><span class="user-avatar">${escapeHtml(userInitials(user))}</span><strong>${escapeHtml(user.username)}</strong></span></td>
          <td>${escapeHtml(user.email || "")}</td>
          <td>${(user.roles || [user.role])
            .map((name) => `<span class="chip ${name === "admin" ? "success" : "info"}">${escapeHtml(name)}</span>`)
            .join(" ")}</td>
          <td>${user.is_active ? "Active" : "Disabled"}${user.is_service ? " · service" : ""}</td>
          <td class="actions-col">
            <button class="ghost-button admin-action" type="button" data-edit-user="${index}">Edit</button>
            <button class="ghost-button admin-action" type="button" data-toggle-user="${index}">${user.is_active ? "Deactivate" : "Activate"}</button>
          </td>
        </tr>`
      )
      .join("");
  } else {
    tbody.innerHTML = '<tr><td colspan="5">No users loaded.</td></tr>';
  }
  replaceIcons();
  applyRoleMode();
  document.querySelectorAll("[data-edit-user]").forEach((button) => {
    button.addEventListener("click", () => editUser(users[Number(button.dataset.editUser)]));
  });
  document.querySelectorAll("[data-toggle-user]").forEach((button) => {
    button.addEventListener("click", () => toggleUserActive(users[Number(button.dataset.toggleUser)]));
  });
}

async function patchUser(user, payload, successMessage) {
  try {
    const result = await apiRequest(`/api/users/${user.id}`, {
      method: "PATCH",
      body: JSON.stringify(payload)
    });
    const index = users.findIndex((item) => item.id === user.id);
    if (index >= 0) {
      users[index] = result.user;
    }
    renderUsers();
    showToast(successMessage || `Updated ${result.user.username}.`);
  } catch (error) {
    showToast(error.message, { type: "error" });
  }
}

async function toggleUserActive(user) {
  if (!user) return;
  const action = user.is_active ? "Deactivate" : "Activate";
  const confirmed = await appConfirm({
    title: `${action} ${user.username}?`,
    body: user.is_active
      ? "They will no longer be able to sign in. Their saved queries and history are kept."
      : "They will be able to sign in again.",
    confirmLabel: action,
    danger: Boolean(user.is_active),
  });
  if (!confirmed) return;
  await patchUser(
    user,
    { is_active: !user.is_active },
    `${user.username} ${user.is_active ? "deactivated" : "activated"}.`
  );
}

async function editUser(user) {
  if (!user) return;
  if (!rolesCatalog.length) await loadRolesFromApi();
  const currentRoles = user.roles || [user.role];
  const result = await openAppDialog({
    title: `Edit ${user.username}`,
    confirmLabel: "Save changes",
    fields: [
      {
        name: "roles",
        label: "Roles",
        type: "checkboxes",
        value: currentRoles,
        options: rolesCatalog.map((role) => ({ value: role.name, label: role.name })),
      },
      {
        name: "password",
        label: "New password",
        type: "password",
        placeholder: "Leave blank to keep current",
        autocomplete: "new-password",
      },
    ],
  });
  if (result === null) return;

  const payload = {};
  const requested = (result.roles || []).slice().sort();
  if (requested.join(",") !== currentRoles.slice().sort().join(",")) payload.roles = result.roles;
  if (result.password && result.password.trim()) payload.password = result.password;

  if (Object.keys(payload).length === 0) {
    showToast("No changes to apply.");
    return;
  }
  await patchUser(user, payload);
}

async function createUserFromPrompt() {
  if (!rolesCatalog.length) await loadRolesFromApi();
  const result = await openAppDialog({
    title: "Create user",
    confirmLabel: "Create user",
    fields: [
      { name: "username", label: "Username", placeholder: "e.g. dana", autocomplete: "off" },
      {
        name: "account_type",
        label: "Account type",
        type: "select",
        value: "person",
        options: [
          { value: "person", label: "Person (password sign-in)" },
          { value: "service", label: "Service account (API tokens only)" },
        ],
      },
      {
        name: "password",
        label: "Password (people only)",
        type: "password",
        placeholder: "At least 10 characters",
        autocomplete: "new-password",
      },
      {
        name: "roles",
        label: "Roles",
        type: "checkboxes",
        value: ["user"],
        options: rolesCatalog.map((role) => ({ value: role.name, label: role.name })),
      },
      { name: "email", label: "Email (optional)", type: "email", placeholder: "dana@company.com" },
    ],
  });
  if (result === null) return;

  const username = result.username.trim();
  const isService = result.account_type === "service";
  if (!username) {
    showToast("Username is required.", { type: "error" });
    return;
  }
  if (!isService && !result.password.trim()) {
    showToast("Password is required.", { type: "error" });
    return;
  }
  try {
    const created = await apiRequest("/api/users", {
      method: "POST",
      body: JSON.stringify({
        username,
        password: isService ? "" : result.password,
        is_service: isService,
        roles: result.roles && result.roles.length ? result.roles : ["user"],
        email: result.email.trim()
      })
    });
    await loadUsersFromApi();
    showToast(`Created ${created.user.username}.`, { type: "success" });
  } catch (error) {
    showToast(error.message, { type: "error" });
  }
}

// --- Roles & security audit (RBAC) -----------------------------------------
let rolesCatalog = [];
let allPrivileges = [];

async function loadRolesFromApi() {
  try {
    const data = await apiRequest("/api/roles");
    rolesCatalog = data.roles || [];
    allPrivileges = data.privileges || [];
    renderRoles();
  } catch (error) {
    if (!/Authentication required/.test(error.message)) {
      console.warn("Roles load failed:", error.message);
    }
  }
}

function grantSummary(grants) {
  if (grants.includes("*")) return "All";
  return grants.length ? grants.join(", ") : "None";
}

function renderRoles() {
  const tbody = document.getElementById("roleRows");
  if (!tbody) return;
  if (!rolesCatalog.length) {
    tbody.innerHTML = '<tr><td colspan="6">No roles loaded.</td></tr>';
    return;
  }
  tbody.innerHTML = rolesCatalog
    .map(
      (role, index) => `
      <tr>
        <td>
          <strong>${escapeHtml(role.name)}</strong>${role.is_system ? ' <span class="chip neutral">system</span>' : ""}
          ${role.description ? `<br /><small>${escapeHtml(role.description)}</small>` : ""}
        </td>
        <td>${role.privileges.length ? escapeHtml(role.privileges.join(", ")) : "—"}</td>
        <td>${escapeHtml(grantSummary(role.cluster_grants))}</td>
        <td>${escapeHtml(grantSummary(role.catalog_grants))}</td>
        <td>${role.member_count}</td>
        <td class="actions-col">
          <button class="ghost-button admin-action" type="button" data-edit-role="${index}">Edit</button>
          ${role.is_system ? "" : `<button class="ghost-button admin-action" type="button" data-delete-role="${index}">Delete</button>`}
        </td>
      </tr>`
    )
    .join("");
  replaceIcons();
  applyRoleMode();
  tbody.querySelectorAll("[data-edit-role]").forEach((button) => {
    button.addEventListener("click", () => editRoleFromDialog(rolesCatalog[Number(button.dataset.editRole)]));
  });
  tbody.querySelectorAll("[data-delete-role]").forEach((button) => {
    button.addEventListener("click", () => deleteRoleWithConfirm(rolesCatalog[Number(button.dataset.deleteRole)]));
  });
}

function roleGrantFields(role) {
  const clusterOptions = [{ value: "*", label: "All clusters" }].concat(
    clusters.map((cluster) => ({ value: String(cluster.id), label: cluster.name }))
  );
  const catalogOptions = [{ value: "*", label: "All catalogs" }].concat(
    catalogRecords
      .filter((catalog) => catalog.name !== "system")
      .map((catalog) => ({ value: catalog.name, label: catalog.name }))
  );
  return [
    {
      name: "privileges",
      label: "Privileges",
      type: "checkboxes",
      value: role ? role.privileges : [],
      options: allPrivileges.map((privilege) => ({ value: privilege, label: privilege })),
    },
    {
      name: "cluster_grants",
      label: "Cluster access",
      type: "checkboxes",
      value: role ? role.cluster_grants : ["*"],
      options: clusterOptions,
    },
    {
      name: "catalog_grants",
      label: "Catalog access",
      type: "checkboxes",
      value: role ? role.catalog_grants : ["*"],
      options: catalogOptions,
    },
  ];
}

async function createRoleFromDialog() {
  const result = await openAppDialog({
    title: "Create role",
    confirmLabel: "Create role",
    fields: [
      { name: "name", label: "Name", placeholder: "e.g. analysts", autocomplete: "off" },
      { name: "description", label: "Description (optional)", placeholder: "What this role is for" },
      ...roleGrantFields(null),
    ],
  });
  if (result === null) return;
  try {
    await apiRequest("/api/roles", {
      method: "POST",
      body: JSON.stringify({
        name: result.name.trim(),
        description: result.description.trim(),
        privileges: result.privileges,
        cluster_grants: result.cluster_grants,
        catalog_grants: result.catalog_grants,
      }),
    });
    await loadRolesFromApi();
    showToast(`Role ${result.name.trim()} created.`, { type: "success" });
  } catch (error) {
    showToast(error.message, { type: "error" });
  }
}

async function editRoleFromDialog(role) {
  if (!role) return;
  const locked = role.is_system && role.name === "admin";
  const result = await openAppDialog({
    title: `Edit role ${role.name}`,
    body: locked ? "The admin role's privileges and grants are fixed; only the description can change." : "",
    confirmLabel: "Save changes",
    fields: [
      { name: "description", label: "Description", value: role.description || "" },
      ...(locked ? [] : roleGrantFields(role)),
    ],
  });
  if (result === null) return;
  const payload = { description: result.description.trim() };
  if (!locked) {
    payload.privileges = result.privileges;
    payload.cluster_grants = result.cluster_grants;
    payload.catalog_grants = result.catalog_grants;
  }
  try {
    await apiRequest(`/api/roles/${role.id}`, { method: "PATCH", body: JSON.stringify(payload) });
    await loadRolesFromApi();
    showToast(`Role ${role.name} updated.`);
  } catch (error) {
    showToast(error.message, { type: "error" });
  }
}

async function deleteRoleWithConfirm(role) {
  if (!role) return;
  const confirmed = await appConfirm({
    title: `Delete role ${role.name}?`,
    body:
      role.member_count > 0
        ? `${role.member_count} user(s) hold this role; they will lose its privileges and grants.`
        : "This role has no members.",
    confirmLabel: "Delete role",
    danger: true,
  });
  if (!confirmed) return;
  try {
    await apiRequest(`/api/roles/${role.id}`, { method: "DELETE" });
    await loadRolesFromApi();
    showToast(`Role ${role.name} deleted.`);
  } catch (error) {
    showToast(error.message, { type: "error" });
  }
}

async function loadAuditLog() {
  const tbody = document.getElementById("auditLogRows");
  const chip = document.getElementById("auditLogChip");
  if (!tbody) return;
  try {
    const data = await apiRequest("/api/security/audit?limit=100");
    const entries = data.entries || [];
    if (chip) {
      chip.textContent = `${entries.length} recent`;
      chip.className = "chip info";
    }
    tbody.innerHTML = entries.length
      ? entries
          .map(
            (entry) => `
            <tr>
              <td>${escapeHtml((entry.created_at || "").replace("T", " ").replace("+00:00", ""))}</td>
              <td>${escapeHtml(entry.actor_username || "system")}</td>
              <td>${escapeHtml(entry.action)}</td>
              <td>${escapeHtml(entry.target || "")}</td>
              <td><small>${escapeHtml(JSON.stringify(entry.detail || {}))}</small></td>
            </tr>`
          )
          .join("")
      : '<tr><td colspan="5">No security events recorded yet.</td></tr>';
  } catch (error) {
    // Users without MANAGE_SECURITY just don't see entries.
    const panel = document.getElementById("auditLogPanel");
    if (panel) panel.hidden = true;
  }
}

// --- Scheduled SQL jobs (Phase 3) --------------------------------------------
let scheduledJobs = [];

async function loadJobsFromApi() {
  try {
    const data = await apiRequest("/api/jobs");
    scheduledJobs = data.jobs || [];
    renderJobs();
  } catch (error) {
    if (!/Authentication required/.test(error.message)) {
      console.warn("Jobs load failed:", error.message);
    }
  }
}

function jobScheduleText(job) {
  if (job.schedule_type === "interval") return `Every ${job.interval_minutes} min`;
  return `cron: ${job.cron_expression}`;
}

function jobClusterName(job) {
  const cluster = clusters.find((c) => c.id === job.cluster_id);
  return cluster ? cluster.name : `#${job.cluster_id}`;
}

function renderJobs() {
  const tbody = document.getElementById("jobRows");
  if (!tbody) return;
  if (!scheduledJobs.length) {
    tbody.innerHTML = '<tr><td colspan="7">No scheduled jobs yet.</td></tr>';
    return;
  }
  const shortTime = (value) => (value ? value.replace("T", " ").slice(0, 16) : "—");
  tbody.innerHTML = scheduledJobs
    .map(
      (job, index) => `
      <tr>
        <td><strong>${escapeHtml(job.name)}</strong>${job.enabled ? "" : ' <span class="chip neutral">paused</span>'}<br /><small>${escapeHtml(job.sql.slice(0, 80))}</small></td>
        <td>${escapeHtml(jobClusterName(job))}</td>
        <td>${escapeHtml(jobScheduleText(job))}</td>
        <td>${escapeHtml(job.run_as_username)}</td>
        <td>${escapeHtml(job.last_status || "—")}<br /><small>${escapeHtml(shortTime(job.last_run_at))}</small></td>
        <td>${escapeHtml(job.enabled ? shortTime(job.next_run_at) : "—")}</td>
        <td class="actions-col">
          <button class="ghost-button" type="button" data-job-runs="${index}">Runs</button>
          <button class="ghost-button" type="button" data-job-run-now="${index}">Run now</button>
          <button class="ghost-button" type="button" data-job-toggle="${index}">${job.enabled ? "Pause" : "Resume"}</button>
          <button class="ghost-button" type="button" data-job-delete="${index}">Delete</button>
        </td>
      </tr>`
    )
    .join("");
  replaceIcons();
  tbody.querySelectorAll("[data-job-runs]").forEach((b) =>
    b.addEventListener("click", () => showJobRuns(scheduledJobs[Number(b.dataset.jobRuns)]))
  );
  tbody.querySelectorAll("[data-job-run-now]").forEach((b) =>
    b.addEventListener("click", () => runJobNow(scheduledJobs[Number(b.dataset.jobRunNow)]))
  );
  tbody.querySelectorAll("[data-job-toggle]").forEach((b) =>
    b.addEventListener("click", () => toggleJob(scheduledJobs[Number(b.dataset.jobToggle)]))
  );
  tbody.querySelectorAll("[data-job-delete]").forEach((b) =>
    b.addEventListener("click", () => deleteJobWithConfirm(scheduledJobs[Number(b.dataset.jobDelete)]))
  );
}

async function createJobDialog() {
  if (!clusters.length) {
    showToast("Create a cluster first — jobs need one to run on.", { type: "error" });
    return;
  }
  const result = await openAppDialog({
    title: "Create scheduled job",
    confirmLabel: "Create job",
    fields: [
      { name: "name", label: "Name", placeholder: "e.g. nightly-compaction", autocomplete: "off" },
      { name: "sql", label: "SQL (one statement)", type: "textarea", rows: 5, placeholder: "SELECT ..." },
      {
        name: "cluster_id",
        label: "Cluster",
        type: "select",
        value: String(clusters[0].id),
        options: clusters.map((cluster) => ({ value: String(cluster.id), label: cluster.name })),
      },
      {
        name: "schedule_type",
        label: "Schedule",
        type: "select",
        value: "interval",
        options: [
          { value: "interval", label: "Every N minutes" },
          { value: "cron", label: "Cron expression" },
        ],
      },
      { name: "interval_minutes", label: "Interval minutes (interval schedules)", type: "number", value: "60" },
      { name: "cron_expression", label: "Cron (cron schedules, e.g. 0 3 * * *)", placeholder: "0 3 * * *", autocomplete: "off" },
    ],
  });
  if (result === null) return;
  const payload = {
    name: result.name.trim(),
    sql: result.sql.trim(),
    cluster_id: Number(result.cluster_id),
    schedule_type: result.schedule_type,
  };
  if (result.schedule_type === "interval") payload.interval_minutes = Number(result.interval_minutes);
  else payload.cron_expression = result.cron_expression.trim();
  try {
    await apiRequest("/api/jobs", { method: "POST", body: JSON.stringify(payload) });
    await loadJobsFromApi();
    showToast(`Job ${payload.name} scheduled.`, { type: "success" });
  } catch (error) {
    showToast(error.message, { type: "error" });
  }
}

async function toggleJob(job) {
  try {
    await apiRequest(`/api/jobs/${job.id}`, {
      method: "PATCH",
      body: JSON.stringify({ enabled: !job.enabled }),
    });
    await loadJobsFromApi();
  } catch (error) {
    showToast(error.message, { type: "error" });
  }
}

async function runJobNow(job) {
  try {
    await apiRequest(`/api/jobs/${job.id}/run`, { method: "POST", body: JSON.stringify({}) });
    showToast(`${job.name} started.`);
    await loadJobsFromApi();
    showJobRuns(job);
  } catch (error) {
    showToast(error.message, { type: "error" });
  }
}

async function deleteJobWithConfirm(job) {
  const confirmed = await appConfirm({
    title: `Delete job ${job.name}?`,
    body: "Its run history is removed too. Queries already submitted keep running.",
    confirmLabel: "Delete job",
    danger: true,
  });
  if (!confirmed) return;
  try {
    await apiRequest(`/api/jobs/${job.id}`, { method: "DELETE" });
    await loadJobsFromApi();
    document.getElementById("jobRunsPanel").hidden = true;
  } catch (error) {
    showToast(error.message, { type: "error" });
  }
}

async function showJobRuns(job) {
  const panel = document.getElementById("jobRunsPanel");
  const tbody = document.getElementById("jobRunRows");
  const title = document.getElementById("jobRunsTitle");
  if (!panel || !tbody) return;
  title.textContent = `Recent runs — ${job.name}`;
  panel.hidden = false;
  try {
    const data = await apiRequest(`/api/jobs/${job.id}/runs`);
    const runs = data.runs || [];
    tbody.innerHTML = runs.length
      ? runs
          .map(
            (run) => `
            <tr>
              <td>${escapeHtml((run.started_at || "").replace("T", " ").slice(0, 19))}</td>
              <td>${run.attempt}</td>
              <td>${escapeHtml(run.status)}</td>
              <td>${run.elapsed_ms != null ? escapeHtml(formatElapsedMs(run.elapsed_ms)) : "—"}</td>
              <td><small>${escapeHtml(run.error || "")}</small></td>
            </tr>`
          )
          .join("")
      : '<tr><td colspan="5">No runs yet.</td></tr>';
  } catch (error) {
    tbody.innerHTML = `<tr><td colspan="5">${escapeHtml(error.message)}</td></tr>`;
  }
}

// --- Utilization chart + costs (Phase 5) --------------------------------------

// Inline SVG time-series of the persisted poller samples (24 h window):
// worker CPU %, running queries, and active workers. Zero-dependency, same
// approach as the result chart renderer.
async function loadDetailStatsChart(cluster) {
  const box = document.getElementById("detailStatsChart");
  if (!box || !cluster || !cluster.id) return;
  box.innerHTML = "";
  let samples = [];
  try {
    const data = await apiRequest(`/api/clusters/${cluster.id}/stats?hours=24`);
    if (!selectedClusterDetail || selectedClusterDetail.id !== cluster.id) return;
    samples = data.samples || [];
  } catch (error) {
    return;
  }
  if (samples.length < 2) return;
  const width = 560;
  const height = 120;
  const pad = 6;
  const series = [
    { key: "avg_worker_cpu", label: "CPU %", color: CHART_PALETTE[0], max: 100 },
    { key: "running_queries", label: "Running queries", color: CHART_PALETTE[1] },
    { key: "active_workers", label: "Workers", color: CHART_PALETTE[2] },
  ];
  const paths = series
    .map((line) => {
      const values = samples.map((sample) => Number(sample[line.key] ?? 0) || 0);
      const max = line.max || Math.max(1, ...values);
      const points = values
        .map((value, index) => {
          const x = pad + (index / (samples.length - 1)) * (width - 2 * pad);
          const y = height - pad - (Math.min(value, max) / max) * (height - 2 * pad);
          return `${x.toFixed(1)},${y.toFixed(1)}`;
        })
        .join(" ");
      return `<polyline fill="none" stroke="${line.color}" stroke-width="1.5" points="${points}" />`;
    })
    .join("");
  const legend = series
    .map((line) => `<span style="color:${line.color}">● ${escapeHtml(line.label)}</span>`)
    .join(" &nbsp; ");
  box.innerHTML = `
    <div class="util-chart">
      <svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" style="width:100%;height:120px">
        ${paths}
      </svg>
      <small>${legend} &nbsp;·&nbsp; last 24 h, ${samples.length} samples</small>
    </div>`;
}

// 30-day cost estimate for this cluster (operators only; 403s are silent).
async function loadDetailMonthlyCost(cluster) {
  const note = document.getElementById("detailCostNote");
  if (!note || !cluster || !cluster.id) return;
  try {
    const data = await apiRequest("/api/costs");
    if (!selectedClusterDetail || selectedClusterDetail.id !== cluster.id) return;
    const entry = (data.clusters || []).find((item) => item.cluster_id === cluster.id);
    if (entry && entry.cost_30d_usd > 0) {
      note.textContent = `${note.textContent} · ~$${entry.cost_30d_usd.toFixed(2)} last 30 d (${entry.running_hours_30d} h running)`;
    }
  } catch (error) {
    // Not an operator or costs unavailable: keep the hourly estimate only.
  }
}

// --- Sharing (Phase 3) --------------------------------------------------------

async function openShareDialog(entityLabel, basePath, entityId) {
  if (!rolesCatalog.length) await loadRolesFromApi();
  let existing = [];
  try {
    existing = (await apiRequest(`${basePath}/${entityId}/shares`)).shares || [];
  } catch (error) {
    showToast(error.message, { type: "error" });
    return;
  }
  const summary = existing.length
    ? `Currently shared with: ${existing.map((s) => `${s.role} (${s.access})`).join(", ")}`
    : "Not shared yet.";
  const result = await openAppDialog({
    title: `Share ${entityLabel}`,
    body: summary,
    confirmLabel: "Share",
    cancelLabel: existing.length ? "Close" : "Cancel",
    fields: [
      {
        name: "role",
        label: "Role",
        type: "select",
        value: rolesCatalog[0] ? rolesCatalog[0].name : "",
        options: rolesCatalog.map((role) => ({ value: role.name, label: role.name })),
      },
      {
        name: "access",
        label: "Access",
        type: "select",
        value: "view",
        options: [
          { value: "view", label: "View" },
          { value: "run", label: "View and run" },
          { value: "edit", label: "Edit" },
        ],
      },
      ...(existing.length
        ? [
            {
              name: "remove",
              label: "Remove existing shares",
              type: "checkboxes",
              value: [],
              options: existing.map((share) => ({
                value: String(share.id),
                label: `${share.role} (${share.access})`,
              })),
            },
          ]
        : []),
    ],
  });
  if (result === null) return;
  try {
    for (const shareId of result.remove || []) {
      await apiRequest(`${basePath}/${entityId}/shares/${shareId}`, { method: "DELETE" });
    }
    if (result.role && !(result.remove || []).length) {
      await apiRequest(`${basePath}/${entityId}/shares`, {
        method: "POST",
        body: JSON.stringify({ role: result.role, access: result.access }),
      });
    }
    showToast("Sharing updated.", { type: "success" });
  } catch (error) {
    showToast(error.message, { type: "error" });
  }
}

// --- Global search (Cmd+K) ------------------------------------------------------

let searchModalEl = null;

function ensureSearchModal() {
  if (searchModalEl) return searchModalEl;
  const modal = document.createElement("div");
  modal.className = "itype-modal";
  modal.id = "globalSearchModal";
  modal.hidden = true;
  modal.innerHTML = `
    <div class="itype-modal-dialog" role="dialog" aria-modal="true" aria-label="Global search">
      <div class="itype-modal-tools">
        <div class="itype-search" style="flex:1">
          <span data-icon="search"></span>
          <input type="search" id="globalSearchInput" placeholder="Search clusters, catalogs, tables, queries… (Esc to close)" autocomplete="off" />
        </div>
      </div>
      <div class="itype-modal-body" id="globalSearchResults"><div class="empty-results">Type at least two characters.</div></div>
    </div>`;
  document.body.appendChild(modal);
  replaceIcons();
  const input = modal.querySelector("#globalSearchInput");
  let timer = null;
  input.addEventListener("input", () => {
    window.clearTimeout(timer);
    timer = window.setTimeout(() => runGlobalSearch(input.value), 200);
  });
  modal.addEventListener("mousedown", (event) => {
    if (event.target === modal) closeSearchModal();
  });
  searchModalEl = modal;
  return modal;
}

function openSearchModal() {
  const modal = ensureSearchModal();
  modal.hidden = false;
  const input = modal.querySelector("#globalSearchInput");
  input.value = "";
  modal.querySelector("#globalSearchResults").innerHTML =
    '<div class="empty-results">Type at least two characters.</div>';
  window.setTimeout(() => input.focus(), 0);
}

function closeSearchModal() {
  if (searchModalEl) searchModalEl.hidden = true;
}

async function runGlobalSearch(query) {
  const box = document.getElementById("globalSearchResults");
  if (!box) return;
  const text = query.trim();
  if (text.length < 2) {
    box.innerHTML = '<div class="empty-results">Type at least two characters.</div>';
    return;
  }
  try {
    const data = await apiRequest(`/api/search?q=${encodeURIComponent(text)}`);
    const results = data.results || [];
    box.innerHTML = results.length
      ? results
          .map(
            (result, index) => `
            <button class="itype-card" type="button" data-search-index="${index}" style="width:100%;text-align:left">
              <strong>${escapeHtml(result.title)}</strong>
              <small>${escapeHtml(result.subtitle)}</small>
            </button>`
          )
          .join("")
      : '<div class="empty-results">No matches.</div>';
    box.querySelectorAll("[data-search-index]").forEach((button) => {
      button.addEventListener("click", () => {
        const result = results[Number(button.dataset.searchIndex)];
        closeSearchModal();
        navigateTo(result.view);
      });
    });
  } catch (error) {
    box.innerHTML = `<div class="empty-results">${escapeHtml(error.message)}</div>`;
  }
}

function wireGlobalSearch() {
  document.addEventListener("keydown", (event) => {
    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
      event.preventDefault();
      if (!currentUser) return;
      openSearchModal();
    } else if (event.key === "Escape" && searchModalEl && !searchModalEl.hidden) {
      closeSearchModal();
    }
  });
}

// --- Fine-grained data security (Phase 6) -------------------------------------

async function loadDataSecurity() {
  const policyBody = document.getElementById("dataPolicyRows");
  if (!policyBody) return;
  try {
    const [policies, tags, tagPolicies] = await Promise.all([
      apiRequest("/api/data-policies"),
      apiRequest("/api/tags"),
      apiRequest("/api/tag-policies"),
    ]);
    renderDataPolicies(policies.policies || []);
    renderEntityTags(tags.tags || []);
    renderTagPolicies(tagPolicies.policies || []);
  } catch (error) {
    // Users without MANAGE_SECURITY simply don't see this data.
  }
}

function renderDataPolicies(policies) {
  const tbody = document.getElementById("dataPolicyRows");
  if (!tbody) return;
  tbody.innerHTML = policies.length
    ? policies
        .map((policy) => {
          const scope = [policy.catalog, policy.schema || "*", policy.table || "*"].join(".");
          const columnBits = [];
          if (policy.allowed_columns.length) columnBits.push(`allow: ${policy.allowed_columns.join(",")}`);
          if (policy.denied_columns.length) columnBits.push(`deny: ${policy.denied_columns.join(",")}`);
          const maskCount = Object.keys(policy.column_masks || {}).length;
          if (maskCount) columnBits.push(`${maskCount} masked`);
          return `
            <tr>
              <td><span class="chip info">${escapeHtml(policy.role)}</span></td>
              <td><code>${escapeHtml(scope)}</code></td>
              <td>${escapeHtml(policy.privileges.join(", "))}</td>
              <td>${escapeHtml(columnBits.join(" · ") || "all")}</td>
              <td><small>${escapeHtml(policy.row_filter || "—")}</small></td>
              <td class="actions-col"><button class="ghost-button" type="button" data-delete-policy="${policy.id}">Delete</button></td>
            </tr>`;
        })
        .join("")
    : '<tr><td colspan="6">No data policies.</td></tr>';
  tbody.querySelectorAll("[data-delete-policy]").forEach((button) => {
    button.addEventListener("click", async () => {
      const confirmed = await appConfirm({
        title: "Delete this data policy?",
        body: "Members of the role regain full access at the next cluster start.",
        confirmLabel: "Delete policy",
        danger: true,
      });
      if (!confirmed) return;
      try {
        await apiRequest(`/api/data-policies/${button.dataset.deletePolicy}`, { method: "DELETE" });
        await loadDataSecurity();
      } catch (error) {
        showToast(error.message, { type: "error" });
      }
    });
  });
}

function renderEntityTags(tags) {
  const tbody = document.getElementById("entityTagRows");
  if (!tbody) return;
  tbody.innerHTML = tags.length
    ? tags
        .map(
          (tag) => `
          <tr>
            <td><code>${escapeHtml(tag.entity)}</code></td>
            <td><span class="chip ${tag.status === "accepted" ? "success" : "warning"}">${escapeHtml(tag.tag)}</span></td>
            <td>${escapeHtml(tag.status)}</td>
            <td>${escapeHtml(tag.source)}</td>
            <td class="actions-col">
              ${tag.status === "proposed" ? `<button class="ghost-button" type="button" data-accept-tag="${tag.id}">Accept</button>` : ""}
              <button class="ghost-button" type="button" data-reject-tag="${tag.id}">${tag.status === "proposed" ? "Reject" : "Remove"}</button>
            </td>
          </tr>`
        )
        .join("")
    : '<tr><td colspan="5">No tags. Run "Scan for PII" to propose some from cached metadata.</td></tr>';
  tbody.querySelectorAll("[data-accept-tag]").forEach((button) => {
    button.addEventListener("click", async () => {
      try {
        await apiRequest(`/api/tags/${button.dataset.acceptTag}`, { method: "PATCH", body: JSON.stringify({}) });
        await loadDataSecurity();
      } catch (error) {
        showToast(error.message, { type: "error" });
      }
    });
  });
  tbody.querySelectorAll("[data-reject-tag]").forEach((button) => {
    button.addEventListener("click", async () => {
      try {
        await apiRequest(`/api/tags/${button.dataset.rejectTag}`, { method: "DELETE" });
        await loadDataSecurity();
      } catch (error) {
        showToast(error.message, { type: "error" });
      }
    });
  });
}

function renderTagPolicies(policies) {
  const tbody = document.getElementById("tagPolicyRows");
  if (!tbody) return;
  tbody.innerHTML = policies.length
    ? policies
        .map(
          (policy) => `
          <tr>
            <td>${escapeHtml(policy.tag)}</td>
            <td><span class="chip info">${escapeHtml(policy.role)}</span></td>
            <td>${escapeHtml(policy.effect === "deny" ? "Deny column" : "Mask with NULL")}</td>
            <td class="actions-col"><button class="ghost-button" type="button" data-delete-tag-policy="${policy.id}">Delete</button></td>
          </tr>`
        )
        .join("")
    : '<tr><td colspan="4">No tag policies.</td></tr>';
  tbody.querySelectorAll("[data-delete-tag-policy]").forEach((button) => {
    button.addEventListener("click", async () => {
      try {
        await apiRequest(`/api/tag-policies/${button.dataset.deleteTagPolicy}`, { method: "DELETE" });
        await loadDataSecurity();
      } catch (error) {
        showToast(error.message, { type: "error" });
      }
    });
  });
}

async function createDataPolicyDialog() {
  if (!rolesCatalog.length) await loadRolesFromApi();
  const result = await openAppDialog({
    title: "Create data policy",
    body: "Members of the role are limited to their policies; columns/filter/masks apply to matching tables. Takes effect at the next cluster start.",
    confirmLabel: "Create policy",
    fields: [
      {
        name: "role",
        label: "Role",
        type: "select",
        value: rolesCatalog[0] ? rolesCatalog[0].name : "",
        options: rolesCatalog.map((role) => ({ value: role.name, label: role.name })),
      },
      { name: "catalog", label: "Catalog", placeholder: "e.g. lake", autocomplete: "off" },
      { name: "schema", label: "Schema (blank = all)", autocomplete: "off" },
      { name: "table", label: "Table (blank = all)", autocomplete: "off" },
      {
        name: "privileges",
        label: "Privileges",
        type: "checkboxes",
        value: ["SELECT"],
        options: ["SELECT", "INSERT", "UPDATE", "DELETE"].map((p) => ({ value: p, label: p })),
      },
      { name: "denied_columns", label: "Denied columns (comma-separated)", autocomplete: "off" },
      { name: "row_filter", label: "Row filter SQL (optional)", placeholder: "region = 'EU'", autocomplete: "off" },
      {
        name: "column_masks",
        label: "Column masks, one per line: column = expression",
        type: "textarea",
        rows: 2,
        placeholder: "email = substr(email, 1, 3) || '…'",
      },
    ],
  });
  if (result === null) return;
  const masks = {};
  for (const line of String(result.column_masks || "").split("\n")) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    const eq = trimmed.indexOf("=");
    if (eq < 1) {
      showToast(`Mask lines look like "column = expression" — check: ${trimmed}`, { type: "error" });
      return;
    }
    masks[trimmed.slice(0, eq).trim()] = trimmed.slice(eq + 1).trim();
  }
  try {
    await apiRequest("/api/data-policies", {
      method: "POST",
      body: JSON.stringify({
        role: result.role,
        catalog: result.catalog.trim(),
        schema: result.schema.trim(),
        table: result.table.trim(),
        privileges: result.privileges,
        denied_columns: splitList(result.denied_columns || ""),
        row_filter: result.row_filter.trim(),
        column_masks: masks,
      }),
    });
    await loadDataSecurity();
    showToast("Data policy created. It applies at the next cluster start.", { type: "success" });
  } catch (error) {
    showToast(error.message, { type: "error" });
  }
}

async function createTagDialog() {
  const result = await openAppDialog({
    title: "Tag an entity",
    confirmLabel: "Add tag",
    fields: [
      { name: "entity", label: "Entity (catalog.schema.table[.column])", placeholder: "lake.crm.users.email", autocomplete: "off" },
      { name: "tag", label: "Tag", placeholder: "pii-email", autocomplete: "off" },
    ],
  });
  if (result === null) return;
  try {
    await apiRequest("/api/tags", {
      method: "POST",
      body: JSON.stringify({ entity: result.entity.trim(), tag: result.tag.trim() }),
    });
    await loadDataSecurity();
  } catch (error) {
    showToast(error.message, { type: "error" });
  }
}

async function createTagPolicyDialog() {
  if (!rolesCatalog.length) await loadRolesFromApi();
  const result = await openAppDialog({
    title: "Create tag policy",
    body: "Columns carrying the tag are denied or masked (NULL) for the role's members.",
    confirmLabel: "Create tag policy",
    fields: [
      { name: "tag", label: "Tag", placeholder: "pii-email", autocomplete: "off" },
      {
        name: "role",
        label: "Role",
        type: "select",
        value: rolesCatalog[0] ? rolesCatalog[0].name : "",
        options: rolesCatalog.map((role) => ({ value: role.name, label: role.name })),
      },
      {
        name: "effect",
        label: "Effect",
        type: "select",
        value: "deny",
        options: [
          { value: "deny", label: "Deny column" },
          { value: "mask", label: "Mask with NULL" },
        ],
      },
    ],
  });
  if (result === null) return;
  try {
    await apiRequest("/api/tag-policies", {
      method: "POST",
      body: JSON.stringify({ tag: result.tag.trim(), role: result.role, effect: result.effect }),
    });
    await loadDataSecurity();
  } catch (error) {
    showToast(error.message, { type: "error" });
  }
}

async function runPiiClassifier() {
  try {
    const result = await apiRequest("/api/security/classify", { method: "POST", body: JSON.stringify({}) });
    await loadDataSecurity();
    showToast(
      result.proposed
        ? `${result.proposed} PII tag(s) proposed — review below.`
        : "No new PII-shaped columns found in cached metadata."
    );
  } catch (error) {
    showToast(error.message, { type: "error" });
  }
}

// --- SSO, sessions & API tokens (Phase 2) -----------------------------------

async function loadSsoSettings() {
  try {
    const data = await apiRequest("/api/sso/oidc");
    const sso = data.oidc || {};
    const set = (id, value) => {
      const el = document.getElementById(id);
      if (el) el.value = value || "";
    };
    set("ssoIssuer", sso.issuer);
    set("ssoClientId", sso.client_id);
    set("ssoGroupClaim", sso.group_claim);
    const policy = document.getElementById("ssoPasswordLogin");
    if (policy) policy.value = sso.password_login || "all";
    const mappings = document.getElementById("ssoMappings");
    if (mappings) {
      mappings.value = Object.entries(sso.group_role_mappings || {})
        .map(([group, role]) => `${group} = ${role}`)
        .join("\n");
    }
    const enabled = document.getElementById("ssoEnabled");
    if (enabled) enabled.checked = Boolean(sso.enabled);
    const secret = document.getElementById("ssoClientSecret");
    if (secret) secret.placeholder = sso.client_secret_set ? "Leave blank to keep current" : "Required to enable";
    const chip = document.getElementById("ssoChip");
    if (chip) {
      chip.textContent = sso.enabled ? "Enabled" : "Disabled";
      chip.className = `chip ${sso.enabled ? "success" : "neutral"}`;
    }
  } catch (error) {
    // Users without MANAGE_SETTINGS don't see this panel's data.
  }
}

async function saveSsoSettings() {
  const mappingsText = document.getElementById("ssoMappings").value;
  const mappings = {};
  for (const line of mappingsText.split("\n")) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    const [group, role] = trimmed.split("=").map((part) => part.trim());
    if (!group || !role) {
      showToast(`Mapping lines look like "idp-group = role" — check: ${trimmed}`, { type: "error" });
      return;
    }
    mappings[group] = role;
  }
  const payload = {
    enabled: document.getElementById("ssoEnabled").checked,
    issuer: document.getElementById("ssoIssuer").value.trim(),
    client_id: document.getElementById("ssoClientId").value.trim(),
    group_claim: document.getElementById("ssoGroupClaim").value.trim() || "groups",
    group_role_mappings: mappings,
    password_login: document.getElementById("ssoPasswordLogin").value,
  };
  const secret = document.getElementById("ssoClientSecret").value;
  if (secret) payload.client_secret = secret;
  try {
    await apiRequest("/api/sso/oidc", { method: "PUT", body: JSON.stringify(payload) });
    document.getElementById("ssoClientSecret").value = "";
    await loadSsoSettings();
    showToast("SSO settings saved.", { type: "success" });
  } catch (error) {
    showToast(error.message, { type: "error" });
  }
}

async function loadSessionSettings() {
  try {
    const data = await apiRequest("/api/security/session");
    const input = document.getElementById("sessionHoursInput");
    if (input) input.value = String(data.session_hours);
    const chip = document.getElementById("sessionChip");
    if (chip) chip.textContent = `${data.session_hours} h`;
  } catch (error) {
    // Non-operators: leave defaults.
  }
}

async function saveSessionHours() {
  const hours = Number(document.getElementById("sessionHoursInput").value);
  try {
    await apiRequest("/api/security/session", {
      method: "PUT",
      body: JSON.stringify({ session_hours: hours }),
    });
    await loadSessionSettings();
    showToast(`Sessions now last ${hours} hours.`, { type: "success" });
  } catch (error) {
    showToast(error.message, { type: "error" });
  }
}

async function revokeMySessions() {
  const confirmed = await appConfirm({
    title: "Sign out everywhere?",
    body: "All of your active sessions (including this one) are revoked; you sign in again immediately.",
    confirmLabel: "Sign out everywhere",
    danger: true,
  });
  if (!confirmed) return;
  try {
    await apiRequest("/api/auth/revoke-sessions", { method: "POST", body: JSON.stringify({}) });
  } catch (error) {
    // The session may already be gone; fall through to the login screen.
  }
  currentUser = null;
  showLogin("Signed out everywhere. Please sign in again.");
}

async function loadNotificationSettings() {
  try {
    const data = await apiRequest("/api/notifications");
    const config = data.notifications || {};
    const input = document.getElementById("notifyWebhookUrl");
    if (input) input.value = config.webhook_url || "";
    const checks = document.getElementById("notifyEventChecks");
    if (checks) {
      checks.innerHTML = (data.events || [])
        .map(
          (event) => `
          <label class="app-dialog-check">
            <input type="checkbox" value="${escapeHtml(event)}"${(config.events || []).includes(event) ? " checked" : ""} />
            <span>${escapeHtml(event.replaceAll("_", " "))}</span>
          </label>`
        )
        .join("");
    }
    const chip = document.getElementById("notificationsChip");
    if (chip) {
      const on = Boolean(config.webhook_url) && (config.events || []).length > 0;
      chip.textContent = on ? `${config.events.length} events` : "Off";
      chip.className = `chip ${on ? "success" : "neutral"}`;
    }
  } catch (error) {
    // Non-operators: panel stays inert.
  }
}

async function saveNotificationSettings() {
  const events = Array.from(
    document.querySelectorAll("#notifyEventChecks input:checked")
  ).map((input) => input.value);
  try {
    await apiRequest("/api/notifications", {
      method: "PUT",
      body: JSON.stringify({
        webhook_url: document.getElementById("notifyWebhookUrl").value.trim(),
        events,
      }),
    });
    await loadNotificationSettings();
    showToast("Notification settings saved.", { type: "success" });
  } catch (error) {
    showToast(error.message, { type: "error" });
  }
}

async function loadAskSettings() {
  try {
    const data = await apiRequest("/api/ask-settings");
    const config = data.ask_trino || {};
    const input = document.getElementById("askModelInput");
    if (input) {
      input.value = config.model || "";
      input.placeholder = config.default_model || "vendor/model";
    }
    const chip = document.getElementById("askModelChip");
    if (chip) {
      const custom = Boolean(config.model);
      chip.textContent = custom ? "Custom" : "Default";
      chip.className = `chip ${custom ? "success" : "neutral"}`;
    }
    const hint = document.getElementById("askModelHint");
    if (hint) {
      const parts = [`Using ${config.effective_model || config.default_model}`];
      if (!config.key_configured) parts.push("· set OPENROUTER_API_KEY on the server to enable");
      hint.textContent = parts.join(" ");
    }
  } catch (error) {
    // Non-operators: panel stays inert.
  }
}

async function saveAskSettings() {
  try {
    await apiRequest("/api/ask-settings", {
      method: "PUT",
      body: JSON.stringify({ model: document.getElementById("askModelInput").value.trim() }),
    });
    await loadAskSettings();
    showToast("Ask Trino model saved.", { type: "success" });
  } catch (error) {
    showToast(error.message, { type: "error" });
  }
}

async function loadApiTokens() {
  const tbody = document.getElementById("apiTokenRows");
  if (!tbody) return;
  try {
    const data = await apiRequest("/api/tokens");
    const tokens = data.tokens || [];
    tbody.innerHTML = tokens.length
      ? tokens
          .map(
            (token, index) => `
            <tr>
              <td><strong>${escapeHtml(token.name)}</strong></td>
              <td>${escapeHtml(token.username)}</td>
              <td>${escapeHtml((token.created_at || "").slice(0, 10))}</td>
              <td>${escapeHtml(token.expires_at ? token.expires_at.slice(0, 10) : "Never")}</td>
              <td>${escapeHtml(token.last_used_at ? token.last_used_at.replace("T", " ").slice(0, 16) : "Never")}</td>
              <td class="actions-col"><button class="ghost-button" type="button" data-revoke-token="${token.id}">Revoke</button></td>
            </tr>`
          )
          .join("")
      : '<tr><td colspan="6">No tokens.</td></tr>';
    tbody.querySelectorAll("[data-revoke-token]").forEach((button) => {
      button.addEventListener("click", () => revokeApiToken(Number(button.dataset.revokeToken)));
    });
  } catch (error) {
    tbody.innerHTML = '<tr><td colspan="6">Tokens unavailable.</td></tr>';
  }
}

async function revokeApiToken(tokenId) {
  const confirmed = await appConfirm({
    title: "Revoke this token?",
    body: "Anything still using it loses API access immediately.",
    confirmLabel: "Revoke token",
    danger: true,
  });
  if (!confirmed) return;
  try {
    await apiRequest(`/api/tokens/${tokenId}`, { method: "DELETE" });
    await loadApiTokens();
    showToast("Token revoked.");
  } catch (error) {
    showToast(error.message, { type: "error" });
  }
}

async function createApiTokenDialog() {
  const fields = [
    { name: "name", label: "Token name", placeholder: "e.g. tableau-prod", autocomplete: "off" },
    { name: "expires_days", label: "Expires in days (blank = never)", type: "number", placeholder: "90" },
  ];
  // Operators can mint tokens for other users/service accounts.
  if (users.length > 1) {
    fields.splice(1, 0, {
      name: "user_id",
      label: "Acts as",
      type: "select",
      value: currentUser ? String(currentUser.id) : "",
      options: users
        .filter((user) => user.is_active)
        .map((user) => ({
          value: String(user.id),
          label: user.is_service ? `${user.username} (service account)` : user.username,
        })),
    });
  }
  const result = await openAppDialog({ title: "Create API token", confirmLabel: "Create token", fields });
  if (result === null) return;
  if (!result.name.trim()) {
    showToast("Token name is required.", { type: "error" });
    return;
  }
  const payload = { name: result.name.trim() };
  if (result.user_id) payload.user_id = Number(result.user_id);
  if (result.expires_days) payload.expires_days = Number(result.expires_days);
  try {
    const created = await apiRequest("/api/tokens", { method: "POST", body: JSON.stringify(payload) });
    await loadApiTokens();
    await openAppDialog({
      title: "Token created — copy it now",
      body: `This token is shown once and cannot be recovered:\n\n${created.token}`,
      confirmLabel: "Copy and close",
      fields: [],
    });
    try {
      await copyText(created.token);
      showToast("Token copied to clipboard.", { type: "success" });
    } catch (error) {
      showToast("Copy failed — the token was shown in the dialog.", { type: "error" });
    }
  } catch (error) {
    showToast(error.message, { type: "error" });
  }
}

function ensureCatalogRegionOption(region) {
  const select = catalogFieldEl("glue_region");
  if (!select || !region) return;
  if (!Array.from(select.options).some((option) => option.value === region || option.textContent === region)) {
    const option = document.createElement("option");
    option.value = region;
    option.textContent = region;
    select.append(option);
  }
}

const CATALOG_TYPE_TITLES = {
  s3_glue: "S3 + Glue catalog",
  delta_glue: "Delta Lake catalog",
  hive_glue: "Hive catalog",
  hudi_glue: "Hudi catalog",
  postgresql: "PostgreSQL catalog",
  mysql: "MySQL catalog",
  redshift: "Amazon Redshift catalog",
  sqlserver: "SQL Server catalog",
  mariadb: "MariaDB catalog",
  singlestore: "SingleStore catalog",
  clickhouse: "ClickHouse catalog",
  oracle: "Oracle catalog",
  snowflake: "Snowflake catalog",
  druid: "Apache Druid catalog",
  mongodb: "MongoDB catalog",
  elasticsearch: "Elasticsearch catalog",
  opensearch: "OpenSearch catalog",
  cassandra: "Apache Cassandra catalog",
  prometheus: "Prometheus catalog",
  bigquery: "Google BigQuery catalog",
  gsheets: "Google Sheets catalog",
  memory: "Memory catalog",
  blackhole: "Black Hole catalog",
  faker: "Faker catalog"
};

// Default catalog name suggested when starting a new catalog of each type.
const CATALOG_TYPE_DEFAULT_NAMES = {
  s3_glue: "analytics_s3",
  delta_glue: "analytics_delta",
  hive_glue: "analytics_hive",
  hudi_glue: "analytics_hudi",
  postgresql: "warehouse_pg",
  mysql: "warehouse_mysql",
  redshift: "warehouse_redshift",
  sqlserver: "warehouse_sqlserver",
  mariadb: "warehouse_mariadb",
  singlestore: "warehouse_singlestore",
  clickhouse: "warehouse_clickhouse",
  oracle: "warehouse_oracle",
  snowflake: "warehouse_snowflake",
  druid: "warehouse_druid",
  mongodb: "docs_mongo",
  elasticsearch: "logs_es",
  opensearch: "logs_os",
  cassandra: "warehouse_cassandra",
  prometheus: "metrics_prometheus",
  bigquery: "warehouse_bigquery",
  gsheets: "sheets",
  memory: "scratch",
  blackhole: "sink",
  faker: "sample_data"
};

// Group order + copy for the connector picker. The connectors within each group
// come from the fetched schema (grouped by its `group` field), so this only
// carries presentation: ordering and the descriptive blurb.
const CATALOG_PICKER_GROUP_META = [
  { title: "Object storage", description: "Query S3 tables through the AWS Glue Data Catalog, authenticated by the cluster IAM role — no stored credentials." },
  { title: "Databases", description: "Connect over JDBC. Credentials are stored in AWS Secrets Manager, never in the catalog config." },
  { title: "Document & search", description: "Host, port, connection user and default schema, with password authentication." },
  { title: "Google Cloud", description: "Cross-cloud sources authenticated by a service-account JSON key stored in AWS Secrets Manager." },
  { title: "Test & sample data", description: "Zero-configuration connectors for testing and demos — just give the catalog a name." }
];

// Group title -> chip glyph for the full-page connector picker.
const CATALOG_PICKER_GROUP_GLYPH = {
  "Object storage": "cloud",
  Databases: "database",
  "Document & search": "search",
  "Google Cloud": "sheet",
  "Test & sample data": "flask"
};

function renderCatalogPicker() {
  const body = document.getElementById("catalogPickerBody");
  if (!body) return;
  // Any group present in the schema but missing from the meta list still renders,
  // appended after the curated ones, so a new group can't silently disappear.
  const knownTitles = CATALOG_PICKER_GROUP_META.map((g) => g.title);
  const extraTitles = [...new Set(connectorTypeCatalog.map((c) => c.group))].filter((g) => g && !knownTitles.includes(g));
  const groups = [...CATALOG_PICKER_GROUP_META, ...extraTitles.map((title) => ({ title, description: "" }))];
  body.innerHTML = groups
    .map((group) => {
      const connectors = connectorTypeCatalog.filter((c) => c.group === group.title);
      if (!connectors.length) return "";
      const tiles = connectors
        .map(
          (connector) => `
            <button class="cat-connector" type="button" data-connector-type="${escapeHtml(connector.type)}">
              <span class="cat-connector-icon">${connectorGlyphSvg(CATALOG_GLYPH_BY_TYPE[connector.type] || connector.icon || "database", 18, 1.7)}</span>
              <span class="cat-connector-label">${escapeHtml(connector.label)}</span>
              <span class="cat-connector-chev">${iconSvg("chevron-right")}</span>
            </button>
          `
        )
        .join("");
      return `
        <section class="cat-pick-group">
          <div class="cat-pick-group-head">
            <span class="cat-pick-chip">${connectorGlyphSvg(CATALOG_PICKER_GROUP_GLYPH[group.title] || "database", 16, 1.85)}</span>
            <span class="cat-pick-group-title">${escapeHtml(group.title)}</span>
          </div>
          ${group.description ? `<p class="cat-pick-note">${escapeHtml(group.description)}</p>` : ""}
          <div class="cat-tilegrid">${tiles}</div>
        </section>
      `;
    })
    .join("");
}

async function openCatalogPicker() {
  const role = document.getElementById("roleSelect").value;
  if (role !== "admin") {
    showToast("Only admins can add catalogs.");
    return;
  }
  if (!connectorTypeCatalog.length) await loadConnectorTypes();
  navigateTo("catalogs");
  catalogView = "pick";
  renderCatalogPicker();
  syncCatalogViewVisibility();
  const state = document.getElementById("catalogPickerState");
  if (state) state.scrollTop = 0;
}

function catalogBackToList() {
  catalogView = "list";
  editingCatalogId = null;
  renderCatalogs();
}

function selectConnectorFromPicker(type) {
  startNewCatalog(type);
}

// Open the full-canvas editor on a fresh catalog of the given connector type.
function startNewCatalog(type) {
  const connectorType = CATALOG_TYPE_TITLES[type] ? type : "s3_glue";
  openCatalogEditor(null, connectorType);
  const nameInput = document.getElementById("catalogName");
  if (nameInput) {
    nameInput.focus();
    nameInput.select();
  }
}

function applyCatalogConnectorType(type) {
  const connectorType = CATALOG_TYPE_TITLES[type] ? type : "s3_glue";
  // Field markup (labels, placeholders, the fixed table-format value, the JDBC URL
  // hint) all come from the type's schema now — no per-type branching here.
  renderCatalogFields(connectorType);
  renderConnectorDriverPanel(connectorType);
}

// Overlay a saved catalog's config onto the freshly rendered fields. Fields
// absent from `config` keep the schema defaults from renderCatalogFields(); the
// credential is write-only (never echoed back), so it always starts empty and an
// empty field on edit keeps the stored secret.
function populateCatalogFields(config) {
  const type = document.getElementById("catalogConnectorType").value;
  const schema = connectorSchema(type);
  if (!schema) return;
  const setupRegion = liveSetupStatus && liveSetupStatus.setup ? liveSetupStatus.setup.region : "";
  for (const field of schema.fields) {
    const el = catalogFieldEl(field.name);
    if (!el || field.input === "readonly") continue;
    if (field.input === "region") {
      const region = config.glue_region || setupRegion;
      if (region) {
        ensureCatalogRegionOption(region);
        el.value = region;
      }
      continue;
    }
    if (field.name === "access_mode") {
      if (config.access_mode) {
        el.value = config.access_mode === "read_only" ? "Read only" : "Read and write";
      }
      continue;
    }
    const value = config[field.name];
    if (value !== undefined && value !== null && value !== "") {
      el.value = value;
    }
  }
  if (schema.credential) {
    const el = catalogFieldEl(schema.credential.name);
    if (el) el.value = "";
  }
}

function catalogPillHtml(statusKey) {
  return `<span class="cat-pill ${statusKey}"><span class="cat-dot"></span>${CATALOG_STATUS_LABELS[statusKey]}</span>`;
}

// The three-node live-connection map shown on the right of the editor:
// Data source -> Trino connector -> Attached clusters.
function catalogLiveNodes(catalog) {
  const type = catalog.type;
  const connName = CONNECTOR_NAME_BY_TYPE[type] || type;
  let sourceSub;
  let authSub;
  if (isGlueCatalogType(type)) {
    sourceSub = "Object storage via AWS Glue";
    authSub = "Authenticated by the cluster node IAM role — no stored credentials.";
  } else if (type === "bigquery" || type === "gsheets") {
    sourceSub = "Cross-cloud Google source";
    authSub = "Service-account JSON key stored in AWS Secrets Manager, delivered over the signed node channel.";
  } else if (isGeneratorCatalogType(type)) {
    sourceSub = "In-cluster generator";
    authSub = "No endpoint or stored credentials.";
  } else if (isCassandraCatalogType(type) || isPrometheusCatalogType(type)) {
    // Optional-auth connectors: a stored secret exists only when a user is set.
    sourceSub = "Reachable from the cluster VPC";
    authSub = catalog.config && catalog.config.connection_user
      ? "Password stored in AWS Secrets Manager, delivered over the signed node channel."
      : "Unauthenticated — no stored credentials.";
  } else {
    sourceSub = "Reachable from the cluster VPC";
    authSub = "Password stored in AWS Secrets Manager, delivered over the signed node channel.";
  }
  const names = catalogClusterNames(catalog);
  return [
    { label: "Data source", value: catalogHost(catalog) || "—", mono: true, sub: sourceSub },
    { label: "Trino connector", value: "connector.name = " + connName, mono: true, sub: authSub },
    {
      label: "Attached clusters",
      value: catalogClustersLabel(catalog),
      mono: false,
      sub: names.length ? "Only attached clusters can query this catalog." : "Attach it from a cluster to start querying."
    }
  ];
}

function checkViewFromState(state) {
  if (state.status === "checking") return { kind: "warn", title: "Checking connection…", text: state.text || "Running SHOW SCHEMAS against an attached cluster." };
  if (state.status === "healthy") return { kind: "ok", title: "Connection healthy", text: state.text };
  if (state.status === "error") return { kind: "err", title: "Check failed", text: state.text };
  return { kind: "muted", title: "Not checked yet", text: state.text || "Run a connection check to verify connectivity." };
}

function catalogCheckView(catalog) {
  if (!catalog || editingCatalogType === "builtin") return { kind: "muted", title: "Built-in catalog", text: "No connection test needed — enabled per cluster." };
  if (!catalogEditorEnabled) return { kind: "muted", title: "Catalog disabled", text: "Enable this catalog to run a connectivity check." };
  const cached = catalog.id != null ? catalogCheckState[catalog.id] : null;
  if (cached) return checkViewFromState(cached);
  return { kind: "muted", title: "Not checked yet", text: "Run a connection check to verify connectivity and permissions." };
}

// Render the connection-check card. Pass `override` to show a specific result
// (e.g. a live check just returned); otherwise the view is derived from the
// cached per-catalog check state.
function renderCheckCard(catalog, override) {
  const hostEl = document.getElementById("catalogCheckHost");
  if (!hostEl) return;
  const v = override || catalogCheckView(catalog);
  const iconKey = v.kind === "ok" ? "check" : v.kind === "err" ? "x" : v.kind === "warn" ? "spin" : "info";
  const disabled = editingCatalogType === "builtin" || !catalogEditorEnabled;
  hostEl.innerHTML = `
    <div class="cat-check ${v.kind}">
      <div class="cat-check-head">${connectorGlyphSvg(iconKey, 17, 2)}<span>${escapeHtml(v.title)}</span></div>
      <div class="cat-check-text">${escapeHtml(v.text || "")}</div>
      <button class="cat-check-btn admin-action" type="button" id="testCatalogConfig"${disabled ? " disabled" : ""}>${connectorGlyphSvg("check", 14, 2)}Run connection check</button>
    </div>`;
}

// Build the full-canvas editor for a catalog (or a new one of `type`): the
// header (icon/name/status/toggle), the connection-settings form on the left,
// and the live-connection map + connection-check panel on the right.
function renderCatalogEditor(catalog, type) {
  const host = document.getElementById("catalogEditor");
  if (!host) return;
  const isBuiltin = type === "builtin" || (catalog && catalog.type === "builtin");
  const name = (catalog && catalog.name) || CATALOG_TYPE_DEFAULT_NAMES[type] || "new_catalog";
  const displayStatus = catalog ? catalogStatusKey(catalog) : "enabled";
  const glyph = catalog ? catalogGlyphKey(catalog) : CATALOG_GLYPH_BY_TYPE[type] || "database";
  const typeLabel = catalog ? catalogTypeLabel(catalog) : (CATALOG_TYPE_TITLES[type] || type).replace(/ catalog$/, "");
  const detail = catalog ? catalogMetaDetail(catalog) : "Not saved yet";

  const formBody = isBuiltin
    ? `<div class="cat-callout">${connectorGlyphSvg("info", 18, 1.8)}<div><b>Built-in catalog.</b> Always available — no connection settings. Enable it per cluster from the cluster form.</div></div>`
    : `<input type="hidden" id="catalogConnectorType" value="${escapeHtml(type)}">
       <div class="cat-fieldgrid">
         <label class="span-2"><span>Catalog name</span><input id="catalogName" value="${escapeHtml(name)}" autocomplete="off" spellcheck="false" /></label>
         <div id="catalogFields" style="display: contents"></div>
       </div>
       <div id="catalogDriverPanel" class="cat-driver" hidden>
         <div class="cat-driver-head"><strong>JDBC driver</strong><span id="catalogDriverStatus" class="chip neutral">No driver uploaded</span></div>
         <p class="cat-driver-note">This connector's JDBC driver isn't bundled with Trino (licensing). Upload the driver JAR once; cluster nodes install it at boot. Restart a running cluster to apply a new or changed driver.</p>
         <div class="cat-driver-actions">
           <input id="catalogDriverFile" type="file" accept=".jar,application/java-archive" hidden />
           <button class="secondary-button admin-action danger" id="catalogDriverDeleteButton" type="button" hidden>Remove driver</button>
           <button class="secondary-button admin-action" id="catalogDriverUploadButton" type="button"><span data-icon="plus"></span>Upload driver JAR</button>
         </div>
       </div>`;

  const rightCol = isBuiltin
    ? `<div id="catalogCheckHost"></div>`
    : `<div class="cat-live">
         <div class="cat-live-eyebrow">Live connection</div>
         <div class="cat-timeline">
           ${catalogLiveNodes(catalog || { type, config: {} })
             .map(
               (nd) => `
             <div class="cat-node">
               <span class="cat-node-dot"></span>
               <div class="cat-node-label">${escapeHtml(nd.label)}</div>
               <div class="cat-node-value${nd.mono ? " mono" : ""}">${escapeHtml(nd.value)}</div>
               <div class="cat-node-sub">${escapeHtml(nd.sub)}</div>
             </div>`
             )
             .join("")}
         </div>
       </div>
       <div id="catalogCheckHost"></div>`;

  const toggle = isBuiltin
    ? ""
    : `<div class="cat-toggle-wrap">
         <span class="cat-toggle-label" id="catalogToggleLabel">${catalogEditorEnabled ? "Enabled" : "Disabled"}</span>
         <button class="cat-toggle admin-action${catalogEditorEnabled ? " on" : ""}" id="catalogEnableToggle" type="button" role="switch" aria-checked="${catalogEditorEnabled}" aria-label="Enable catalog"><span class="cat-toggle-knob"></span></button>
       </div>`;

  host.innerHTML = `
    <div class="cat-ed-head">
      <span class="cat-bigtile">${connectorGlyphSvg(glyph, 24, 1.7)}</span>
      <div class="cat-ed-titles">
        <div class="cat-ed-name-row"><span class="cat-ed-name" id="catalogEditorName">${escapeHtml(name)}</span>${catalogPillHtml(displayStatus)}</div>
        <div class="cat-ed-sub">${escapeHtml(typeLabel)} · ${escapeHtml(detail)}</div>
      </div>
      ${toggle}
    </div>
    <div class="cat-ed-grid">
      <div class="cat-formcard">
        <div class="cat-formcard-head">Connection settings</div>
        <div class="cat-formcard-body">${formBody}</div>
        ${
          isBuiltin
            ? ""
            : `<div class="cat-formcard-foot"><span class="cat-foot-help">Passwords are write-only — leave blank to keep the stored secret.</span><button class="cat-save admin-action" id="saveCatalog" type="button">Save catalog</button></div>`
        }
      </div>
      <div class="cat-ed-right">${rightCol}</div>
    </div>`;

  if (!isBuiltin) {
    applyCatalogConnectorType(type);
    populateCatalogFields((catalog && catalog.config) || {});
  }
  renderCheckCard(catalog);
  replaceIcons();
}

// Enter the edit state on a saved catalog, or a new one of `type`.
function openCatalogEditor(catalog, type) {
  editingCatalogId = catalog && catalog.id != null ? catalog.id : null;
  editingCatalogType = (catalog && catalog.type) || type || "s3_glue";
  catalogEditorEnabled = catalog ? Boolean(catalog.enabled) : true;
  catalogView = "edit";
  renderCatalogEditor(catalog, editingCatalogType);
  renderCatalogs();
  const state = document.getElementById("catalogEditorState");
  if (state) state.scrollTop = 0;
}

function updateEditorToggleUi() {
  const toggle = document.getElementById("catalogEnableToggle");
  const label = document.getElementById("catalogToggleLabel");
  if (toggle) {
    toggle.classList.toggle("on", catalogEditorEnabled);
    toggle.setAttribute("aria-checked", String(catalogEditorEnabled));
  }
  if (label) label.textContent = catalogEditorEnabled ? "Enabled" : "Disabled";
}

function updateEditorHeaderStatus(catalog) {
  const pill = document.querySelector("#catalogEditor .cat-ed-name-row .cat-pill");
  if (!pill) return;
  const status = catalogStatusKey(catalog);
  pill.className = "cat-pill " + status;
  pill.innerHTML = `<span class="cat-dot"></span>${CATALOG_STATUS_LABELS[status]}`;
}

// Flip enabled. For a saved catalog this PATCHes immediately (keeping the stored
// secret); for a new catalog it just records the choice, applied at create.
async function toggleCatalogEnabled() {
  catalogEditorEnabled = !catalogEditorEnabled;
  updateEditorToggleUi();
  if (editingCatalogId == null) {
    renderCheckCard({ type: editingCatalogType, id: null, config: {} });
    return;
  }
  const payload = catalogPayloadFromForm();
  payload.enabled = catalogEditorEnabled;
  try {
    const result = await apiRequest(`/api/catalogs/${editingCatalogId}`, { method: "PATCH", body: JSON.stringify(payload) });
    const index = catalogRecords.findIndex((catalog) => catalog.id === result.catalog.id);
    if (index >= 0) catalogRecords.splice(index, 1, result.catalog);
    updateEditorHeaderStatus(result.catalog);
    renderCheckCard(result.catalog);
    renderCatalogList();
    showToast(`${result.catalog.name} ${result.catalog.enabled ? "enabled" : "disabled"}.`);
  } catch (error) {
    catalogEditorEnabled = !catalogEditorEnabled;
    updateEditorToggleUi();
    renderCheckCard(catalogRecords.find((c) => String(c.id) === String(editingCatalogId)));
    showToast(error.message, { type: "error" });
  }
}

// Run a live SHOW SCHEMAS check against an attached running cluster (or the
// selected query cluster) and reflect the result in the check card + list status.
async function runCatalogCheck() {
  if (editingCatalogType === "builtin") return;
  const payload = catalogPayloadFromForm();
  const validationError = validateCatalogPayload(payload);
  if (validationError) {
    showToast(validationError);
    return;
  }
  const id = editingCatalogId;
  const record = id != null ? catalogRecords.find((c) => String(c.id) === String(id)) : null;
  const attached = record ? catalogClusterNames(record) : [];
  const attachedCluster = clusters.find((c) => attached.includes(c.name) && /running/i.test(c.status));
  let clusterId = attachedCluster ? attachedCluster.id : "";
  if (!clusterId) {
    const sel = document.getElementById("queryCluster");
    if (sel && sel.value) clusterId = sel.value;
  }
  if (clusterId) payload.cluster_id = Number(clusterId);

  if (id != null) catalogCheckState[id] = { status: "checking" };
  renderCheckCard(record, checkViewFromState({ status: "checking" }));
  renderCatalogList();
  try {
    const result = await apiRequest("/api/catalogs/check", { method: "POST", body: JSON.stringify(payload) });
    const live = result.live_check || {};
    let view;
    let cache = null;
    if (live.checked && live.ok) {
      cache = {
        status: "healthy",
        text: `SHOW SCHEMAS succeeded${live.row_count != null ? " · " + live.row_count + " schemas" : ""}${live.cluster_id ? " on cluster #" + live.cluster_id : ""}.`
      };
      view = checkViewFromState(cache);
    } else if (live.checked) {
      cache = { status: "error", text: live.error_message || "The connection check failed." };
      view = checkViewFromState(cache);
    } else {
      view = { kind: "muted", title: "Configuration valid", text: live.reason || "No running cluster with this catalog attached to test against." };
    }
    if (id != null) {
      if (cache) catalogCheckState[id] = cache;
      else delete catalogCheckState[id];
    }
    renderCheckCard(record, view);
    if (record) updateEditorHeaderStatus(record);
    renderCatalogList();
  } catch (error) {
    if (id != null) catalogCheckState[id] = { status: "error", text: error.message };
    renderCheckCard(record, checkViewFromState({ status: "error", text: error.message }));
    if (record) updateEditorHeaderStatus(record);
    renderCatalogList();
  }
}

function catalogPayloadFromForm() {
  const type = document.getElementById("catalogConnectorType").value;
  const name = document.getElementById("catalogName").value.trim();
  // Fields are addressed by their schema `name` (== config key) within the
  // rendered #catalogFields; the write-only credential lives in the "password"
  // field for every credentialed type.
  const fieldValue = (fieldName) => {
    const el = catalogFieldEl(fieldName);
    return el ? el.value : "";
  };
  if (isJdbcCatalogType(type)) {
    const payload = {
      name,
      type,
      config: {
        connection_url: fieldValue("connection_url").trim(),
        connection_user: fieldValue("connection_user").trim()
      }
    };
    // Only send a password when one was typed; an empty field on edit keeps the secret.
    const password = fieldValue("password");
    if (password) payload.password = password;
    return payload;
  }
  if (isSearchCatalogType(type)) {
    const payload = {
      name,
      type,
      config: {
        host: fieldValue("host").trim(),
        port: Number(fieldValue("port")) || 9200,
        connection_user: fieldValue("connection_user").trim(),
        default_schema: fieldValue("default_schema").trim() || "default"
      }
    };
    const password = fieldValue("password");
    if (password) payload.password = password;
    return payload;
  }
  if (isCassandraCatalogType(type)) {
    const config = {
      contact_points: fieldValue("contact_points").trim(),
      port: Number(fieldValue("port")) || 9042
    };
    // Optional auth: only send a user when one is set; the password rides the
    // write-only slot and is required (client-side) only alongside a user.
    const user = fieldValue("connection_user").trim();
    if (user) config.connection_user = user;
    const payload = { name, type, config };
    const password = fieldValue("password");
    if (password) payload.password = password;
    return payload;
  }
  if (isPrometheusCatalogType(type)) {
    const config = { uri: fieldValue("uri").trim() };
    // Optional basic auth: only send a user when set; password rides the write-only
    // slot and is required (client-side) only alongside a user.
    const user = fieldValue("connection_user").trim();
    if (user) config.connection_user = user;
    const payload = { name, type, config };
    const password = fieldValue("password");
    if (password) payload.password = password;
    return payload;
  }
  if (isGeneratorCatalogType(type)) {
    return { name, type, config: {} };
  }
  if (type === "gsheets") {
    const payload = {
      name,
      type: "gsheets",
      config: { metadata_sheet_id: fieldValue("metadata_sheet_id").trim() }
    };
    const credentials = fieldValue("password").trim();
    if (credentials) payload.password = credentials;
    return payload;
  }
  if (type === "bigquery") {
    const config = { project_id: fieldValue("project_id").trim() };
    const parent = fieldValue("parent_project_id").trim();
    if (parent) config.parent_project_id = parent;
    const payload = { name, type: "bigquery", config };
    // The service-account JSON key travels in the write-only `password` slot; on
    // edit, an empty field keeps the stored key.
    const credentials = fieldValue("password").trim();
    if (credentials) payload.password = credentials;
    return payload;
  }
  const glue = GLUE_CATALOG_TYPES[type] || GLUE_CATALOG_TYPES.s3_glue;
  const glueType = GLUE_CATALOG_TYPES[type] ? type : "s3_glue";
  const accessMode = fieldValue("access_mode") === "Read only" ? "read_only" : "read_write";
  return {
    name,
    type: glueType,
    config: {
      glue_region: fieldValue("glue_region"),
      s3_region: fieldValue("glue_region"),
      warehouse: fieldValue("warehouse").trim(),
      default_schema: fieldValue("default_schema").trim() || "default",
      table_format: glue.tableFormat,
      file_format: "PARQUET",
      access_mode: accessMode
    }
  };
}

// Shared by BigQuery and Google Sheets: an empty key is allowed on edit (keeps
// the stored secret); a provided key must parse as a service_account document.
function validateServiceAccountKey(password) {
  if (!password) return "";
  try {
    const key = JSON.parse(password);
    if (!key || key.type !== "service_account") {
      return 'The service-account key must be JSON with "type": "service_account".';
    }
  } catch (error) {
    return "The service-account key must be valid JSON (paste the whole key file).";
  }
  return "";
}

function validateCatalogPayload(payload) {
  if (!/^[a-z][a-z0-9_]{1,62}$/.test(payload.name)) {
    return "Catalog name must use lowercase letters, numbers, and underscores.";
  }
  if (isJdbcCatalogType(payload.type)) {
    const jdbc = JDBC_CATALOG_TYPES[payload.type];
    if (!jdbc.urlPattern.test(payload.config.connection_url)) {
      return `Connection URL must look like ${jdbc.urlExample}.`;
    }
    if (!/^[A-Za-z_][A-Za-z0-9_.\-]{0,127}$/.test(payload.config.connection_user)) {
      return "Connection user must be a valid database username.";
    }
    // Password is required on create (no editing id), optional on edit (keeps stored secret).
    if (!editingCatalogId && !payload.password) {
      return `A connection password is required for a new ${jdbc.label} catalog.`;
    }
    return "";
  }
  if (isSearchCatalogType(payload.type)) {
    const label = SEARCH_CATALOG_TYPES[payload.type].label;
    if (!/^[A-Za-z0-9][A-Za-z0-9.\-]{0,253}$/.test(payload.config.host)) {
      return "Host must be a valid hostname or IP address.";
    }
    const port = payload.config.port;
    if (!Number.isInteger(port) || port < 1 || port > 65535) {
      return "Port must be between 1 and 65535.";
    }
    if (!/^[A-Za-z_][A-Za-z0-9_.\-]{0,127}$/.test(payload.config.connection_user)) {
      return "Connection user must be a valid username.";
    }
    if (!/^[A-Za-z_][A-Za-z0-9_]{0,127}$/.test(payload.config.default_schema)) {
      return "Default schema must use letters, numbers, or underscores.";
    }
    if (!editingCatalogId && !payload.password) {
      return `A connection password is required for a new ${label} catalog.`;
    }
    return "";
  }
  if (isCassandraCatalogType(payload.type)) {
    const hosts = String(payload.config.contact_points || "")
      .split(",")
      .map((h) => h.trim())
      .filter(Boolean);
    if (!hosts.length) {
      return "Add at least one Cassandra contact point (host or IP).";
    }
    if (!hosts.every((h) => /^[A-Za-z0-9][A-Za-z0-9.\-]{0,253}$/.test(h))) {
      return "Each contact point must be a valid hostname or IP address.";
    }
    const port = payload.config.port;
    if (!Number.isInteger(port) || port < 1 || port > 65535) {
      return "Port must be between 1 and 65535.";
    }
    // Auth is optional; a user (if given) must be valid and needs a password on create.
    if (payload.config.connection_user) {
      if (!/^[A-Za-z_][A-Za-z0-9_.\-]{0,127}$/.test(payload.config.connection_user)) {
        return "Connection user must be a valid username.";
      }
      if (!editingCatalogId && !payload.password) {
        return "A password is required when a Cassandra connection user is set.";
      }
    }
    return "";
  }
  if (isPrometheusCatalogType(payload.type)) {
    if (!/^https?:\/\/[^/:?\s]+(?::\d+)?(?:\/\S*)?$/.test(payload.config.uri)) {
      return "Prometheus URL must be an http:// or https:// endpoint.";
    }
    // Auth is optional; a user (if given) must be valid and needs a password on create.
    if (payload.config.connection_user) {
      if (!/^[A-Za-z_][A-Za-z0-9_.\-]{0,127}$/.test(payload.config.connection_user)) {
        return "Connection user must be a valid username.";
      }
      if (!editingCatalogId && !payload.password) {
        return "A password is required when a Prometheus connection user is set.";
      }
    }
    return "";
  }
  if (isGeneratorCatalogType(payload.type)) {
    return ""; // name-only; nothing else to validate
  }
  if (payload.type === "bigquery") {
    if (!/^[a-z][a-z0-9-]{4,28}[a-z0-9]$/.test(payload.config.project_id)) {
      return "Project ID must be a valid GCP project ID (6–30 chars, lowercase).";
    }
    if (payload.config.parent_project_id && !/^[a-z][a-z0-9-]{4,28}[a-z0-9]$/.test(payload.config.parent_project_id)) {
      return "Parent project ID must be a valid GCP project ID.";
    }
    if (!editingCatalogId && !payload.password) {
      return "A service-account JSON key is required for a new BigQuery catalog.";
    }
    return validateServiceAccountKey(payload.password);
  }
  if (payload.type === "gsheets") {
    if (!/^[A-Za-z0-9_-]{20,120}$/.test(payload.config.metadata_sheet_id)) {
      return "Metadata sheet ID must be a Google Sheets spreadsheet ID.";
    }
    if (!editingCatalogId && !payload.password) {
      return "A service-account JSON key is required for a new Google Sheets catalog.";
    }
    return validateServiceAccountKey(payload.password);
  }
  if (!new RegExp("^s3://[a-z0-9][a-z0-9.-]{1,61}[a-z0-9](?:/\\S*)?$").test(payload.config.warehouse)) {
    return "Warehouse must be an s3:// bucket path.";
  }
  if (!/^[A-Za-z_][A-Za-z0-9_]{0,127}$/.test(payload.config.default_schema)) {
    return "Default schema must use letters, numbers, or underscores.";
  }
  return "";
}

async function saveCatalogFromForm() {
  const role = document.getElementById("roleSelect").value;
  if (role !== "admin") {
    showToast("Only admins can save catalogs.");
    return;
  }
  const payload = catalogPayloadFromForm();
  const validationError = validateCatalogPayload(payload);
  if (validationError) {
    showToast(validationError);
    return;
  }

  const existing = catalogRecords.find((catalog) => catalog.type !== "builtin" && catalog.name === payload.name);
  const catalogId = editingCatalogId || (existing && existing.id);
  const path = catalogId ? `/api/catalogs/${catalogId}` : "/api/catalogs";
  const method = catalogId ? "PATCH" : "POST";
  try {
    document.getElementById("saveCatalog").disabled = true;
    const result = await apiRequest(path, {
      method,
      body: JSON.stringify(payload)
    });
    const index = catalogRecords.findIndex((catalog) => catalog.id === result.catalog.id);
    if (index >= 0) {
      catalogRecords.splice(index, 1, result.catalog);
    } else {
      catalogRecords.push(result.catalog);
    }
    // Config changed, so any cached check result is stale.
    if (result.catalog.id != null) delete catalogCheckState[result.catalog.id];
    openCatalogEditor(result.catalog);
    showToast(`${result.catalog.name} saved.`);
  } catch (error) {
    showToast(error.message, { type: "error" });
  } finally {
    document.getElementById("saveCatalog").disabled = false;
  }
}

function setCatalogGroupBy(mode) {
  catalogGroupBy = mode === "status" ? "status" : "source";
  document.querySelectorAll("#catalogListState .cat-seg-btn").forEach((btn) => {
    const on = btn.dataset.groupBy === catalogGroupBy;
    btn.classList.toggle("active", on);
    btn.setAttribute("aria-selected", String(on));
  });
  renderCatalogList();
}

// One delegated set of handlers on the persistent #view-catalogs container, so
// they survive the list/editor/picker being re-rendered (their inner DOM — and
// thus any per-element listeners — is replaced on every state change).
function wireCatalogs() {
  const root = document.getElementById("view-catalogs");
  if (!root) return;

  root.addEventListener("click", (event) => {
    const target = event.target;
    if (target.closest("[data-catalog-add]")) return void openCatalogPicker();
    if (target.closest("[data-catalog-back]")) return void catalogBackToList();
    const seg = target.closest("[data-group-by]");
    if (seg) return void setCatalogGroupBy(seg.dataset.groupBy);
    const connector = target.closest(".cat-connector");
    if (connector && connector.dataset.connectorType) return void selectConnectorFromPicker(connector.dataset.connectorType);
    const card = target.closest(".cat-card[data-edit-catalog]");
    if (card) {
      const catalog = catalogRecords.find((item) => String(item.id) === card.dataset.editCatalog);
      if (catalog) openCatalogEditor(catalog);
      return;
    }
    if (target.closest("#saveCatalog")) return void saveCatalogFromForm();
    const checkBtn = target.closest("#testCatalogConfig");
    if (checkBtn) {
      if (!checkBtn.disabled) runCatalogCheck();
      return;
    }
    if (target.closest("#catalogEnableToggle")) return void toggleCatalogEnabled();
    if (target.closest("#catalogDriverUploadButton")) {
      const file = document.getElementById("catalogDriverFile");
      if (file) file.click();
      return;
    }
    if (target.closest("#catalogDriverDeleteButton")) return void handleDriverDelete(editingCatalogType);
  });

  root.addEventListener("change", (event) => {
    if (event.target.id === "catalogDriverFile") {
      handleDriverUpload(editingCatalogType, event.target.files[0]);
      event.target.value = "";
    }
  });

  root.addEventListener("input", (event) => {
    if (event.target.id === "catalogSearch") {
      catalogSearchTerm = event.target.value.trim().toLowerCase();
      renderCatalogList();
    } else if (event.target.id === "catalogName") {
      const heading = document.getElementById("catalogEditorName");
      if (heading) heading.textContent = event.target.value || "new_catalog";
    }
  });

  document.addEventListener("keydown", (event) => {
    if (
      event.key === "Escape" &&
      (catalogView === "pick" || catalogView === "edit") &&
      root.classList.contains("active")
    ) {
      catalogBackToList();
    }
  });
}

function updateQueryClusterOptions() {
  const select = document.getElementById("queryCluster");
  if (!select) return;
  const previous = select.value;
  const savedClusters = clusters.filter((cluster) => cluster.id);
  select.innerHTML = savedClusters.length
    ? savedClusters
        .map(
          (cluster) =>
            `<option value="${cluster.id}">${escapeHtml(cluster.name)} - ${escapeHtml(cluster.status)}</option>`
        )
        .join("")
    : '<option value="">No saved clusters</option>';
  if (savedClusters.some((cluster) => String(cluster.id) === previous)) {
    select.value = previous;
  }
  syncQueryContextFromActiveTab();
  resetSchemaBrowserForSelectedCluster();
}

function navigateTo(viewName) {
  // A toast about the previous screen shouldn't follow the user around.
  dismissToast();
  const role = document.getElementById("roleSelect").value;
  if (role === "user" && ["users", "settings", "create"].includes(viewName)) {
    showToast("Query users can run SQL and view clusters, but admin screens are locked.");
    viewName = "sql";
  }

  document.querySelectorAll(".view").forEach((view) => view.classList.remove("active"));
  const view = document.getElementById(`view-${viewName}`);
  if (!view) return;
  view.classList.add("active");

  document.querySelectorAll(".nav-item").forEach((item) => {
    item.classList.toggle("active", item.dataset.viewTarget === viewName);
  });

  const title = view.dataset.title || "TrinoHub";
  document.getElementById("viewTitle").textContent = title;

  // Lazy view-scoped data: roles power the Users screen; the audit log,
  // SSO/session settings, and API tokens live in Settings. All are cheap
  // reads and refresh on every visit.
  if (viewName === "users") {
    loadRolesFromApi();
    loadDataSecurity();
  }
  if (viewName === "jobs") loadJobsFromApi();
  if (viewName === "settings") {
    loadAuditLog();
    loadSsoSettings();
    loadSessionSettings();
    loadApiTokens();
    loadNotificationSettings();
    loadAskSettings();
  }
}

function wireNavigation() {
  document.querySelectorAll("[data-view-target]").forEach((button) => {
    button.addEventListener("click", () => navigateTo(button.dataset.viewTarget));
  });
}

function loadClosedSqlSidebars() {
  try {
    const value = JSON.parse(localStorage.getItem(SQL_SIDEBAR_STORAGE_KEY) || "[]");
    return new Set(Array.isArray(value) ? value : []);
  } catch (error) {
    return new Set();
  }
}

function saveClosedSqlSidebars() {
  try {
    localStorage.setItem(SQL_SIDEBAR_STORAGE_KEY, JSON.stringify(Array.from(closedSqlSidebars)));
  } catch (error) {
    // localStorage can be unavailable in private browsing; drawers still work for this page load.
  }
}

function sidebarToggleIcon(side, closed) {
  if (side === "left") return closed ? "chevron-right" : "chevron-left";
  return closed ? "chevron-left" : "chevron-right";
}

function applySqlSidebarState(side) {
  const workspace = document.querySelector("#view-sql .sql-workspace");
  if (!workspace) return;
  const closed = closedSqlSidebars.has(side);
  workspace.classList.toggle(`${side}-sidebar-closed`, closed);
  document.querySelectorAll(`[data-sql-sidebar-panel="${side}"]`).forEach((panel) => {
    panel.setAttribute("aria-hidden", closed ? "true" : "false");
    if ("inert" in panel) panel.inert = closed;
  });
  document.querySelectorAll(`[data-sql-sidebar-rail="${side}"]`).forEach((rail) => {
    rail.hidden = !closed;
  });
  document.querySelectorAll(`[data-sql-sidebar-toggle="${side}"]`).forEach((button) => {
    const label = button.dataset.sqlSidebarLabel || "side panel";
    const action = closed ? "Open" : "Close";
    button.setAttribute("aria-expanded", closed ? "false" : "true");
    button.setAttribute("aria-label", `${action} ${label}`);
    button.title = `${action} ${label}`;
    const icon = button.querySelector("[data-icon]");
    if (icon) {
      icon.dataset.icon = sidebarToggleIcon(side, closed);
      icon.innerHTML = iconSvg(icon.dataset.icon);
    }
  });
}

function focusSqlSidebarPanel(panelId) {
  if (!panelId) return;
  window.setTimeout(() => {
    const panel = document.getElementById(panelId);
    if (!panel) return;
    panel.scrollIntoView({ block: "nearest", inline: "nearest" });
    const focusTarget = panel.querySelector("input, select, textarea, [tabindex]") || panel.querySelector("button");
    if (focusTarget) focusTarget.focus({ preventScroll: true });
  }, 220);
}

function toggleSqlSidebar(side, focusPanelId = "") {
  const opening = closedSqlSidebars.has(side);
  if (closedSqlSidebars.has(side)) {
    closedSqlSidebars.delete(side);
  } else {
    closedSqlSidebars.add(side);
  }
  saveClosedSqlSidebars();
  applySqlSidebarState(side);
  if (opening) focusSqlSidebarPanel(focusPanelId);
}

function wireSqlSidebars() {
  closedSqlSidebars = loadClosedSqlSidebars();
  document.querySelectorAll("[data-sql-sidebar-toggle]").forEach((button) => {
    const side = button.dataset.sqlSidebarToggle;
    button.addEventListener("click", () => toggleSqlSidebar(side, button.dataset.sqlSidebarFocus || ""));
  });
  applySqlSidebarState("left");
  applySqlSidebarState("right");
}

function renderClusters() {
  const tbody = document.getElementById("clusterRows");
  const search = document.getElementById("clusterSearch").value.trim().toLowerCase();
  const filtered = clusters.filter((cluster) => {
    const matchesSearch = [cluster.name, cluster.catalogs, cluster.status, cluster.instance_type || cluster.preset]
      .join(" ")
      .toLowerCase()
      .includes(search);
    const matchesFilter = currentFilter === "all" || cluster.status.toLowerCase() === currentFilter;
    return matchesSearch && matchesFilter;
  });

  tbody.innerHTML = filtered
    .map(
      (cluster, index) => `
        <tr>
          <td><strong>${cluster.name}</strong><br><small>${cluster.catalogs}</small></td>
          <td><span class="chip ${statusClass(cluster.status)}">${cluster.status}</span>${
            progressHint(cluster.status)
              ? `<br><small class="status-hint">${progressHint(cluster.status)}</small>`
              : ""
          }</td>
          <td>${cluster.instance_type || cluster.preset || "—"}</td>
          <td>${cluster.trino_version ? escapeHtml(cluster.trino_version) : "—"}</td>
          <td>${cluster.region}</td>
          <td>${cluster.workers}</td>
          <td>${cluster.autoscaling}</td>
          <td>${cluster.suspend}</td>
          <td>${cluster.owner}</td>
          <td class="actions-col">
            <div class="table-actions">
              <button class="icon-button" type="button" title="Connection info" data-connect-cluster="${index}"><span data-icon="info"></span></button>
              <button class="icon-button" type="button" title="Open cluster" data-open-cluster="${index}"><span data-icon="server"></span></button>
              <button class="icon-button admin-action" type="button" title="Start or resume" data-start-cluster="${index}"><span data-icon="play"></span></button>
              <button class="icon-button admin-action" type="button" title="Edit" data-edit-cluster="${index}"><span data-icon="settings"></span></button>
              <button class="icon-button admin-action" type="button" title="Suspend" data-suspend-cluster="${index}"><span data-icon="pause"></span></button>
              <span class="table-actions-divider" aria-hidden="true"></span>
              <button class="icon-button admin-action" type="button" title="Disable" data-disable-cluster="${index}"><span data-icon="shield"></span></button>
              <button class="icon-button admin-action" type="button" title="Delete" data-delete-cluster="${index}"><span data-icon="trash"></span></button>
            </div>
          </td>
        </tr>
      `
    )
    .join("");

  if (!filtered.length) {
    tbody.innerHTML = clusters.length
      ? '<tr><td colspan="10">No clusters match the current filters.</td></tr>'
      : `<tr><td colspan="10">
           <div class="table-empty">
             <span class="table-empty-icon" data-icon="server"></span>
             <strong>No clusters yet</strong>
             <p>Create your first Trino cluster to start running SQL against your data.</p>
             <button class="primary-button admin-action" type="button" data-empty-create-cluster>
               <span data-icon="plus"></span> Create cluster
             </button>
           </div>
         </td></tr>`;
    const emptyCta = tbody.querySelector("[data-empty-create-cluster]");
    if (emptyCta) emptyCta.addEventListener("click", () => navigateTo("create"));
  }

  replaceIcons();
  applyRoleMode();
  updateQueryClusterOptions();
  scheduleClusterPolling();
  document.querySelectorAll("[data-open-cluster]").forEach((button) => {
    button.addEventListener("click", () => {
      const cluster = filtered[Number(button.dataset.openCluster)];
      openClusterDetail(cluster);
    });
  });
  document.querySelectorAll("[data-connect-cluster]").forEach((button) => {
    button.addEventListener("click", () => {
      const cluster = filtered[Number(button.dataset.connectCluster)];
      openConnectModal(cluster);
    });
  });
  document.querySelectorAll("[data-start-cluster]").forEach((button) => {
    button.addEventListener("click", async () => {
      const cluster = filtered[Number(button.dataset.startCluster)];
      await startCluster(cluster);
    });
  });
  document.querySelectorAll("[data-edit-cluster]").forEach((button) => {
    button.addEventListener("click", async () => {
      const cluster = filtered[Number(button.dataset.editCluster)];
      await editCluster(cluster);
    });
  });
  document.querySelectorAll("[data-suspend-cluster]").forEach((button) => {
    button.addEventListener("click", async () => {
      const cluster = filtered[Number(button.dataset.suspendCluster)];
      await suspendCluster(cluster);
    });
  });
  document.querySelectorAll("[data-disable-cluster]").forEach((button) => {
    button.addEventListener("click", async () => {
      const cluster = filtered[Number(button.dataset.disableCluster)];
      await disableCluster(cluster);
    });
  });
  document.querySelectorAll("[data-delete-cluster]").forEach((button) => {
    button.addEventListener("click", async () => {
      const cluster = filtered[Number(button.dataset.deleteCluster)];
      await deleteCluster(cluster);
    });
  });
}

function openClusterDetail(cluster) {
  selectedClusterDetail = cluster;
  document.getElementById("detailName").textContent = cluster.name;
  const status = document.getElementById("detailStatus");
  status.textContent = cluster.status;
  status.className = `chip ${statusClass(cluster.status)}`;
  const metaRegion = document.getElementById("detailRegion");
  if (metaRegion) metaRegion.textContent = cluster.region || "";
  const metaInstance = document.getElementById("detailInstanceType");
  if (metaInstance) {
    metaInstance.textContent = `${cluster.instance_type || cluster.preset || ""}${
      cluster.accelerated ? " · accelerated" : ""
    }`;
  }
  const metaWorkers = document.getElementById("detailWorkerRange");
  if (metaWorkers) {
    metaWorkers.textContent =
      cluster.worker_mode === "fixed"
        ? `${cluster.min_workers} workers`
        : `${cluster.min_workers}-${cluster.max_workers} workers (auto)`;
  }
  setDetailActionAvailability(cluster.status);
  const banner = document.getElementById("detailColdStart");
  if (banner) {
    const hint = progressHint(cluster.status);
    banner.textContent = hint;
    banner.hidden = !hint;
  }
  renderClusterDetailSummary(cluster);
  navigateTo("cluster-detail");
  loadClusterDetailLive(cluster);
  loadCoordinatorUiLink(cluster);
  loadDetailStatsChart(cluster);
  loadDetailMonthlyCost(cluster);
}

// Point the detail page's "Coordinator UI" button at the cluster's Trino web UI
// (same resolved host as the connection strings). Hidden until a resolvable
// address exists, and available to every user — not just admins. Guards against
// a stale response winning when the user switches clusters mid-fetch.
async function loadCoordinatorUiLink(cluster) {
  const link = document.getElementById("clusterDetailUiLink");
  if (!link) return;
  link.hidden = true;
  link.removeAttribute("href");
  if (!cluster || !cluster.id) return;
  try {
    const info = await apiRequest(`/api/clusters/${cluster.id}/connection`);
    if (
      selectedClusterDetail &&
      selectedClusterDetail.id === cluster.id &&
      info.resolvable &&
      info.web_ui
    ) {
      link.href = info.web_ui;
      link.hidden = false;
    }
  } catch (error) {
    // Non-fatal: leave the button hidden if the address can't be resolved.
  }
}

// Grey out lifecycle actions that make no sense for the current status —
// e.g. Start on a Running cluster, Suspend on a suspended one. Role gating
// still applies on top (applyRoleMode respects data-status-disabled).
function setDetailActionAvailability(status) {
  const normalized = String(status).toLowerCase();
  const running = normalized === "running";
  const inFlight = ["starting", "suspending", "deleting", "updating", "scaling"].some((s) =>
    normalized.includes(s)
  );
  const availability = {
    clusterDetailStart: !running && !inFlight,
    clusterDetailSuspend: running,
  };
  Object.entries(availability).forEach(([id, enabled]) => {
    const button = document.getElementById(id);
    if (!button) return;
    if (enabled) delete button.dataset.statusDisabled;
    else button.dataset.statusDisabled = "1";
  });
  applyRoleMode();
}

function renderClusterDetailSummary(cluster) {
  document.getElementById("detailWorkersMetric").textContent =
    cluster.worker_mode === "fixed" ? String(cluster.min_workers) : `${cluster.min_workers}-${cluster.max_workers}`;
  document.getElementById("detailWorkersNote").textContent =
    cluster.worker_mode === "fixed" ? "Fixed worker target" : "Autoscale min-max";
  document.getElementById("detailQueriesMetric").textContent = "-";
  document.getElementById("detailQueriesNote").textContent = "No queue sample loaded";
  document.getElementById("detailCpuMetric").textContent = "-";
  document.getElementById("detailCpuNote").textContent = "No CloudWatch sample loaded";
  document.getElementById("detailSuspendMetric").textContent = cluster.auto_suspend_minutes
    ? `${cluster.auto_suspend_minutes} min`
    : "Never";
  document.getElementById("detailSuspendNote").textContent = cluster.accelerated
    ? "Suspending discards the warm NVMe cache"
    : "Configured interval";
  renderClusterCost(cluster);
  renderDetailUtilization(null);
  document.getElementById("detailResourceDiagram").innerHTML = '<div class="diagram-node">No AWS resources loaded</div>';
  document.getElementById("detailScalingRows").innerHTML = '<tr><td colspan="4">No scaling events loaded.</td></tr>';
}

// The Utilization panel only ever shows real samples. Until the autoscaler
// reports one, say so plainly — no decorative charts.
function renderDetailUtilization(signals, desired) {
  const box = document.getElementById("detailUtilization");
  const chip = document.getElementById("detailUtilizationChip");
  if (!box || !chip) return;
  if (!signals) {
    box.innerHTML =
      '<p class="util-empty">No utilization samples yet. Data appears after the autoscaler takes its first reading.</p>';
    chip.textContent = "No data yet";
    chip.className = "chip";
    return;
  }
  const rows = [
    ["Avg worker CPU", signals.avg_worker_cpu == null ? "—" : `${Number(signals.avg_worker_cpu).toFixed(0)}%`],
    ["Running queries", String(signals.running_queries || 0)],
    ["Queued queries", String(signals.queued_queries || 0)],
    ["Workers (desired)", desired == null ? "—" : String(desired)],
  ];
  box.innerHTML = rows
    .map(([label, value]) => `<div class="util-row"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`)
    .join("");
  chip.textContent = "Live";
  chip.className = "chip success";
}

// Estimated running cost per hour from the resolved preset price × node count
// (1 coordinator + workers). TrinoHub owns provisioning, so it can surface the
// hourly spend that managed platforms bill invisibly (roadmap F5). Figures are approximate and
// labelled as such. `desired` overrides the configured worker target when a
// live autoscaler capacity is known.
// Resolve a cluster's instance type + hourly rate. New clusters carry an explicit
// instance_type (priced from instanceCatalog); legacy preset-based clusters fall
// back to the resolved preset tier so their cost still renders.
function clusterInstanceMeta(cluster) {
  const itype = cluster.instance_type || "";
  if (itype && instanceCatalog[itype]) {
    return { instance: itype, hourly_usd: instanceCatalog[itype].hourly_usd };
  }
  const tier = presetTier(cluster.preset);
  if (tier) return { instance: tier.instance_type, hourly_usd: tier.hourly_usd };
  return null;
}

function clusterHourlyCost(cluster, desired) {
  const meta = clusterInstanceMeta(cluster);
  if (!meta || meta.hourly_usd == null) return null;
  const rate = meta.hourly_usd;
  if (Number.isInteger(desired)) {
    return { instance: meta.instance, low: rate * (1 + desired), high: rate * (1 + desired), nodes: desired };
  }
  if (cluster.worker_mode === "fixed") {
    return { instance: meta.instance, low: rate * (1 + cluster.min_workers), high: rate * (1 + cluster.min_workers) };
  }
  return {
    instance: meta.instance,
    low: rate * (1 + cluster.min_workers),
    high: rate * (1 + cluster.max_workers)
  };
}

function formatUsd(value) {
  return `$${value.toFixed(2)}`;
}

function renderClusterCost(cluster, desired) {
  const metric = document.getElementById("detailCostMetric");
  const note = document.getElementById("detailCostNote");
  if (!metric || !note) return;
  const cost = clusterHourlyCost(cluster, desired);
  if (!cost) {
    metric.textContent = "-";
    note.textContent = "Pricing unavailable for this instance type";
    return;
  }
  metric.textContent =
    cost.low === cost.high ? `${formatUsd(cost.low)}/hr` : `${formatUsd(cost.low)}–${formatUsd(cost.high)}/hr`;
  const scope = Number.isInteger(cost.nodes)
    ? `1 + ${cost.nodes} × ${cost.instance}`
    : `1 + ${cluster.worker_mode === "fixed" ? cluster.min_workers : `${cluster.min_workers}-${cluster.max_workers}`} × ${cost.instance}`;
  note.textContent = `${scope}, approx on-demand`;
}

function renderDetailResources(resources) {
  const diagram = document.getElementById("detailResourceDiagram");
  if (!resources.length) {
    diagram.innerHTML = '<div class="diagram-node">No tracked AWS resources</div>';
    return;
  }
  const nodes = resources
    .map((resource) => {
      const label = resource.type.replace(/_/g, " ");
      return `<div class="diagram-line"></div><div class="diagram-node">${escapeHtml(label)}<br><small>${escapeHtml(
        resource.resource_id
      )}</small></div>`;
    })
    .join("");
  diagram.innerHTML = `<div class="diagram-node control">TrinoHub API</div>${nodes}`;

  const asg = resources.find((resource) => resource.type === "auto_scaling_group");
  if (asg && asg.metadata) {
    const desired = asg.metadata.desired_capacity;
    const min = asg.metadata.min_size;
    const max = asg.metadata.max_size;
    if (desired != null) {
      document.getElementById("detailWorkersMetric").textContent = String(desired);
      document.getElementById("detailWorkersNote").textContent = `Desired capacity, range ${min}-${max}`;
      if (selectedClusterDetail) renderClusterCost(selectedClusterDetail, Number(desired));
    }
    const signals = asg.metadata.last_autoscale && asg.metadata.last_autoscale.signals;
    if (signals) {
      document.getElementById("detailQueriesMetric").textContent = String(signals.running_queries || 0);
      document.getElementById("detailQueriesNote").textContent = `${signals.queued_queries || 0} queued`;
      document.getElementById("detailCpuMetric").textContent =
        signals.avg_worker_cpu == null ? "-" : `${Number(signals.avg_worker_cpu).toFixed(0)}%`;
      document.getElementById("detailCpuNote").textContent =
        signals.reserved_memory == null ? "Latest autoscale sample" : "Latest CPU and memory sample";
    }
    renderDetailUtilization(signals || null, desired != null ? Number(desired) : undefined);
  }
}

function renderDetailScalingEvents(events) {
  const rows = document.getElementById("detailScalingRows");
  if (!events.length) {
    rows.innerHTML = '<tr><td colspan="4">No scaling events yet.</td></tr>';
    return;
  }
  rows.innerHTML = events
    .slice(0, 10)
    .map((event) => {
      const time = event.created_at ? new Date(event.created_at).toLocaleTimeString() : "-";
      return `<tr>
        <td>${escapeHtml(time)}</td>
        <td>${escapeHtml(event.direction === "up" ? "Scaled up" : "Scaled down")}</td>
        <td>${escapeHtml(event.reason || "")}</td>
        <td>${escapeHtml(event.from_workers)} to ${escapeHtml(event.to_workers)}</td>
      </tr>`;
    })
    .join("");
}

async function loadClusterDetailLive(cluster) {
  if (!cluster || !cluster.id || !currentUser || currentUser.role !== "admin") {
    return;
  }
  try {
    const resources = await apiRequest(`/api/clusters/${cluster.id}/resources`);
    renderDetailResources(resources.resources || []);
  } catch (error) {
    document.getElementById("detailResourceDiagram").innerHTML =
      `<div class="diagram-node">Resources unavailable<br><small>${escapeHtml(error.message)}</small></div>`;
  }
  try {
    const scaling = await apiRequest(`/api/clusters/${cluster.id}/scaling-events`);
    renderDetailScalingEvents(scaling.scaling_events || []);
  } catch (error) {
    document.getElementById("detailScalingRows").innerHTML =
      `<tr><td colspan="4">${escapeHtml(error.message)}</td></tr>`;
  }
}

async function startCluster(cluster) {
  if (!cluster || !cluster.id) {
    showToast("This sample row is not connected to a saved cluster.");
    return;
  }
  const confirmed = await appConfirm({
    title: `Start ${cluster.name}?`,
    body: "This creates billable AWS resources: one coordinator EC2 instance, worker capacity, a launch template, an Auto Scaling Group, and security-group rules.",
    confirmLabel: "Start cluster",
  });
  if (!confirmed) {
    return;
  }
  try {
    showToast(`Starting AWS provisioning for ${cluster.name}.`);
    const result = await apiRequest(`/api/clusters/${cluster.id}/start`, {
      method: "POST",
      body: JSON.stringify({ confirm_billable: true })
    });
    const index = clusters.findIndex((item) => item.id === cluster.id);
    const wasDetailOpen = selectedClusterDetail && selectedClusterDetail.id === cluster.id;
    if (index >= 0) {
      clusters[index] = clusterFromApi(result.cluster);
      if (wasDetailOpen) {
        selectedClusterDetail = clusters[index];
      }
    }
    if (wasDetailOpen) {
      openClusterDetail(selectedClusterDetail);
    }
    renderClusters();
    showToast(result.message || `${cluster.name} is starting — first boot takes ~${COLD_START_MINUTES} min.`);
  } catch (error) {
    showToast(error.message, { type: "error" });
  }
}

async function suspendCluster(cluster) {
  if (!cluster || !cluster.id) {
    showToast("This sample row is not connected to a saved cluster.");
    return;
  }
  const confirmed = await appConfirm({
    title: `Suspend ${cluster.name}?`,
    body: "Tracked runtime AWS resources are cleaned up. The cluster definition is kept and can be started again later.",
    confirmLabel: "Suspend",
  });
  if (!confirmed) {
    return;
  }
  try {
    const result = await apiRequest(`/api/clusters/${cluster.id}/suspend`, {
      method: "POST",
      body: JSON.stringify({})
    });
    const index = clusters.findIndex((item) => item.id === cluster.id);
    const wasDetailOpen = selectedClusterDetail && selectedClusterDetail.id === cluster.id;
    if (index >= 0) {
      clusters[index] = clusterFromApi(result.cluster);
      if (wasDetailOpen) {
        selectedClusterDetail = clusters[index];
      }
    }
    if (wasDetailOpen) {
      openClusterDetail(selectedClusterDetail);
    }
    renderClusters();
    showToast(result.message || `${cluster.name} suspended.`);
  } catch (error) {
    showToast(error.message, { type: "error" });
  }
}

async function disableCluster(cluster) {
  if (!cluster || !cluster.id) {
    showToast("This sample row is not connected to a saved cluster.");
    return;
  }
  const confirmed = await appConfirm({
    title: `Disable ${cluster.name}?`,
    body: "Tracked runtime AWS resources are cleaned up and the cluster is marked disabled until an admin re-enables it.",
    confirmLabel: "Disable",
    danger: true,
  });
  if (!confirmed) {
    return;
  }
  try {
    const result = await apiRequest(`/api/clusters/${cluster.id}/disable`, {
      method: "POST",
      body: JSON.stringify({})
    });
    const index = clusters.findIndex((item) => item.id === cluster.id);
    const wasDetailOpen = selectedClusterDetail && selectedClusterDetail.id === cluster.id;
    if (index >= 0) {
      clusters[index] = clusterFromApi(result.cluster);
      if (wasDetailOpen) {
        selectedClusterDetail = clusters[index];
      }
    }
    if (wasDetailOpen) {
      openClusterDetail(selectedClusterDetail);
    }
    renderClusters();
    showToast(result.message || `${cluster.name} disabled.`);
  } catch (error) {
    showToast(error.message, { type: "error" });
  }
}

function parseWorkerCount(raw, label) {
  const value = Number(String(raw).trim());
  if (!Number.isInteger(value) || value < 1) {
    return { error: `${label} must be a whole number of 1 or more.` };
  }
  return { value };
}

async function editCluster(cluster) {
  if (!cluster || !cluster.id) {
    showToast("This sample row is not connected to a saved cluster.");
    return;
  }

  const result = await openAppDialog({
    title: `Edit ${cluster.name}`,
    confirmLabel: "Save changes",
    fields: [
      { name: "min_workers", label: "Minimum workers", type: "number", value: cluster.min_workers },
      { name: "max_workers", label: "Maximum workers", type: "number", value: cluster.max_workers },
      {
        name: "auto_suspend_minutes",
        label: "Auto-suspend after idle minutes",
        type: "number",
        value: cluster.auto_suspend_minutes == null ? "" : cluster.auto_suspend_minutes,
        placeholder: "Blank = never",
        hint: "Leave blank to keep the cluster running until suspended manually.",
      },
      {
        name: "uptime_schedule",
        label: "Keep-warm windows (UTC, one per line)",
        type: "textarea",
        rows: 2,
        value: uptimeScheduleText(cluster.uptime_schedule),
        placeholder: "mon-fri 08:00-18:00",
        hint: "Auto-suspend is suppressed inside these windows.",
      },
    ],
  });
  if (result === null) return;

  const payload = {};
  const min = parseWorkerCount(result.min_workers, "Minimum workers");
  if (min.error) {
    showToast(min.error, { type: "error" });
    return;
  }
  if (min.value !== cluster.min_workers) payload.min_workers = min.value;

  const max = parseWorkerCount(result.max_workers, "Maximum workers");
  if (max.error) {
    showToast(max.error, { type: "error" });
    return;
  }
  if (max.value !== cluster.max_workers) payload.max_workers = max.value;

  let suspend = null;
  if (String(result.auto_suspend_minutes).trim() !== "") {
    suspend = Number(String(result.auto_suspend_minutes).trim());
    if (!Number.isInteger(suspend) || suspend < 1) {
      showToast("Auto-suspend minutes must be a whole number of 1 or more, or blank.", { type: "error" });
      return;
    }
  }
  if (suspend !== cluster.auto_suspend_minutes) payload.auto_suspend_minutes = suspend;

  const scheduleLines = String(result.uptime_schedule || "")
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
  if (uptimeScheduleText(cluster.uptime_schedule) !== scheduleLines.join("\n")) {
    payload.uptime_schedule = scheduleLines;
  }

  if (Object.keys(payload).length === 0) {
    showToast("No changes to apply.");
    return;
  }

  try {
    const result = await apiRequest(`/api/clusters/${cluster.id}`, {
      method: "PATCH",
      body: JSON.stringify(payload)
    });
    const index = clusters.findIndex((item) => item.id === cluster.id);
    const wasDetailOpen = selectedClusterDetail && selectedClusterDetail.id === cluster.id;
    if (index >= 0) {
      clusters[index] = clusterFromApi(result.cluster);
      if (wasDetailOpen) {
        selectedClusterDetail = clusters[index];
      }
    }
    if (wasDetailOpen) {
      openClusterDetail(selectedClusterDetail);
    }
    renderClusters();
    let message = `Updated ${result.cluster.name}.`;
    if (result.restart_required) {
      message += " Some changes need a suspend + start to take effect.";
    }
    showToast(message);
  } catch (error) {
    showToast(error.message, { type: "error" });
  }
}

async function deleteCluster(cluster) {
  if (!cluster || !cluster.id) {
    showToast("This sample row is not connected to a saved cluster.");
    return;
  }
  const confirmed = await appConfirm({
    title: `Delete ${cluster.name}?`,
    body: "This permanently removes the cluster record and deletes tracked TrinoHub AWS resources. This cannot be undone.",
    confirmLabel: "Delete cluster",
    danger: true,
  });
  if (!confirmed) {
    return;
  }
  try {
    showToast(`Deleting ${cluster.name}.`);
    await apiRequest(`/api/clusters/${cluster.id}`, {
      method: "DELETE",
      body: JSON.stringify({})
    });
    const index = clusters.findIndex((item) => item.id === cluster.id);
    if (index >= 0) {
      clusters.splice(index, 1);
    }
    if (selectedClusterDetail && selectedClusterDetail.id === cluster.id) {
      selectedClusterDetail = null;
      navigateTo("clusters");
    }
    renderClusters();
    showToast(`${cluster.name} deleted.`);
  } catch (error) {
    showToast(error.message, { type: "error" });
  }
}

function renderHistory() {
  const tbody = document.getElementById("historyRows");
  const rows = filteredQueryHistory();
  if (!rows.length) {
    tbody.innerHTML = '<tr><td colspan="6">No query history yet.</td></tr>';
  } else {
    tbody.innerHTML = rows
      .map(
        (row) => `
        <tr data-history-query-id="${row.id}" class="${row.id === selectedHistoryQueryId ? "selected" : ""}">
          <td><span class="chip ${statusClass(row.status)}">${row.status}</span></td>
          <td><code>${escapeHtml(row.query)}</code></td>
          <td>${escapeHtml(row.cluster)}</td>
          <td>${escapeHtml(row.user)}</td>
          <td>${escapeHtml(row.elapsed)}</td>
          <td>${escapeHtml(row.rows)}</td>
        </tr>
      `
      )
      .join("");
    tbody.querySelectorAll("[data-history-query-id]").forEach((row) => {
      row.addEventListener("click", () => showQueryDetail(Number(row.dataset.historyQueryId)));
    });
  }

  const inline = document.getElementById("inlineHistory");
  if (!inline) return;
  inline.innerHTML = queryHistory.length
    ? queryHistory
        .slice(0, 5)
        .map(
          (row) => `
            <button type="button">
              <strong>${escapeHtml(row.status)}</strong>
              <span>${escapeHtml(row.query)}</span>
              <small>${escapeHtml(row.cluster)} - ${escapeHtml(row.elapsed)}</small>
            </button>
          `
        )
        .join("")
    : '<div class="empty-results">No recent queries.</div>';
}

function filteredQueryHistory() {
  const text = historyFilter.trim().toLowerCase();
  const now = new Date();
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const weekAgo = now.getTime() - 7 * 24 * 60 * 60 * 1000;
  return queryHistory.filter((row) => {
    if (historyStatusFilter && row.status !== historyStatusFilter) return false;
    if (historyRoleFilter && row.user_role !== historyRoleFilter) return false;
    if (historyDateFilter) {
      const created = Date.parse(row.created_at || "");
      if (!Number.isFinite(created)) return false;
      if (historyDateFilter === "today" && created < startOfToday) return false;
      if (historyDateFilter === "week" && created < weekAgo) return false;
    }
    if (!text) return true;
    return [
      row.query,
      row.cluster,
      row.catalog,
      row.schema,
      row.user,
      row.user_role,
      row.status
    ]
      .join(" ")
      .toLowerCase()
      .includes(text);
  });
}

function showQueryDetail(id) {
  const query = queryHistory.find((item) => item.id === id);
  const panel = document.getElementById("queryDetailPanel");
  if (!query || !panel) return;
  selectedHistoryQueryId = id;
  panel.hidden = false;
  document.getElementById("queryDetailTitle").textContent = `Query #${query.id}`;
  document.getElementById("queryDetailStatus").textContent = query.status;
  document.getElementById("queryDetailCluster").textContent = query.cluster;
  document.getElementById("queryDetailContext").textContent = [query.catalog, query.schema].filter(Boolean).join(".") || "-";
  document.getElementById("queryDetailElapsed").textContent = query.elapsed;
  document.getElementById("queryDetailRows").textContent = query.rows;
  document.getElementById("queryDetailUser").textContent = `${query.user}${query.user_role ? ` (${query.user_role})` : ""}`;
  document.getElementById("queryDetailSql").textContent = query.query;
  const error = document.getElementById("queryDetailError");
  error.hidden = !query.error_message;
  error.textContent = query.error_message || "";
  renderHistory();
}

function historyQueryForDetail() {
  return queryHistory.find((item) => item.id === selectedHistoryQueryId) || null;
}

function openHistoryQueryInEditor() {
  const query = historyQueryForDetail();
  if (!query) return;
  const editor = document.getElementById("sqlText");
  editor.value = query.query;
  ensureSelectOption(document.getElementById("queryCluster"), query.cluster_id);
  ensureSelectOption(document.getElementById("queryCatalog"), query.catalog);
  ensureSelectOption(document.getElementById("querySchema"), query.schema);
  if (query.cluster_id != null) document.getElementById("queryCluster").value = String(query.cluster_id);
  if (query.catalog) document.getElementById("queryCatalog").value = query.catalog;
  if (query.schema) document.getElementById("querySchema").value = query.schema;
  renderSqlHighlight();
  scheduleSaveActiveQueryTab();
  navigateTo("sql");
}

async function copyHistoryQuerySql() {
  const query = historyQueryForDetail();
  if (!query) return;
  try {
    await copyText(query.query);
    showToast("SQL copied.");
  } catch (error) {
    showToast("Clipboard is unavailable.");
  }
}

async function saveHistoryQuery() {
  const query = historyQueryForDetail();
  if (!query) return;
  try {
    const result = await apiRequest("/api/saved-queries", {
      method: "POST",
      body: JSON.stringify({
        name: `Query #${query.id}`,
        sql: query.query,
        cluster_id: query.cluster_id,
        catalog: query.catalog,
        schema: query.schema
      })
    });
    savedQueries.unshift(result.query);
    renderSavedQueries();
    showToast("Query saved.");
  } catch (error) {
    showToast(error.message, { type: "error" });
  }
}

function sortedSavedQueries() {
  const filter = savedQueryFilter.trim().toLowerCase();
  const rows = savedQueries.filter((query) => {
    if (!filter) return true;
    return `${query.name} ${query.sql} ${query.catalog} ${query.schema}`.toLowerCase().includes(filter);
  });
  return rows.sort((left, right) => {
    if (savedQuerySort === "name") return left.name.localeCompare(right.name);
    if (savedQuerySort === "created") return String(right.created_at || "").localeCompare(String(left.created_at || ""));
    return String(right.updated_at || "").localeCompare(String(left.updated_at || ""));
  });
}

function renderSavedQueries() {
  const list = document.getElementById("savedQueryList");
  const count = document.getElementById("savedQueryCount");
  if (!list) return;
  const rows = sortedSavedQueries();
  if (count) count.textContent = String(savedQueries.length);
  list.innerHTML = rows.length
    ? rows
        .map(
          (query) => `
            <div class="saved-query-row">
              <span>
                <strong>${escapeHtml(query.name)}</strong>
                <span>${escapeHtml(query.sql)}</span>
                <small>${escapeHtml(
                  query.shared_access
                    ? `Shared by ${query.owner_username} (${query.shared_access})`
                    : [query.catalog, query.schema].filter(Boolean).join(".") || "No context"
                )}</small>
              </span>
              <span class="saved-query-actions">
                <button type="button" data-open-saved-query="${query.id}" aria-label="Open ${escapeHtml(query.name)}" title="Open"><span data-icon="arrow-right"></span></button>
                ${
                  query.shared_access
                    ? ""
                    : `<button type="button" data-share-saved-query="${query.id}" aria-label="Share ${escapeHtml(query.name)}" title="Share"><span data-icon="users"></span></button>
                <button type="button" data-rename-saved-query="${query.id}" aria-label="Rename ${escapeHtml(query.name)}" title="Rename"><span data-icon="settings"></span></button>
                <button type="button" data-delete-saved-query="${query.id}" aria-label="Delete ${escapeHtml(query.name)}" title="Delete"><span data-icon="trash"></span></button>`
                }
              </span>
            </div>
          `
        )
        .join("")
    : '<div class="empty-results">No saved queries.</div>';
  replaceIcons();
  list.querySelectorAll("[data-open-saved-query]").forEach((button) => {
    button.addEventListener("click", () => openSavedQuery(Number(button.dataset.openSavedQuery)));
  });
  list.querySelectorAll("[data-rename-saved-query]").forEach((button) => {
    button.addEventListener("click", (event) => {
      event.stopPropagation();
      renameSavedQuery(Number(button.dataset.renameSavedQuery));
    });
  });
  list.querySelectorAll("[data-share-saved-query]").forEach((button) => {
    button.addEventListener("click", (event) => {
      event.stopPropagation();
      openShareDialog("saved query", "/api/saved-queries", Number(button.dataset.shareSavedQuery));
    });
  });
  list.querySelectorAll("[data-delete-saved-query]").forEach((button) => {
    button.addEventListener("click", (event) => {
      event.stopPropagation();
      deleteSavedQuery(Number(button.dataset.deleteSavedQuery));
    });
  });
}

async function loadSavedQueriesFromApi() {
  if (!currentUser) return;
  try {
    const result = await apiRequest("/api/saved-queries");
    savedQueries.splice.apply(savedQueries, [0, savedQueries.length].concat(result.queries || []));
    renderSavedQueries();
  } catch (error) {
    if (!/Authentication required/.test(error.message)) showToast(error.message, { type: "error" });
  }
}

async function saveCurrentQuery() {
  const payload = queryTabPayloadFromEditor();
  const sql = payload.sql.trim();
  if (!sql) {
    showToast("Enter SQL before saving.");
    return;
  }
  const active = activeQueryTab();
  const suggested = active ? active.name.replace(/\.sql$/i, "") : sql.slice(0, 80);
  const name = await appPrompt({
    title: "Save query",
    label: "Name",
    value: suggested || "Saved query",
  });
  if (name === null) return;
  const trimmed = name.trim();
  if (!trimmed) {
    showToast("Saved query name is required.");
    return;
  }
  try {
    const result = await apiRequest("/api/saved-queries", {
      method: "POST",
      body: JSON.stringify({
        name: trimmed,
        sql,
        cluster_id: payload.cluster_id,
        catalog: payload.catalog,
        schema: payload.schema
      })
    });
    savedQueries.unshift(result.query);
    renderSavedQueries();
    showToast("Query saved.");
  } catch (error) {
    showToast(error.message, { type: "error" });
  }
}

async function openSavedQuery(id) {
  const query = savedQueries.find((item) => item.id === id);
  if (!query) return;
  const tab = activeQueryTab();
  if (!tab) return;
  window.clearTimeout(queryTabSaveTimer);
  document.getElementById("sqlText").value = query.sql;
  ensureSelectOption(document.getElementById("queryCluster"), query.cluster_id);
  ensureSelectOption(document.getElementById("queryCatalog"), query.catalog);
  ensureSelectOption(document.getElementById("querySchema"), query.schema);
  if (query.cluster_id != null) document.getElementById("queryCluster").value = String(query.cluster_id);
  if (query.catalog) document.getElementById("queryCatalog").value = query.catalog;
  if (query.schema) document.getElementById("querySchema").value = query.schema;
  tab.sql = query.sql;
  tab.cluster_id = query.cluster_id;
  tab.catalog = query.catalog;
  tab.schema = query.schema;
  renderSqlHighlight();
  resetSchemaBrowserForSelectedCluster();
  await saveActiveQueryTabNow();
  showToast(`Opened ${query.name}.`);
}

async function renameSavedQuery(id) {
  const query = savedQueries.find((item) => item.id === id);
  if (!query) return;
  const name = await appPrompt({
    title: "Rename saved query",
    label: "Name",
    value: query.name,
  });
  if (name === null) return;
  const trimmed = name.trim();
  if (!trimmed) {
    showToast("Saved query name is required.");
    return;
  }
  try {
    const result = await apiRequest(`/api/saved-queries/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ name: trimmed })
    });
    Object.assign(query, result.query);
    renderSavedQueries();
  } catch (error) {
    showToast(error.message, { type: "error" });
  }
}

async function deleteSavedQuery(id) {
  const query = savedQueries.find((item) => item.id === id);
  if (!query) return;
  const confirmed = await appConfirm({
    title: `Delete saved query "${query.name}"?`,
    body: "This cannot be undone.",
    confirmLabel: "Delete",
    danger: true,
  });
  if (!confirmed) return;
  try {
    await apiRequest(`/api/saved-queries/${id}`, { method: "DELETE", body: JSON.stringify({}) });
    const index = savedQueries.findIndex((item) => item.id === id);
    if (index >= 0) savedQueries.splice(index, 1);
    renderSavedQueries();
    showToast("Saved query deleted.");
  } catch (error) {
    showToast(error.message, { type: "error" });
  }
}

async function loadQueryHistoryFromApi() {
  try {
    const result = await apiRequest("/api/query-history");
    const mappedQueries = result.queries.map((query) => ({
        id: query.id,
        status: query.status,
        query: query.sql,
        cluster_id: query.cluster_id,
        cluster_name: query.cluster_name || "",
        cluster: queryClusterLabel(query),
        catalog: query.catalog || "",
        schema: query.schema || "",
        user: query.username || (query.user_id ? `user ${query.user_id}` : "unknown"),
        user_role: query.user_role || "",
        elapsed: formatElapsedMs(query.elapsed_ms),
        rows: String(query.row_count),
        error_message: query.error_message || "",
        trino_query_id: query.trino_query_id || "",
        created_at: query.created_at,
        updated_at: query.updated_at
    }));
    queryHistory.splice.apply(queryHistory, [0, queryHistory.length].concat(mappedQueries));
    renderHistory();
  } catch (error) {
    if (/Authentication required/.test(error.message)) {
      queryHistory.splice(0, queryHistory.length);
      renderHistory();
    } else {
      showToast(error.message, { type: "error" });
    }
  }
}

function activeQueryTab() {
  return (
    queryTabs.find((tab) => tab.id === activeQueryTabId) ||
    queryTabs.find((tab) => tab.is_active) ||
    queryTabs[0] ||
    null
  );
}

function normalizedQueryClusterId() {
  const value = document.getElementById("queryCluster").value;
  return value ? Number(value) : null;
}

function ensureSelectOption(select, value) {
  if (!select || !value) return;
  if (Array.from(select.options).some((option) => option.value === String(value))) return;
  const option = document.createElement("option");
  option.value = String(value);
  option.textContent = String(value);
  select.append(option);
}

function queryTabPayloadFromEditor() {
  return {
    sql: document.getElementById("sqlText").value,
    cluster_id: normalizedQueryClusterId(),
    catalog: document.getElementById("queryCatalog").value,
    schema: document.getElementById("querySchema").value,
    run_mode: currentRunMode
  };
}

function updateActiveQueryTabFromEditor() {
  const tab = activeQueryTab();
  if (!tab) return;
  const payload = queryTabPayloadFromEditor();
  tab.sql = payload.sql;
  tab.cluster_id = payload.cluster_id;
  tab.catalog = payload.catalog;
  tab.schema = payload.schema;
}

function syncQueryContextFromActiveTab() {
  const tab = activeQueryTab();
  if (!tab) return;
  suppressQueryTabAutosave = true;
  const cluster = document.getElementById("queryCluster");
  const catalog = document.getElementById("queryCatalog");
  const schema = document.getElementById("querySchema");
  ensureSelectOption(cluster, tab.cluster_id);
  ensureSelectOption(catalog, tab.catalog);
  ensureSelectOption(schema, tab.schema);
  if (cluster && tab.cluster_id != null) cluster.value = String(tab.cluster_id);
  if (catalog && tab.catalog) catalog.value = tab.catalog;
  if (schema && tab.schema) schema.value = tab.schema;
  suppressQueryTabAutosave = false;
}

function applyQueryTabToEditor(tab) {
  if (!tab) return;
  suppressQueryTabAutosave = true;
  document.getElementById("sqlText").value = tab.sql || "";
  suppressQueryTabAutosave = false;
  renderSqlHighlight();
  syncQueryContextFromActiveTab();
  applyRunMode(tab.run_mode || "current");
  setQueryState("Ready", "0.0s", "0");
  activeQueryResult = null;
  resetQueryBatchResults();
  document.getElementById("downloadCsv").disabled = true;
  document.getElementById("resultsTable").innerHTML = '<div class="empty-results">Run a query to see results.</div>';
}

function renderQueryTabs() {
  const tabbar = document.getElementById("queryTabBar");
  if (!tabbar) return;
  const active = activeQueryTab();
  if (active && activeQueryTabId !== active.id) activeQueryTabId = active.id;
  const tabsMarkup = (queryTabs.length ? queryTabs : [{ id: "local", name: "query-1.sql", is_active: true }])
    .map(
      (tab) => `
        <div class="code-tab ${activeQueryTabId === tab.id || tab.id === "local" ? "active" : ""}" role="presentation" data-query-tab-shell-id="${escapeHtml(tab.id)}" draggable="${tab.id === "local" ? "false" : "true"}">
          <button type="button" role="tab" data-query-tab-id="${escapeHtml(tab.id)}" title="Double-click to rename">
            <span class="dot"></span>
            <span class="code-tab-name">${escapeHtml(tab.name)}</span>
          </button>
          ${
            tab.id === "local"
              ? ""
              : `<button class="code-tab-close" type="button" data-close-query-tab-id="${escapeHtml(tab.id)}" title="Close tab" aria-label="Close ${escapeHtml(tab.name)}">&times;</button>`
          }
        </div>
      `
    )
    .join("");
  tabbar.innerHTML = `${tabsMarkup}
    <button class="code-tab-add" id="addQueryTab" type="button" title="New query tab" aria-label="New query tab">
      <span data-icon="plus"></span>
    </button>`;
  replaceIcons();
  tabbar.querySelectorAll("[data-query-tab-id]").forEach((button) => {
    button.addEventListener("click", () => selectQueryTab(button.dataset.queryTabId));
    button.addEventListener("dblclick", () => renameQueryTab(button.dataset.queryTabId));
  });
  tabbar.querySelectorAll("[data-close-query-tab-id]").forEach((button) => {
    button.addEventListener("click", (event) => {
      event.stopPropagation();
      closeQueryTab(button.dataset.closeQueryTabId);
    });
  });
  tabbar.querySelectorAll("[data-query-tab-shell-id]").forEach((tabNode) => {
    if (tabNode.dataset.queryTabShellId === "local") return;
    tabNode.addEventListener("dragstart", (event) => {
      draggedQueryTabId = Number(tabNode.dataset.queryTabShellId);
      tabNode.classList.add("dragging");
      event.dataTransfer.effectAllowed = "move";
      event.dataTransfer.setData("text/plain", String(draggedQueryTabId));
    });
    tabNode.addEventListener("dragover", (event) => {
      event.preventDefault();
      if (Number(tabNode.dataset.queryTabShellId) !== draggedQueryTabId) {
        tabNode.classList.add("drag-over");
      }
    });
    tabNode.addEventListener("dragleave", () => {
      tabNode.classList.remove("drag-over");
    });
    tabNode.addEventListener("drop", (event) => {
      event.preventDefault();
      tabNode.classList.remove("drag-over");
      reorderQueryTabs(draggedQueryTabId, Number(tabNode.dataset.queryTabShellId));
    });
    tabNode.addEventListener("dragend", () => {
      draggedQueryTabId = null;
      tabbar.querySelectorAll(".code-tab").forEach((node) => {
        node.classList.remove("dragging", "drag-over");
      });
    });
  });
  const add = document.getElementById("addQueryTab");
  if (add) add.addEventListener("click", createQueryTab);
}

function reorderQueryTabs(sourceId, targetId) {
  if (!sourceId || !targetId || sourceId === targetId) return;
  const sourceIndex = queryTabs.findIndex((tab) => tab.id === sourceId);
  const targetIndex = queryTabs.findIndex((tab) => tab.id === targetId);
  if (sourceIndex < 0 || targetIndex < 0) return;
  const [moved] = queryTabs.splice(sourceIndex, 1);
  queryTabs.splice(targetIndex, 0, moved);
  renderQueryTabs();
  persistQueryTabPositions();
}

async function persistQueryTabPositions() {
  const changed = [];
  queryTabs.forEach((tab, index) => {
    if (tab.position !== index) {
      tab.position = index;
      changed.push(tab);
    }
  });
  if (!changed.length) return;
  try {
    await Promise.all(
      changed.map((tab) =>
        apiRequest(`/api/query-tabs/${tab.id}`, {
          method: "PATCH",
          body: JSON.stringify({ position: tab.position })
        })
      )
    );
  } catch (error) {
    showToast(error.message, { type: "error" });
    loadQueryTabsFromApi();
  }
}

async function loadQueryTabsFromApi() {
  if (!currentUser) return;
  try {
    const result = await apiRequest("/api/query-tabs");
    queryTabs.splice.apply(queryTabs, [0, queryTabs.length].concat(result.tabs || []));
    const active = activeQueryTab();
    activeQueryTabId = active ? active.id : null;
    renderQueryTabs();
    applyQueryTabToEditor(active);
  } catch (error) {
    if (!/Authentication required/.test(error.message)) {
      showToast(error.message, { type: "error" });
    }
  }
}

async function saveActiveQueryTabNow(payload = null) {
  const tab = activeQueryTab();
  if (!tab || tab.id === "local" || !currentUser) return null;
  const body = payload || queryTabPayloadFromEditor();
  try {
    const result = await apiRequest(`/api/query-tabs/${tab.id}`, {
      method: "PATCH",
      body: JSON.stringify(body)
    });
    Object.assign(tab, result.tab);
    return result.tab;
  } catch (error) {
    showToast(error.message, { type: "error" });
    return null;
  }
}

function scheduleSaveActiveQueryTab() {
  if (suppressQueryTabAutosave) return;
  updateActiveQueryTabFromEditor();
  window.clearTimeout(queryTabSaveTimer);
  queryTabSaveTimer = window.setTimeout(() => {
    saveActiveQueryTabNow();
  }, 600);
}

async function selectQueryTab(rawId) {
  const id = Number(rawId);
  const tab = queryTabs.find((item) => item.id === id);
  if (!tab || tab.id === activeQueryTabId) return;
  window.clearTimeout(queryTabSaveTimer);
  await saveActiveQueryTabNow();
  queryTabs.forEach((item) => {
    item.is_active = item.id === id;
  });
  activeQueryTabId = id;
  renderQueryTabs();
  applyQueryTabToEditor(tab);
  saveActiveQueryTabNow({ is_active: true });
}

async function createQueryTab() {
  if (!currentUser) return;
  window.clearTimeout(queryTabSaveTimer);
  await saveActiveQueryTabNow();
  const nextNumber = queryTabs.length + 1;
  try {
    const result = await apiRequest("/api/query-tabs", {
      method: "POST",
      body: JSON.stringify({
        name: `query-${nextNumber}.sql`,
        sql: "",
        cluster_id: normalizedQueryClusterId(),
        catalog: document.getElementById("queryCatalog").value,
        schema: document.getElementById("querySchema").value,
        run_mode: currentRunMode,
        is_active: true
      })
    });
    queryTabs.forEach((tab) => {
      tab.is_active = false;
    });
    queryTabs.push(result.tab);
    activeQueryTabId = result.tab.id;
    renderQueryTabs();
    applyQueryTabToEditor(result.tab);
  } catch (error) {
    showToast(error.message, { type: "error" });
  }
}

async function renameQueryTab(rawId) {
  const id = Number(rawId);
  const tab = queryTabs.find((item) => item.id === id);
  if (!tab) return;
  const name = await appPrompt({
    title: "Rename tab",
    label: "Tab name",
    value: tab.name,
  });
  if (name === null) return;
  const trimmed = name.trim();
  if (!trimmed) {
    showToast("Tab name is required.");
    return;
  }
  try {
    const result = await apiRequest(`/api/query-tabs/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ name: trimmed })
    });
    Object.assign(tab, result.tab);
    renderQueryTabs();
  } catch (error) {
    showToast(error.message, { type: "error" });
  }
}

async function closeQueryTab(rawId) {
  const id = Number(rawId);
  const tab = queryTabs.find((item) => item.id === id);
  if (!tab) return;
  try {
    const result = await apiRequest(`/api/query-tabs/${id}`, {
      method: "DELETE",
      body: JSON.stringify({})
    });
    queryTabs.splice.apply(queryTabs, [0, queryTabs.length].concat(result.tabs || []));
    const active = activeQueryTab();
    activeQueryTabId = active ? active.id : null;
    renderQueryTabs();
    applyQueryTabToEditor(active);
  } catch (error) {
    showToast(error.message, { type: "error" });
  }
}

const SQL_KEYWORDS = new Set(
  [
    "all",
    "alter",
    "and",
    "as",
    "asc",
    "between",
    "by",
    "case",
    "cast",
    "create",
    "cross",
    "delete",
    "desc",
    "describe",
    "distinct",
    "drop",
    "else",
    "end",
    "except",
    "exists",
    "explain",
    "false",
    "from",
    "full",
    "group",
    "having",
    "if",
    "in",
    "inner",
    "insert",
    "intersect",
    "into",
    "is",
    "join",
    "left",
    "like",
    "limit",
    "not",
    "null",
    "on",
    "or",
    "order",
    "outer",
    "right",
    "select",
    "set",
    "show",
    "table",
    "then",
    "true",
    "union",
    "update",
    "use",
    "values",
    "when",
    "where",
    "with"
  ]
);

const SQL_FUNCTIONS = new Set([
  "avg",
  "coalesce",
  "count",
  "date_trunc",
  "format",
  "json_extract",
  "lower",
  "max",
  "min",
  "regexp_like",
  "sum",
  "try",
  "upper"
]);

const SQL_TOKEN_PATTERN =
  /(--[^\n]*|\/\*[\s\S]*?\*\/|'(?:''|[^'])*'|"(?:\"\"|[^"])*"|\b\d+(?:\.\d+)?\b|\b[A-Za-z_][A-Za-z0-9_]*\b|\s+|.)/g;

function sqlTokenClass(token) {
  if (/^--/.test(token) || /^\/\*/.test(token)) return "sql-token-comment";
  if (/^'/.test(token)) return "sql-token-string";
  if (/^"/.test(token)) return "sql-token-identifier";
  if (/^\d/.test(token)) return "sql-token-number";
  if (/^[A-Za-z_]/.test(token)) {
    const lowered = token.toLowerCase();
    if (SQL_KEYWORDS.has(lowered)) return "sql-token-keyword";
    if (SQL_FUNCTIONS.has(lowered)) return "sql-token-function";
  }
  return "";
}

function findSqlSearchMatches(sql, query) {
  if (!query) return [];
  const matches = [];
  const haystack = sql.toLowerCase();
  const needle = query.toLowerCase();
  let index = haystack.indexOf(needle);
  while (index !== -1) {
    matches.push({ start: index, end: index + query.length });
    index = haystack.indexOf(needle, index + Math.max(1, query.length));
  }
  return matches;
}

function renderSqlSearchCounter() {
  const count = document.getElementById("sqlSearchCount");
  if (!count) return;
  const total = sqlSearchState.matches.length;
  count.textContent = total ? `${sqlSearchState.activeIndex + 1} of ${total}` : "0 of 0";
  ["sqlSearchPrev", "sqlSearchNext", "sqlReplaceOne", "sqlReplaceAll"].forEach((id) => {
    const button = document.getElementById(id);
    if (button) button.disabled = !total;
  });
}

function syncSqlSearchState(sql) {
  const bar = document.getElementById("sqlSearchBar");
  const input = document.getElementById("sqlSearchInput");
  const query = bar && !bar.hidden && input ? input.value : "";
  const queryChanged = query !== sqlSearchState.query;
  sqlSearchState.query = query;
  sqlSearchState.matches = findSqlSearchMatches(sql, query);
  if (!sqlSearchState.matches.length) {
    sqlSearchState.activeIndex = -1;
  } else if (queryChanged || sqlSearchState.activeIndex < 0) {
    sqlSearchState.activeIndex = 0;
  } else if (sqlSearchState.activeIndex >= sqlSearchState.matches.length) {
    sqlSearchState.activeIndex = sqlSearchState.matches.length - 1;
  }
  renderSqlSearchCounter();
}

function sqlBracketPositions(sql) {
  const positions = [];
  let state = "normal";
  for (let index = 0; index < sql.length; index += 1) {
    const char = sql[index];
    const next = sql[index + 1];

    if (state === "line-comment") {
      if (char === "\n") state = "normal";
      continue;
    }
    if (state === "block-comment") {
      if (char === "*" && next === "/") {
        state = "normal";
        index += 1;
      }
      continue;
    }
    if (state === "single-quote") {
      if (char === "'" && next === "'") {
        index += 1;
      } else if (char === "'") {
        state = "normal";
      }
      continue;
    }
    if (state === "double-quote") {
      if (char === '"' && next === '"') {
        index += 1;
      } else if (char === '"') {
        state = "normal";
      }
      continue;
    }

    if (char === "-" && next === "-") {
      state = "line-comment";
      index += 1;
    } else if (char === "/" && next === "*") {
      state = "block-comment";
      index += 1;
    } else if (char === "'") {
      state = "single-quote";
    } else if (char === '"') {
      state = "double-quote";
    } else if ("()[]{}".includes(char)) {
      positions.push({ index, char });
    }
  }
  return positions;
}

function findSqlBracketMatch(sql, caret) {
  const pairs = { "(": ")", "[": "]", "{": "}" };
  const reversePairs = { ")": "(", "]": "[", "}": "{" };
  const positions = sqlBracketPositions(sql);
  const byIndex = new Map(positions.map((item) => [item.index, item.char]));
  const candidates = [caret - 1, caret].filter((index) => byIndex.has(index));
  if (!candidates.length) return [];
  const anchor = candidates[0];
  const char = byIndex.get(anchor);

  if (pairs[char]) {
    let depth = 0;
    for (const item of positions) {
      if (item.index < anchor) continue;
      if (item.char === char) depth += 1;
      if (item.char === pairs[char]) depth -= 1;
      if (depth === 0) return [anchor, item.index];
    }
    return [anchor];
  }

  if (reversePairs[char]) {
    const open = reversePairs[char];
    let depth = 0;
    for (let index = positions.length - 1; index >= 0; index -= 1) {
      const item = positions[index];
      if (item.index > anchor) continue;
      if (item.char === char) depth += 1;
      if (item.char === open) depth -= 1;
      if (depth === 0) return [item.index, anchor];
    }
    return [anchor];
  }
  return [];
}

function sqlHighlightDecorations(sql, editor) {
  syncSqlSearchState(sql);
  const decorations = [];
  sqlSearchState.matches.forEach((match, index) => {
    decorations.push({
      start: match.start,
      end: match.end,
      className: index === sqlSearchState.activeIndex ? "sql-token-search sql-token-search-active" : "sql-token-search"
    });
  });

  if (editor && editor.selectionStart === editor.selectionEnd) {
    const bracketPositions = findSqlBracketMatch(sql, editor.selectionStart || 0);
    if (bracketPositions.length === 2) {
      bracketPositions.forEach((position) => {
        decorations.push({ start: position, end: position + 1, className: "sql-token-bracket-match" });
      });
    } else if (bracketPositions.length === 1) {
      decorations.push({ start: bracketPositions[0], end: bracketPositions[0] + 1, className: "sql-token-bracket-unmatched" });
    }
  }
  return decorations;
}

function decoratedSqlTokenHtml(token, start, decorations) {
  const end = start + token.length;
  const tokenClass = sqlTokenClass(token);
  const boundaries = new Set([0, token.length]);
  decorations.forEach((decoration) => {
    if (decoration.start < end && decoration.end > start) {
      boundaries.add(Math.max(0, decoration.start - start));
      boundaries.add(Math.min(token.length, decoration.end - start));
    }
  });
  const points = Array.from(boundaries).sort((left, right) => left - right);
  return points
    .slice(0, -1)
    .map((point, index) => {
      const next = points[index + 1];
      const text = token.slice(point, next);
      if (!text) return "";
      const pieceStart = start + point;
      const pieceEnd = start + next;
      const classes = [];
      if (tokenClass) classes.push(tokenClass);
      decorations.forEach((decoration) => {
        if (decoration.start < pieceEnd && decoration.end > pieceStart) classes.push(decoration.className);
      });
      return classes.length ? `<span class="${classes.join(" ")}">${escapeHtml(text)}</span>` : escapeHtml(text);
    })
    .join("");
}

function highlightSql(sql, decorations = []) {
  const text = sql || "";
  SQL_TOKEN_PATTERN.lastIndex = 0;
  let html = "";
  let match = SQL_TOKEN_PATTERN.exec(text);
  while (match) {
    html += decoratedSqlTokenHtml(match[0], match.index, decorations);
    match = SQL_TOKEN_PATTERN.exec(text);
  }
  return html.replace(/\n$/, "\n ");
}

function renderSqlLineNumbers(sql) {
  const lineNumbers = document.getElementById("sqlLineNumbers");
  if (!lineNumbers) return;
  const count = Math.max(1, String(sql || "").split("\n").length);
  lineNumbers.textContent = Array.from({ length: count }, (_, index) => String(index + 1)).join("\n");
}

function renderSqlHighlight() {
  const editor = document.getElementById("sqlText");
  const highlight = document.getElementById("sqlHighlight");
  if (!editor || !highlight) return;
  renderSqlLineNumbers(editor.value);
  highlight.innerHTML = highlightSql(editor.value, sqlHighlightDecorations(editor.value, editor));
  syncSqlHighlightScroll();
}

function syncSqlHighlightScroll() {
  const editor = document.getElementById("sqlText");
  const highlight = document.getElementById("sqlHighlight");
  const lineNumbers = document.getElementById("sqlLineNumbers");
  if (!editor || !highlight) return;
  highlight.scrollTop = editor.scrollTop;
  highlight.scrollLeft = editor.scrollLeft;
  if (lineNumbers) lineNumbers.scrollTop = editor.scrollTop;
  positionSqlAutocomplete();
}

function insertEditorText(text) {
  const editor = document.getElementById("sqlText");
  if (!editor) return;
  insertAtCursor(editor, text);
  renderSqlHighlight();
  scheduleSaveActiveQueryTab();
}

function openSqlSearch() {
  const bar = document.getElementById("sqlSearchBar");
  const input = document.getElementById("sqlSearchInput");
  const editor = document.getElementById("sqlText");
  if (!bar || !input) return;
  bar.hidden = false;
  replaceIcons();
  if (editor && editor.selectionStart !== editor.selectionEnd) {
    input.value = editor.value.slice(editor.selectionStart, editor.selectionEnd);
  }
  input.focus();
  input.select();
  renderSqlHighlight();
}

function closeSqlSearch() {
  const bar = document.getElementById("sqlSearchBar");
  if (!bar) return;
  bar.hidden = true;
  sqlSearchState.query = "";
  sqlSearchState.matches = [];
  sqlSearchState.activeIndex = -1;
  renderSqlHighlight();
  const editor = document.getElementById("sqlText");
  if (editor) editor.focus();
}

function goToSqlSearchMatch(delta) {
  const editor = document.getElementById("sqlText");
  if (!editor) return;
  renderSqlHighlight();
  if (!sqlSearchState.matches.length) return;
  sqlSearchState.activeIndex =
    (sqlSearchState.activeIndex + delta + sqlSearchState.matches.length) % sqlSearchState.matches.length;
  const match = sqlSearchState.matches[sqlSearchState.activeIndex];
  editor.focus();
  editor.setSelectionRange(match.start, match.end);
  renderSqlHighlight();
}

function replaceCurrentSqlMatch() {
  const editor = document.getElementById("sqlText");
  const replacement = document.getElementById("sqlReplaceInput");
  if (!editor || !replacement) return;
  renderSqlHighlight();
  if (!sqlSearchState.matches.length) return;
  const match = sqlSearchState.matches[sqlSearchState.activeIndex];
  editor.value = editor.value.slice(0, match.start) + replacement.value + editor.value.slice(match.end);
  const caret = match.start + replacement.value.length;
  editor.setSelectionRange(caret, caret);
  renderSqlHighlight();
  scheduleSaveActiveQueryTab();
}

function replaceAllSqlMatches() {
  const editor = document.getElementById("sqlText");
  const replacement = document.getElementById("sqlReplaceInput");
  if (!editor || !replacement) return;
  renderSqlHighlight();
  if (!sqlSearchState.matches.length) return;
  let nextValue = editor.value;
  sqlSearchState.matches
    .slice()
    .reverse()
    .forEach((match) => {
      nextValue = nextValue.slice(0, match.start) + replacement.value + nextValue.slice(match.end);
    });
  editor.value = nextValue;
  editor.setSelectionRange(0, 0);
  renderSqlHighlight();
  scheduleSaveActiveQueryTab();
  showToast("Replaced all matches.");
}

function protectSqlSegments(sql) {
  const values = [];
  const work = String(sql || "").replace(/(--[^\n]*|\/\*[\s\S]*?\*\/|'(?:''|[^'])*'|"(?:\"\"|[^"])*")/g, (match) => {
    const key = `__SQL_PLACEHOLDER_${values.length}__`;
    values.push(match);
    return key;
  });
  return { work, values };
}

function restoreSqlSegments(sql, values) {
  return values.reduce((text, value, index) => text.split(`__SQL_PLACEHOLDER_${index}__`).join(value), sql);
}

function formatSqlText(sql) {
  const protectedSql = protectSqlSegments(sql);
  let work = protectedSql.work.trim().replace(/\s+/g, " ");
  if (!work) return "";
  const keywords = Array.from(SQL_KEYWORDS).sort((left, right) => right.length - left.length).join("|");
  work = work.replace(new RegExp(`\\b(${keywords})\\b`, "gi"), (match) => match.toUpperCase());
  work = work
    .replace(/\s*,\s*/g, ", ")
    .replace(/\s*;\s*/g, ";\n")
    .replace(/\s+(FROM|WHERE|GROUP BY|HAVING|ORDER BY|LIMIT|UNION|EXCEPT|INTERSECT|VALUES)\b/g, "\n$1")
    .replace(/\s+((?:LEFT|RIGHT|FULL|INNER|CROSS)\s+JOIN|JOIN)\b/g, "\n$1")
    .replace(/\s+(AND|OR)\b/g, "\n  $1");
  work = work
    .split("\n")
    .map((line) => line.trimEnd())
    .join("\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
  return restoreSqlSegments(work, protectedSql.values);
}

function formatSqlEditor() {
  const editor = document.getElementById("sqlText");
  if (!editor) return;
  const start = editor.selectionStart || 0;
  const end = editor.selectionEnd || 0;
  if (end > start) {
    const formatted = formatSqlText(editor.value.slice(start, end));
    editor.value = editor.value.slice(0, start) + formatted + editor.value.slice(end);
    editor.setSelectionRange(start, start + formatted.length);
  } else {
    const formatted = formatSqlText(editor.value);
    editor.value = formatted;
    editor.setSelectionRange(Math.min(start, formatted.length), Math.min(start, formatted.length));
  }
  renderSqlHighlight();
  scheduleSaveActiveQueryTab();
  showToast("SQL formatted.");
}

function activeSchemaTableParts() {
  if (!schemaBrowserState.activeTable) return null;
  const parts = schemaBrowserState.activeTable.split("\u001f");
  if (parts.length < 3) return null;
  return { catalog: parts[0], schema: parts[1], table: parts[2] };
}

function commandPaletteCommands() {
  const table = activeSchemaTableParts();
  const commands = [
    {
      id: "run-current",
      title: "Run current statement",
      description: "Switch to current statement mode and execute.",
      group: "Run",
      action: () => {
        applyRunMode("current", { save: true });
        document.getElementById("runQuery").click();
      }
    },
    {
      id: "run-selected",
      title: "Run selected SQL",
      description: "Switch to selected SQL mode and execute the selection.",
      group: "Run",
      action: () => {
        applyRunMode("selected", { save: true });
        document.getElementById("runQuery").click();
      }
    },
    {
      id: "run-all",
      title: "Run all statements",
      description: "Execute every statement in the active tab.",
      group: "Run",
      action: () => {
        applyRunMode("all", { save: true });
        document.getElementById("runQuery").click();
      }
    },
    {
      id: "run-csv",
      title: "Run and download CSV",
      description: "Execute and prepare a CSV download from the active result.",
      group: "Run",
      action: () => document.getElementById("runAndDownload").click()
    },
    {
      id: "format",
      title: "Format SQL",
      description: "Apply TrinoHub's SQL formatter to the editor or selection.",
      group: "Edit",
      action: formatSqlEditor
    },
    {
      id: "find",
      title: "Find and replace",
      description: "Open the editor search and replace bar.",
      group: "Edit",
      action: openSqlSearch
    },
    {
      id: "new-tab",
      title: "New query tab",
      description: "Create a blank query tab using the current context.",
      group: "Tabs",
      action: createQueryTab
    },
    {
      id: "save-query",
      title: "Save active query",
      description: "Store the active SQL in your saved query library.",
      group: "Saved",
      action: saveCurrentQuery
    },
    {
      id: "download",
      title: "Download active result CSV",
      description: "Download CSV for the currently selected result.",
      group: "Results",
      action: () => downloadReadyResult(activeQueryResult)
    }
  ];

  if (table) {
    commands.push(
      {
        id: "insert-select-active",
        title: "Insert SELECT for active table",
        description: `${table.catalog}.${table.schema}.${table.table}`,
        group: "Schema",
        action: () => insertSchemaAction("insert-select", table.catalog, table.schema, table.table)
      },
      {
        id: "insert-describe-active",
        title: "Insert DESCRIBE for active table",
        description: `${table.catalog}.${table.schema}.${table.table}`,
        group: "Schema",
        action: () => insertSchemaAction("insert-describe", table.catalog, table.schema, table.table)
      },
      {
        id: "insert-show-create-active",
        title: "Insert SHOW CREATE TABLE",
        description: `${table.catalog}.${table.schema}.${table.table}`,
        group: "Schema",
        action: () => insertSchemaAction("insert-show-create", table.catalog, table.schema, table.table)
      }
    );
  }

  return commands;
}

function filteredCommandPaletteCommands() {
  const query = commandPaletteState.query.trim().toLowerCase();
  const commands = commandPaletteCommands();
  if (!query) return commands;
  return commands.filter((command) =>
    `${command.title} ${command.description} ${command.group}`.toLowerCase().includes(query)
  );
}

function renderCommandPalette() {
  const list = document.getElementById("commandList");
  if (!list) return;
  const commands = filteredCommandPaletteCommands();
  commandPaletteState.commands = commands;
  if (commandPaletteState.activeIndex >= commands.length) commandPaletteState.activeIndex = Math.max(0, commands.length - 1);
  list.innerHTML = commands.length
    ? commands
        .map(
          (command, index) => `
            <button type="button" class="command-item ${index === commandPaletteState.activeIndex ? "active" : ""}" data-command-index="${index}" role="option" aria-selected="${index === commandPaletteState.activeIndex ? "true" : "false"}">
              <span>
                <strong>${escapeHtml(command.title)}</strong>
                <span>${escapeHtml(command.description)}</span>
              </span>
              <small>${escapeHtml(command.group)}</small>
            </button>
          `
        )
        .join("")
    : '<div class="schema-empty">No matching commands.</div>';
  list.querySelectorAll("[data-command-index]").forEach((button) => {
    button.addEventListener("click", () => runCommandPaletteCommand(Number(button.dataset.commandIndex)));
  });
}

function openCommandPalette() {
  const palette = document.getElementById("commandPalette");
  const search = document.getElementById("commandSearch");
  if (!palette || !search) return;
  commandPaletteState.open = true;
  commandPaletteState.query = "";
  commandPaletteState.activeIndex = 0;
  search.value = "";
  palette.hidden = false;
  renderCommandPalette();
  replaceIcons();
  search.focus();
}

function closeCommandPalette() {
  const palette = document.getElementById("commandPalette");
  if (!palette) return;
  palette.hidden = true;
  commandPaletteState.open = false;
  const editor = document.getElementById("sqlText");
  if (editor) editor.focus();
}

function moveCommandPalette(delta) {
  const total = commandPaletteState.commands.length;
  if (!total) return;
  commandPaletteState.activeIndex = (commandPaletteState.activeIndex + delta + total) % total;
  renderCommandPalette();
}

function runCommandPaletteCommand(index = commandPaletteState.activeIndex) {
  const command = commandPaletteState.commands[index];
  if (!command) return;
  closeCommandPalette();
  command.action();
}

function trimStatement(raw, start) {
  const leading = raw.match(/^\s*/)[0].length;
  const trailing = raw.match(/\s*$/)[0].length;
  const end = start + raw.length - trailing;
  const trimmedStart = start + leading;
  if (trimmedStart >= end) return null;
  return {
    sql: raw.slice(leading, raw.length - trailing),
    start: trimmedStart,
    end
  };
}

function splitSqlStatements(sql) {
  const statements = [];
  let statementStart = 0;
  let state = "normal";

  for (let index = 0; index < sql.length; index += 1) {
    const char = sql[index];
    const next = sql[index + 1];

    if (state === "line-comment") {
      if (char === "\n") state = "normal";
      continue;
    }
    if (state === "block-comment") {
      if (char === "*" && next === "/") {
        state = "normal";
        index += 1;
      }
      continue;
    }
    if (state === "single-quote") {
      if (char === "'" && next === "'") {
        index += 1;
      } else if (char === "'") {
        state = "normal";
      }
      continue;
    }
    if (state === "double-quote") {
      if (char === '"' && next === '"') {
        index += 1;
      } else if (char === '"') {
        state = "normal";
      }
      continue;
    }

    if (char === "-" && next === "-") {
      state = "line-comment";
      index += 1;
    } else if (char === "/" && next === "*") {
      state = "block-comment";
      index += 1;
    } else if (char === "'") {
      state = "single-quote";
    } else if (char === '"') {
      state = "double-quote";
    } else if (char === ";") {
      const statement = trimStatement(sql.slice(statementStart, index), statementStart);
      if (statement) statements.push(statement);
      statementStart = index + 1;
    }
  }

  const last = trimStatement(sql.slice(statementStart), statementStart);
  if (last) statements.push(last);
  return statements;
}

function currentSqlStatement(editor) {
  const statements = splitSqlStatements(editor.value);
  if (!statements.length) return null;
  const cursor = editor.selectionStart || 0;
  const containing = statements.find((statement) => cursor >= statement.start && cursor <= statement.end);
  if (containing) return containing;
  for (let index = statements.length - 1; index >= 0; index -= 1) {
    if (statements[index].end <= cursor) return statements[index];
  }
  return statements[0];
}

function selectedEditorSql(editor) {
  const start = editor.selectionStart || 0;
  const end = editor.selectionEnd || 0;
  if (end <= start) return "";
  return editor.value.slice(start, end).trim();
}

function sqlStatementsForRunMode(editor) {
  if (currentRunMode === "selected") {
    const selected = selectedEditorSql(editor);
    return selected ? [{ sql: selected, label: "selected SQL" }] : [];
  }
  if (currentRunMode === "all") {
    return splitSqlStatements(editor.value).map((statement, index) => ({
      sql: statement.sql,
      label: `statement ${index + 1}`
    }));
  }
  const current = currentSqlStatement(editor);
  return current ? [{ sql: current.sql, label: "current statement" }] : [];
}

function applyRunMode(mode, options = {}) {
  currentRunMode = ["current", "selected", "all"].includes(mode) ? mode : "current";
  document.querySelectorAll("[data-run-mode]").forEach((button) => {
    button.classList.toggle("active", button.dataset.runMode === currentRunMode);
  });
  if (options.save) scheduleSaveActiveQueryTab();
}

function completionContext(editor) {
  const caret = editor.selectionStart || 0;
  const before = editor.value.slice(0, caret);
  let start = before.length;
  while (start > 0 && /[A-Za-z0-9_.$"]/.test(before[start - 1])) {
    start -= 1;
  }
  const raw = before.slice(start);
  const parts = raw.split(".");
  const rawPrefix = parts.pop() || "";
  return {
    parts: parts.map(unquoteIdentifier).filter(Boolean),
    prefix: unquoteIdentifier(rawPrefix),
    rangeStart: caret - rawPrefix.length,
    rangeEnd: caret
  };
}

function unquoteIdentifier(value) {
  const text = String(value || "");
  if (text.length >= 2 && text.startsWith('"') && text.endsWith('"')) {
    return text.slice(1, -1).replace(/""/g, '"');
  }
  return text.replace(/^"/, "").replace(/"$/, "");
}

function knownCatalogNames() {
  const cluster = selectedQueryCluster();
  if (cluster && Array.isArray(cluster.catalogList)) return cluster.catalogList;
  return catalogRecords.filter((catalog) => catalog.enabled).map((catalog) => catalog.name);
}

function autocompleteItemsForContext(context) {
  const prefix = context.prefix.toLowerCase();
  const items = [];
  const seen = new Set();

  function add(label, type, insert = label) {
    if (!label) return;
    const key = `${type}:${String(label).toLowerCase()}`;
    if (seen.has(key)) return;
    if (prefix && !String(label).toLowerCase().startsWith(prefix)) return;
    seen.add(key);
    items.push({ label: String(label), type, insert: String(insert) });
  }

  if (context.parts.length === 0) {
    Array.from(SQL_KEYWORDS).sort().forEach((keyword) => add(keyword.toUpperCase(), "keyword", keyword.toUpperCase()));
    Array.from(SQL_FUNCTIONS).sort().forEach((fn) => add(fn, "function"));
    knownCatalogNames().forEach((catalog) => add(catalog, "catalog"));
  } else if (context.parts.length === 1) {
    const schemas = schemaBrowserState.schemasByCatalog[context.parts[0]] || [];
    schemas.forEach((schema) => add(schema.name, "schema"));
  } else if (context.parts.length === 2) {
    const key = schemaBrowserKey(context.parts[0], context.parts[1]);
    const tables = schemaBrowserState.tablesBySchema[key] || [];
    tables.forEach((table) => add(table.name, String(table.type || "table").toLowerCase().includes("view") ? "view" : "table"));
  } else {
    const key = schemaBrowserKey(context.parts[0], context.parts[1], context.parts[2]);
    const columns = schemaBrowserState.columnsByTable[key] || [];
    columns.forEach((column) => add(column.name, column.type || "column"));
  }

  return items.slice(0, 12);
}

async function ensureAutocompleteMetadata(context) {
  const cluster = selectedQueryCluster();
  // Suspended clusters still complete from the server-side metadata cache,
  // which /api/clusters/{id}/metadata serves when no coordinator is live.
  if (!cluster) return;
  if (context.parts.length === 1) {
    const catalog = context.parts[0];
    if (!knownCatalogNames().includes(catalog) || schemaBrowserState.schemasByCatalog[catalog]) return;
    const result = await loadClusterMetadata(sqlSchemaBrowser, { catalog });
    schemaBrowserState.schemasByCatalog[catalog] = result.schemas || [];
  } else if (context.parts.length === 2) {
    const [catalog, schema] = context.parts;
    const key = schemaBrowserKey(catalog, schema);
    if (schemaBrowserState.tablesBySchema[key]) return;
    const result = await loadClusterMetadata(sqlSchemaBrowser, { catalog, schema });
    schemaBrowserState.tablesBySchema[key] = result.tables || [];
  } else if (context.parts.length >= 3) {
    const [catalog, schema, table] = context.parts;
    const key = schemaBrowserKey(catalog, schema, table);
    if (schemaBrowserState.columnsByTable[key]) return;
    const result = await loadClusterMetadata(sqlSchemaBrowser, { catalog, schema, table });
    schemaBrowserState.columnsByTable[key] = result.columns || [];
  }
}

let autocompleteRequestId = 0;

async function refreshSqlAutocomplete(options = {}) {
  const editor = document.getElementById("sqlText");
  if (!editor) return;
  const context = completionContext(editor);
  const shouldOpen = options.force || context.parts.length > 0 || context.prefix.length >= 2;
  if (!shouldOpen) {
    closeSqlAutocomplete();
    return;
  }

  const requestId = (autocompleteRequestId += 1);
  autocompleteState.rangeStart = context.rangeStart;
  autocompleteState.rangeEnd = context.rangeEnd;
  autocompleteState.items = autocompleteItemsForContext(context);
  autocompleteState.activeIndex = 0;
  renderSqlAutocomplete();

  try {
    await ensureAutocompleteMetadata(context);
  } catch (error) {
    return;
  }
  if (requestId !== autocompleteRequestId) return;
  autocompleteState.items = autocompleteItemsForContext(context);
  autocompleteState.activeIndex = 0;
  renderSqlAutocomplete();
}

function closeSqlAutocomplete(options = {}) {
  if (!options.keepRequest) autocompleteRequestId += 1;
  autocompleteState.open = false;
  autocompleteState.items = [];
  const popup = document.getElementById("sqlAutocomplete");
  if (popup) popup.hidden = true;
}

function renderSqlAutocomplete() {
  const popup = document.getElementById("sqlAutocomplete");
  const editor = document.getElementById("sqlText");
  if (!popup || !editor || !autocompleteState.items.length) {
    closeSqlAutocomplete({ keepRequest: true });
    return;
  }
  autocompleteState.open = true;
  popup.hidden = false;
  popup.innerHTML = autocompleteState.items
    .map(
      (item, index) => `
        <button type="button" class="${index === autocompleteState.activeIndex ? "active" : ""}" data-autocomplete-index="${index}">
          <strong>${escapeHtml(item.label)}</strong>
          <small>${escapeHtml(item.type)}</small>
        </button>
      `
    )
    .join("");
  popup.querySelectorAll("[data-autocomplete-index]").forEach((button) => {
    button.addEventListener("mousedown", (event) => {
      event.preventDefault();
      acceptSqlAutocomplete(Number(button.dataset.autocompleteIndex));
    });
  });
  positionSqlAutocomplete();
}

function positionSqlAutocomplete() {
  const popup = document.getElementById("sqlAutocomplete");
  const editor = document.getElementById("sqlText");
  const shell = popup ? popup.closest(".sql-editor-shell") : null;
  if (!popup || !editor || !shell || popup.hidden) return;
  const before = editor.value.slice(0, editor.selectionStart || 0);
  const lines = before.split("\n");
  const line = lines.length - 1;
  const column = lines[lines.length - 1].length;
  const style = window.getComputedStyle(editor);
  const lineHeight = Number.parseFloat(style.lineHeight) || 22;
  const fontSize = Number.parseFloat(style.fontSize) || 14;
  const paddingTop = Number.parseFloat(style.paddingTop) || 14;
  const paddingLeft = Number.parseFloat(style.paddingLeft) || 16;
  const top = paddingTop + line * lineHeight - editor.scrollTop + lineHeight + 4;
  const left = paddingLeft + column * fontSize * 0.58 - editor.scrollLeft;
  popup.style.top = `${Math.min(Math.max(8, top), Math.max(8, shell.clientHeight - 56))}px`;
  popup.style.left = `${Math.min(Math.max(8, left), Math.max(8, shell.clientWidth - 336))}px`;
}

function moveSqlAutocomplete(delta) {
  if (!autocompleteState.open || !autocompleteState.items.length) return;
  const next = autocompleteState.activeIndex + delta;
  autocompleteState.activeIndex = (next + autocompleteState.items.length) % autocompleteState.items.length;
  renderSqlAutocomplete();
}

function acceptSqlAutocomplete(index = autocompleteState.activeIndex) {
  const editor = document.getElementById("sqlText");
  const item = autocompleteState.items[index];
  if (!editor || !item) return;
  editor.value =
    editor.value.slice(0, autocompleteState.rangeStart) + item.insert + editor.value.slice(autocompleteState.rangeEnd);
  const caret = autocompleteState.rangeStart + item.insert.length;
  editor.selectionStart = caret;
  editor.selectionEnd = caret;
  closeSqlAutocomplete();
  renderSqlHighlight();
  scheduleSaveActiveQueryTab();
  editor.focus();
}

function wireClusterFilters() {
  document.getElementById("clusterSearch").addEventListener("input", renderClusters);
  document.querySelectorAll("[data-filter]").forEach((button) => {
    button.addEventListener("click", () => {
      currentFilter = button.dataset.filter;
      document.querySelectorAll("[data-filter]").forEach((other) => other.classList.toggle("active", other === button));
      renderClusters();
    });
  });
  document.getElementById("openCreateCluster").addEventListener("click", () => navigateTo("create"));
}

function wireJobs() {
  const createButton = document.getElementById("openCreateJob");
  if (createButton) createButton.addEventListener("click", () => createJobDialog());
  const closeRuns = document.getElementById("closeJobRuns");
  if (closeRuns) {
    closeRuns.addEventListener("click", () => {
      document.getElementById("jobRunsPanel").hidden = true;
    });
  }
}

function wireUsers() {
  const createButton = document.getElementById("openCreateUser");
  if (createButton) {
    createButton.addEventListener("click", () => createUserFromPrompt());
  }
  const createRoleButton = document.getElementById("openCreateRole");
  if (createRoleButton) {
    createRoleButton.addEventListener("click", () => createRoleFromDialog());
  }
  const createPolicyButton = document.getElementById("openCreateDataPolicy");
  if (createPolicyButton) createPolicyButton.addEventListener("click", () => createDataPolicyDialog());
  const createTagButton = document.getElementById("openCreateTag");
  if (createTagButton) createTagButton.addEventListener("click", () => createTagDialog());
  const createTagPolicyButton = document.getElementById("openCreateTagPolicy");
  if (createTagPolicyButton) createTagPolicyButton.addEventListener("click", () => createTagPolicyDialog());
  const classifyButton = document.getElementById("runClassifierButton");
  if (classifyButton) classifyButton.addEventListener("click", () => runPiiClassifier());
}

function wireClusterDetailActions() {
  document.getElementById("clusterDetailStart").addEventListener("click", () => {
    startCluster(selectedClusterDetail);
  });
  document.getElementById("clusterDetailEdit").addEventListener("click", () => {
    editCluster(selectedClusterDetail);
  });
  document.getElementById("clusterDetailSuspend").addEventListener("click", () => {
    suspendCluster(selectedClusterDetail);
  });
  document.getElementById("clusterDetailDisable").addEventListener("click", () => {
    disableCluster(selectedClusterDetail);
  });
  document.getElementById("clusterDetailDelete").addEventListener("click", () => {
    deleteCluster(selectedClusterDetail);
  });
}

function updateWizard() {
  document.querySelectorAll(".wizard-step").forEach((step) => {
    step.classList.toggle("active", Number(step.dataset.step) === currentWizardStep);
  });
  document.querySelectorAll("[data-step-marker]").forEach((marker) => {
    marker.classList.toggle("active", Number(marker.dataset.stepMarker) === currentWizardStep);
  });
  document.getElementById("wizardStepNumber").textContent = String(currentWizardStep + 1);
  document.getElementById("wizardBack").disabled = currentWizardStep === 0;
  document.getElementById("wizardNext").innerHTML =
    currentWizardStep === 4 ? 'Finish setup <span data-icon="check"></span>' : 'Next <span data-icon="arrow-right"></span>';
  document.getElementById("reviewAdmin").textContent = document.getElementById("setupAdmin").value || "admin";
  document.getElementById("reviewRegion").textContent = document.getElementById("setupRegion").value;
  replaceIcons();
}

function wireWizard() {
  document.getElementById("wizardBack").addEventListener("click", () => {
    currentWizardStep = Math.max(0, currentWizardStep - 1);
    updateWizard();
  });
  document.getElementById("wizardNext").addEventListener("click", () => {
    if (currentWizardStep === 4) {
      completeSetup();
      return;
    }
    currentWizardStep += 1;
    updateWizard();
  });
  ["setupAdmin", "setupRegion"].forEach((id) => {
    document.getElementById(id).addEventListener("input", updateWizard);
    document.getElementById(id).addEventListener("change", updateWizard);
  });
}

function presetTier(preset) {
  return presetTiers.find((tier) => tier.preset === preset) || null;
}

function presetTierLabel(tier) {
  if (!tier) return "—";
  return tier.memory_gib ? `${tier.instance_type} (${tier.memory_gib} GiB)` : tier.instance_type;
}

// Drive the Create-cluster preset cards, the Review panel and the Settings tier
// list from the AWS-resolved instance types instead of a hardcoded fallback
// (roadmap B1). Falls back gracefully to whatever markup is present if the
// tiers have not loaded yet.
function renderPresetTiers() {
  document.querySelectorAll("[data-preset]").forEach((button) => {
    const tier = presetTier(button.dataset.preset);
    const strong = button.querySelector("strong");
    if (tier && strong) strong.textContent = tier.instance_type;
  });
  const settingsList = document.getElementById("settingsPresetTiers");
  if (settingsList && presetTiers.length) {
    settingsList.innerHTML = presetTiers
      .map((tier) => `<div><span>${escapeHtml(tier.preset)}</span><strong>${escapeHtml(presetTierLabel(tier))}</strong></div>`)
      .join("");
  }
  updateCreateReview();
}

async function loadPresetTiers() {
  try {
    const result = await apiRequest("/api/preset-tiers");
    presetTiers = result.tiers || [];
    renderPresetTiers();
  } catch (error) {
    if (!/Authentication required/.test(error.message)) {
      // Non-fatal: the cards keep their last-known labels.
      console.warn("Preset tier load failed:", error.message);
    }
  }
}

// Instance types power three views: the Settings summary (enabled types as pills),
// the Settings edit modal (search + presets + family-grouped cards), and the
// Create-cluster picker (only enabled types appear). The list is AWS-resolved per
// region; the GET is read-only for any signed-in user, while the PUT that saves
// the allowlist is admin-gated server-side too.
const INSTANCE_PRESETS = {
  recommended: ["r7i.xlarge", "r7i.2xlarge", "r7i.4xlarge"],
  cost: ["r6i.xlarge", "r5.xlarge"]
};
let instanceOptionsOrdered = [];
let instanceModalDraft = [];

function instanceSpecText(option) {
  const cost = option.hourly_usd == null ? "" : ` · ~${formatUsd(option.hourly_usd)}/hr`;
  const nvme = option.instance_store_gb ? ` · ${option.instance_store_gb} GB NVMe` : "";
  return `${option.vcpu} vCPU · ${option.memory_gib} GiB${nvme}${cost}`;
}

// Per-node hourly range across a set of enabled types (a meaningful figure,
// unlike summing one-of-each). Empty string when nothing is priced.
function instanceCostNote(ids) {
  const prices = ids
    .map((id) => instanceCatalog[id])
    .filter((option) => option && option.hourly_usd != null)
    .map((option) => option.hourly_usd);
  if (!prices.length) return "";
  const lo = Math.min(...prices);
  const hi = Math.max(...prices);
  return lo === hi ? `${formatUsd(lo)}/hr per node` : `${formatUsd(lo)}–${formatUsd(hi)}/hr per node`;
}

// Settings: enabled types as removable pills, with a per-node cost range.
function renderInstanceTypeSummary() {
  const summary = document.getElementById("instanceTypeSummary");
  const costNote = document.getElementById("instanceTypeCostNote");
  const editButton = document.getElementById("editInstanceTypesButton");
  const isAdmin = Boolean(currentUser && currentUser.role === "admin");
  if (summary) {
    if (!allowedInstanceTypes.length) {
      summary.innerHTML =
        '<p class="instance-empty">No instance types enabled yet — clusters can\'t be created until you add at least one.</p>';
    } else {
      summary.innerHTML = allowedInstanceTypes
        .map((id) => {
          const option = instanceCatalog[id];
          const meta = option ? ` <span class="itype-pill-meta">${escapeHtml(`${option.memory_gib} GiB`)}</span>` : "";
          const remove = isAdmin
            ? ` <button class="itype-pill-x" type="button" data-remove-instance="${escapeHtml(id)}" aria-label="Remove ${escapeHtml(id)}">×</button>`
            : "";
          return `<span class="itype-pill">${escapeHtml(id)}${meta}${remove}</span>`;
        })
        .join("");
    }
  }
  if (costNote) {
    const note = instanceCostNote(allowedInstanceTypes);
    costNote.textContent = note ? `Enabled nodes: ${note}` : "";
  }
  if (editButton) editButton.disabled = !isAdmin;
}

// Settings edit modal: search + family-grouped selectable cards.
function instanceMatchesSearch(option, term) {
  if (!term) return true;
  return (
    option.instance_type.toLowerCase().includes(term) ||
    String(option.family).toLowerCase().includes(term) ||
    `${option.vcpu} vcpu`.includes(term) ||
    `${option.memory_gib} gib`.includes(term)
  );
}

function renderInstanceTypeModalList() {
  const body = document.getElementById("instanceTypeModalList");
  if (!body) return;
  const term = (document.getElementById("instanceTypeSearch").value || "").toLowerCase().trim();
  const matches = instanceOptionsOrdered.filter((option) => instanceMatchesSearch(option, term));
  if (!matches.length) {
    body.innerHTML = '<p class="itype-empty">No instance types match your search.</p>';
    return;
  }
  const families = [];
  const grouped = {};
  matches.forEach((option) => {
    if (!grouped[option.family]) {
      grouped[option.family] = [];
      families.push(option.family);
    }
    grouped[option.family].push(option);
  });
  body.innerHTML = families
    .map((family) => {
      const cards = grouped[family]
        .map((option) => {
          const selected = instanceModalDraft.includes(option.instance_type);
          const unavailable = !option.available;
          const tag = unavailable ? '<span class="itype-card-tag">not in region</span>' : "";
          return `
            <div class="itype-card${selected ? " is-selected" : ""}${unavailable ? " is-unavailable" : ""}" data-instance-type="${escapeHtml(option.instance_type)}">
              <input type="checkbox" ${selected ? "checked" : ""} ${unavailable ? "disabled" : ""} tabindex="-1" />
              <div class="itype-card-main">
                <div class="itype-card-name">${escapeHtml(option.instance_type)}</div>
                <div class="itype-card-spec">${escapeHtml(`${option.vcpu} vCPU · ${option.memory_gib} GiB`)}</div>
              </div>
              ${tag}
              <div class="itype-card-price">${option.hourly_usd == null ? "" : `~${formatUsd(option.hourly_usd)}/hr`}</div>
            </div>`;
        })
        .join("");
      return `<div class="itype-group"><div class="itype-group-title">${escapeHtml(family)} family</div><div class="itype-group-cards">${cards}</div></div>`;
    })
    .join("");
}

function updateInstanceModalFoot() {
  const count = document.getElementById("instanceTypeModalCount");
  const cost = document.getElementById("instanceTypeModalCost");
  if (count) count.textContent = `${instanceModalDraft.length} selected`;
  if (cost) {
    const note = instanceCostNote(instanceModalDraft);
    cost.textContent = note ? `${note} · estimated` : "";
  }
}

function toggleInstanceDraft(id) {
  const option = instanceCatalog[id];
  if (!option || !option.available) return;
  if (instanceModalDraft.includes(id)) {
    instanceModalDraft = instanceModalDraft.filter((x) => x !== id);
  } else {
    instanceModalDraft.push(id);
  }
  renderInstanceTypeModalList();
  updateInstanceModalFoot();
}

function applyInstancePreset(name) {
  const wanted = INSTANCE_PRESETS[name] || [];
  // Keep canonical order and drop anything not offered in the region.
  instanceModalDraft = instanceOptionsOrdered
    .filter((option) => option.available && wanted.includes(option.instance_type))
    .map((option) => option.instance_type);
  renderInstanceTypeModalList();
  updateInstanceModalFoot();
}

function openInstanceTypeModal() {
  if (!currentUser || currentUser.role !== "admin") return;
  instanceModalDraft = [...allowedInstanceTypes];
  const search = document.getElementById("instanceTypeSearch");
  if (search) search.value = "";
  renderInstanceTypeModalList();
  updateInstanceModalFoot();
  const modal = document.getElementById("instanceTypeModal");
  if (modal) modal.hidden = false;
  replaceIcons();
}

function closeInstanceTypeModal() {
  const modal = document.getElementById("instanceTypeModal");
  if (modal) modal.hidden = true;
}

// One labeled, copy-able connection field (JDBC URL / ODBC / CLI / Host / …).
// The copy handler reads the <code> text, so no value goes through an attribute.
function connectField(label, value) {
  return `
    <div class="connect-field">
      <label>${escapeHtml(label)}</label>
      <div class="connect-value">
        <code>${escapeHtml(value)}</code>
        <button class="ghost-button connect-copy" type="button" data-copy-field title="Copy" aria-label="Copy ${escapeHtml(label)}"><span data-icon="copy"></span></button>
      </div>
    </div>`;
}

// Per-cluster "Connection info" popup. Fetches the derived JDBC/ODBC/CLI strings
// (host = per-cluster override, else <name>.<base-domain>, else coordinator IP)
// and renders them with copy buttons. Falls back to a hint when nothing resolves.
async function openConnectModal(cluster) {
  if (!cluster || !cluster.id) return;
  const modal = document.getElementById("connectModal");
  const body = document.getElementById("connectModalBody");
  const sub = document.getElementById("connectModalSub");
  const title = document.getElementById("connectModalTitle");
  if (!modal || !body) return;
  title.textContent = `Connect to ${cluster.name}`;
  sub.textContent = "Loading connection details…";
  body.innerHTML = '<p class="instance-empty">Loading…</p>';
  modal.hidden = false;
  replaceIcons();
  let info;
  try {
    info = await apiRequest(`/api/clusters/${cluster.id}/connection`);
  } catch (error) {
    sub.textContent = "";
    body.innerHTML = `<p class="instance-empty">${escapeHtml(error.message)}</p>`;
    return;
  }
  const versionMeta = info.trino_version
    ? `<div class="connect-meta">Trino version <strong>${escapeHtml(info.trino_version)}</strong></div>`
    : "";
  if (!info.resolvable) {
    sub.textContent = "No connection address yet.";
    body.innerHTML = versionMeta + `<div class="connect-hint">${escapeHtml(info.hint || "")}</div>`;
    return;
  }
  sub.textContent =
    info.via === "coordinator_ip"
      ? "Internal coordinator endpoint (HTTP). Set a base domain in Settings for a stable HTTPS hostname."
      : "Requires a secure connection (HTTPS/SSL/TLS) terminated at your domain.";
  const uiAction = info.web_ui
    ? `<div class="connect-actions"><a class="secondary-button connect-ui-link" href="${escapeHtml(info.web_ui)}" target="_blank" rel="noopener noreferrer"><span data-icon="external-link"></span> Open coordinator UI</a></div>`
    : "";
  body.innerHTML =
    versionMeta +
    uiAction +
    `<div class="connect-fields">${[
      connectField("JDBC URL", info.jdbc_url),
      connectField("ODBC", info.odbc),
      connectField("CLI", info.cli),
      connectField("Host", info.host),
      connectField("Port", String(info.port)),
      connectField("User", info.user || "—")
    ].join("")}</div>`;
  replaceIcons();
}

function closeConnectModal() {
  const modal = document.getElementById("connectModal");
  if (modal) modal.hidden = true;
}

function wireConnectModal() {
  const modal = document.getElementById("connectModal");
  if (!modal) return;
  const close = document.getElementById("closeConnectModal");
  if (close) close.addEventListener("click", closeConnectModal);
  modal.addEventListener("mousedown", (event) => {
    if (event.target === modal) closeConnectModal();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !modal.hidden) closeConnectModal();
  });
  document.getElementById("connectModalBody").addEventListener("click", (event) => {
    const button = event.target.closest("[data-copy-field]");
    if (!button) return;
    const code = button.parentElement.querySelector("code");
    if (!code) return;
    copyText(code.textContent)
      .then(() => showToast("Copied to clipboard"))
      .catch(() => showToast("Copy failed — select the text and copy manually"));
  });
}

async function saveClusterBaseDomain() {
  if (!currentUser || currentUser.role !== "admin") {
    showToast("Only admins can change the base domain.");
    return;
  }
  const input = document.getElementById("settingsBaseDomain");
  if (!input) return;
  try {
    const result = await apiRequest("/api/cluster-base-domain", {
      method: "PUT",
      body: JSON.stringify({ cluster_base_domain: input.value.trim() })
    });
    const saved = (result.setup && result.setup.cluster_base_domain) || "";
    input.value = saved;
    const chip = document.getElementById("baseDomainChip");
    if (chip) {
      chip.textContent = saved || "Not set";
      chip.className = `chip ${saved ? "success" : "neutral"}`;
    }
    showToast(saved ? "Base domain saved" : "Base domain cleared");
  } catch (error) {
    showToast(error.message, { type: "error" });
  }
}

async function saveUiCidrs() {
  if (!currentUser || currentUser.role !== "admin") {
    showToast("Only admins can change the UI allowlist.");
    return;
  }
  const input = document.getElementById("settingsUiCidrsInput");
  if (!input) return;
  const cidrs = splitList(input.value);
  const persist = async (confirmLockout) => {
    const result = await apiRequest("/api/security/ui-cidrs", {
      method: "PUT",
      body: JSON.stringify({ allowed_ui_cidrs: cidrs, confirm_lockout: confirmLockout })
    });
    const saved = result.allowed_ui_cidrs || [];
    input.value = saved.join(", ");
    document.getElementById("settingsUiCidrs").textContent = saved.join(", ") || "local access";
    showToast(saved.length ? "UI allowlist saved" : "UI allowlist cleared (open to the security group)");
  };
  try {
    await persist(false);
  } catch (error) {
    // The server refuses a list that excludes the caller's own address unless
    // explicitly confirmed; surface that as a real decision, not a dead end.
    if (!/lock you out/.test(error.message)) {
      showToast(error.message, { type: "error" });
      return;
    }
    const confirmed = await openAppDialog({
      title: "This allowlist blocks your own address",
      body: `${error.message} Save anyway? You would need host access to undo it.`,
      confirmLabel: "Save and lock me out",
      danger: true
    });
    if (confirmed === null) return;
    try {
      await persist(true);
    } catch (retryError) {
      showToast(retryError.message, { type: "error" });
    }
  }
}

async function persistInstanceTypes(instanceTypes, successMessage) {
  await apiRequest("/api/instance-types", {
    method: "PUT",
    body: JSON.stringify({ instance_types: instanceTypes })
  });
  showToast(successMessage);
  await loadInstanceTypes();
}

async function saveInstanceTypeSelection() {
  const saveButton = document.getElementById("saveInstanceTypeModal");
  const chosen = [...instanceModalDraft];
  try {
    if (saveButton) saveButton.disabled = true;
    await persistInstanceTypes(
      chosen,
      chosen.length
        ? `${chosen.length} instance type${chosen.length === 1 ? "" : "s"} enabled for new clusters.`
        : "No instance types enabled — clusters can't be created until you add one."
    );
    closeInstanceTypeModal();
  } catch (error) {
    showToast(error.message, { type: "error" });
  } finally {
    if (saveButton) saveButton.disabled = false;
  }
}

async function removeInstanceType(id) {
  if (!currentUser || currentUser.role !== "admin") return;
  const next = allowedInstanceTypes.filter((x) => x !== id);
  try {
    await persistInstanceTypes(next, `${id} removed.`);
  } catch (error) {
    showToast(error.message, { type: "error" });
  }
}

// Create cluster: one selectable card per enabled (and available) type.
function renderInstanceTypeGrid() {
  const grid = document.getElementById("instanceTypeGrid");
  if (!grid) return;
  const choices = allowedInstanceTypes
    .map((itype) => instanceCatalog[itype])
    .filter((option) => option && option.available);
  if (!choices.length) {
    // Don't dead-end a fresh install: let admins enable the recommended set
    // right here instead of round-tripping through Settings.
    const isAdmin = document.getElementById("roleSelect").value !== "user";
    grid.innerHTML = `
      <div class="instance-empty">
        <p>No instance types enabled yet — clusters need at least one.</p>
        ${
          isAdmin
            ? `<div class="instance-empty-actions">
                 <button class="secondary-button" type="button" data-enable-recommended>
                   <span data-icon="sparkles"></span> Enable Trino recommended types
                 </button>
                 <button class="ghost-button" type="button" data-goto-settings>Choose in Settings</button>
               </div>`
            : "<p>Ask an admin to enable one in Settings → Node instance types.</p>"
        }
      </div>`;
    const enable = grid.querySelector("[data-enable-recommended]");
    if (enable) {
      enable.addEventListener("click", async () => {
        const available = INSTANCE_PRESETS.recommended.filter(
          (id) => instanceCatalog[id] && instanceCatalog[id].available
        );
        const fallback = instanceOptionsOrdered
          .filter((option) => option.available)
          .slice(0, 3)
          .map((option) => option.instance_type);
        const toEnable = available.length ? available : fallback;
        if (!toEnable.length) {
          showToast("No instance types are available in this region.", { type: "error" });
          return;
        }
        enable.disabled = true;
        try {
          await persistInstanceTypes(toEnable, `${toEnable.length} instance types enabled.`);
        } catch (error) {
          enable.disabled = false;
          showToast(error.message, { type: "error" });
        }
      });
    }
    const goto = grid.querySelector("[data-goto-settings]");
    if (goto) goto.addEventListener("click", () => navigateTo("settings"));
    replaceIcons();
    selectedInstanceType = "";
    updateCreateReview();
    return;
  }
  if (!choices.some((option) => option.instance_type === selectedInstanceType)) {
    selectedInstanceType = choices[0].instance_type;
  }
  grid.innerHTML = choices
    .map(
      (option) => `
        <button class="preset${option.instance_type === selectedInstanceType ? " selected" : ""}" data-instance-type="${escapeHtml(option.instance_type)}" type="button">
          <span class="preset-name">${escapeHtml(option.family)}</span>
          <strong>${escapeHtml(option.instance_type)}</strong>
          <span>${escapeHtml(instanceSpecText(option))}</span>
        </button>`
    )
    .join("");
  grid.querySelectorAll("[data-instance-type]").forEach((button) => {
    button.addEventListener("click", () => {
      selectedInstanceType = button.dataset.instanceType;
      grid
        .querySelectorAll("[data-instance-type]")
        .forEach((other) => other.classList.toggle("selected", other === button));
      updateCreateReview();
    });
  });
  updateCreateReview();
}

function renderInstanceTypeOptions(data) {
  const options = data.instance_types || [];
  instanceOptionsOrdered = options;
  instanceCatalog = {};
  options.forEach((option) => {
    instanceCatalog[option.instance_type] = option;
  });
  allowedInstanceTypes = data.allowed_instance_types || [];

  const chip = document.getElementById("instanceTypeChip");
  if (chip) {
    chip.textContent = `${allowedInstanceTypes.length} selected`;
    chip.className = `chip ${allowedInstanceTypes.length ? "info" : "neutral"}`;
  }
  renderInstanceTypeSummary();
  renderInstanceTypeGrid();
  // Keep an open modal in sync after a save/reload.
  const modal = document.getElementById("instanceTypeModal");
  if (modal && !modal.hidden) {
    renderInstanceTypeModalList();
    updateInstanceModalFoot();
  }
  replaceIcons();
}

async function loadInstanceTypes() {
  try {
    const data = await apiRequest("/api/instance-types");
    renderInstanceTypeOptions(data);
  } catch (error) {
    if (!/Authentication required/.test(error.message)) {
      console.warn("Instance-type load failed:", error.message);
    }
  }
}

async function loadTrinoVersions() {
  const select = document.getElementById("newTrinoVersion");
  if (!select) return;
  try {
    const data = await apiRequest("/api/trino-versions");
    const versions = data.versions || [];
    select.innerHTML = versions
      .map(
        (version) =>
          `<option value="${escapeHtml(version)}">${escapeHtml(version)}${
            version === data.default ? " (latest)" : ""
          }</option>`
      )
      .join("");
    if (data.default) select.value = data.default;
  } catch (error) {
    if (!/Authentication required/.test(error.message)) {
      console.warn("Trino-version load failed:", error.message);
    }
  }
}

function wireSettings() {
  const editButton = document.getElementById("editInstanceTypesButton");
  if (editButton) editButton.addEventListener("click", openInstanceTypeModal);

  const saveSso = document.getElementById("saveSsoButton");
  if (saveSso) saveSso.addEventListener("click", saveSsoSettings);
  const saveSession = document.getElementById("saveSessionHoursButton");
  if (saveSession) saveSession.addEventListener("click", saveSessionHours);
  const revokeSessions = document.getElementById("revokeSessionsButton");
  if (revokeSessions) revokeSessions.addEventListener("click", revokeMySessions);
  const createToken = document.getElementById("createApiTokenButton");
  if (createToken) createToken.addEventListener("click", createApiTokenDialog);
  const saveNotifications = document.getElementById("saveNotificationsButton");
  if (saveNotifications) saveNotifications.addEventListener("click", saveNotificationSettings);
  const saveAskModel = document.getElementById("saveAskModelButton");
  if (saveAskModel) saveAskModel.addEventListener("click", saveAskSettings);

  const saveBaseDomain = document.getElementById("saveBaseDomainButton");
  if (saveBaseDomain) saveBaseDomain.addEventListener("click", saveClusterBaseDomain);
  const saveUiCidrsButton = document.getElementById("saveUiCidrsButton");
  if (saveUiCidrsButton) saveUiCidrsButton.addEventListener("click", saveUiCidrs);
  const baseDomainInput = document.getElementById("settingsBaseDomain");
  if (baseDomainInput) {
    baseDomainInput.addEventListener("keydown", (event) => {
      if (event.key === "Enter") saveClusterBaseDomain();
    });
  }

  // Remove a type directly from a summary pill (persists immediately).
  const summary = document.getElementById("instanceTypeSummary");
  if (summary) {
    summary.addEventListener("click", (event) => {
      const button = event.target.closest("[data-remove-instance]");
      if (button) removeInstanceType(button.dataset.removeInstance);
    });
  }

  const modal = document.getElementById("instanceTypeModal");
  if (!modal) return;
  document.getElementById("closeInstanceTypeModal").addEventListener("click", closeInstanceTypeModal);
  document.getElementById("cancelInstanceTypeModal").addEventListener("click", closeInstanceTypeModal);
  modal.addEventListener("mousedown", (event) => {
    if (event.target === modal) closeInstanceTypeModal();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !modal.hidden) closeInstanceTypeModal();
  });
  document.getElementById("instanceTypeSearch").addEventListener("input", renderInstanceTypeModalList);
  modal.querySelectorAll("[data-itype-preset]").forEach((button) => {
    button.addEventListener("click", () => applyInstancePreset(button.dataset.itypePreset));
  });
  document.getElementById("instanceTypeModalList").addEventListener("click", (event) => {
    const card = event.target.closest(".itype-card");
    if (card) toggleInstanceDraft(card.dataset.instanceType);
  });
  document.getElementById("saveInstanceTypeModal").addEventListener("click", saveInstanceTypeSelection);
}

function updateCreateReview() {
  let min = Number(document.getElementById("minWorkers").value);
  let max = Number(document.getElementById("maxWorkers").value);

  if (currentWorkerMode === "fixed") {
    max = min;
    document.getElementById("maxWorkers").value = String(max);
  } else if (max < min) {
    max = min;
    document.getElementById("maxWorkers").value = String(max);
  }

  document.getElementById("minWorkersValue").textContent = String(min);
  document.getElementById("maxWorkersValue").textContent = String(max);
  document.getElementById("reviewCoordinator").textContent = `1 x ${selectedInstanceType || "…"}`;
  document.getElementById("reviewWorkers").textContent =
    currentWorkerMode === "fixed" ? `${min} workers` : `${min}-${max} workers`;
  document.getElementById("reviewScaler").textContent =
    currentWorkerMode === "fixed" ? "Manual resize" : "Query queue + CPU";
  document.getElementById("reviewCatalogs").textContent = selectedClusterCatalogs().join(", ");
}

function wireCreateCluster() {
  // The instance-type cards are rendered and wired dynamically in
  // renderInstanceTypeGrid() from the Settings allowlist.
  document.querySelectorAll("[data-worker-mode]").forEach((button) => {
    button.addEventListener("click", () => {
      currentWorkerMode = button.dataset.workerMode;
      document.querySelectorAll("[data-worker-mode]").forEach((other) => other.classList.toggle("selected", other === button));
      // Autoscaling reshuffles cached splits, so it turns acceleration off.
      const acceleratedToggle = document.getElementById("newAccelerated");
      if (acceleratedToggle && button.dataset.workerMode === "autoscale" && acceleratedToggle.checked) {
        acceleratedToggle.checked = false;
        showToast("Accelerated caching turned off — it requires a fixed worker count.");
      }
      updateCreateReview();
    });
  });

  const acceleratedToggle = document.getElementById("newAccelerated");
  if (acceleratedToggle) {
    acceleratedToggle.addEventListener("change", () => {
      if (!acceleratedToggle.checked) return;
      // Acceleration implies fixed workers and a long auto-suspend: the NVMe
      // cache is wiped when nodes terminate, so aggressive idling wastes it.
      currentWorkerMode = "fixed";
      document
        .querySelectorAll("[data-worker-mode]")
        .forEach((button) => button.classList.toggle("selected", button.dataset.workerMode === "fixed"));
      const suspend = document.getElementById("newAutoSuspend");
      if (suspend && suspend.value !== "" && Number(suspend.value) < 240) suspend.value = "240";
      const chosen = instanceCatalog[selectedInstanceType];
      if (chosen && !chosen.has_instance_store) {
        showToast("Pick an NVMe instance type (i4i, r6id, i3en) for the cache.", { type: "error" });
      }
      updateCreateReview();
    });
  }

  ["minWorkers", "maxWorkers"].forEach((id) => {
    document.getElementById(id).addEventListener("input", updateCreateReview);
    document.getElementById(id).addEventListener("change", updateCreateReview);
  });

  // The per-catalog toggles are rendered dynamically, so listen via delegation.
  document.getElementById("clusterCatalogChoices").addEventListener("change", updateCreateReview);

  document.getElementById("createClusterButton").addEventListener("click", async () => {
    const role = document.getElementById("roleSelect").value;
    if (role !== "admin") {
      showToast("Only admins can create clusters.");
      return;
    }

    if (!selectedInstanceType) {
      showToast("Select an instance type first — enable one from the Instance type section above.", { type: "error" });
      return;
    }

    const name = document.getElementById("newClusterName").value.trim() || "new-cluster";
    const min = Number(document.getElementById("minWorkers").value);
    const max = Number(document.getElementById("maxWorkers").value);
    const autoSuspendValue = document.getElementById("newAutoSuspend").value;
    const autoSuspendMinutes = autoSuspendValue === "" ? null : Number.parseInt(autoSuspendValue, 10);
    const accelerated = Boolean(document.getElementById("newAccelerated")?.checked);
    const chosenType = instanceCatalog[selectedInstanceType];
    if (accelerated && chosenType && !chosenType.has_instance_store) {
      showToast("Accelerated clusters need an NVMe instance type (i4i, r6id, i3en).", { type: "error" });
      return;
    }
    const payload = {
      name,
      instance_type: selectedInstanceType,
      worker_mode: currentWorkerMode,
      min_workers: min,
      max_workers: currentWorkerMode === "fixed" ? min : max,
      auto_suspend_minutes: Number.isNaN(autoSuspendMinutes) ? null : autoSuspendMinutes,
      trino_version: document.getElementById("newTrinoVersion").value || undefined,
      accelerated,
      catalogs: selectedClusterCatalogs()
    };

    try {
      document.getElementById("createClusterButton").disabled = true;
      const result = await apiRequest("/api/clusters", {
        method: "POST",
        body: JSON.stringify(payload)
      });
      clusters.unshift(clusterFromApi(result.cluster));
      renderClusters();
      navigateTo("clusters");
      showToast(`${name} was saved. Use Start when you are ready to create AWS resources.`);
    } catch (error) {
      showToast(error.message, { type: "error" });
    } finally {
      document.getElementById("createClusterButton").disabled = false;
    }
  });
}

function setQueryState(state, elapsed = "0.0s", rows = "0") {
  const status = document.getElementById("queryStatus");
  status.textContent = state;
  status.className = `chip ${statusClass(state)}`;
  document.getElementById("queryElapsed").textContent = elapsed;
  document.getElementById("queryRows").textContent = rows;
}

function renderQueryResults(query) {
  if (activeResultView === "profile") {
    renderQueryProfile(query);
    return;
  }
  if (activeResultView === "chart") {
    renderQueryChart(query);
    return;
  }
  if (!query) {
    document.getElementById("resultsTable").innerHTML = '<div class="empty-results">Run a query to see results.</div>';
    return;
  }
  if (query.error_message) {
    document.getElementById("resultsTable").innerHTML = `<div class="empty-results">${escapeHtml(query.error_message)}</div>`;
    return;
  }
  const columns = query.columns || [];
  const rows = query.data || [];
  if (!columns.length) {
    document.getElementById("resultsTable").innerHTML =
      query.status === "Running"
        ? '<div class="empty-results">Waiting for result metadata.</div>'
        : '<div class="empty-results">Query completed without tabular results.</div>';
    return;
  }
  if (!rows.length) {
    document.getElementById("resultsTable").innerHTML = '<div class="empty-results">No rows returned.</div>';
    return;
  }
  const banner = query.truncated
    ? `<div class="truncation-banner">Showing the first ${rows.length} rows${
        query.total_row_count ? ` of ${query.total_row_count} returned` : ""
      }. Add a LIMIT or narrow the query to see the rest.</div>`
    : "";
  const table = `
    ${banner}
    <table>
      <thead>
        <tr>
          ${columns.map((column) => `<th>${escapeHtml(column.name || "")}</th>`).join("")}
        </tr>
      </thead>
      <tbody>
        ${rows
          .map(
            (row) =>
              `<tr>${row
                .map((cell) => {
                  const value = cell === null ? "NULL" : typeof cell === "object" ? JSON.stringify(cell) : cell;
                  return `<td>${escapeHtml(value)}</td>`;
                })
                .join("")}</tr>`
          )
          .join("")}
      </tbody>
    </table>
  `;
  document.getElementById("resultsTable").innerHTML = table;
}

function renderQueryProfile(query) {
  const target = document.getElementById("resultsTable");
  if (!query) {
    target.innerHTML = '<div class="empty-results">Run a query to see profile details.</div>';
    return;
  }
  const profile = [
    ["Status", query.status],
    ["Trino query ID", query.trino_query_id || "-"],
    ["Cluster", queryClusterLabel(query)],
    ["Context", [query.catalog, query.schema].filter(Boolean).join(".") || "-"],
    ["Elapsed", formatElapsedMs(query.elapsed_ms)],
    ["Rows shown", query.row_count],
    ["Rows returned", query.total_row_count],
    ["CSV rows", query.download_row_count],
    ["Result bytes", query.result_bytes],
    ["Truncated", query.truncated ? "Yes" : "No"]
  ];
  target.innerHTML = `
    <div class="query-profile-grid">
      ${profile
        .map(
          ([label, value]) => `
            <div>
              <span>${escapeHtml(label)}</span>
              <strong>${escapeHtml(value == null ? "-" : value)}</strong>
            </div>
          `
        )
        .join("")}
    </div>
    <pre class="query-detail-sql">${escapeHtml(query.sql || "")}</pre>
    ${
      query.error_message
        ? `<div class="query-detail-error">${escapeHtml(query.error_message)}</div>`
        : ""
    }
    <div id="queryProfileDetails"></div>
  `;
  if (query.id && query.trino_query_id) loadQueryProfileDetails(query.id);
}

// Deep execution detail from the coordinator (/v1/query): per-stage rows,
// splits, memory. Best-effort — suspended clusters simply have none.
async function loadQueryProfileDetails(queryId) {
  const box = document.getElementById("queryProfileDetails");
  if (!box) return;
  try {
    const details = await apiRequest(`/api/query/${queryId}/details`);
    const stale = document.getElementById("queryProfileDetails");
    if (!stale || stale !== box) return;
    const stats = details.stats || {};
    const statRows = [
      ["Coordinator state", details.state],
      ["Queued", stats.queued_time],
      ["Execution", stats.execution_time],
      ["CPU time", stats.cpu_time],
      ["Input rows", stats.total_rows],
      ["Input bytes", stats.total_bytes],
      ["Peak memory", stats.peak_memory],
      ["Splits", stats.total_splits != null ? `${stats.completed_splits}/${stats.total_splits}` : null],
    ].filter(([, value]) => value != null && value !== "");
    const stages = details.stages || [];
    box.innerHTML = `
      <h3 class="section-title">Execution detail</h3>
      <div class="query-profile-grid">
        ${statRows
          .map(([label, value]) => `<div><span>${escapeHtml(label)}</span><strong>${escapeHtml(String(value))}</strong></div>`)
          .join("")}
      </div>
      ${
        stages.length
          ? `<table class="stage-table">
              <thead><tr><th>Stage</th><th>State</th><th>Tasks</th><th>Input rows</th><th>Input</th><th>CPU</th><th>Memory</th></tr></thead>
              <tbody>
                ${stages
                  .map(
                    (stage) => `
                    <tr>
                      <td>${escapeHtml(String(stage.stage_id))}</td>
                      <td>${escapeHtml(stage.state || "")}</td>
                      <td>${stage.tasks != null ? stage.tasks : "—"}</td>
                      <td>${stage.input_rows != null ? stage.input_rows : "—"}</td>
                      <td>${escapeHtml(stage.input_bytes || "—")}</td>
                      <td>${escapeHtml(stage.cpu_time || "—")}</td>
                      <td>${escapeHtml(stage.memory || "—")}</td>
                    </tr>`
                  )
                  .join("")}
              </tbody>
            </table>`
          : ""
      }`;
  } catch (error) {
    // Coordinator gone (suspended cluster) or query expired from its memory:
    // the basic profile above is all there is.
    box.innerHTML = "";
  }
}

// Chart tab: render a simple client-side chart from the capped result set
// (roadmap F1). No charting library — a small inline SVG keeps the dependency
// footprint at zero, consistent with the rest of the app.
const CHART_PALETTE = ["#9e3fd6", "#3b7bdd", "#16a37b", "#a734d7", "#e0921c", "#5dcaa5"];
const CHART_MAX_POINTS = 50;

function chartNumber(value) {
  if (value === null || value === undefined || value === "") return NaN;
  const n = Number(value);
  return Number.isFinite(n) ? n : NaN;
}

function renderQueryChart(query) {
  const target = document.getElementById("resultsTable");
  if (!query) {
    target.innerHTML = '<div class="empty-results">Run a query to chart its results.</div>';
    return;
  }
  const columns = query.columns || [];
  const rows = query.data || [];
  if (!columns.length || !rows.length) {
    target.innerHTML = '<div class="empty-results">No rows to chart.</div>';
    return;
  }
  const numericIndexes = columns
    .map((_, index) => index)
    .filter((index) => rows.some((row) => !Number.isNaN(chartNumber(row[index]))));
  if (!numericIndexes.length) {
    target.innerHTML = '<div class="empty-results">No numeric column to plot.</div>';
    return;
  }
  // Validate/seed the selected axes against the current result shape. Note:
  // Number("") is 0, so an unset axis must be treated as NaN or the seed
  // logic silently picks column 0 for both axes.
  let xIndex = chartState.x === "" ? NaN : Number(chartState.x);
  let yIndex = chartState.y === "" ? NaN : Number(chartState.y);
  if (!Number.isInteger(xIndex) || xIndex < 0 || xIndex >= columns.length) {
    const firstNonNumeric = columns.findIndex((_, index) => !numericIndexes.includes(index));
    xIndex = firstNonNumeric >= 0 ? firstNonNumeric : 0;
  }
  if (!numericIndexes.includes(yIndex)) {
    // Prefer a measure that isn't also the category axis.
    const differentFromX = numericIndexes.find((index) => index !== xIndex);
    yIndex = differentFromX !== undefined ? differentFromX : numericIndexes[0];
  }
  chartState.x = String(xIndex);
  chartState.y = String(yIndex);

  const points = rows.slice(0, CHART_MAX_POINTS).map((row) => ({
    label: row[xIndex] === null ? "NULL" : String(row[xIndex]),
    value: chartNumber(row[yIndex])
  }));
  const truncatedNote =
    rows.length > CHART_MAX_POINTS
      ? `<div class="truncation-banner">Charting the first ${CHART_MAX_POINTS} of ${rows.length} rows.</div>`
      : "";

  const typeOptions = [
    ["bar", "Bar"],
    ["line", "Line"],
    ["area", "Area"],
    ["pie", "Pie"]
  ]
    .map(([value, label]) => `<option value="${value}"${chartState.type === value ? " selected" : ""}>${label}</option>`)
    .join("");
  const columnOptions = (selected) =>
    columns
      .map((column, index) => `<option value="${index}"${index === selected ? " selected" : ""}>${escapeHtml(column.name || `col ${index}`)}</option>`)
      .join("");

  target.innerHTML = `
    <div class="chart-controls">
      <label>Chart type
        <select id="chartType">${typeOptions}</select>
      </label>
      <label>X / category
        <select id="chartX">${columnOptions(xIndex)}</select>
      </label>
      <label>Y / value
        <select id="chartY">${columnOptions(yIndex)}</select>
      </label>
    </div>
    ${truncatedNote}
    <div class="chart-canvas">${buildChartSvg(chartState.type, points)}</div>
  `;

  const rerender = (key) => (event) => {
    chartState[key] = event.target.value;
    renderQueryChart(query);
  };
  document.getElementById("chartType").addEventListener("change", rerender("type"));
  document.getElementById("chartX").addEventListener("change", rerender("x"));
  document.getElementById("chartY").addEventListener("change", rerender("y"));
}

function buildChartSvg(type, points) {
  const valid = points.filter((point) => !Number.isNaN(point.value));
  if (!valid.length) return '<div class="empty-results">Selected value column is not numeric.</div>';
  if (type === "pie") return buildPieSvg(valid);

  const width = Math.max(420, valid.length * 48);
  const height = 280;
  const pad = { top: 16, right: 16, bottom: 56, left: 56 };
  const plotW = width - pad.left - pad.right;
  const plotH = height - pad.top - pad.bottom;
  const max = Math.max(0, ...valid.map((p) => p.value));
  const min = Math.min(0, ...valid.map((p) => p.value));
  const span = max - min || 1;
  const yFor = (value) => pad.top + plotH - ((value - min) / span) * plotH;
  const step = plotW / valid.length;
  const color = CHART_PALETTE[0];

  const axis = `
    <line x1="${pad.left}" y1="${pad.top}" x2="${pad.left}" y2="${pad.top + plotH}" stroke="currentColor" opacity="0.25" />
    <line x1="${pad.left}" y1="${yFor(0)}" x2="${pad.left + plotW}" y2="${yFor(0)}" stroke="currentColor" opacity="0.25" />
    <text x="${pad.left - 8}" y="${yFor(max)}" text-anchor="end" font-size="10" fill="currentColor" opacity="0.7">${escapeHtml(formatChartNumber(max))}</text>
    <text x="${pad.left - 8}" y="${yFor(min)}" text-anchor="end" font-size="10" fill="currentColor" opacity="0.7">${escapeHtml(formatChartNumber(min))}</text>
  `;
  const labels = valid
    .map((p, i) => {
      const x = pad.left + step * i + step / 2;
      const text = p.label.length > 10 ? `${p.label.slice(0, 9)}…` : p.label;
      return `<text x="${x}" y="${height - 36}" transform="rotate(35 ${x} ${height - 36})" font-size="10" fill="currentColor" opacity="0.7">${escapeHtml(text)}</text>`;
    })
    .join("");

  let series = "";
  if (type === "bar") {
    series = valid
      .map((p, i) => {
        const barW = Math.max(4, step * 0.6);
        const x = pad.left + step * i + (step - barW) / 2;
        const y = yFor(Math.max(0, p.value));
        const h = Math.abs(yFor(p.value) - yFor(0));
        return `<rect x="${x}" y="${y}" width="${barW}" height="${h}" fill="${color}"><title>${escapeHtml(p.label)}: ${escapeHtml(formatChartNumber(p.value))}</title></rect>`;
      })
      .join("");
  } else {
    const coords = valid.map((p, i) => [pad.left + step * i + step / 2, yFor(p.value)]);
    const path = coords.map(([x, y], i) => `${i === 0 ? "M" : "L"}${x.toFixed(1)} ${y.toFixed(1)}`).join(" ");
    if (type === "area") {
      const areaPath = `${path} L${coords[coords.length - 1][0].toFixed(1)} ${yFor(0).toFixed(1)} L${coords[0][0].toFixed(1)} ${yFor(0).toFixed(1)} Z`;
      series += `<path d="${areaPath}" fill="${color}" opacity="0.18" />`;
    }
    series += `<path d="${path}" fill="none" stroke="${color}" stroke-width="2" />`;
    series += coords
      .map(([x, y], i) => `<circle cx="${x}" cy="${y}" r="3" fill="${color}"><title>${escapeHtml(valid[i].label)}: ${escapeHtml(formatChartNumber(valid[i].value))}</title></circle>`)
      .join("");
  }

  return `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Result chart">${axis}${series}${labels}</svg>`;
}

function buildPieSvg(points) {
  const total = points.reduce((sum, p) => sum + Math.max(0, p.value), 0);
  if (total <= 0) return '<div class="empty-results">Pie charts need positive values.</div>';
  const size = 240;
  const r = 100;
  const cx = size / 2;
  const cy = size / 2;
  let angle = -Math.PI / 2;
  const slices = points
    .map((p, i) => {
      const fraction = Math.max(0, p.value) / total;
      const next = angle + fraction * Math.PI * 2;
      const large = fraction > 0.5 ? 1 : 0;
      const x1 = cx + r * Math.cos(angle);
      const y1 = cy + r * Math.sin(angle);
      const x2 = cx + r * Math.cos(next);
      const y2 = cy + r * Math.sin(next);
      angle = next;
      const color = CHART_PALETTE[i % CHART_PALETTE.length];
      return `<path d="M${cx} ${cy} L${x1.toFixed(1)} ${y1.toFixed(1)} A${r} ${r} 0 ${large} 1 ${x2.toFixed(1)} ${y2.toFixed(1)} Z" fill="${color}"><title>${escapeHtml(p.label)}: ${escapeHtml(formatChartNumber(p.value))} (${(fraction * 100).toFixed(1)}%)</title></path>`;
    })
    .join("");
  const legend = points
    .map((p, i) => `<span><i style="background:${CHART_PALETTE[i % CHART_PALETTE.length]}"></i>${escapeHtml(p.label)}</span>`)
    .join("");
  return `<svg viewBox="0 0 ${size} ${size}" role="img" aria-label="Result pie chart">${slices}</svg><div class="chart-legend">${legend}</div>`;
}

function formatChartNumber(value) {
  if (!Number.isFinite(value)) return "-";
  if (Math.abs(value) >= 1000) return value.toLocaleString(undefined, { maximumFractionDigits: 1 });
  return String(Math.round(value * 100) / 100);
}

function addQueryToInlineHistory(query) {
  const inline = document.getElementById("inlineHistory");
  const clusterName = queryClusterLabel(query);
  const button = document.createElement("button");
  button.type = "button";
  button.innerHTML = `<strong>${escapeHtml(query.status)}</strong><span>${escapeHtml(query.sql)}</span><small>${escapeHtml(
    clusterName
  )} - ${escapeHtml(formatElapsedMs(query.elapsed_ms))}</small>`;
  inline.prepend(button);
}

function downloadQueryCsv(query) {
  const link = document.createElement("a");
  link.href = `/api/query/${query.id}/csv`;
  link.download = `trinohub-query-${query.id}.csv`;
  document.body.append(link);
  link.click();
  link.remove();
}

function batchResultStatus(item) {
  if (!item.query) return "Pending";
  return item.query.status;
}

function resetQueryBatchResults(statements = []) {
  queryBatchResults = statements.map((statement, index) => ({
    label: statement.label || `statement ${index + 1}`,
    sql: statement.sql,
    query: null
  }));
  activeQueryResultIndex = queryBatchResults.length ? 0 : -1;
  renderQueryResultNav();
}

function renderQueryResultNav() {
  const nav = document.getElementById("queryResultNav");
  if (!nav) return;
  if (queryBatchResults.length <= 1) {
    nav.hidden = true;
    nav.innerHTML = "";
    return;
  }
  nav.hidden = false;
  nav.innerHTML = queryBatchResults
    .map((item, index) => {
      const status = batchResultStatus(item);
      const rows = item.query ? item.query.row_count : 0;
      return `
        <button type="button" class="${index === activeQueryResultIndex ? "active" : ""}" data-query-result-index="${index}" ${
          item.query ? "" : "disabled"
        }>
          <strong>${escapeHtml(String(index + 1))}</strong>
          <span>${escapeHtml(status)}</span>
          <small>${escapeHtml(String(rows))}</small>
        </button>
      `;
    })
    .join("");
  nav.querySelectorAll("[data-query-result-index]").forEach((button) => {
    button.addEventListener("click", () => {
      showBatchResult(Number(button.dataset.queryResultIndex));
    });
  });
}

function showBatchResult(index) {
  const item = queryBatchResults[index];
  if (!item || !item.query) return;
  activeQueryResultIndex = index;
  applyQueryResult(item.query, { renderNav: false });
  renderQueryResultNav();
}

function updateBatchResult(index, query) {
  if (index >= 0) {
    if (!queryBatchResults[index]) {
      queryBatchResults[index] = { label: `statement ${index + 1}`, sql: query.sql || "", query: null };
    }
    queryBatchResults[index].query = query;
    activeQueryResultIndex = index;
  }
  applyQueryResult(query, { renderNav: false });
  renderQueryResultNav();
}

function downloadReadyResult(query = activeQueryResult) {
  if (!query || !(query.data || []).length) {
    showToast("No query results are ready to download.");
    return false;
  }
  downloadQueryCsv(query);
  showToast("CSV download prepared.");
  return true;
}

function downloadLatestBatchResult() {
  const downloadable = queryBatchResults
    .slice()
    .reverse()
    .find((item) => item.query && (item.query.data || []).length);
  if (downloadable) {
    const index = queryBatchResults.indexOf(downloadable);
    if (index >= 0) showBatchResult(index);
    return downloadReadyResult(downloadable.query);
  }
  return downloadReadyResult(activeQueryResult);
}

function applyQueryResult(query, options = {}) {
  activeQueryResult = query;
  setQueryState(query.status, formatElapsedMs(query.elapsed_ms), String(query.row_count));
  renderQueryResults(query);
  document.getElementById("downloadCsv").disabled = !(query.data || []).length;
  if (options.renderNav !== false) renderQueryResultNav();
}

function finishTerminalQuery(query, options = {}) {
  applyQueryResult(query);
  addQueryToInlineHistory(query);
  loadQueryHistoryFromApi();
  if (options.toast === false) return;
  if (query.status === "Finished") {
    showToast(`Query finished with ${query.row_count} rows.`);
  } else if (query.error_message) {
    showToast(query.error_message);
  } else {
    showToast(`Query ${query.status.toLowerCase()}.`);
  }
}

async function waitForQueryTerminal(queryId, resultIndex = -1) {
  while (!queryBatchCancelled && activeQueryId === queryId) {
    await delay(1000);
    const result = await apiRequest(`/api/query/${queryId}`);
    updateBatchResult(resultIndex, result.query);
    reflectPendingClusterStart(result.query);
    if (isTerminalQueryStatus(result.query.status)) {
      activeQueryId = null;
      return result.query;
    }
  }
  return activeQueryResult;
}

// A query submitted to an auto-suspended cluster stays Queued while the cluster
// resumes (typically one to five minutes), then dispatches to Trino on its own.
// Surface that so the wait doesn't just read as a stuck "Queued".
function reflectPendingClusterStart(query) {
  if (!query || !query.pending_cluster_start) return;
  setQueryState("Starting cluster", formatElapsedMs(query.elapsed_ms), "0");
  document.getElementById("resultsTable").innerHTML =
    '<div class="empty-results">Cluster is resuming from auto-suspend. Your query runs automatically once it is ready.</div>';
}

async function submitSqlStatement(clusterId, sqlText, resultIndex = -1) {
  const result = await apiRequest("/api/query", {
    method: "POST",
    body: JSON.stringify({
      cluster_id: Number(clusterId),
      catalog: document.getElementById("queryCatalog").value,
      schema: document.getElementById("querySchema").value,
      sql: sqlText
    })
  });
  activeQueryId = result.query.id;
  updateBatchResult(resultIndex, result.query);
  reflectPendingClusterStart(result.query);
  if (isTerminalQueryStatus(result.query.status)) {
    activeQueryId = null;
    return result.query;
  }
  return waitForQueryTerminal(result.query.id, resultIndex);
}

async function runSqlStatements(clusterId, statements) {
  let terminal = null;
  resetQueryBatchResults(statements);
  for (let index = 0; index < statements.length; index += 1) {
    if (queryBatchCancelled) break;
    const prefix = statements.length > 1 ? `Statement ${index + 1} of ${statements.length}: ` : "";
    document.getElementById("resultsTable").innerHTML = `<div class="empty-results">${escapeHtml(
      `${prefix}Submitting query to Trino.`
    )}</div>`;
    setQueryState("Queued", "0.0s", "0");
    terminal = await submitSqlStatement(clusterId, statements[index].sql, index);
    if (!terminal) break;
    finishTerminalQuery(terminal, { toast: statements.length === 1 });
    if (terminal.status !== "Finished") break;
  }
  return terminal;
}

function wireSqlEditor() {
  const run = document.getElementById("runQuery");
  const runAndDownload = document.getElementById("runAndDownload");
  const cancel = document.getElementById("cancelQuery");
  const download = document.getElementById("downloadCsv");
  const editor = document.getElementById("sqlText");
  document.getElementById("saveQuery").addEventListener("click", saveCurrentQuery);
  document.getElementById("savedQuerySearch").addEventListener("input", (event) => {
    savedQueryFilter = event.target.value;
    renderSavedQueries();
  });
  document.getElementById("savedQuerySort").addEventListener("change", (event) => {
    savedQuerySort = event.target.value;
    renderSavedQueries();
  });
  document.querySelectorAll("[data-result-view]").forEach((button) => {
    button.addEventListener("click", () => {
      activeResultView = button.dataset.resultView;
      document.querySelectorAll("[data-result-view]").forEach((other) => {
        other.classList.toggle("active", other.dataset.resultView === activeResultView);
      });
      renderQueryResults(activeQueryResult);
    });
  });
  document.getElementById("openSqlSearch").addEventListener("click", openSqlSearch);
  document.getElementById("formatSql").addEventListener("click", formatSqlEditor);
  document.getElementById("openCommandPalette").addEventListener("click", openCommandPalette);
  document.getElementById("closeCommandPalette").addEventListener("click", closeCommandPalette);
  document.getElementById("commandPalette").addEventListener("mousedown", (event) => {
    if (event.target.id === "commandPalette") closeCommandPalette();
  });
  document.getElementById("commandSearch").addEventListener("input", (event) => {
    commandPaletteState.query = event.target.value;
    commandPaletteState.activeIndex = 0;
    renderCommandPalette();
  });
  document.getElementById("commandSearch").addEventListener("keydown", (event) => {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      moveCommandPalette(1);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      moveCommandPalette(-1);
    } else if (event.key === "Enter") {
      event.preventDefault();
      runCommandPaletteCommand();
    } else if (event.key === "Escape") {
      event.preventDefault();
      closeCommandPalette();
    }
  });
  document.getElementById("closeSqlSearch").addEventListener("click", closeSqlSearch);
  document.getElementById("sqlSearchInput").addEventListener("input", () => {
    sqlSearchState.activeIndex = 0;
    renderSqlHighlight();
  });
  document.getElementById("sqlSearchInput").addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      goToSqlSearchMatch(event.shiftKey ? -1 : 1);
    } else if (event.key === "Escape") {
      event.preventDefault();
      closeSqlSearch();
    }
  });
  document.getElementById("sqlReplaceInput").addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      replaceCurrentSqlMatch();
    } else if (event.key === "Escape") {
      event.preventDefault();
      closeSqlSearch();
    }
  });
  document.getElementById("sqlSearchPrev").addEventListener("click", () => goToSqlSearchMatch(-1));
  document.getElementById("sqlSearchNext").addEventListener("click", () => goToSqlSearchMatch(1));
  document.getElementById("sqlReplaceOne").addEventListener("click", replaceCurrentSqlMatch);
  document.getElementById("sqlReplaceAll").addEventListener("click", replaceAllSqlMatches);
  document.querySelectorAll("[data-run-mode]").forEach((button) => {
    button.addEventListener("click", () => {
      applyRunMode(button.dataset.runMode, { save: true });
      if (editor) editor.focus();
    });
  });
  ["sqlText", "queryCluster", "queryCatalog", "querySchema"].forEach((id) => {
    const control = document.getElementById(id);
    if (!control) return;
    if (id === "sqlText") {
      control.addEventListener("input", () => {
        renderSqlHighlight();
        scheduleSaveActiveQueryTab();
        refreshSqlAutocomplete();
      });
    } else {
      control.addEventListener("change", () => {
        scheduleSaveActiveQueryTab();
        closeSqlAutocomplete();
        if (id === "queryCluster") resetSchemaBrowserForSelectedCluster();
      });
    }
  });
  if (editor) {
    editor.addEventListener("scroll", syncSqlHighlightScroll);
    editor.addEventListener("click", () => {
      renderSqlHighlight();
      refreshSqlAutocomplete();
    });
    editor.addEventListener("select", renderSqlHighlight);
    editor.addEventListener("keyup", renderSqlHighlight);
    editor.addEventListener("blur", () => window.setTimeout(closeSqlAutocomplete, 120));
    editor.addEventListener("keydown", (event) => {
      if (autocompleteState.open) {
        if (event.key === "ArrowDown") {
          event.preventDefault();
          moveSqlAutocomplete(1);
          return;
        }
        if (event.key === "ArrowUp") {
          event.preventDefault();
          moveSqlAutocomplete(-1);
          return;
        }
        if (event.key === "Enter" || event.key === "Tab") {
          event.preventDefault();
          acceptSqlAutocomplete();
          return;
        }
        if (event.key === "Escape") {
          event.preventDefault();
          closeSqlAutocomplete();
          return;
        }
      }

      if ((event.ctrlKey || event.metaKey) && event.shiftKey && event.key.toLowerCase() === "f") {
        event.preventDefault();
        formatSqlEditor();
      } else if ((event.ctrlKey || event.metaKey) && event.shiftKey && event.key.toLowerCase() === "p") {
        event.preventDefault();
        openCommandPalette();
      } else if ((event.ctrlKey || event.metaKey) && event.key === " ") {
        event.preventDefault();
        refreshSqlAutocomplete({ force: true });
      } else if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "f") {
        event.preventDefault();
        openSqlSearch();
      } else if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
        event.preventDefault();
        run.click();
      } else if (event.key === "Escape") {
        const searchBar = document.getElementById("sqlSearchBar");
        if (searchBar && !searchBar.hidden) {
          event.preventDefault();
          closeSqlSearch();
        }
      } else if (event.key === "Tab") {
        event.preventDefault();
        insertEditorText("  ");
      }
    });
  }
  renderSqlHighlight();

  const runCurrentEditor = async (options = {}) => {
    window.clearTimeout(queryTimer);
    window.clearTimeout(queryTabSaveTimer);
    updateActiveQueryTabFromEditor();
    activeQueryId = null;
    activeQueryResult = null;
    resetQueryBatchResults();
    const clusterId = document.getElementById("queryCluster").value;
    if (!clusterId) {
      showToast("Select a saved running cluster.");
      return;
    }
    let statements = sqlStatementsForRunMode(editor);
    if (!statements.length) {
      showToast(currentRunMode === "selected" ? "Select SQL to run." : "Enter SQL to run.");
      return;
    }
    if (options.explain) {
      // Query plan without executing: wrap each statement in EXPLAIN
      // (or EXPLAIN ANALYZE to run and profile it).
      const keyword = options.explain === "analyze" ? "EXPLAIN ANALYZE" : "EXPLAIN";
      statements = statements.map((statement) => ({
        ...statement,
        sql: `${keyword} ${statement.sql}`,
      }));
    }
    closeSqlAutocomplete();
    run.disabled = true;
    runAndDownload.disabled = true;
    cancel.disabled = false;
    download.disabled = true;
    queryBatchCancelled = false;
    setQueryState("Queued", "0.0s", "0");

    try {
      await saveActiveQueryTabNow();
      const terminal = await runSqlStatements(clusterId, statements);
      if (statements.length > 1 && terminal) {
        if (terminal.status === "Finished" && !queryBatchCancelled) {
          showToast(`Ran ${statements.length} statements.`);
        } else if (terminal.error_message) {
          showToast(terminal.error_message);
        } else {
          showToast(`Query ${terminal.status.toLowerCase()}.`);
        }
      }
      if (options.downloadAfterFinish && !queryBatchCancelled) {
        downloadLatestBatchResult();
      }
    } catch (error) {
      showToast(error.message, { type: "error" });
    } finally {
      activeQueryId = null;
      run.disabled = false;
      runAndDownload.disabled = false;
      cancel.disabled = true;
    }
  };

  run.addEventListener("click", () => runCurrentEditor());
  runAndDownload.addEventListener("click", () => runCurrentEditor({ downloadAfterFinish: true }));
  const explainButton = document.getElementById("explainQuery");
  if (explainButton) explainButton.addEventListener("click", () => runCurrentEditor({ explain: true }));
  const explainAnalyzeButton = document.getElementById("explainAnalyzeQuery");
  if (explainAnalyzeButton) explainAnalyzeButton.addEventListener("click", () => runCurrentEditor({ explain: "analyze" }));

  cancel.addEventListener("click", async () => {
    window.clearTimeout(queryTimer);
    queryBatchCancelled = true;
    if (!activeQueryId) {
      setQueryState("Cancelled", document.getElementById("queryElapsed").textContent, "0");
      document.getElementById("resultsTable").innerHTML = '<div class="empty-results">Query cancelled.</div>';
      run.disabled = false;
      runAndDownload.disabled = false;
      cancel.disabled = true;
      download.disabled = true;
      return;
    }
    try {
      const result = await apiRequest(`/api/query/${activeQueryId}`, { method: "DELETE" });
      activeQueryId = null;
      updateBatchResult(activeQueryResultIndex, result.query);
      run.disabled = false;
      runAndDownload.disabled = false;
      cancel.disabled = true;
      download.disabled = true;
      loadQueryHistoryFromApi();
      showToast("Query cancelled.");
    } catch (error) {
      showToast(error.message, { type: "error" });
    }
  });

  download.addEventListener("click", () => {
    downloadReadyResult(activeQueryResult);
  });
}

function wireHistoryControls() {
  const search = document.getElementById("historySearch");
  const status = document.getElementById("historyStatus");
  const role = document.getElementById("historyRole");
  const date = document.getElementById("historyDate");
  if (search) {
    search.addEventListener("input", (event) => {
      historyFilter = event.target.value;
      renderHistory();
    });
  }
  if (status) {
    status.addEventListener("change", (event) => {
      historyStatusFilter = event.target.value;
      renderHistory();
    });
  }
  if (role) {
    role.addEventListener("change", (event) => {
      historyRoleFilter = event.target.value;
      renderHistory();
    });
  }
  if (date) {
    date.addEventListener("change", (event) => {
      historyDateFilter = event.target.value;
      renderHistory();
    });
  }
  document.getElementById("openHistoryQuery").addEventListener("click", openHistoryQueryInEditor);
  document.getElementById("copyHistoryQuery").addEventListener("click", copyHistoryQuerySql);
  document.getElementById("saveHistoryQuery").addEventListener("click", saveHistoryQuery);
}

// ---- Theme (light / dark) -------------------------------------------------

const THEME_KEY = "trinohub-theme";

function applyTheme(theme) {
  const normalized = theme === "dark" ? "dark" : "light";
  document.documentElement.dataset.theme = normalized;
  document.querySelectorAll("[data-theme-set]").forEach((button) => {
    button.classList.toggle("active", button.dataset.themeSet === normalized);
  });
}

function wireThemeToggle() {
  let stored = "light";
  try {
    stored = localStorage.getItem(THEME_KEY) || "light";
  } catch (err) {
    // localStorage may be unavailable (private mode); fall back to light.
  }
  applyTheme(stored);
  document.querySelectorAll("[data-theme-set]").forEach((button) => {
    button.addEventListener("click", () => {
      const theme = button.dataset.themeSet;
      applyTheme(theme);
      try {
        localStorage.setItem(THEME_KEY, theme);
      } catch (err) {
        // Ignore persistence failures.
      }
    });
  });
}

// ---- Schema browser -------------------------------------------------------

function insertAtCursor(field, text) {
  if (!field) {
    return;
  }
  const start = typeof field.selectionStart === "number" ? field.selectionStart : field.value.length;
  const end = typeof field.selectionEnd === "number" ? field.selectionEnd : field.value.length;
  field.value = field.value.slice(0, start) + text + field.value.slice(end);
  const caret = start + text.length;
  field.selectionStart = caret;
  field.selectionEnd = caret;
}

function selectedQueryCluster() {
  const clusterId = normalizedQueryClusterId();
  return clusters.find((cluster) => Number(cluster.id) === Number(clusterId)) || null;
}

function resetSchemaBrowserForSelectedCluster() {
  resetSchemaBrowserContext(sqlSchemaBrowser);
}

function resetSchemaBrowserContext(ctx) {
  const clusterId = ctx.getClusterId();
  if (ctx.state.clusterId !== clusterId) {
    ctx.state.clusterId = clusterId;
    ctx.state.expandedCatalogs.clear();
    ctx.state.expandedSchemas.clear();
    ctx.state.expandedTables.clear();
    ctx.state.schemasByCatalog = {};
    ctx.state.tablesBySchema = {};
    ctx.state.columnsByTable = {};
    ctx.state.loading.clear();
    ctx.state.errors = {};
    ctx.state.activeTable = "";
  }
  renderSchemaBrowser(ctx);
}

function quotedPathPart(value) {
  return `"${String(value).replace(/"/g, '""')}"`;
}

function quotedTablePath(catalog, schema, table) {
  return [catalog, schema, table].map(quotedPathPart).join(".");
}

function schemaBrowserKey() {
  return Array.from(arguments).join("\u001f");
}

function schemaNodeIcon(expanded) {
  return expanded ? "chevron-down" : "chevron-right";
}

function normalizedTableKind(table) {
  const type = String(table.type || "TABLE").toLowerCase();
  if (type.includes("materialized")) return { icon: "table", label: "MV" };
  if (type.includes("view")) return { icon: "visibility", label: "View" };
  return { icon: "table", label: "Table" };
}

function renderMetadataError(message, indentClass, retryAction, attrs) {
  const dataAttrs = Object.entries(attrs || {})
    .filter((entry) => entry[1] != null)
    .map(([key, value]) => `data-${key}="${escapeHtml(value)}"`)
    .join(" ");
  return `
    <div class="schema-empty metadata-error ${indentClass}">
      <span>${escapeHtml(message)}</span>
      <button type="button" data-schema-action="${retryAction}" ${dataAttrs}>Retry</button>
    </div>
  `;
}

// Global data search over the schema tree (roadmap F3). Filtering operates on
// metadata already loaded into the browser (plus catalog names), so analysts can
// locate a table/column without manually expanding every catalog.
function schemaSearchActive(ctx) {
  return ctx.searchQuery.trim().length > 0;
}

function schemaTextMatch(ctx, text) {
  return String(text || "").toLowerCase().includes(ctx.searchQuery.trim().toLowerCase());
}

function tableHasSchemaMatch(ctx, catalog, schema, table) {
  if (schemaTextMatch(ctx, table)) return true;
  const columns = ctx.state.columnsByTable[schemaBrowserKey(catalog, schema, table)] || [];
  return columns.some((column) => schemaTextMatch(ctx, column.name));
}

function schemaHasMatch(ctx, catalog, schema) {
  if (schemaTextMatch(ctx, schema)) return true;
  const tables = ctx.state.tablesBySchema[schemaBrowserKey(catalog, schema)] || [];
  return tables.some((table) => tableHasSchemaMatch(ctx, catalog, schema, table.name));
}

function catalogHasMatch(ctx, catalog) {
  if (schemaTextMatch(ctx, catalog)) return true;
  const schemas = ctx.state.schemasByCatalog[catalog] || [];
  return schemas.some((schema) => schemaHasMatch(ctx, catalog, schema.name));
}

function renderSchemaBrowser(ctx) {
  const tree = document.getElementById(ctx.treeId);
  if (!tree) return;
  const cluster = ctx.getCluster();
  if (!cluster) {
    tree.innerHTML = `<div class="schema-empty">${escapeHtml(ctx.emptyHint)}</div>`;
    return;
  }
  let catalogNames = cluster.catalogList || [];
  if (!catalogNames.length) {
    tree.innerHTML = '<div class="schema-empty">No catalogs attached.</div>';
    return;
  }
  if (schemaSearchActive(ctx)) {
    catalogNames = catalogNames.filter((catalog) => catalogHasMatch(ctx, catalog));
    if (!catalogNames.length) {
      tree.innerHTML = '<div class="schema-empty search-none">No matches in loaded metadata. Expand a catalog to load more.</div>';
      return;
    }
  }
  tree.innerHTML = catalogNames.map((catalog) => renderCatalogNode(ctx, cluster, catalog)).join("");
  replaceIcons();
}

function renderCatalogNode(ctx, cluster, catalog) {
  const searching = schemaSearchActive(ctx);
  const expanded = searching || ctx.state.expandedCatalogs.has(catalog);
  const loadingKey = schemaBrowserKey("schemas", catalog);
  const error = ctx.state.errors[loadingKey];
  let schemas = ctx.state.schemasByCatalog[catalog] || [];
  if (searching && !schemaTextMatch(ctx, catalog)) {
    schemas = schemas.filter((schema) => schemaHasMatch(ctx, catalog, schema.name));
  }
  const liveDisabled = cluster.status !== "Running";
  return `
    <div class="schema-node catalog" data-schema-action="toggle-catalog" data-catalog="${escapeHtml(catalog)}">
      <span data-icon="${schemaNodeIcon(expanded)}"></span>
      <span class="icon db" data-icon="database"></span>
      <span class="schema-node-name">${escapeHtml(catalog)}</span>
    </div>
    ${
      expanded
        ? liveDisabled
          ? '<div class="schema-empty indent-1">Start the cluster to browse schemas.</div>'
          : error
            ? renderMetadataError(error, "indent-1", "retry-catalog", { catalog })
            : ctx.state.loading.has(loadingKey)
              ? '<div class="schema-empty indent-1">Loading schemas...</div>'
              : schemas.length
                ? schemas.map((schema) => renderSchemaNode(ctx, catalog, schema.name)).join("")
                : '<div class="schema-empty indent-1">No schemas found.</div>'
        : ""
    }
  `;
}

function renderSchemaNode(ctx, catalog, schema) {
  const key = schemaBrowserKey(catalog, schema);
  const searching = schemaSearchActive(ctx);
  const schemaSelfMatch = searching && schemaTextMatch(ctx, schema);
  const expanded = (searching && !schemaSelfMatch) || ctx.state.expandedSchemas.has(key);
  const loadingKey = schemaBrowserKey("tables", catalog, schema);
  const error = ctx.state.errors[loadingKey];
  let tables = ctx.state.tablesBySchema[key] || [];
  if (searching && !schemaSelfMatch) {
    tables = tables.filter((table) => tableHasSchemaMatch(ctx, catalog, schema, table.name));
  }
  return `
    <div class="schema-node schema indent-1" data-schema-action="toggle-schema" data-catalog="${escapeHtml(catalog)}" data-schema="${escapeHtml(schema)}">
      <span data-icon="${schemaNodeIcon(expanded)}"></span>
      <span class="schema-node-name">${escapeHtml(schema)}</span>
    </div>
    ${
      expanded
        ? error
          ? renderMetadataError(error, "indent-2", "retry-schema", { catalog, schema })
          : ctx.state.loading.has(loadingKey)
            ? '<div class="schema-empty indent-2">Loading tables...</div>'
            : tables.length
              ? tables.map((table) => renderTableNode(ctx, catalog, schema, table)).join("")
              : '<div class="schema-empty indent-2">No tables found.</div>'
        : ""
    }
  `;
}

function renderTableNode(ctx, catalog, schema, table) {
  const tableName = table.name;
  const key = schemaBrowserKey(catalog, schema, tableName);
  const searching = schemaSearchActive(ctx);
  const tableSelfMatch = searching && schemaTextMatch(ctx, tableName);
  const expanded = (searching && !tableSelfMatch) || ctx.state.expandedTables.has(key);
  const active = ctx.state.activeTable === key;
  const loadingKey = schemaBrowserKey("columns", catalog, schema, tableName);
  const error = ctx.state.errors[loadingKey];
  let columns = ctx.state.columnsByTable[key] || [];
  if (searching && !tableSelfMatch) {
    columns = columns.filter((column) => schemaTextMatch(ctx, column.name));
  }
  const tableKind = normalizedTableKind(table);
  return `
    <div class="schema-node table indent-2 ${active ? "active" : ""}" data-schema-action="toggle-table" data-catalog="${escapeHtml(catalog)}" data-schema="${escapeHtml(schema)}" data-table="${escapeHtml(tableName)}">
      <span data-icon="${schemaNodeIcon(expanded)}"></span>
      <span data-icon="${tableKind.icon}"></span>
      <span class="schema-node-name">${escapeHtml(tableName)}</span>
      <small class="schema-node-kind">${escapeHtml(tableKind.label)}</small>
      <span class="schema-node-actions">
        <button type="button" data-schema-action="insert-select" data-catalog="${escapeHtml(catalog)}" data-schema="${escapeHtml(schema)}" data-table="${escapeHtml(tableName)}">SELECT</button>
        <button type="button" data-schema-action="insert-describe" data-catalog="${escapeHtml(catalog)}" data-schema="${escapeHtml(schema)}" data-table="${escapeHtml(tableName)}">DESC</button>
        <button type="button" data-schema-action="insert-show-create" data-catalog="${escapeHtml(catalog)}" data-schema="${escapeHtml(schema)}" data-table="${escapeHtml(tableName)}">DDL</button>
      </span>
    </div>
    ${
      expanded
        ? error
          ? renderMetadataError(error, "indent-3", "retry-table", { catalog, schema, table: tableName })
          : ctx.state.loading.has(loadingKey)
            ? '<div class="schema-empty indent-3">Loading columns...</div>'
            : columns.length
              ? columns.map((column) => renderColumnNode(catalog, schema, tableName, column)).join("")
              : '<div class="schema-empty indent-3">No columns found.</div>'
        : ""
    }
  `;
}

function renderColumnNode(catalog, schema, table, column) {
  return `
    <div class="schema-node column indent-3" data-schema-action="insert-column" data-catalog="${escapeHtml(catalog)}" data-schema="${escapeHtml(schema)}" data-table="${escapeHtml(table)}" data-column="${escapeHtml(column.name)}">
      <span data-icon="table"></span>
      <span class="schema-node-name">${escapeHtml(column.name)}</span>
      <small>${escapeHtml(column.type || "")}</small>
    </div>
  `;
}

async function loadClusterMetadata(ctx, params) {
  const clusterId = ctx.getClusterId();
  if (!clusterId) return null;
  const query = new URLSearchParams();
  Object.keys(params).forEach((key) => {
    if (params[key]) query.set(key, params[key]);
  });
  const suffix = query.toString() ? `?${query}` : "";
  return apiRequest(`/api/clusters/${clusterId}/metadata${suffix}`);
}

async function fetchCatalogSchemas(ctx, catalog) {
  const key = schemaBrowserKey("schemas", catalog);
  ctx.state.loading.add(key);
  delete ctx.state.errors[key];
  renderSchemaBrowser(ctx);
  try {
    const result = (await loadClusterMetadata(ctx, { catalog })) || {};
    ctx.state.schemasByCatalog[catalog] = result.schemas || [];
  } catch (error) {
    ctx.state.errors[key] = error.message;
  } finally {
    ctx.state.loading.delete(key);
    renderSchemaBrowser(ctx);
  }
}

async function fetchSchemaTables(ctx, catalog, schema) {
  const schemaKey = schemaBrowserKey(catalog, schema);
  const loadingKey = schemaBrowserKey("tables", catalog, schema);
  ctx.state.loading.add(loadingKey);
  delete ctx.state.errors[loadingKey];
  renderSchemaBrowser(ctx);
  try {
    const result = (await loadClusterMetadata(ctx, { catalog, schema })) || {};
    ctx.state.tablesBySchema[schemaKey] = result.tables || [];
  } catch (error) {
    ctx.state.errors[loadingKey] = error.message;
  } finally {
    ctx.state.loading.delete(loadingKey);
    renderSchemaBrowser(ctx);
  }
}

async function fetchTableColumns(ctx, catalog, schema, table) {
  const tableKey = schemaBrowserKey(catalog, schema, table);
  const loadingKey = schemaBrowserKey("columns", catalog, schema, table);
  ctx.state.loading.add(loadingKey);
  delete ctx.state.errors[loadingKey];
  renderSchemaBrowser(ctx);
  try {
    const result = (await loadClusterMetadata(ctx, { catalog, schema, table })) || {};
    ctx.state.columnsByTable[tableKey] = result.columns || [];
  } catch (error) {
    ctx.state.errors[loadingKey] = error.message;
  } finally {
    ctx.state.loading.delete(loadingKey);
    renderSchemaBrowser(ctx);
  }
}

async function toggleCatalog(ctx, catalog) {
  const key = schemaBrowserKey("schemas", catalog);
  if (ctx.state.expandedCatalogs.has(catalog)) {
    ctx.state.expandedCatalogs.delete(catalog);
    renderSchemaBrowser(ctx);
    return;
  }
  ctx.state.expandedCatalogs.add(catalog);
  renderSchemaBrowser(ctx);
  if (ctx.state.schemasByCatalog[catalog] || ctx.state.loading.has(key)) return;
  await fetchCatalogSchemas(ctx, catalog);
}

async function toggleSchema(ctx, catalog, schema) {
  const schemaKey = schemaBrowserKey(catalog, schema);
  const loadingKey = schemaBrowserKey("tables", catalog, schema);
  if (ctx.state.expandedSchemas.has(schemaKey)) {
    ctx.state.expandedSchemas.delete(schemaKey);
    renderSchemaBrowser(ctx);
    return;
  }
  ctx.state.expandedSchemas.add(schemaKey);
  renderSchemaBrowser(ctx);
  if (ctx.state.tablesBySchema[schemaKey] || ctx.state.loading.has(loadingKey)) return;
  await fetchSchemaTables(ctx, catalog, schema);
}

async function toggleTable(ctx, catalog, schema, table) {
  const tableKey = schemaBrowserKey(catalog, schema, table);
  const loadingKey = schemaBrowserKey("columns", catalog, schema, table);
  ctx.state.activeTable = tableKey;
  if (ctx.state.expandedTables.has(tableKey)) {
    ctx.state.expandedTables.delete(tableKey);
    renderSchemaBrowser(ctx);
    return;
  }
  ctx.state.expandedTables.add(tableKey);
  renderSchemaBrowser(ctx);
  if (ctx.state.columnsByTable[tableKey] || ctx.state.loading.has(loadingKey)) return;
  await fetchTableColumns(ctx, catalog, schema, table);
}

async function retryCatalogMetadata(ctx, catalog) {
  delete ctx.state.schemasByCatalog[catalog];
  ctx.state.expandedCatalogs.add(catalog);
  await fetchCatalogSchemas(ctx, catalog);
}

async function retrySchemaMetadata(ctx, catalog, schema) {
  const schemaKey = schemaBrowserKey(catalog, schema);
  delete ctx.state.tablesBySchema[schemaKey];
  ctx.state.expandedCatalogs.add(catalog);
  ctx.state.expandedSchemas.add(schemaKey);
  await fetchSchemaTables(ctx, catalog, schema);
}

async function retryTableMetadata(ctx, catalog, schema, table) {
  const schemaKey = schemaBrowserKey(catalog, schema);
  const tableKey = schemaBrowserKey(catalog, schema, table);
  delete ctx.state.columnsByTable[tableKey];
  ctx.state.expandedCatalogs.add(catalog);
  ctx.state.expandedSchemas.add(schemaKey);
  ctx.state.expandedTables.add(tableKey);
  ctx.state.activeTable = tableKey;
  await fetchTableColumns(ctx, catalog, schema, table);
}

function insertSchemaAction(ctx, action, catalog, schema, table, column) {
  const tablePath = quotedTablePath(catalog, schema, table);
  if (action === "insert-select") {
    ctx.insertText(`SELECT *\nFROM ${tablePath}\nLIMIT 10;`);
  } else if (action === "insert-describe") {
    ctx.insertText(`DESCRIBE ${tablePath};`);
  } else if (action === "insert-show-create") {
    ctx.insertText(`SHOW CREATE TABLE ${tablePath};`);
  } else if (action === "insert-column") {
    ctx.insertText(quotedPathPart(column));
  }
}

function wireSchemaBrowser(ctx) {
  const tree = document.getElementById(ctx.treeId);
  if (!tree) return;
  tree.addEventListener("click", (event) => {
    const actionNode = event.target.closest("[data-schema-action]");
    if (!actionNode) return;
    event.stopPropagation();
    const { schemaAction, catalog, schema, table, column } = actionNode.dataset;
    if (schemaAction === "toggle-catalog") {
      toggleCatalog(ctx, catalog);
    } else if (schemaAction === "toggle-schema") {
      toggleSchema(ctx, catalog, schema);
    } else if (schemaAction === "toggle-table") {
      toggleTable(ctx, catalog, schema, table);
    } else if (schemaAction === "retry-catalog") {
      retryCatalogMetadata(ctx, catalog);
    } else if (schemaAction === "retry-schema") {
      retrySchemaMetadata(ctx, catalog, schema);
    } else if (schemaAction === "retry-table") {
      retryTableMetadata(ctx, catalog, schema, table);
    } else if (
      schemaAction === "insert-select" ||
      schemaAction === "insert-describe" ||
      schemaAction === "insert-show-create" ||
      schemaAction === "insert-column"
    ) {
      insertSchemaAction(ctx, schemaAction, catalog, schema, table, column);
    }
  });
  const search = document.getElementById(ctx.searchId);
  if (search) {
    search.addEventListener("input", (event) => {
      ctx.searchQuery = event.target.value;
      renderSchemaBrowser(ctx);
    });
  }
  renderSchemaBrowser(ctx);
}

function applyRoleMode() {
  const role = document.getElementById("roleSelect").value;
  document.body.classList.toggle("user-mode", role === "user");
  document.querySelectorAll(".admin-action").forEach((control) => {
    // Buttons can also be disabled by state (e.g. Start on a Running cluster);
    // don't let a role toggle re-enable those.
    control.disabled = role === "user" || control.dataset.statusDisabled === "1";
  });
}

function wireRoleSwitcher() {
  document.getElementById("roleSelect").addEventListener("change", (event) => {
    applyRoleMode();
    if (event.target.value === "user") {
      const activeView = document.querySelector(".view.active");
      if (activeView && ["view-users", "view-settings", "view-create"].includes(activeView.id)) {
        navigateTo("sql");
      }
      showToast("Viewing as analyst (query-only). The API still enforces your real role.");
    } else {
      showToast("Viewing as admin.");
    }
  });
}

async function refreshAuthMethods() {
  const ssoButton = document.getElementById("ssoLoginButton");
  if (!ssoButton) return;
  try {
    const methods = await apiRequest("/api/auth/methods");
    ssoButton.hidden = !methods.oidc;
  } catch (error) {
    ssoButton.hidden = true;
  }
}

function showLogin(message) {
  const screen = document.getElementById("loginScreen");
  screen.hidden = false;
  refreshAuthMethods();
  const params = new URLSearchParams(window.location.search);
  const ssoError = params.get("sso_error");
  if (ssoError && !message) message = `SSO sign-in failed: ${ssoError}`;
  const error = document.getElementById("loginError");
  if (message) {
    error.textContent = message;
    error.hidden = false;
  } else {
    error.hidden = true;
    error.textContent = "";
  }
  document.getElementById("loginPassword").value = "";
  setAccountBadge(null);
  applyRoleConstraints();
  const username = document.getElementById("loginUsername");
  if (username && !username.value) {
    username.focus();
  }
}

function hideLogin() {
  document.getElementById("loginScreen").hidden = true;
}

function setAccountBadge(user) {
  const menu = document.getElementById("accountMenu");
  if (user) {
    document.getElementById("accountName").textContent = `${user.username} (${user.role})`;
    menu.hidden = false;
  } else {
    menu.hidden = true;
  }
}

function applyRoleConstraints() {
  // The "View as" switcher is an admin-only preview: the API enforces the
  // signed-in user's real role regardless, so showing it to analysts (or on
  // the login/setup screens) only invites confusion.
  const roleSelect = document.getElementById("roleSelect");
  const switcher = document.getElementById("roleSwitcher");
  if (currentUser) {
    roleSelect.value = currentUser.role;
    roleSelect.disabled = currentUser.role !== "admin";
    if (switcher) switcher.hidden = currentUser.role !== "admin";
  } else {
    roleSelect.disabled = false;
    if (switcher) switcher.hidden = true;
  }
}

function onAuthenticated(user) {
  currentUser = user;
  hideLogin();
  setAccountBadge(user);
  applyRoleConstraints();
  applyRoleMode();
  // First-run setup is only relevant before the control plane is configured.
  const setupNav = document.querySelector('[data-view-target="setup"]');
  if (setupNav) {
    setupNav.hidden = true;
  }
  loadLiveSetupStatus();
  loadPresetTiers();
  loadInstanceTypes();
  loadTrinoVersions();
  loadQueryTabsFromApi();
  loadSavedQueriesFromApi();
  loadNotebooksFromApi();
  loadDocsManifest();
  navigateTo(user.role === "admin" ? "clusters" : "sql");
}

function handleSessionExpired() {
  currentUser = null;
  clusters.splice(0, clusters.length);
  queryTabs.splice(0, queryTabs.length);
  savedQueries.splice(0, savedQueries.length);
  activeQueryTabId = null;
  resetNotebookState();
  resetDocsState();
  renderQueryTabs();
  renderSavedQueries();
  showLogin("Your session expired. Please sign in again.");
}

async function doLogin(event) {
  event.preventDefault();
  const username = document.getElementById("loginUsername").value.trim();
  const password = document.getElementById("loginPassword").value;
  const submit = document.getElementById("loginSubmit");
  const error = document.getElementById("loginError");
  error.hidden = true;
  submit.disabled = true;
  try {
    const result = await apiRequest("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password })
    });
    onAuthenticated(result.user);
  } catch (err) {
    error.textContent = err.message;
    error.hidden = false;
  } finally {
    submit.disabled = false;
  }
}

async function doLogout() {
  try {
    await apiRequest("/api/auth/logout", { method: "POST", body: JSON.stringify({}) });
  } catch (err) {
    // Even if the server call fails, drop the local authenticated view.
  }
  currentUser = null;
  clusters.splice(0, clusters.length);
  queryTabs.splice(0, queryTabs.length);
  savedQueries.splice(0, savedQueries.length);
  activeQueryTabId = null;
  resetNotebookState();
  resetDocsState();
  renderClusters();
  renderQueryTabs();
  renderSavedQueries();
  showLogin();
  showToast("Signed out.");
}

function wireAuth() {
  document.getElementById("loginForm").addEventListener("submit", doLogin);
  document.getElementById("logoutButton").addEventListener("click", doLogout);
}

async function initAuth() {
  let me = null;
  try {
    const result = await apiRequest("/api/me");
    me = result.user;
  } catch (err) {
    // /api/me does not require auth; a failure means the API is unreachable.
  }
  if (me) {
    onAuthenticated(me);
    return;
  }
  let configured = false;
  try {
    const status = await apiRequest("/api/setup/status");
    configured = Boolean(status.configured);
  } catch (err) {
    // Treat an unreachable status endpoint as "not configured".
  }
  if (configured) {
    showLogin();
  } else {
    // First-run: show the setup wizard; no login required until an admin exists.
    hideLogin();
    setAccountBadge(null);
    navigateTo("setup");
    loadLiveSetupStatus();
  }
}

// ---------------------------------------------------------------------------
// Notebooks
// ---------------------------------------------------------------------------

function relativeTime(iso) {
  if (!iso) return "";
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return iso;
  const seconds = Math.round((Date.now() - then) / 1000);
  if (seconds < 45) return "just now";
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  if (days < 30) return `${days}d ago`;
  return new Date(then).toLocaleDateString();
}

function resetNotebookState() {
  cellRuntime.forEach((runtime) => {
    runtime.runSeq += 1;
  });
  notebooks.splice(0, notebooks.length);
  notebookCells.splice(0, notebookCells.length);
  cellRuntime.clear();
  activeNotebookId = null;
  const canvas = document.getElementById("notebookCanvas");
  const listPane = document.getElementById("notebookListPane");
  if (canvas) canvas.hidden = true;
  if (listPane) listPane.hidden = false;
  renderNotebookList();
}

async function loadNotebooksFromApi() {
  if (!currentUser) return;
  try {
    const result = await apiRequest("/api/notebooks");
    notebooks.splice.apply(notebooks, [0, notebooks.length].concat(result.notebooks || []));
    renderNotebookList();
  } catch (error) {
    if (!/Authentication required/.test(error.message)) showToast(error.message, { type: "error" });
  }
}

function clusterOptionsHtml(selectedId, defaultLabel) {
  const saved = clusters.filter((cluster) => cluster.id);
  // With no clusters at all, a placeholder like "Notebook default" or "Select
  // cluster…" implies a selectable default that doesn't exist — say so plainly.
  if (!saved.length) {
    return '<option value="">No clusters available</option>';
  }
  const options = [];
  if (defaultLabel) {
    options.push(`<option value=""${!selectedId ? " selected" : ""}>${escapeHtml(defaultLabel)}</option>`);
  }
  saved.forEach((cluster) => {
    const selected = String(cluster.id) === String(selectedId) ? " selected" : "";
    options.push(`<option value="${cluster.id}"${selected}>${escapeHtml(cluster.name)} - ${escapeHtml(cluster.status)}</option>`);
  });
  return options.join("");
}

function activeNotebook() {
  return notebooks.find((item) => item.id === activeNotebookId) || null;
}

function activeNotebookCluster() {
  const notebook = activeNotebook();
  if (!notebook || !notebook.cluster_id) return null;
  return clusters.find((cluster) => Number(cluster.id) === Number(notebook.cluster_id)) || null;
}

function populateNotebookClusterOptions() {
  const select = document.getElementById("notebookCluster");
  if (select) {
    const notebook = activeNotebook();
    select.innerHTML = clusterOptionsHtml(notebook ? notebook.cluster_id : "", "Select cluster…");
  }
  document.querySelectorAll("[data-cell-cluster]").forEach((sel) => {
    const holder = sel.closest("[data-cell-id]");
    if (!holder) return;
    const cell = notebookCells.find((item) => item.id === Number(holder.dataset.cellId));
    sel.innerHTML = clusterOptionsHtml(cell ? cell.cluster_id : "", "Notebook default");
  });
  populateNotebookContextSelects();
  // Cluster status feeds the tree's "start the cluster" hints, so keep it live.
  renderSchemaBrowser(notebookSchemaBrowser);
}

// A notebook with no cluster picked defaults to the only running cluster —
// same convenience the SQL editor gives. Runs on open and again whenever
// cluster data refreshes, so a cluster that finishes starting gets adopted.
function maybeDefaultNotebookCluster() {
  const notebook = activeNotebook();
  if (!notebook || notebook.cluster_id) return;
  const running = clusters.filter((cluster) => cluster.status === "Running" && cluster.id);
  if (running.length !== 1) return;
  notebook.cluster_id = running[0].id;
  populateNotebookClusterOptions();
  resetSchemaBrowserContext(notebookSchemaBrowser);
  patchNotebook({ cluster_id: running[0].id });
}

function notebookCatalogNames(clusterId) {
  const cluster = clusterId
    ? clusters.find((item) => Number(item.id) === Number(clusterId))
    : null;
  if (cluster && Array.isArray(cluster.catalogList) && cluster.catalogList.length) {
    return cluster.catalogList;
  }
  return catalogRecords.filter((catalog) => catalog.enabled).map((catalog) => catalog.name);
}

function fillContextSelect(select, names, selectedValue, defaultLabel) {
  if (!select) return;
  const options = [`<option value=""${selectedValue ? "" : " selected"}>${escapeHtml(defaultLabel)}</option>`];
  const seen = new Set();
  names.forEach((name) => {
    if (seen.has(name)) return;
    seen.add(name);
    const selected = name === selectedValue ? " selected" : "";
    options.push(`<option value="${escapeHtml(name)}"${selected}>${escapeHtml(name)}</option>`);
  });
  // A saved value the current option source doesn't know about (cluster
  // detached, metadata not loaded yet) must survive re-rendering.
  if (selectedValue && !seen.has(selectedValue)) {
    options.push(`<option value="${escapeHtml(selectedValue)}" selected>${escapeHtml(selectedValue)}</option>`);
  }
  select.innerHTML = options.join("");
}

function cachedNotebookSchemaNames(catalog) {
  if (!catalog) return null;
  const schemas = notebookSchemaBrowser.state.schemasByCatalog[catalog];
  return schemas ? schemas.map((schema) => schema.name) : null;
}

// Load a catalog's schemas into the notebook browser cache (running cluster
// only), then refresh the selects that were rendered without them.
async function ensureNotebookSchemas(catalog) {
  if (!catalog || cachedNotebookSchemaNames(catalog)) return;
  const cluster = activeNotebookCluster();
  if (!cluster || cluster.status !== "Running") return;
  if (notebookSchemaBrowser.state.loading.has(schemaBrowserKey("schemas", catalog))) return;
  await fetchCatalogSchemas(notebookSchemaBrowser, catalog);
  populateNotebookContextSelects();
}

// Notebook-level and per-cell catalog/schema selects mirror the SQL editor's
// context pills: catalogs come from the effective cluster's attachments and
// schemas from live cluster metadata. Cells inherit the notebook default via
// an empty-value option.
function populateNotebookContextSelects() {
  const notebook = activeNotebook();
  if (!notebook) return;
  const catalogs = notebookCatalogNames(notebook.cluster_id);
  fillContextSelect(document.getElementById("notebookCatalog"), catalogs, notebook.catalog || "", "No default");
  const notebookSchemas = cachedNotebookSchemaNames(notebook.catalog);
  fillContextSelect(document.getElementById("notebookSchema"), notebookSchemas || [], notebook.schema || "", "No default");
  if (notebook.catalog && !notebookSchemas) ensureNotebookSchemas(notebook.catalog);

  document.querySelectorAll(".notebook-cell").forEach((node) => {
    const cell = notebookCells.find((item) => item.id === Number(node.dataset.cellId));
    if (!cell) return;
    const cellCatalogs = notebookCatalogNames(cell.cluster_id || notebook.cluster_id);
    fillContextSelect(node.querySelector("[data-cell-catalog]"), cellCatalogs, cell.catalog || "", "Notebook default");
    // Schemas are cached per catalog against the notebook's cluster; a cell
    // overriding to a different cluster still gets a usable list plus its own
    // saved value.
    const effectiveCatalog = cell.catalog || notebook.catalog || "";
    const cellSchemas = cachedNotebookSchemaNames(effectiveCatalog);
    fillContextSelect(node.querySelector("[data-cell-schema]"), cellSchemas || [], cell.schema || "", "Notebook default");
    if (effectiveCatalog && !cellSchemas) ensureNotebookSchemas(effectiveCatalog);
  });
}

function insertNotebookCellText(text) {
  let node = lastFocusedNotebookCellId != null
    ? document.querySelector(`.notebook-cell[data-cell-id="${lastFocusedNotebookCellId}"]`)
    : null;
  if (!node) node = document.querySelector(".notebook-cell");
  if (!node) {
    showToast("Add a cell to insert SQL into.");
    return;
  }
  const editor = node.querySelector(".notebook-cell-sql");
  insertAtCursor(editor, text);
  const cell = notebookCells.find((item) => item.id === Number(node.dataset.cellId));
  if (cell) {
    cell.sql = editor.value;
    scheduleCellSave(cell.id);
  }
  editor.focus();
}

function renderNotebookList() {
  const list = document.getElementById("notebookList");
  if (!list) return;

  if (!notebooks.length) {
    list.classList.add("is-empty");
    list.innerHTML = `
      <div class="notebook-empty">
        <span class="notebook-empty-icon" data-icon="book"></span>
        <h3>Create your first notebook</h3>
        <p>Notebooks let you organize SQL into runnable cells, keep queries and their results side by side, and save an analysis you can come back to — all against your Trino clusters.</p>
        <button class="primary-button" type="button" data-new-notebook><span data-icon="plus"></span> New notebook</button>
      </div>`;
    const cta = list.querySelector("[data-new-notebook]");
    if (cta) cta.addEventListener("click", createNotebook);
    replaceIcons();
    return;
  }

  list.classList.remove("is-empty");
  const sorted = notebooks.slice().sort((a, b) => (a.position - b.position) || (a.id - b.id));
  list.innerHTML = "";

  sorted.forEach((notebook) => {
    const card = document.createElement("div");
    card.className = "notebook-card";
    card.dataset.openNotebook = notebook.id;
    const context = [notebook.catalog, notebook.schema].filter(Boolean).join(".") || "No default context";
    const cluster = notebook.cluster_id ? clusterNameForId(notebook.cluster_id) : "No cluster";
    const cellPart = notebook.cell_count != null
      ? `${notebook.cell_count} cell${notebook.cell_count === 1 ? "" : "s"} · ` : "";
    const updated = notebook.updated_at ? `edited ${relativeTime(notebook.updated_at)}` : "draft";
    const sharedNote = notebook.shared_access
      ? `Shared by ${notebook.owner_username} (${notebook.shared_access}) · `
      : "";
    card.innerHTML = `
      <div class="notebook-card-top">
        <span class="notebook-card-icon" data-icon="book"></span>
        ${
          notebook.shared_access
            ? ""
            : `<button class="notebook-card-delete" type="button" data-share-notebook="${notebook.id}" aria-label="Share notebook" title="Share notebook">
          <span data-icon="users"></span>
        </button>
        <button class="notebook-card-delete" type="button" data-delete-notebook="${notebook.id}" aria-label="Delete notebook" title="Delete notebook">
          <span data-icon="trash"></span>
        </button>`
        }
      </div>
      <div class="notebook-card-body">
        <strong>${escapeHtml(notebook.name)}</strong>
        <span class="notebook-card-meta">${escapeHtml(sharedNote)}${cellPart}${escapeHtml(updated)}</span>
      </div>
      <div class="notebook-card-footer">
        <span class="notebook-card-cluster" title="${escapeHtml(cluster)} · ${escapeHtml(context)}"><span data-icon="server"></span>${escapeHtml(cluster)}</span>
        <span class="notebook-card-open-hint">Open <span data-icon="chevron-right"></span></span>
      </div>`;
    list.append(card);
  });

  const add = document.createElement("button");
  add.type = "button";
  add.className = "notebook-add-tile";
  add.innerHTML = `
    <span class="notebook-add-icon" data-icon="plus"></span>
    <span class="notebook-add-title">New notebook</span>
    <span class="notebook-add-sub">Start from a blank cell</span>`;
  add.addEventListener("click", createNotebook);
  list.append(add);

  list.querySelectorAll(".notebook-card").forEach((card) => {
    card.addEventListener("click", () => openNotebook(Number(card.dataset.openNotebook)));
  });
  list.querySelectorAll("[data-delete-notebook]").forEach((button) => {
    button.addEventListener("click", (e) => {
      e.stopPropagation();
      const id = Number(button.dataset.deleteNotebook);
      const notebook = notebooks.find((item) => item.id === id);
      deleteNotebook(id, notebook ? notebook.name : "");
    });
  });
  list.querySelectorAll("[data-share-notebook]").forEach((button) => {
    button.addEventListener("click", (e) => {
      e.stopPropagation();
      openShareDialog("notebook", "/api/notebooks", Number(button.dataset.shareNotebook));
    });
  });

  replaceIcons();
}

async function createNotebook() {
  const name = await appPrompt({
    title: "New notebook",
    label: "Notebook name",
    value: "Untitled notebook",
    confirmLabel: "Create",
  });
  if (name === null) return;
  const trimmed = name.trim();
  if (!trimmed) {
    showToast("Notebook name is required.");
    return;
  }
  try {
    const result = await apiRequest("/api/notebooks", { method: "POST", body: JSON.stringify({ name: trimmed }) });
    await loadNotebooksFromApi();
    openNotebook(result.notebook.id);
  } catch (error) {
    if (!/Authentication required/.test(error.message)) showToast(error.message, { type: "error" });
  }
}

async function deleteNotebook(id, name) {
  const confirmed = await appConfirm({
    title: `Delete notebook "${name}"?`,
    body: "All cells and their saved results are removed. This cannot be undone.",
    confirmLabel: "Delete notebook",
    danger: true,
  });
  if (!confirmed) return;
  try {
    await apiRequest(`/api/notebooks/${id}`, { method: "DELETE", body: JSON.stringify({}) });
    if (activeNotebookId === id) closeNotebook();
    await loadNotebooksFromApi();
    showToast("Notebook deleted.");
  } catch (error) {
    if (!/Authentication required/.test(error.message)) showToast(error.message, { type: "error" });
  }
}

async function patchNotebook(patch) {
  if (!activeNotebookId) return;
  try {
    const result = await apiRequest(`/api/notebooks/${activeNotebookId}`, {
      method: "PATCH",
      body: JSON.stringify(patch)
    });
    const notebook = notebooks.find((item) => item.id === activeNotebookId);
    if (notebook && result.notebook) Object.assign(notebook, result.notebook);
    renderNotebookList();
  } catch (error) {
    if (!/Authentication required/.test(error.message)) showToast(error.message, { type: "error" });
  }
}

function debounceNotebookField(field, fn) {
  if (notebookFieldTimers[field]) window.clearTimeout(notebookFieldTimers[field]);
  notebookFieldTimers[field] = window.setTimeout(fn, 600);
}

async function openNotebook(id) {
  try {
    const result = await apiRequest(`/api/notebooks/${id}/cells`);
    activeNotebookId = id;
    lastFocusedNotebookCellId = null;
    notebookCells.splice(0, notebookCells.length, ...(result.cells || []));
    cellRuntime.clear();
    notebookCells.forEach(initCellRuntime);
    const notebook = notebooks.find((item) => item.id === id);
    document.getElementById("notebookName").value = notebook ? notebook.name : "";
    document.getElementById("notebookListPane").hidden = true;
    document.getElementById("notebookCanvas").hidden = false;
    renderNotebookCells();
    populateNotebookClusterOptions();
    maybeDefaultNotebookCluster();
    resetSchemaBrowserContext(notebookSchemaBrowser);
    restoreNotebookCellResults(id);
  } catch (error) {
    if (!/Authentication required/.test(error.message)) showToast(error.message, { type: "error" });
  }
}

// Bring back the last run's results for each cell so a saved analysis reopens
// with its tables/charts instead of empty "Run this cell" placeholders.
async function restoreNotebookCellResults(notebookId) {
  const targets = notebookCells.filter((cell) => cell.last_query_id);
  await Promise.all(
    targets.map(async (cell) => {
      const runtime = cellRuntime.get(cell.id);
      if (!runtime || runtime.result || runtime.running) return;
      const token = runtime.runSeq;
      try {
        const result = await apiRequest(`/api/query/${cell.last_query_id}`);
        if (activeNotebookId !== notebookId || runtime.runSeq !== token) return;
        const query = result.query;
        if (!query || !isTerminalQueryStatus(query.status)) return;
        runtime.result = query;
        runtime.status = query.status;
        setCellStatus(cell.id);
        renderCellResult(cell.id);
        updateCellCsvButton(cell.id);
      } catch (error) {
        // A pruned or no-longer-accessible run just means nothing to restore.
      }
    })
  );
}

function closeNotebook() {
  // Abort any in-flight cell polls so they don't write into a closed notebook.
  cellRuntime.forEach((runtime) => {
    runtime.runSeq += 1;
  });
  activeNotebookId = null;
  notebookCells.splice(0, notebookCells.length);
  cellRuntime.clear();
  document.getElementById("notebookCanvas").hidden = true;
  document.getElementById("notebookListPane").hidden = false;
}

function initCellRuntime(cell) {
  if (cellRuntime.has(cell.id)) return;
  const config = cell.chart_config || {};
  cellRuntime.set(cell.id, {
    status: "Ready",
    result: null,
    error: null,
    activeQueryId: null,
    running: false,
    runSeq: 0,
    view: cell.view_pref === "chart" ? "chart" : "table",
    chartState: {
      type: config.type || "bar",
      x: config.x != null ? String(config.x) : "",
      y: config.y != null ? String(config.y) : ""
    }
  });
}

function renderNotebookCells() {
  const container = document.getElementById("notebookCells");
  if (!container) return;
  notebookCells.sort((a, b) => (a.position - b.position) || (a.id - b.id));
  container.innerHTML = "";
  notebookCells.forEach((cell, index) => {
    initCellRuntime(cell);
    container.append(cellNode(cell, index));
    renderCellResult(cell.id);
    updateCellCsvButton(cell.id);
  });
  replaceIcons();
}

function cellNode(cell, index) {
  const runtime = cellRuntime.get(cell.id);
  const node = document.createElement("div");
  node.className = "notebook-cell";
  node.dataset.cellId = cell.id;
  node.innerHTML = `
    <div class="notebook-cell-toolbar">
      <span class="notebook-cell-index">[${index + 1}]</span>
      <label class="cell-context-pill"><span>Cluster</span><select data-cell-cluster></select></label>
      <label class="cell-context-pill"><span>Catalog</span><select data-cell-catalog></select></label>
      <label class="cell-context-pill"><span>Schema</span><select data-cell-schema></select></label>
      <span class="chip ${statusClass(runtime.status)}" data-cell-status>${escapeHtml(runtime.status)}</span>
      <div class="cell-toolbar-spacer"></div>
      <div class="cell-view-toggle" role="group" aria-label="Result view">
        <button type="button" data-cell-view="table" class="${runtime.view === "table" ? "active" : ""}">Table</button>
        <button type="button" data-cell-view="chart" class="${runtime.view === "chart" ? "active" : ""}">Chart</button>
      </div>
      <button class="ghost-button" type="button" data-cell-move="up" aria-label="Move cell up" title="Move up"><span data-icon="chevron-up"></span></button>
      <button class="ghost-button" type="button" data-cell-move="down" aria-label="Move cell down" title="Move down"><span data-icon="chevron-down"></span></button>
      <button class="ghost-button" type="button" data-cell-csv aria-label="Download CSV" title="Download CSV" disabled><span data-icon="download"></span></button>
      <button class="ghost-button" type="button" data-cell-delete aria-label="Delete cell" title="Delete cell"><span data-icon="trash"></span></button>
      <button class="primary-button" type="button" data-cell-run><span data-icon="play"></span>Run</button>
    </div>
    <textarea class="sql-editor notebook-cell-sql" spellcheck="false"></textarea>
    <div class="results-table notebook-cell-result" data-cell-result></div>
  `;

  node.querySelector(".notebook-cell-sql").value = cell.sql || "";
  node.querySelector("[data-cell-cluster]").innerHTML = clusterOptionsHtml(cell.cluster_id, "Notebook default");

  const textarea = node.querySelector(".notebook-cell-sql");
  textarea.addEventListener("focus", () => {
    lastFocusedNotebookCellId = cell.id;
  });
  textarea.addEventListener("input", (event) => {
    cell.sql = event.target.value;
    scheduleCellSave(cell.id);
  });
  textarea.addEventListener("keydown", (event) => {
    if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
      event.preventDefault();
      runCell(cell.id);
    }
  });
  node.querySelector("[data-cell-cluster]").addEventListener("change", (event) => {
    cell.cluster_id = event.target.value ? Number(event.target.value) : null;
    patchCell(cell.id, { cluster_id: cell.cluster_id });
    populateNotebookContextSelects();
  });
  node.querySelector("[data-cell-catalog]").addEventListener("change", (event) => {
    cell.catalog = event.target.value;
    // A new catalog invalidates the old schema pick.
    cell.schema = "";
    patchCell(cell.id, { catalog: cell.catalog, schema: "" });
    populateNotebookContextSelects();
  });
  node.querySelector("[data-cell-schema]").addEventListener("change", (event) => {
    cell.schema = event.target.value;
    patchCell(cell.id, { schema: cell.schema });
  });
  node.querySelectorAll("[data-cell-view]").forEach((button) => {
    button.addEventListener("click", () => {
      runtime.view = button.dataset.cellView;
      node.querySelectorAll("[data-cell-view]").forEach((other) => {
        other.classList.toggle("active", other.dataset.cellView === runtime.view);
      });
      patchCell(cell.id, { view_pref: runtime.view });
      renderCellResult(cell.id);
    });
  });
  node.querySelector("[data-cell-run]").addEventListener("click", () => runCell(cell.id));
  node.querySelector('[data-cell-move="up"]').addEventListener("click", () => moveCell(cell.id, "up"));
  node.querySelector('[data-cell-move="down"]').addEventListener("click", () => moveCell(cell.id, "down"));
  node.querySelector("[data-cell-csv]").addEventListener("click", () => {
    if (runtime.result) downloadQueryCsv(runtime.result);
  });
  node.querySelector("[data-cell-delete]").addEventListener("click", () => deleteNotebookCell(cell.id));
  return node;
}

function scheduleCellSave(cellId) {
  if (cellSaveTimers.has(cellId)) window.clearTimeout(cellSaveTimers.get(cellId));
  cellSaveTimers.set(cellId, window.setTimeout(() => {
    cellSaveTimers.delete(cellId);
    const node = document.querySelector(`.notebook-cell[data-cell-id="${cellId}"]`);
    if (!node) return;
    patchCell(cellId, {
      sql: node.querySelector(".notebook-cell-sql").value,
      catalog: node.querySelector("[data-cell-catalog]").value.trim(),
      schema: node.querySelector("[data-cell-schema]").value.trim()
    });
  }, 700));
}

// Read live editor/input values back into the cell model before any operation
// that consumes the model or rebuilds the DOM, so unsaved keystrokes survive.
function syncCellEditorsToModel() {
  document.querySelectorAll(".notebook-cell").forEach((node) => {
    const cell = notebookCells.find((item) => item.id === Number(node.dataset.cellId));
    if (!cell) return;
    cell.sql = node.querySelector(".notebook-cell-sql").value;
    cell.catalog = node.querySelector("[data-cell-catalog]").value.trim();
    cell.schema = node.querySelector("[data-cell-schema]").value.trim();
  });
}

async function patchCell(cellId, patch) {
  if (!activeNotebookId) return null;
  try {
    const result = await apiRequest(`/api/notebooks/${activeNotebookId}/cells/${cellId}`, {
      method: "PATCH",
      body: JSON.stringify(patch)
    });
    const cell = notebookCells.find((item) => item.id === cellId);
    if (cell && result.cell) Object.assign(cell, result.cell);
    return result.cell;
  } catch (error) {
    if (!/Authentication required/.test(error.message)) showToast(error.message, { type: "error" });
    return null;
  }
}

async function addNotebookCell() {
  if (!activeNotebookId) return;
  syncCellEditorsToModel();
  try {
    const result = await apiRequest(`/api/notebooks/${activeNotebookId}/cells`, {
      method: "POST",
      body: JSON.stringify({ sql: "" })
    });
    notebookCells.push(result.cell);
    initCellRuntime(result.cell);
    renderNotebookCells();
    populateNotebookClusterOptions();
  } catch (error) {
    if (!/Authentication required/.test(error.message)) showToast(error.message, { type: "error" });
  }
}

async function deleteNotebookCell(cellId) {
  syncCellEditorsToModel();
  try {
    await apiRequest(`/api/notebooks/${activeNotebookId}/cells/${cellId}`, {
      method: "DELETE",
      body: JSON.stringify({})
    });
    const runtime = cellRuntime.get(cellId);
    if (runtime) runtime.runSeq += 1; // abort any in-flight poll
    cellRuntime.delete(cellId);
    const index = notebookCells.findIndex((item) => item.id === cellId);
    if (index >= 0) notebookCells.splice(index, 1);
    renderNotebookCells();
    populateNotebookClusterOptions();
  } catch (error) {
    if (!/Authentication required/.test(error.message)) showToast(error.message, { type: "error" });
  }
}

async function moveCell(cellId, direction) {
  syncCellEditorsToModel();
  notebookCells.sort((a, b) => (a.position - b.position) || (a.id - b.id));
  const index = notebookCells.findIndex((item) => item.id === cellId);
  const swapIndex = direction === "up" ? index - 1 : index + 1;
  if (swapIndex < 0 || swapIndex >= notebookCells.length) return;
  const current = notebookCells[index];
  const neighbor = notebookCells[swapIndex];
  const currentPosition = current.position;
  const neighborPosition = neighbor.position;
  await patchCell(current.id, { position: neighborPosition });
  await patchCell(neighbor.id, { position: currentPosition });
  renderNotebookCells();
  populateNotebookClusterOptions();
}

function setCellStatus(cellId) {
  const node = document.querySelector(`.notebook-cell[data-cell-id="${cellId}"]`);
  if (!node) return;
  const runtime = cellRuntime.get(cellId);
  const chip = node.querySelector("[data-cell-status]");
  if (chip) {
    chip.textContent = runtime.status;
    chip.className = `chip ${statusClass(runtime.status)}`;
  }
}

function updateCellCsvButton(cellId) {
  const node = document.querySelector(`.notebook-cell[data-cell-id="${cellId}"]`);
  if (!node) return;
  const runtime = cellRuntime.get(cellId);
  const button = node.querySelector("[data-cell-csv]");
  if (button) button.disabled = !(runtime.result && runtime.result.data && runtime.result.data.length);
}

async function runCell(cellId) {
  syncCellEditorsToModel();
  const cell = notebookCells.find((item) => item.id === cellId);
  const runtime = cellRuntime.get(cellId);
  if (!cell || !runtime) return null;
  const sql = (cell.sql || "").trim();
  if (!sql) {
    showToast("Enter SQL in this cell before running.");
    return null;
  }
  const notebook = notebooks.find((item) => item.id === activeNotebookId);
  const clusterId = cell.cluster_id || (notebook && notebook.cluster_id);
  if (!clusterId) {
    showToast("Pick a cluster for this notebook or cell before running.");
    return null;
  }
  const catalog = cell.catalog || (notebook && notebook.catalog) || "";
  const schema = cell.schema || (notebook && notebook.schema) || "";
  const token = (runtime.runSeq += 1);
  runtime.running = true;
  runtime.error = null;
  runtime.status = "Queued";
  setCellStatus(cellId);
  renderCellResult(cellId);
  try {
    const result = await apiRequest("/api/query", {
      method: "POST",
      body: JSON.stringify({ cluster_id: Number(clusterId), catalog, schema, sql })
    });
    if (runtime.runSeq !== token) return null;
    let query = result.query;
    runtime.activeQueryId = query.id;
    // A query submitted to an auto-suspended cluster stays Queued while the
    // cluster resumes; show "Starting cluster" instead of a stuck "Queued".
    runtime.status = query.pending_cluster_start ? "Starting cluster" : query.status;
    setCellStatus(cellId);
    renderCellResult(cellId);
    while (!isTerminalQueryStatus(query.status)) {
      await delay(1000);
      if (runtime.runSeq !== token) return null;
      const poll = await apiRequest(`/api/query/${query.id}`);
      query = poll.query;
      runtime.status = query.pending_cluster_start ? "Starting cluster" : query.status;
      setCellStatus(cellId);
      renderCellResult(cellId);
    }
    if (runtime.runSeq !== token) return null;
    runtime.result = query;
    runtime.status = query.status;
    runtime.running = false;
    runtime.activeQueryId = null;
    setCellStatus(cellId);
    updateCellCsvButton(cellId);
    renderCellResult(cellId);
    // Remember the run so reopening the notebook can restore this result.
    cell.last_query_id = query.id;
    patchCell(cellId, { last_query_id: query.id });
    if (query.status !== "Finished" && query.error_message) showToast(query.error_message);
    return query;
  } catch (error) {
    if (runtime.runSeq !== token) return null;
    runtime.running = false;
    runtime.status = "Failed";
    runtime.error = error.message;
    runtime.activeQueryId = null;
    setCellStatus(cellId);
    renderCellResult(cellId);
    if (!/Authentication required/.test(error.message)) showToast(error.message, { type: "error" });
    return null;
  }
}

async function runAllCells() {
  if (!activeNotebookId) return;
  syncCellEditorsToModel();
  notebookCells.sort((a, b) => (a.position - b.position) || (a.id - b.id));
  for (const cell of notebookCells.slice()) {
    if (!(cell.sql || "").trim()) continue;
    const terminal = await runCell(cell.id);
    if (!terminal || terminal.status !== "Finished") break;
  }
}

function renderCellResult(cellId) {
  const node = document.querySelector(`.notebook-cell[data-cell-id="${cellId}"]`);
  if (!node) return;
  const target = node.querySelector("[data-cell-result]");
  const runtime = cellRuntime.get(cellId);
  if (runtime.running && !runtime.result) {
    const message =
      runtime.status === "Starting cluster"
        ? "Starting cluster — resuming from auto-suspend. This cell runs automatically once it is ready."
        : "Running…";
    target.innerHTML = `<div class="empty-results">${escapeHtml(message)}</div>`;
    return;
  }
  if (runtime.error) {
    target.innerHTML = `<div class="empty-results">${escapeHtml(runtime.error)}</div>`;
    return;
  }
  const query = runtime.result;
  if (!query) {
    target.innerHTML = '<div class="empty-results">Run this cell to see results.</div>';
    return;
  }
  if (runtime.view === "chart") {
    renderCellChart(cellId, target, query, runtime);
    return;
  }
  renderCellTable(target, query);
}

function renderCellTable(target, query) {
  if (query.error_message) {
    target.innerHTML = `<div class="empty-results">${escapeHtml(query.error_message)}</div>`;
    return;
  }
  const columns = query.columns || [];
  const rows = query.data || [];
  if (!columns.length) {
    target.innerHTML = '<div class="empty-results">Query completed without tabular results.</div>';
    return;
  }
  if (!rows.length) {
    target.innerHTML = '<div class="empty-results">No rows returned.</div>';
    return;
  }
  const banner = query.truncated
    ? `<div class="truncation-banner">Showing the first ${rows.length} rows${
        query.total_row_count ? ` of ${query.total_row_count} returned` : ""
      }. Add a LIMIT or narrow the query to see the rest.</div>`
    : "";
  target.innerHTML = `
    ${banner}
    <table>
      <thead>
        <tr>${columns.map((column) => `<th>${escapeHtml(column.name || "")}</th>`).join("")}</tr>
      </thead>
      <tbody>
        ${rows
          .map(
            (row) =>
              `<tr>${row
                .map((cell) => {
                  const value = cell === null ? "NULL" : typeof cell === "object" ? JSON.stringify(cell) : cell;
                  return `<td>${escapeHtml(value)}</td>`;
                })
                .join("")}</tr>`
          )
          .join("")}
      </tbody>
    </table>
  `;
}

// Per-cell chart: same zero-dependency SVG builders as the SQL editor, but
// driven by the cell's own chartState so cells chart independently.
function renderCellChart(cellId, target, query, runtime) {
  const columns = query.columns || [];
  const rows = query.data || [];
  if (!columns.length || !rows.length) {
    target.innerHTML = '<div class="empty-results">No rows to chart.</div>';
    return;
  }
  const numericIndexes = columns
    .map((_, index) => index)
    .filter((index) => rows.some((row) => !Number.isNaN(chartNumber(row[index]))));
  if (!numericIndexes.length) {
    target.innerHTML = '<div class="empty-results">No numeric column to plot.</div>';
    return;
  }
  const chartState = runtime.chartState;
  // Number("") is 0 — treat unset axes as NaN so the seed logic below runs.
  let xIndex = chartState.x === "" ? NaN : Number(chartState.x);
  let yIndex = chartState.y === "" ? NaN : Number(chartState.y);
  if (!Number.isInteger(xIndex) || xIndex < 0 || xIndex >= columns.length) {
    const firstNonNumeric = columns.findIndex((_, index) => !numericIndexes.includes(index));
    xIndex = firstNonNumeric >= 0 ? firstNonNumeric : 0;
  }
  if (!numericIndexes.includes(yIndex)) {
    const differentFromX = numericIndexes.find((index) => index !== xIndex);
    yIndex = differentFromX !== undefined ? differentFromX : numericIndexes[0];
  }
  chartState.x = String(xIndex);
  chartState.y = String(yIndex);

  const points = rows.slice(0, CHART_MAX_POINTS).map((row) => ({
    label: row[xIndex] === null ? "NULL" : String(row[xIndex]),
    value: chartNumber(row[yIndex])
  }));
  const truncatedNote =
    rows.length > CHART_MAX_POINTS
      ? `<div class="truncation-banner">Charting the first ${CHART_MAX_POINTS} of ${rows.length} rows.</div>`
      : "";
  const typeOptions = [
    ["bar", "Bar"],
    ["line", "Line"],
    ["area", "Area"],
    ["pie", "Pie"]
  ]
    .map(([value, label]) => `<option value="${value}"${chartState.type === value ? " selected" : ""}>${label}</option>`)
    .join("");
  const columnOptions = (selected) =>
    columns
      .map((column, index) => `<option value="${index}"${index === selected ? " selected" : ""}>${escapeHtml(column.name || `col ${index}`)}</option>`)
      .join("");

  target.innerHTML = `
    <div class="chart-controls">
      <label>Chart type<select data-cell-chart="type">${typeOptions}</select></label>
      <label>X / category<select data-cell-chart="x">${columnOptions(xIndex)}</select></label>
      <label>Y / value<select data-cell-chart="y">${columnOptions(yIndex)}</select></label>
    </div>
    ${truncatedNote}
    <div class="chart-canvas">${buildChartSvg(chartState.type, points)}</div>
  `;

  const rerender = (key) => (event) => {
    chartState[key] = event.target.value;
    patchCell(cellId, { chart_config: { type: chartState.type, x: chartState.x, y: chartState.y } });
    renderCellChart(cellId, target, query, runtime);
  };
  target.querySelector('[data-cell-chart="type"]').addEventListener("change", rerender("type"));
  target.querySelector('[data-cell-chart="x"]').addEventListener("change", rerender("x"));
  target.querySelector('[data-cell-chart="y"]').addEventListener("change", rerender("y"));
}

function wireNotebooks() {
  const newButton = document.getElementById("newNotebook");
  if (newButton) newButton.addEventListener("click", createNotebook);
  const back = document.getElementById("notebookBack");
  if (back) back.addEventListener("click", closeNotebook);
  const addCell = document.getElementById("notebookAddCell");
  if (addCell) addCell.addEventListener("click", addNotebookCell);
  const runAll = document.getElementById("notebookRunAll");
  if (runAll) runAll.addEventListener("click", runAllCells);
  const nameInput = document.getElementById("notebookName");
  if (nameInput) {
    nameInput.addEventListener("input", (event) => {
      const value = event.target.value.trim();
      if (!value) return;
      debounceNotebookField("name", () => patchNotebook({ name: value }));
    });
  }
  const clusterSelect = document.getElementById("notebookCluster");
  if (clusterSelect) {
    clusterSelect.addEventListener("change", (event) => {
      const notebook = activeNotebook();
      const clusterId = event.target.value ? Number(event.target.value) : null;
      if (notebook) notebook.cluster_id = clusterId;
      patchNotebook({ cluster_id: clusterId });
      populateNotebookContextSelects();
      resetSchemaBrowserContext(notebookSchemaBrowser);
    });
  }
  const catalogSelect = document.getElementById("notebookCatalog");
  if (catalogSelect) {
    catalogSelect.addEventListener("change", (event) => {
      const notebook = activeNotebook();
      if (notebook) {
        notebook.catalog = event.target.value;
        // A new catalog invalidates the old schema pick.
        notebook.schema = "";
      }
      patchNotebook({ catalog: event.target.value, schema: "" });
      populateNotebookContextSelects();
    });
  }
  const schemaSelect = document.getElementById("notebookSchema");
  if (schemaSelect) {
    schemaSelect.addEventListener("change", (event) => {
      const notebook = activeNotebook();
      if (notebook) notebook.schema = event.target.value;
      patchNotebook({ schema: event.target.value });
    });
  }
}

// ---------------------------------------------------------------------------
// Docs / documentation
// ---------------------------------------------------------------------------

async function loadDocsManifest() {
  if (!currentUser) return;
  try {
    const result = await apiRequest("/api/help/topics");
    docsManifest.groups = result.groups || [];
    renderDocsSidebar();
    const view = document.getElementById("view-docs");
    if (view && view.classList.contains("active") && !activeDocSlug) openFirstDocTopic();
  } catch (error) {
    if (!/Authentication required/.test(error.message)) showToast(error.message, { type: "error" });
  }
}

function renderDocsSidebar() {
  const sidebar = document.getElementById("docsSidebar");
  if (!sidebar) return;
  if (!docsManifest.groups.length) {
    sidebar.innerHTML = '<div class="empty-results">No help topics available.</div>';
    return;
  }
  sidebar.innerHTML = docsManifest.groups
    .map((group) => {
      const topics = (group.topics || [])
        .map(
          (topic) =>
            `<button type="button" class="docs-topic${topic.slug === activeDocSlug ? " active" : ""}" data-doc-slug="${escapeHtml(topic.slug)}">${escapeHtml(topic.title)}</button>`
        )
        .join("");
      // Admin groups carry .admin-only so user-mode hides them, mirroring the
      // admin-only nav items. The server also omits them for non-admin users.
      const groupClass = group.admin ? "docs-group admin-only" : "docs-group";
      return `<div class="${groupClass}"><p class="docs-group-label">${escapeHtml(group.label)}</p>${topics}</div>`;
    })
    .join("");
}

function openFirstDocTopic() {
  for (const group of docsManifest.groups) {
    const first = (group.topics || [])[0];
    if (first) {
      openDocTopic(first.slug);
      return;
    }
  }
}

async function openDocTopic(slug) {
  const content = document.getElementById("docsContent");
  if (!content) return;
  activeDocSlug = slug;
  document.querySelectorAll("#docsSidebar .docs-topic").forEach((button) => {
    button.classList.toggle("active", button.dataset.docSlug === slug);
  });
  content.innerHTML = '<div class="empty-results">Loading…</div>';
  try {
    const response = await fetch(`/api/help/topics/${encodeURIComponent(slug)}`, { credentials: "same-origin" });
    if (!response.ok) {
      if (response.status === 401 && currentUser) handleSessionExpired();
      const payload = await response.json().catch(() => ({}));
      throw new Error(payload.error || `Request failed with ${response.status}`);
    }
    const markdown = await response.text();
    content.innerHTML = renderMarkdown(markdown);
    content.scrollTop = 0;
  } catch (error) {
    content.innerHTML = `<div class="empty-results">${escapeHtml(error.message)}</div>`;
  }
}

function resetDocsState() {
  docsManifest.groups = [];
  activeDocSlug = null;
  const sidebar = document.getElementById("docsSidebar");
  const content = document.getElementById("docsContent");
  if (sidebar) sidebar.innerHTML = '<div class="empty-results">Loading help…</div>';
  if (content) content.innerHTML = '<div class="empty-results">Select a topic to begin.</div>';
}

function wireDocs() {
  const sidebar = document.getElementById("docsSidebar");
  if (sidebar) {
    sidebar.addEventListener("click", (event) => {
      const button = event.target.closest("[data-doc-slug]");
      if (button) openDocTopic(button.dataset.docSlug);
    });
  }
  const docsNav = document.querySelector('[data-view-target="docs"]');
  if (docsNav) {
    docsNav.addEventListener("click", () => {
      if (!activeDocSlug) openFirstDocTopic();
    });
  }
}

// Tiny zero-dependency Markdown renderer. Supports headings, paragraphs,
// bold/italic/inline-code, fenced code blocks, ordered/unordered lists,
// blockquotes, horizontal rules, pipe tables, and sanitized links. Everything
// is HTML-escaped first, so it is XSS-safe even for untrusted input.
function renderMarkdown(src) {
  const lines = String(src).replace(/\r\n/g, "\n").split("\n");
  let html = "";
  let para = [];
  let i = 0;
  const flushPara = () => {
    if (para.length) {
      html += `<p>${renderMarkdownInline(para.join(" "))}</p>`;
      para = [];
    }
  };
  const isSeparatorRow = (line) => /^\s*\|?[\s:|-]*-[\s:|-]*$/.test(line) && line.includes("-");
  const parseRow = (row) =>
    row
      .replace(/^\s*\|/, "")
      .replace(/\|\s*$/, "")
      .split("|")
      .map((cell) => cell.trim());

  while (i < lines.length) {
    const line = lines[i];
    if (/^```/.test(line.trim())) {
      flushPara();
      i += 1;
      const code = [];
      while (i < lines.length && lines[i].trim() !== "```") {
        code.push(lines[i]);
        i += 1;
      }
      i += 1; // skip closing fence
      html += `<pre><code>${escapeHtml(code.join("\n"))}</code></pre>`;
      continue;
    }
    if (line.trim() === "") {
      flushPara();
      i += 1;
      continue;
    }
    const heading = line.match(/^(#{1,4})\s+(.*)$/);
    if (heading) {
      flushPara();
      const level = heading[1].length;
      html += `<h${level}>${renderMarkdownInline(heading[2].trim())}</h${level}>`;
      i += 1;
      continue;
    }
    if (/^---+\s*$/.test(line)) {
      flushPara();
      html += "<hr />";
      i += 1;
      continue;
    }
    if (/^>\s?/.test(line)) {
      flushPara();
      const quote = [];
      while (i < lines.length && /^>\s?/.test(lines[i])) {
        quote.push(lines[i].replace(/^>\s?/, ""));
        i += 1;
      }
      html += `<blockquote>${renderMarkdownInline(quote.join(" "))}</blockquote>`;
      continue;
    }
    if (line.includes("|") && i + 1 < lines.length && isSeparatorRow(lines[i + 1])) {
      flushPara();
      const headers = parseRow(line);
      i += 2; // skip header + separator
      const bodyRows = [];
      while (i < lines.length && lines[i].includes("|") && lines[i].trim() !== "") {
        bodyRows.push(parseRow(lines[i]));
        i += 1;
      }
      const head = headers.map((cell) => `<th>${renderMarkdownInline(cell)}</th>`).join("");
      const body = bodyRows
        .map((row) => `<tr>${row.map((cell) => `<td>${renderMarkdownInline(cell)}</td>`).join("")}</tr>`)
        .join("");
      html += `<table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>`;
      continue;
    }
    if (/^\s*[-*]\s+/.test(line)) {
      flushPara();
      const items = [];
      while (i < lines.length && /^\s*[-*]\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^\s*[-*]\s+/, ""));
        i += 1;
      }
      html += `<ul>${items.map((item) => `<li>${renderMarkdownInline(item)}</li>`).join("")}</ul>`;
      continue;
    }
    if (/^\s*\d+\.\s+/.test(line)) {
      flushPara();
      const items = [];
      while (i < lines.length && /^\s*\d+\.\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^\s*\d+\.\s+/, ""));
        i += 1;
      }
      html += `<ol>${items.map((item) => `<li>${renderMarkdownInline(item)}</li>`).join("")}</ol>`;
      continue;
    }
    para.push(line.trim());
    i += 1;
  }
  flushPara();
  return `<div class="doc-article">${html}</div>`;
}

function sanitizeDocUrl(url) {
  const trimmed = url.trim();
  if (/^https?:\/\//i.test(trimmed) || trimmed.startsWith("/") || trimmed.startsWith("#")) return trimmed;
  return "";
}

function renderMarkdownInline(text) {
  let value = escapeHtml(text);
  // Protect inline code so bold/italic markers inside it are left untouched.
  const codes = [];
  value = value.replace(/`([^`]+)`/g, (_, code) => {
    codes.push(code);
    return `@@DOCCODE${codes.length - 1}@@`;
  });
  value = value.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (_, label, url) => {
    const safe = sanitizeDocUrl(url);
    return safe ? `<a href="${safe}" target="_blank" rel="noopener">${label}</a>` : label;
  });
  value = value.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  value = value.replace(/(^|[^*])\*([^*]+)\*/g, "$1<em>$2</em>");
  value = value.replace(/(^|[^A-Za-z0-9_])_([^_]+)_/g, "$1<em>$2</em>");
  value = value.replace(/@@DOCCODE(\d+)@@/g, (_, index) => `<code>${codes[Number(index)]}</code>`);
  return value;
}

// ===========================================================================
// Ask Trino — natural-language analytics assistant.
// The model returns {explanation, sql, chartType, clarifyingQuestion}; the app
// validates the SQL server-side and runs it through the normal query path. Chat
// history lives in localStorage; the last few turns are sent back for context.
// ===========================================================================
const ASK_HISTORY_KEY = "trinohub-ask-history";
const ASK_MAX_STORED = 50;
const ASK_SEND_HISTORY = 20;
// Ask Trino resumes an auto-suspended cluster server-side but only waits ~12s
// before returning. If the cluster is still starting, the browser keeps polling
// the queued query (cold start is typically 3–5 min) and fills in the answer.
const ASK_CLUSTER_START_POLL_MS = 2500;
const ASK_CLUSTER_START_MAX_POLLS = 160;
const ASK_SUGGESTED_PROMPTS = [
  "Top 5 nations by total order value",
  "Order volume by market segment",
  "Which 10 customers have the highest account balance?",
  "Average order value by order priority",
  "Revenue by region, highest first",
  "How many orders were placed per order status?",
];
let askMsgs = [];
let askPending = false;
let askRailTab = "suggested";

function loadAskHistory() {
  try {
    const raw = localStorage.getItem(ASK_HISTORY_KEY);
    askMsgs = raw ? JSON.parse(raw) : [];
  } catch (err) {
    askMsgs = [];
  }
  if (!Array.isArray(askMsgs)) askMsgs = [];
}

function saveAskHistory() {
  try {
    localStorage.setItem(ASK_HISTORY_KEY, JSON.stringify(askMsgs.slice(-ASK_MAX_STORED)));
  } catch (err) {
    // Quota or private mode — chat still works for this session.
  }
}

function askSelectedClusterId() {
  const select = document.getElementById("askCluster");
  const value = select ? select.value : "";
  return value ? Number(value) : null;
}

function populateAskClusterOptions() {
  const select = document.getElementById("askCluster");
  if (!select) return;
  const previous = select.value;
  select.innerHTML = clusterOptionsHtml(previous || "", "Select cluster…");
  updateAskCatalogOptions();
}

function updateAskCatalogOptions() {
  const clusterSelect = document.getElementById("askCluster");
  const catalogSelect = document.getElementById("askCatalog");
  if (!catalogSelect) return;
  const cluster = clusters.find((item) => String(item.id) === String(clusterSelect ? clusterSelect.value : ""));
  const names = cluster && cluster.catalogList ? cluster.catalogList.slice() : ["tpch", "tpcds"];
  const usable = names.filter((name) => name !== "system");
  const list = usable.length ? usable : names;
  const previous = catalogSelect.value;
  catalogSelect.innerHTML = list.length
    ? list.map((name) => `<option value="${escapeHtml(name)}">${escapeHtml(name)}</option>`).join("")
    : '<option value="">No catalogs</option>';
  if (list.includes(previous)) catalogSelect.value = previous;
  updateAskSchemaOptions();
}

async function updateAskSchemaOptions() {
  const schemaSelect = document.getElementById("askSchema");
  if (!schemaSelect) return;
  schemaSelect.innerHTML = '<option value="">Auto-detect</option>';
  const clusterId = askSelectedClusterId();
  const catalogSelect = document.getElementById("askCatalog");
  const catalog = catalogSelect ? catalogSelect.value : "";
  if (!clusterId || !catalog) return;
  try {
    const meta = await apiRequest(`/api/clusters/${clusterId}/metadata?catalog=${encodeURIComponent(catalog)}`);
    const schemas = (meta.schemas || []).map((schema) => schema.name);
    if (schemas.length) {
      schemaSelect.innerHTML =
        '<option value="">Auto-detect</option>' +
        schemas.map((name) => `<option value="${escapeHtml(name)}">${escapeHtml(name)}</option>`).join("");
      if (schemas.includes("sf1")) schemaSelect.value = "sf1";
    }
  } catch (err) {
    // Cluster suspended or metadata unavailable — auto-detect server-side is fine.
  }
}

function askContextText(message) {
  if (message.role === "user") return message.text;
  const result = message.result || {};
  const marks = [];
  if (result.sql) marks.push(`[SQL: ${result.sql}]`);
  if (result.rows && result.rows.length) marks.push(`[Returned ${result.row_count || result.rows.length} rows]`);
  if (result.clarifyingQuestion) marks.push("[Asked a clarifying question]");
  const base = message.text || result.explanation || "";
  return marks.length ? `${base} ${marks.join(" ")}`.trim() : base;
}

async function sendAsk(rawQuestion) {
  const question = String(rawQuestion || "").trim();
  if (!question || askPending) return;
  askMsgs.push({ role: "user", text: question });
  askPending = true;
  saveAskHistory();
  renderAskThread();
  renderAskRail();
  scrollAskToBottom();
  try {
    const payload = {
      question,
      cluster_id: askSelectedClusterId(),
      catalog: (document.getElementById("askCatalog") || {}).value || "",
      schema: (document.getElementById("askSchema") || {}).value || "",
      persona: (document.getElementById("askPersona") || {}).value || "Analyst",
      history: askMsgs
        .slice(0, -1)
        .slice(-ASK_SEND_HISTORY)
        .map((message) => ({ role: message.role, text: askContextText(message) })),
    };
    const result = await apiRequest("/api/ask", { method: "POST", body: JSON.stringify(payload) });
    askMsgs.push({ role: "ai", text: result.explanation || "", result });
  } catch (err) {
    askMsgs.push({
      role: "ai",
      text: "",
      result: { explanation: "", error: err.message, columns: [], rows: [], chartType: "none" },
    });
  } finally {
    askPending = false;
    saveAskHistory();
    renderAskThread();
    renderAskRail();
    scrollAskToBottom();
  }
  // If the answer's SQL was queued against a resuming cluster, keep polling the
  // query client-side and fill in the table/chart once the cluster is Running.
  const last = askMsgs[askMsgs.length - 1];
  if (last && last.role === "ai" && last.result && last.result.pending_cluster_start && last.result.query_id) {
    await pollAskClusterStart(last);
  }
}

async function pollAskClusterStart(message) {
  const result = message.result || {};
  const queryId = result.query_id;
  if (!queryId) return;
  for (let i = 0; i < ASK_CLUSTER_START_MAX_POLLS; i += 1) {
    await delay(ASK_CLUSTER_START_POLL_MS);
    let query;
    try {
      const poll = await apiRequest(`/api/query/${queryId}`);
      query = poll.query;
    } catch (err) {
      break;
    }
    result.pending_cluster_start = Boolean(query.pending_cluster_start);
    result.status = query.status;
    if (isTerminalQueryStatus(query.status)) {
      result.columns = query.columns || [];
      result.rows = query.data || [];
      result.row_count = query.total_row_count || query.row_count || result.rows.length;
      result.truncated = Boolean(query.truncated);
      if (query.status === "Failed") result.error = query.error_message || "The query failed to run.";
      renderAskThread();
      scrollAskToBottom();
      saveAskHistory();
      return;
    }
    renderAskThread();
    scrollAskToBottom();
  }
  // Gave up waiting; drop the banner and tell the user to try again.
  if (result.pending_cluster_start) {
    result.pending_cluster_start = false;
    result.error =
      "The cluster is still starting. Re-run this question in a moment to see results.";
    renderAskThread();
    saveAskHistory();
  }
}

function scrollAskToBottom() {
  const thread = document.getElementById("askThread");
  if (thread) thread.scrollTop = thread.scrollHeight;
}

function renderAskRail() {
  const body = document.getElementById("askRailBody");
  if (!body) return;
  if (askRailTab === "history") {
    const userTurns = askMsgs.filter((message) => message.role === "user");
    body.innerHTML = userTurns.length
      ? userTurns
          .slice()
          .reverse()
          .map(
            (message) =>
              `<button class="ask-suggest-card" type="button" data-ask-prompt="${escapeHtml(message.text)}"><span>${escapeHtml(
                message.text
              )}</span></button>`
          )
          .join("")
      : '<p class="ask-rail-empty">No questions yet.</p>';
  } else {
    body.innerHTML = ASK_SUGGESTED_PROMPTS.map(
      (prompt) =>
        `<button class="ask-suggest-card" type="button" data-ask-prompt="${escapeHtml(prompt)}"><span data-icon="sparkles"></span><span>${escapeHtml(
          prompt
        )}</span></button>`
    ).join("");
  }
  replaceIcons();
}

function renderAskThread() {
  const thread = document.getElementById("askThread");
  if (!thread) return;
  if (!askMsgs.length && !askPending) {
    thread.innerHTML = `<div class="ask-empty">
      <div class="ask-empty-mark"><span data-icon="sparkles"></span></div>
      <h2>Ask Trino</h2>
      <p>Ask a question about your data in plain English. I'll write the Trino SQL, run it on your selected
      cluster, and answer with a table and chart. Pick a starter prompt or type your own below.</p>
    </div>`;
    replaceIcons();
    return;
  }
  let html = "";
  askMsgs.forEach((message, index) => {
    if (message.role === "user") {
      html += `<div class="ask-row user"><div class="ask-bubble user">${escapeHtml(message.text)}</div></div>`;
    } else {
      html += `<div class="ask-row ai"><div class="ask-bubble ai" data-ask-msg="${index}">${askAssistantHtml(
        message.result || { explanation: message.text },
        index
      )}</div></div>`;
    }
  });
  if (askPending) {
    html += `<div class="ask-row ai"><div class="ask-bubble ai ask-loading"><span class="spinner" aria-hidden="true"></span> Thinking…</div></div>`;
  }
  thread.innerHTML = html;
  replaceIcons();
}

function askAssistantHtml(result, index) {
  const parts = [];
  if (result.explanation) parts.push(`<div class="ask-explanation">${renderMarkdown(result.explanation)}</div>`);
  if (result.clarifyingQuestion) parts.push(askClarifyHtml(result.clarifyingQuestion));
  if (result.pending_cluster_start) {
    parts.push(
      '<div class="ask-starting"><span class="spinner" aria-hidden="true"></span> Starting cluster — resuming from auto-suspend. Your query runs automatically once it is ready (cold start is usually 3–5 min).</div>'
    );
  }
  if (result.error) parts.push(`<div class="ask-error">⚠️ Query error: ${escapeHtml(result.error)}</div>`);
  if (result.columns && result.columns.length && result.rows && result.rows.length) {
    parts.push(askTableHtml(result, index));
    if (result.chartType && result.chartType !== "none") parts.push(askChartHtml(result));
  }
  if (result.sql) parts.push(askSqlHtml(result.sql));
  if (!parts.length) parts.push('<div class="ask-explanation">No answer was returned.</div>');
  return parts.join("");
}

function askClarifyHtml(clarifying) {
  const options = [];
  if (clarifying.includeAllOption) options.push("All");
  (clarifying.options || []).forEach((option) => options.push(option));
  const buttons = options
    .map(
      (option) =>
        `<button class="ask-clarify-option" type="button" data-ask-prompt="${escapeHtml(option)}">${escapeHtml(
          option
        )}</button>`
    )
    .join("");
  return `<div class="ask-clarify"><p>${escapeHtml(clarifying.question)}</p><div class="ask-clarify-options">${buttons}</div></div>`;
}

function askTableHtml(result, index) {
  const cols = result.columns || [];
  const rows = result.rows || [];
  const head = cols.map((col) => `<th>${escapeHtml(col.name)}</th>`).join("");
  const body = rows
    .map((row, rowIndex) => {
      const cells = cols
        .map((col, colIndex) => {
          const value = row[colIndex];
          const numeric = typeof value === "number";
          return `<td class="${numeric ? "num" : ""}">${escapeHtml(askFormatCell(value))}</td>`;
        })
        .join("");
      return `<tr class="${rowIndex >= 20 ? "ask-extra-row" : ""}">${cells}</tr>`;
    })
    .join("");
  const showAll =
    rows.length > 20
      ? `<button class="ghost-button ask-showall" type="button" data-ask-showall>Show all ${rows.length} rows</button>`
      : "";
  const totalNote = result.row_count && result.row_count > rows.length ? ` of ${result.row_count}` : "";
  const trunc = result.truncated ? '<span class="ask-trunc">capped</span>' : "";
  return `<div class="ask-result-card" data-ask-result="${index}">
    <div class="ask-result-toolbar">
      <span class="ask-result-meta">${rows.length} row${rows.length === 1 ? "" : "s"}${totalNote} ${trunc}</span>
      <span class="ask-result-actions">
        <button class="ghost-button" type="button" data-ask-copy>Copy</button>
        <button class="ghost-button" type="button" data-ask-csv>Export CSV</button>
      </span>
    </div>
    <div class="ask-table-scroll"><table class="ask-table"><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></div>
    ${showAll}
  </div>`;
}

function askSqlHtml(sql) {
  return `<details class="ask-sql"><summary>Show SQL</summary><div class="ask-sql-body"><button class="ghost-button ask-sql-copy" type="button" data-ask-sql-copy>Copy</button><pre><code>${escapeHtml(
    sql
  )}</code></pre></div></details>`;
}

function askDetectChartColumns(result) {
  const cols = result.columns || [];
  const rows = result.rows || [];
  if (!cols.length || !rows.length) return null;
  let catIdx = -1;
  for (let i = 0; i < cols.length; i += 1) {
    if (rows.some((row) => typeof row[i] === "string")) {
      catIdx = i;
      break;
    }
  }
  let valIdx = -1;
  for (let i = 0; i < cols.length; i += 1) {
    if (i === catIdx) continue;
    if (rows.every((row) => row[i] === null || typeof row[i] === "number")) {
      valIdx = i;
      break;
    }
  }
  if (valIdx === -1) return null;
  return { catIdx, valIdx };
}

function askChartHtml(result) {
  const pick = askDetectChartColumns(result);
  if (!pick) return "";
  const cols = result.columns;
  const rows = result.rows;
  const data = rows.map((row, idx) => ({
    label: pick.catIdx >= 0 ? String(row[pick.catIdx]) : `#${idx + 1}`,
    value: Number(row[pick.valIdx]) || 0,
  }));
  if (!data.length) return "";
  const title = cols[pick.valIdx].name;
  if (result.chartType === "pie") return askChartCard(title, askPieSvg(data.slice(0, 8)));
  if (result.chartType === "line") return askChartCard(title, askLineSvg(data.slice(0, 30)));
  return askChartCard(title, askBarSvg(data.slice(0, 12)));
}

function askChartCard(title, inner) {
  return `<div class="ask-chart-card"><div class="ask-chart-head">${escapeHtml(title || "Result")}</div>${inner}</div>`;
}

function askBarSvg(data) {
  const W = 520;
  const H = 200;
  const pad = 28;
  const max = Math.max.apply(null, data.map((d) => d.value).concat(0)) || 1;
  const bw = (W - pad * 2) / data.length;
  const bars = data
    .map((d, i) => {
      const h = Math.max(2, (d.value / max) * (H - pad * 2));
      const x = pad + i * bw + bw * 0.12;
      const y = H - pad - h;
      return `<rect x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${(bw * 0.76).toFixed(1)}" height="${h.toFixed(
        1
      )}" rx="3" fill="var(--chart-${(i % 6) + 1})"><title>${escapeHtml(d.label)}: ${escapeHtml(
        askFormatNumber(d.value)
      )}</title></rect>`;
    })
    .join("");
  const labels = data
    .map((d, i) => {
      const x = pad + i * bw + bw * 0.5;
      return `<text x="${x.toFixed(1)}" y="${H - 8}" text-anchor="middle" class="ask-axis">${escapeHtml(
        askTruncLabel(d.label)
      )}</text>`;
    })
    .join("");
  return `<svg viewBox="0 0 ${W} ${H}" class="ask-chart-svg" role="img">${bars}${labels}</svg>`;
}

function askLineSvg(data) {
  const W = 520;
  const H = 200;
  const pad = 28;
  const values = data.map((d) => d.value);
  const max = Math.max.apply(null, values.concat(0)) || 1;
  const min = Math.min.apply(null, values.concat(0));
  const span = max - min || 1;
  const points = data.map((d, i) => {
    const x = pad + i * ((W - pad * 2) / Math.max(1, data.length - 1));
    const y = H - pad - ((d.value - min) / span) * (H - pad * 2);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });
  const dots = points
    .map((point) => {
      const [x, y] = point.split(",");
      return `<circle cx="${x}" cy="${y}" r="2.5" fill="var(--chart-1)"></circle>`;
    })
    .join("");
  return `<svg viewBox="0 0 ${W} ${H}" class="ask-chart-svg" role="img"><polyline points="${points.join(
    " "
  )}" fill="none" stroke="var(--chart-1)" stroke-width="2"></polyline>${dots}</svg>`;
}

function askPieSvg(data) {
  const total = data.reduce((sum, d) => sum + Math.max(0, d.value), 0) || 1;
  let acc = 0;
  const stops = [];
  const legend = [];
  data.forEach((d, i) => {
    const start = (acc / total) * 360;
    acc += Math.max(0, d.value);
    const end = (acc / total) * 360;
    stops.push(`var(--chart-${(i % 6) + 1}) ${start.toFixed(1)}deg ${end.toFixed(1)}deg`);
    const pct = ((Math.max(0, d.value) / total) * 100).toFixed(1);
    legend.push(
      `<li><span class="ask-swatch" style="background:var(--chart-${(i % 6) + 1})"></span>${escapeHtml(
        askTruncLabel(d.label)
      )} <strong>${pct}%</strong></li>`
    );
  });
  return `<div class="ask-pie-wrap"><div class="ask-donut" style="background:conic-gradient(${stops.join(
    ","
  )})"><div class="ask-donut-hole"></div></div><ul class="ask-legend">${legend.join("")}</ul></div>`;
}

function askFormatNumber(value) {
  if (typeof value !== "number" || !isFinite(value)) return String(value);
  const abs = Math.abs(value);
  if (abs >= 1e9) return `${(value / 1e9).toFixed(1)}B`;
  if (abs >= 1e6) return `${(value / 1e6).toFixed(1)}M`;
  if (abs >= 1e3) return `${(value / 1e3).toFixed(1)}K`;
  return String(Math.round(value * 100) / 100);
}

function askTruncLabel(value) {
  const text = String(value);
  return text.length > 14 ? `${text.slice(0, 13)}…` : text;
}

function askFormatCell(value) {
  if (value === null || value === undefined) return "";
  return String(value);
}

function askCopyTable(button, asCsv) {
  const card = button.closest("[data-ask-result]");
  if (!card) return;
  const index = Number(card.dataset.askResult);
  const result = askMsgs[index] && askMsgs[index].result;
  if (!result) return;
  const sep = asCsv ? "," : "\t";
  const escape = asCsv
    ? (value) => {
        const text = String(value === null || value === undefined ? "" : value);
        return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
      }
    : (value) => String(value === null || value === undefined ? "" : value);
  const lines = [result.columns.map((col) => escape(col.name)).join(sep)];
  result.rows.forEach((row) => lines.push(row.map(escape).join(sep)));
  const text = lines.join("\n");
  if (asCsv) {
    const blob = new Blob([text], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `ask-trino-${new Date().toISOString().slice(0, 10)}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  } else {
    copyText(text)
      .then(() => showToast("Copied to clipboard"))
      .catch(() => showToast("Copy failed — select the text and copy manually"));
  }
}

function wireAskTrino() {
  loadAskHistory();
  populateAskClusterOptions();
  renderAskRail();
  renderAskThread();

  const clusterSelect = document.getElementById("askCluster");
  if (clusterSelect) clusterSelect.addEventListener("change", updateAskCatalogOptions);
  const catalogSelect = document.getElementById("askCatalog");
  if (catalogSelect) catalogSelect.addEventListener("change", updateAskSchemaOptions);

  const newChat = document.getElementById("askNewChat");
  if (newChat) {
    newChat.addEventListener("click", () => {
      askMsgs = [];
      saveAskHistory();
      renderAskThread();
      renderAskRail();
    });
  }

  document.querySelectorAll(".ask-rail-tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      askRailTab = tab.dataset.askTab;
      document.querySelectorAll(".ask-rail-tab").forEach((other) => other.classList.toggle("active", other === tab));
      renderAskRail();
    });
  });

  const railBody = document.getElementById("askRailBody");
  if (railBody) {
    railBody.addEventListener("click", (event) => {
      const prompt = event.target.closest("[data-ask-prompt]");
      if (prompt) sendAsk(prompt.dataset.askPrompt);
    });
  }

  const thread = document.getElementById("askThread");
  if (thread) {
    thread.addEventListener("click", (event) => {
      const prompt = event.target.closest("[data-ask-prompt]");
      if (prompt) {
        sendAsk(prompt.dataset.askPrompt);
        return;
      }
      const showAll = event.target.closest("[data-ask-showall]");
      if (showAll) {
        const card = showAll.closest(".ask-result-card");
        card.classList.toggle("expanded");
        const total = card.querySelectorAll("tbody tr").length;
        showAll.textContent = card.classList.contains("expanded") ? "Show fewer rows" : `Show all ${total} rows`;
        return;
      }
      const copy = event.target.closest("[data-ask-copy]");
      if (copy) {
        askCopyTable(copy, false);
        return;
      }
      const csv = event.target.closest("[data-ask-csv]");
      if (csv) {
        askCopyTable(csv, true);
        return;
      }
      const sqlCopy = event.target.closest("[data-ask-sql-copy]");
      if (sqlCopy) {
        const code = sqlCopy.parentElement.querySelector("code");
        if (code) {
          copyText(code.textContent)
            .then(() => showToast("SQL copied"))
            .catch(() => showToast("Copy failed — select the text and copy manually"));
        }
      }
    });
  }

  const composer = document.getElementById("askComposer");
  const input = document.getElementById("askInput");
  if (composer && input) {
    composer.addEventListener("submit", (event) => {
      event.preventDefault();
      const question = input.value;
      input.value = "";
      input.style.height = "auto";
      sendAsk(question);
    });
    input.addEventListener("input", () => {
      input.style.height = "auto";
      input.style.height = `${Math.min(160, input.scrollHeight)}px`;
    });
    input.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        composer.requestSubmit();
      }
    });
  }
}

function boot() {
  try {
    wireNavigation();
    replaceIcons();
    wireClusterFilters();
    wireClusterDetailActions();
    wireWizard();
    wireCreateCluster();
    wireCatalogs();
    wireSettings();
    wireConnectModal();
    wireUsers();
    wireSqlEditor();
    wireNotebooks();
    wireAskTrino();
    wireDocs();
    wireSqlSidebars();
    wireHistoryControls();
    wireThemeToggle();
    wireSchemaBrowser(sqlSchemaBrowser);
    wireSchemaBrowser(notebookSchemaBrowser);
    wireRoleSwitcher();
    wireAppDialog();
    wireJobs();
    wireGlobalSearch();
    wireAuth();
    renderClusters();
    renderCatalogs();
    renderUsers();
    renderHistory();
    renderQueryTabs();
    updateWizard();
    updateCreateReview();
    applyRoleMode();
    initAuth();
  } catch (error) {
    console.error(error);
    showToast(`UI initialization failed: ${error.message}`);
  }
}

document.addEventListener("DOMContentLoaded", boot);
