const AGENDA_COLUMNS = new Set([
  "day",
  "topic",
  "focus",
  "how_to_cover",
  "practice",
  "resource",
]);

const STATUS_META = {
  "not-started": { label: "Not started", className: "status-not-started" },
  "in-progress": { label: "In progress", className: "status-in-progress" },
  done: { label: "Done", className: "status-done" },
  blocked: { label: "Blocked", className: "status-blocked" },
  unknown: { label: "Needs review", className: "status-unknown" },
};

const state = {
  rows: [],
  people: [],
  search: "",
  status: "all",
  person: "all",
};

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function parseCsv(text) {
  const rows = [];
  let row = [];
  let cell = "";
  let quoted = false;

  for (let index = 0; index < text.length; index += 1) {
    const character = text[index];
    const next = text[index + 1];
    if (character === '"' && quoted && next === '"') {
      cell += '"';
      index += 1;
    } else if (character === '"') {
      quoted = !quoted;
    } else if (character === "," && !quoted) {
      row.push(cell);
      cell = "";
    } else if ((character === "\n" || character === "\r") && !quoted) {
      if (character === "\r" && next === "\n") {
        index += 1;
      }
      row.push(cell);
      if (row.some((value) => value !== "")) {
        rows.push(row);
      }
      row = [];
      cell = "";
    } else {
      cell += character;
    }
  }

  if (cell !== "" || row.length > 0) {
    row.push(cell);
    if (row.some((value) => value !== "")) {
      rows.push(row);
    }
  }

  if (rows.length < 2) {
    throw new Error("The CSV does not contain an agenda.");
  }

  const headers = rows[0].map((header, index) =>
    index === 0 ? header.replace(/^\uFEFF/, "") : header,
  );
  return rows.slice(1).map((values) =>
    Object.fromEntries(headers.map((header, index) => [header, values[index] ?? ""])),
  );
}

function normalizeStatus(value) {
  const key = String(value ?? "").toLowerCase().replace(/[\s_-]/g, "");
  if (key === "notstarted" || key === "todo" || key === "pending") {
    return "not-started";
  }
  if (key === "inprogress" || key === "doing" || key === "active") {
    return "in-progress";
  }
  if (["done", "complete", "completed", "finished"].includes(key)) {
    return "done";
  }
  if (key === "blocked") {
    return "blocked";
  }
  return "unknown";
}

function statusMeta(value) {
  return STATUS_META[normalizeStatus(value)] ?? STATUS_META.unknown;
}

function statusPill(person, value) {
  const status = statusMeta(value);
  return `
    <span class="status-pill ${status.className}" title="${escapeHtml(status.label)}">
      <i class="status-dot" aria-hidden="true"></i>
      ${escapeHtml(person)}: ${escapeHtml(status.label)}
    </span>`;
}

function rowMatchesSearch(row) {
  const query = state.search.trim().toLowerCase();
  if (!query) {
    return true;
  }
  return ["day", "topic", "focus", "how_to_cover", "practice", "resource"].some(
    (column) => String(row[column] ?? "").toLowerCase().includes(query),
  );
}

function rowMatchesStatus(row) {
  if (state.status === "all") {
    return true;
  }
  const people = state.person === "all" ? state.people : [state.person];
  return people.some((person) => normalizeStatus(row[person]) === state.status);
}

function filteredRows() {
  return state.rows.filter((row) => rowMatchesSearch(row) && rowMatchesStatus(row));
}

function calculateLearnerStats(person) {
  const counts = { done: 0, "in-progress": 0, blocked: 0, "not-started": 0 };
  state.rows.forEach((row) => {
    const status = normalizeStatus(row[person]);
    if (Object.hasOwn(counts, status)) {
      counts[status] += 1;
    }
  });
  const total = state.rows.length;
  return {
    ...counts,
    total,
    percent: total === 0 ? 0 : Math.round((counts.done / total) * 100),
  };
}

function renderStats() {
  const totalUnits = state.rows.length * state.people.length;
  const completedUnits = state.people.reduce(
    (sum, person) => sum + calculateLearnerStats(person).done,
    0,
  );
  const activeLearners = state.people.filter(
    (person) => calculateLearnerStats(person)["in-progress"] > 0,
  ).length;
  const completion = totalUnits === 0 ? 0 : Math.round((completedUnits / totalUnits) * 100);

  document.querySelector("#stats").innerHTML = `
    <article class="stat-card">
      <span class="stat-label">Overall completion</span>
      <strong class="stat-value">${completion}%</strong>
      <span class="stat-detail">${completedUnits} of ${totalUnits} learner-days done</span>
    </article>
    <article class="stat-card">
      <span class="stat-label">Agenda length</span>
      <strong class="stat-value">${state.rows.length} days</strong>
      <span class="stat-detail">One practical focus per day</span>
    </article>
    <article class="stat-card">
      <span class="stat-label">Learners</span>
      <strong class="stat-value">${state.people.length}</strong>
      <span class="stat-detail">${activeLearners} currently in progress</span>
    </article>
    <article class="stat-card">
      <span class="stat-label">Blocked items</span>
      <strong class="stat-value">${state.people.reduce(
        (sum, person) => sum + calculateLearnerStats(person).blocked,
        0,
      )}</strong>
      <span class="stat-detail">Raise these in the next discussion</span>
    </article>`;
}

