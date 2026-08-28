"use strict";

const REFRESH_INTERVAL_MS = 1000;

const elements = {
  connectionDot: document.getElementById("connection-dot"),
  connectionState: document.getElementById("connection-state"),
  telemetryMode: document.getElementById("telemetry-mode"),
  lastUpdate: document.getElementById("last-update"),
  errorBanner: document.getElementById("error-banner"),
  cpuValue: document.getElementById("cpu-value"),
  cpuBusy: document.getElementById("cpu-busy"),
  cpuElapsed: document.getElementById("cpu-elapsed"),
  sramFree: document.getElementById("sram-free"),
  sramPainted: document.getElementById("sram-painted"),
  sramUsed: document.getElementById("sram-used"),
  commOverflow: document.getElementById("comm-overflow"),
  commTimeout: document.getElementById("comm-timeout"),
  commCrc: document.getElementById("comm-crc"),
  watchdogMarker: document.getElementById("watchdog-marker"),
  eventLog: document.getElementById("event-log"),
  cpuChart: document.getElementById("cpu-chart"),
  sramChart: document.getElementById("sram-chart"),
};

function isNumber(value) {
  return typeof value === "number" && Number.isFinite(value);
}

function formatNumber(value, maximumFractionDigits = 0) {
  if (!isNumber(value)) {
    return "—";
  }
  return value.toLocaleString(undefined, { maximumFractionDigits });
}

function formatExecutionTime(value) {
  if (!isNumber(value)) {
    return "—";
  }
  const decimals = Number.isInteger(value) ? 0 : 1;
  return `${formatNumber(value, decimals)} µs`;
}

function formatJitter(value) {
  if (!isNumber(value)) {
    return "—";
  }
  if (value === 0) {
    return "0 ms @ 1 ms resolution";
  }
  return `${formatNumber(value)} ms @ 1 ms resolution`;
}

function formatAge(ageSeconds) {
  if (!isNumber(ageSeconds)) {
    return "age unavailable";
  }
  if (ageSeconds < 1) {
    return "less than 1 s old";
  }
  return `${formatNumber(ageSeconds, 1)} s old`;
}

function renderConnection(status) {
  const connection = status.connection || "DISCONNECTED";
  const normalized = connection.toLowerCase();
  elements.connectionState.textContent = connection;
  elements.connectionDot.className = `status-dot ${normalized}`;

  elements.telemetryMode.className = "telemetry-mode";
  if (connection === "CONNECTED" && !status.stale) {
    elements.telemetryMode.textContent = "LIVE DEVICE TELEMETRY";
    elements.telemetryMode.classList.add("live");
  } else if (connection === "DEGRADED") {
    elements.telemetryMode.textContent = "DEGRADED · CACHED TELEMETRY";
    elements.telemetryMode.classList.add("stale");
  } else if (status.last_update) {
    elements.telemetryMode.textContent = "NO LIVE DEVICE TELEMETRY · STALE CACHE";
    elements.telemetryMode.classList.add("stale");
  } else {
    elements.telemetryMode.textContent = "NO LIVE DEVICE TELEMETRY";
  }

  document.body.classList.toggle("telemetry-stale", Boolean(status.stale));

  if (status.last_update) {
    const localTime = new Date(status.last_update).toLocaleString();
    elements.lastUpdate.textContent =
      `Last update: ${localTime} · ${formatAge(status.age_seconds)}`;
  } else {
    elements.lastUpdate.textContent = "Last update: never";
  }

  if (status.last_error) {
    elements.errorBanner.textContent = `Serial polling: ${status.last_error}`;
    elements.errorBanner.classList.remove("hidden");
  } else {
    elements.errorBanner.textContent = "";
    elements.errorBanner.classList.add("hidden");
  }
}

