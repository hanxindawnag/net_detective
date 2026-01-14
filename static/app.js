const API_BASE = "";
const REFRESH_INTERVAL_MS = 5000;

const state = {
  targets: [],
  availability: new Map(),
  selectedTargetId: null,
  chart: null,
};

const elements = {
  error: document.getElementById("error"),
  targetsBody: document.querySelector("#targets-table tbody"),
  alertsBody: document.querySelector("#alerts-table tbody"),
  addTargetForm: document.getElementById("add-target-form"),
  chart: document.getElementById("chart"),
};

function setError(message) {
  elements.error.textContent = message || "";
}

async function fetchJson(path, options = {}) {
  try {
    const response = await fetch(`${API_BASE}${path}`, options);
    if (!response.ok) {
      throw new Error(`${response.status} ${response.statusText}`);
    }
    const data = await response.json();
    setError("");
    return data;
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    setError(`Error: ${message}`);
    return null;
  }
}

function formatTimestamp(value) {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
}

function formatMs(value) {
  if (value === null || value === undefined) {
    return "-";
  }
  return Number(value).toFixed(2);
}

function formatAvailability(value) {
  if (value === null || value === undefined) {
    return "-";
  }
  return `${(value * 100).toFixed(2)}%`;
}

function isSuccessStatus(target) {
  if (target.latest_error) {
    return false;
  }
  const code = target.latest_status_code;
  if (code === null || code === undefined) {
    return null;
  }
  return code >= 200 && code < 400;
}

function renderTargetsTable() {
  elements.targetsBody.innerHTML = "";
  if (!state.targets.length) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = 9;
    cell.className = "empty";
    cell.textContent = "No targets yet.";
    row.appendChild(cell);
    elements.targetsBody.appendChild(row);
    return;
  }

  state.targets.forEach((target) => {
    const row = document.createElement("tr");
    row.dataset.targetId = String(target.id);
    if (state.selectedTargetId === target.id) {
      row.classList.add("selected");
    }

    const statusValue = isSuccessStatus(target);
    const statusText = statusValue === null ? "unknown" : statusValue ? "up" : "down";
    const statusClass =
      statusValue === null ? "status-unknown" : statusValue ? "status-up" : "status-down";

    row.innerHTML = `
      <td>${target.name}</td>
      <td>${target.url}</td>
      <td class="${statusClass}">${statusText}</td>
      <td>${target.latest_status_code ?? "-"}</td>
      <td>${formatMs(target.latest_response_time_ms)}</td>
      <td>${formatMs(target.latest_dns_time_ms)}</td>
      <td>${formatTimestamp(target.latest_ts)}</td>
      <td>${formatAvailability(state.availability.get(target.id))}</td>
      <td><button class="action-button" data-action="delete">Delete</button></td>
    `;

    row.addEventListener("click", () => {
      if (state.selectedTargetId !== target.id) {
        state.selectedTargetId = target.id;
        renderTargetsTable();
        loadTimeseries(target.id);
      }
    });

    row.querySelector("button")?.addEventListener("click", async (event) => {
      event.stopPropagation();
      await deleteTarget(target.id);
    });

    elements.targetsBody.appendChild(row);
  });
}

function renderAlerts(alerts) {
  elements.alertsBody.innerHTML = "";
  if (!alerts.length) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = 4;
    cell.className = "empty";
    cell.textContent = "No alerts.";
    row.appendChild(cell);
    elements.alertsBody.appendChild(row);
    return;
  }

  const targetMap = new Map(state.targets.map((target) => [target.id, target.name]));

  alerts.forEach((alert) => {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${formatTimestamp(alert.ts)}</td>
      <td>${targetMap.get(alert.target_id) ?? `Target ${alert.target_id}`}</td>
      <td>alert</td>
      <td>${alert.message}</td>
    `;
    elements.alertsBody.appendChild(row);
  });
}

function initChart() {
  state.chart = echarts.init(elements.chart);
  state.chart.setOption({
    tooltip: { trigger: "axis" },
    xAxis: { type: "category", data: [] },
    yAxis: { type: "value", name: "ms" },
    series: [{ type: "line", data: [], smooth: false }],
  });
}

function updateChart(series) {
  const labels = series.map((point) => formatTimestamp(point.ts));
  const values = series.map((point) => point.response_time_ms ?? null);

  state.chart.setOption({
    xAxis: { data: labels },
    series: [{ data: values }],
  });
}

async function loadTimeseries(targetId) {
  if (!targetId) {
    return;
  }
  const data = await fetchJson(`/api/dashboard/timeseries?target_id=${targetId}&minutes=60`);
  if (!data) {
    return;
  }
  updateChart(data.series || []);
}

async function refreshOverview() {
  const data = await fetchJson("/api/dashboard/overview");
  if (!data) {
    return;
  }
  state.targets = data.targets || [];
  if (state.targets.length && !state.selectedTargetId) {
    state.selectedTargetId = state.targets[0].id;
  }
  if (state.selectedTargetId) {
    const stillExists = state.targets.some((target) => target.id === state.selectedTargetId);
    if (!stillExists) {
      state.selectedTargetId = state.targets.length ? state.targets[0].id : null;
    }
  }
  await refreshAvailability();
  renderTargetsTable();
  if (state.selectedTargetId) {
    await loadTimeseries(state.selectedTargetId);
  }
}

async function refreshAvailability() {
  const availabilityMap = new Map();
  const requests = state.targets.map(async (target) => {
    const data = await fetchJson(
      `/api/dashboard/availability?target_id=${target.id}&hours=24`
    );
    availabilityMap.set(target.id, data ? data.availability : null);
  });
  await Promise.all(requests);
  state.availability = availabilityMap;
}

async function refreshAlerts() {
  const data = await fetchJson("/api/alerts?limit=20");
  if (!data) {
    return;
  }
  renderAlerts(data.alerts || []);
}

async function deleteTarget(targetId) {
  const response = await fetchJson(`/api/targets/${targetId}`, { method: "DELETE" });
  if (!response) {
    return;
  }
  await refreshOverview();
}

async function handleAddTarget(event) {
  event.preventDefault();
  const formData = new FormData(elements.addTargetForm);
  const payload = {
    name: String(formData.get("name") || "").trim(),
    url: String(formData.get("url") || "").trim(),
    interval_sec: Number(formData.get("interval_sec")),
    timeout_sec: Number(formData.get("timeout_sec")),
    enabled: formData.get("enabled") === "on",
  };

  if (!payload.name || !payload.url) {
    setError("Error: name and url are required.");
    return;
  }

  const data = await fetchJson("/api/targets", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!data) {
    return;
  }
  elements.addTargetForm.reset();
  elements.addTargetForm.querySelector("input[name='enabled']").checked = true;
  state.selectedTargetId = data.id;
  await refreshOverview();
}

function setup() {
  initChart();
  elements.addTargetForm.addEventListener("submit", handleAddTarget);
  refreshOverview();
  refreshAlerts();
  setInterval(() => {
    refreshOverview();
    refreshAlerts();
  }, REFRESH_INTERVAL_MS);
}

setup();