function renderLearners() {
  const cards = state.people.map((person) => {
    const stats = calculateLearnerStats(person);
    return `
      <article class="learner-card">
        <div class="learner-header">
          <span class="learner-name">${escapeHtml(person)}</span>
          <span class="learner-percent">${stats.percent}%</span>
        </div>
        <div class="progress-track" role="progressbar" aria-label="${escapeHtml(person)} completion"
             aria-valuemin="0" aria-valuemax="100" aria-valuenow="${stats.percent}">
          <div class="progress-bar" style="width: ${stats.percent}%"></div>
        </div>
        <div class="learner-details">
          <span><strong>${stats.done}</strong> done</span>
          <span><strong>${stats["in-progress"]}</strong> active</span>
          <span><strong>${stats.blocked}</strong> blocked</span>
        </div>
      </article>`;
  });
  document.querySelector("#learner-overview").innerHTML = cards.join("");
  document.querySelector("#learner-meta").textContent =
    `${state.people.length} learners · ${state.rows.length} days`;
}

function renderAgenda() {
  const rows = filteredRows();
  document.querySelector("#agenda-meta").textContent =
    `${rows.length} of ${state.rows.length} days shown`;
  if (rows.length === 0) {
    document.querySelector("#agenda-list").innerHTML =
      '<div class="empty-state">No agenda days match these filters. Try resetting the search.</div>';
    return;
  }

  const visiblePeople = state.person === "all" ? state.people : [state.person];
  document.querySelector("#agenda-list").innerHTML = rows
    .map(
      (row) => `
        <article class="agenda-card">
          <div class="agenda-top">
            <span class="day-number" aria-label="Day ${escapeHtml(row.day)}">${escapeHtml(row.day)}</span>
            <div>
              <span class="day-label">Day ${escapeHtml(row.day)}</span>
              <h3 class="agenda-topic">${escapeHtml(row.topic)}</h3>
              <p class="agenda-focus">${escapeHtml(row.focus)}</p>
            </div>
            <div class="status-list">
              ${visiblePeople.map((person) => statusPill(person, row[person])).join("")}
            </div>
          </div>
          <div class="agenda-details">
            <p class="agenda-detail">
              <span class="agenda-detail-label">How to cover</span>
              ${escapeHtml(row.how_to_cover)}
            </p>
            <p class="agenda-detail">
              <span class="agenda-detail-label">Practice</span>
              ${escapeHtml(row.practice)}
            </p>
            <p class="agenda-detail">
              <span class="agenda-detail-label">Suggested resource</span>
              ${escapeHtml(row.resource)}
            </p>
          </div>
        </article>`,
    )
    .join("");
}

function render() {
  renderStats();
  renderLearners();
  renderAgenda();
}

function setupControls() {
  const search = document.querySelector("#search");
  const statusFilter = document.querySelector("#status-filter");
  const personFilter = document.querySelector("#person-filter");
  search.addEventListener("input", (event) => {
    state.search = event.target.value;
    renderAgenda();
  });
  statusFilter.addEventListener("change", (event) => {
    state.status = event.target.value;
    renderAgenda();
  });
  personFilter.addEventListener("change", (event) => {
    state.person = event.target.value;
    renderAgenda();
  });
  document.querySelector("#reset-filters").addEventListener("click", () => {
    state.search = "";
    state.status = "all";
    state.person = "all";
    search.value = "";
    statusFilter.value = "all";
    personFilter.value = "all";
    renderAgenda();
  });
}

async function loadAgenda() {
  const response = await fetch("data/training.csv", { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Could not load data/training.csv (HTTP ${response.status}).`);
  }
  const rows = parseCsv(await response.text());
  const headers = Object.keys(rows[0]);
  state.people = headers.filter((header) => !AGENDA_COLUMNS.has(header));
  state.rows = rows;
  if (state.people.length === 0) {
    throw new Error("The agenda CSV does not contain learner columns.");
  }
}

function showError(error) {
  const message = error instanceof Error ? error.message : String(error);
  document.querySelector("#data-note").textContent = "The agenda could not be loaded.";
  document.querySelector("#stats").innerHTML =
    `<div class="error-card">Unable to load training data: ${escapeHtml(message)}</div>`;
  document.querySelector("#learner-overview").innerHTML =
    `<div class="error-card">Fix the CSV or Pages deployment, then refresh this page.</div>`;
  document.querySelector("#agenda-list").innerHTML = "";
}

setupControls();
loadAgenda()
  .then(() => {
    document.querySelector("#data-note").textContent =
      `Live data source · ${state.rows.length}-day agenda · ${state.people.length} learners`;
    render();
  })
  .catch(showError);