function renderCards(status) {
  const cpu = status.cpu || {};
  const memory = status.runtime_memory || {};
  const comm = status.comm || {};
  const watchdog = status.watchdog || {};

  elements.cpuValue.textContent = formatNumber(
    cpu.scheduled_task_utilization_percent,
    1,
  );
  elements.cpuBusy.textContent = formatNumber(cpu.busy_ticks);
  elements.cpuElapsed.textContent = isNumber(cpu.elapsed_ms)
    ? `${formatNumber(cpu.elapsed_ms)} ms`
    : "—";

  elements.sramFree.textContent = formatNumber(
    memory.minimum_free_observed_bytes,
  );
  elements.sramPainted.textContent = isNumber(memory.painted_region_bytes)
    ? `${formatNumber(memory.painted_region_bytes)} B`
    : "—";
  elements.sramUsed.textContent = isNumber(memory.used_painted_bytes)
    ? `${formatNumber(memory.used_painted_bytes)} B`
    : "—";

  elements.commOverflow.textContent = formatNumber(comm.rx_overflow);
  elements.commTimeout.textContent = formatNumber(comm.parser_timeout);
  elements.commCrc.textContent = formatNumber(comm.crc_errors);

  const marker = watchdog.previous_timeout_detected;
  elements.watchdogMarker.className = "watchdog-value";
  if (marker === true) {
    elements.watchdogMarker.textContent = "YES";
    elements.watchdogMarker.classList.add("detected");
  } else if (marker === false) {
    elements.watchdogMarker.textContent = "NO";
    elements.watchdogMarker.classList.add("clear");
  } else {
    elements.watchdogMarker.textContent = "—";
  }
}

function renderTaskTable(status) {
  const timing = status.timing || {};
  const jitter = status.jitter || {};
  const overruns = status.overruns || {};
  const tasks = [
    ["actuator", "actuator_us", "actuator_ms", "actuator"],
    ["control", "control_us", "control_ms", "control"],
    ["sensor_safety", "sensor_safety_us", "sensor_safety_ms", "sensor_safety"],
    ["communication", "communication_us", "communication_ms", "communication"],
  ];

  for (const [rowName, timingKey, jitterKey, overrunKey] of tasks) {
    const row = document.querySelector(`tr[data-task="${rowName}"]`);
    row.querySelector(".exec").textContent = formatExecutionTime(timing[timingKey]);
    row.querySelector(".jitter").textContent = formatJitter(jitter[jitterKey]);
    row.querySelector(".overrun").textContent = formatNumber(overruns[overrunKey]);
  }
}

function renderEvents(events) {
  elements.eventLog.replaceChildren();
  if (!Array.isArray(events) || events.length === 0) {
    const empty = document.createElement("li");
    empty.className = "empty-event";
    empty.textContent = "No live-derived events yet.";
    elements.eventLog.append(empty);
    return;
  }

  for (const event of events.slice(0, 50)) {
    const item = document.createElement("li");
    const eventTime = document.createElement("span");
    const eventLevel = document.createElement("span");
    const eventMessage = document.createElement("span");

    eventTime.className = "event-time";
    eventTime.textContent = event.timestamp
      ? new Date(event.timestamp).toLocaleTimeString()
      : "—";

    const level = ["info", "warning", "error"].includes(event.level)
      ? event.level
      : "info";
    eventLevel.className = `event-level ${level}`;
    eventLevel.textContent = level;
    eventMessage.textContent = event.message || "Telemetry event";

    item.append(eventTime, eventLevel, eventMessage);
    elements.eventLog.append(item);
  }
}

function chartContext(canvas) {
  const pixelRatio = window.devicePixelRatio || 1;
  const width = Math.max(280, canvas.clientWidth);
  const height = Math.max(180, canvas.clientHeight);
  canvas.width = Math.floor(width * pixelRatio);
  canvas.height = Math.floor(height * pixelRatio);
  const context = canvas.getContext("2d");
  context.scale(pixelRatio, pixelRatio);
  return { context, width, height };
}

function drawLineChart(canvas, samples, field, color, unit, includeZero) {
  const { context, width, height } = chartContext(canvas);
  const points = Array.isArray(samples)
    ? samples.filter((sample) => isNumber(sample[field]))
    : [];
  const margins = { left: 54, right: 16, top: 18, bottom: 28 };
  const plotWidth = width - margins.left - margins.right;
  const plotHeight = height - margins.top - margins.bottom;
  const gridColor = "rgba(143, 164, 175, 0.16)";
  const labelColor = "#8fa4af";

  context.clearRect(0, 0, width, height);
  context.font = "11px ui-monospace, SFMono-Regular, Menlo, monospace";
  context.fillStyle = labelColor;

  if (points.length === 0) {
    context.textAlign = "center";
    context.fillText("No live samples", width / 2, height / 2);
    return;
  }

  const values = points.map((sample) => sample[field]);
  let minimum = Math.min(...values);
  let maximum = Math.max(...values);
  if (includeZero) {
    minimum = Math.min(0, minimum);
  }
  if (minimum === maximum) {
    const padding = maximum === 0 ? 1 : Math.max(1, Math.abs(maximum) * 0.08);
    minimum = Math.max(0, minimum - padding);
    maximum += padding;
  }

  context.strokeStyle = gridColor;
  context.lineWidth = 1;
  context.textAlign = "right";
  context.textBaseline = "middle";
  for (let gridIndex = 0; gridIndex <= 4; gridIndex += 1) {
    const fraction = gridIndex / 4;
    const y = margins.top + plotHeight * fraction;
    const value = maximum - (maximum - minimum) * fraction;
    context.beginPath();
    context.moveTo(margins.left, y);
    context.lineTo(width - margins.right, y);
    context.stroke();
    context.fillText(
      `${formatNumber(value, value < 10 ? 1 : 0)} ${unit}`,
      margins.left - 8,
      y,
    );
  }

  const pointX = (index) => {
    if (points.length === 1) {
      return margins.left + plotWidth / 2;
    }
    return margins.left + (plotWidth * index) / (points.length - 1);
  };
  const pointY = (value) =>
    margins.top + ((maximum - value) / (maximum - minimum)) * plotHeight;

  context.strokeStyle = color;
  context.lineWidth = 2;
  context.lineJoin = "round";
  context.beginPath();
  points.forEach((sample, index) => {
    const x = pointX(index);
    const y = pointY(sample[field]);
    if (index === 0) {
      context.moveTo(x, y);
    } else {
      context.lineTo(x, y);
    }
  });
  context.stroke();

  context.fillStyle = color;
  points.forEach((sample, index) => {
    context.beginPath();
    context.arc(pointX(index), pointY(sample[field]), 2.5, 0, Math.PI * 2);
    context.fill();
  });

  context.fillStyle = labelColor;
  context.textBaseline = "alphabetic";
  context.textAlign = "left";
  context.fillText("oldest", margins.left, height - 7);
  context.textAlign = "right";
  context.fillText("latest", width - margins.right, height - 7);
}

function renderCharts(history) {
  const samples = history && Array.isArray(history.samples) ? history.samples : [];
  const styles = getComputedStyle(document.documentElement);
  drawLineChart(
    elements.cpuChart,
    samples,
    "cpu_utilization_percent",
    styles.getPropertyValue("--blue").trim(),
    "%",
    true,
  );
  drawLineChart(
    elements.sramChart,
    samples,
    "minimum_free_observed_bytes",
    styles.getPropertyValue("--green").trim(),
    "B",
    false,
  );
}

async function fetchJson(resource) {
  const response = await fetch(resource, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`${resource} returned HTTP ${response.status}`);
  }
  return response.json();
}

let refreshInFlight = false;

async function refresh() {
  if (refreshInFlight) {
    return;
  }
  refreshInFlight = true;
  try {
    const [status, history] = await Promise.all([
      fetchJson("/api/status"),
      fetchJson("/api/history"),
    ]);
    renderConnection(status);
    renderCards(status);
    renderTaskTable(status);
    renderEvents(status.events);
    renderCharts(history);
  } catch (error) {
    renderConnection({
      connection: "DISCONNECTED",
      stale: true,
      last_update: null,
      age_seconds: null,
      last_error: `HTTP API unavailable: ${error.message}`,
    });
  } finally {
    refreshInFlight = false;
  }
}

refresh();
window.setInterval(refresh, REFRESH_INTERVAL_MS);
