"use strict";

const state = {
  session: null,
  csrf: "",
  operations: new Map(),
  assets: [],
  production: null,
  intent: null,
};

const byId = (id) => document.getElementById(id);

function setMessage(message, isError = false) {
  const node = byId("global-message");
  node.textContent = message;
  node.classList.toggle("is-error", isError);
}

function jsonText(value) {
  return JSON.stringify(value, null, 2);
}

function parseJSON(id, expected, label) {
  let value;
  try {
    value = JSON.parse(byId(id).value);
  } catch (error) {
    throw new Error(`${label} is not valid JSON: ${error.message}`);
  }
  if (expected === "array" && !Array.isArray(value)) {
    throw new Error(`${label} must be a JSON array.`);
  }
  if (expected === "object" && (value === null || Array.isArray(value) || typeof value !== "object")) {
    throw new Error(`${label} must be a JSON object.`);
  }
  return value;
}

function commaList(value) {
  return [...new Set(value.split(",").map((item) => item.trim()).filter(Boolean))];
}

function constraintList(value) {
  return [...new Set(value.split(/[\n,]/).map((item) => item.trim()).filter(Boolean))];
}

async function fetchJSON(path, options = {}) {
  const response = await fetch(path, options);
  let payload;
  try {
    payload = await response.json();
  } catch (_error) {
    throw new Error(`The local interface returned HTTP ${response.status} without JSON.`);
  }
  if (!response.ok) {
    const message = payload.message || payload.error?.message || payload.error || `HTTP ${response.status}`;
    throw new Error(message);
  }
  return payload;
}

async function call(operation, argumentsValue, approval = null) {
  const envelope = {
    request: {
      schema: "cpcs.application_request/1.0",
      operation,
      arguments: argumentsValue,
    },
  };
  if (approval !== null) {
    envelope.approval = approval;
  }
  const payload = await fetchJSON("/v1/ui/invoke", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CPCS-CSRF": state.csrf,
    },
    body: JSON.stringify(envelope),
  });
  if (payload.status !== "success") {
    throw new Error(payload.error?.message || "The CPCS operation failed.");
  }
  return payload.result;
}

function listNode(values, emptyText) {
  if (!values || values.length === 0) {
    const paragraph = document.createElement("p");
    paragraph.className = "hint";
    paragraph.textContent = emptyText;
    return paragraph;
  }
  const list = document.createElement("ul");
  list.className = "plain-list";
  values.forEach((value) => {
    const item = document.createElement("li");
    item.textContent = typeof value === "string" ? value : jsonText(value);
    list.append(item);
  });
  return list;
}

function replaceChildren(id, ...nodes) {
  byId(id).replaceChildren(...nodes);
}

function intentArguments() {
  const argumentsValue = { text: byId("intent-text").value.trim() };
  const overrides = commaList(byId("profile-overrides").value);
  if (overrides.length) {
    argumentsValue.profile_overrides = overrides;
  }
  const constraints = constraintList(byId("user-constraints").value);
  if (constraints.length) {
    argumentsValue.user_constraints = constraints;
  }
  return argumentsValue;
}

function renderIntent(intent) {
  state.intent = intent;
  const profiles = [];
  const primary = document.createElement("span");
  primary.className = "badge primary";
  primary.textContent = intent.profiles?.primary || "No primary profile";
  profiles.push(primary);
  (intent.profiles?.secondary || []).forEach((profile) => {
    const badge = document.createElement("span");
    badge.className = "badge";
    badge.textContent = profile;
    profiles.push(badge);
  });
  replaceChildren("profile-badges", ...profiles);
  replaceChildren(
    "conflict-list",
    listNode(intent.conflicts || [], "No unresolved profile conflict was detected."),
  );
  replaceChildren(
    "missing-list",
    listNode(intent.requirements?.missing_inputs || [], "No required input is missing."),
  );
  byId("knowledge-query").textContent = intent.routing?.knowledge_query || "No knowledge query was emitted.";
  byId("intent-review").hidden = false;
}

async function reviewIntent() {
  const text = byId("intent-text").value.trim();
  if (!text) {
    throw new Error("Enter a creative brief before reviewing intent.");
  }
  setMessage("Resolving intent and profile routing…");
  const intent = await call("cpcs.intent.normalize", intentArguments());
  renderIntent(intent);
  setMessage("Detected direction is ready for review.");
  byId("intent-review").scrollIntoView({ behavior: "smooth", block: "start" });
}

function productionArguments() {
  const argumentsValue = {
    ...intentArguments(),
    project_id: byId("project-id").value.trim(),
    platform: byId("platform").value.trim(),
    creative_mode: byId("creative-mode").value,
    duration_seconds: Number(byId("duration").value),
    aspect_ratio: byId("aspect-ratio").value,
    resolution: byId("resolution").value,
    seed: Number(byId("seed").value),
    sample_count: Number(byId("sample-count").value),
    assets: state.assets.map((row) => row.asset),
  };
  const overlays = parseJSON("overlays-json", "array", "Score overlays");
  const conflicts = parseJSON("conflict-json", "object", "Conflict resolutions");
  const bindings = parseJSON("asset-bindings-json", "array", "Provider asset bindings");
  if (overlays.length) {
    argumentsValue.overlays = overlays;
  }
  if (Object.keys(conflicts).length) {
    argumentsValue.conflict_resolutions = conflicts;
  }
  if (bindings.length) {
    argumentsValue.asset_bindings = bindings;
  }
  const contextIds = commaList(byId("context-profile-ids").value);
  const contextAsOf = byId("context-as-of").value.trim();
  if (contextIds.length) {
    if (!contextAsOf) {
      throw new Error("Context profile IDs require an exact context as-of time.");
    }
    argumentsValue.context_profile_ids = contextIds;
    argumentsValue.context_as_of = contextAsOf;
  } else if (contextAsOf) {
    throw new Error("Context as-of time requires at least one context profile ID.");
  }
  return argumentsValue;
}

function metric(label, value) {
  const node = document.createElement("div");
  node.className = "metric";
  const name = document.createElement("span");
  name.textContent = label;
  const strong = document.createElement("strong");
  strong.textContent = String(value ?? "Not available");
  node.append(name, strong);
  return node;
}

function controlsTable(controls) {
  const table = document.createElement("table");
  const head = document.createElement("thead");
  const headRow = document.createElement("tr");
  ["Control path", "Resolved value", "Authority"].forEach((label) => {
    const cell = document.createElement("th");
    cell.scope = "col";
    cell.textContent = label;
    headRow.append(cell);
  });
  head.append(headRow);
  const body = document.createElement("tbody");
  controls.forEach((control) => {
    const row = document.createElement("tr");
    const pathCell = document.createElement("td");
    const code = document.createElement("code");
    code.textContent = control.path;
    pathCell.append(code);
    const valueCell = document.createElement("td");
    valueCell.textContent = typeof control.value === "string" ? control.value : JSON.stringify(control.value);
    const authorityCell = document.createElement("td");
    authorityCell.textContent = control.provenance?.winner || control.authority || "canonical resolver";
    row.append(pathCell, valueCell, authorityCell);
    body.append(row);
  });
  table.append(head, body);
  return table;
}

function renderProduction(result) {
  state.production = result;
  renderIntent(result.normalized_intent);
  const score = result.score;
  const build = result.build;
  replaceChildren(
    "build-summary",
    metric("Score status", score.score_status),
    metric("Canonical score", score.score_id),
    metric("Provider build", build.build_id),
    metric("Build disposition", build.disposition),
  );
  const controls = score.provider_neutral_controls || [];
  replaceChildren(
    "control-table",
    controls.length ? controlsTable(controls) : listNode([], "No provider-neutral control was emitted."),
  );
  replaceChildren(
    "score-warnings",
    listNode([...(score.unresolved || []), ...(score.warnings || [])], "No warning or unresolved choice remains."),
  );
  byId("production-json").textContent = jsonText(result);
  byId("runtime-build-id").value = build.build_id;
  replaceChildren(
    "canonical-identity",
    definitionRow("Score", score.score_id),
    definitionRow("Build", build.build_id),
    definitionRow("Build hash", build.build_hash),
  );
  byId("build-review").hidden = false;
}

function definitionRow(term, description) {
  const row = document.createElement("div");
  const dt = document.createElement("dt");
  const dd = document.createElement("dd");
  dt.textContent = term;
  dd.textContent = description;
  row.append(dt, dd);
  return row;
}

async function prepareProduction() {
  setMessage("Resolving the canonical score and provider build…");
  const result = await call("cpcs.production.prepare", productionArguments());
  renderProduction(result);
  setMessage("Canonical score and provider build are ready.");
  byId("build-review").scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderReferences() {
  const list = byId("reference-list");
  list.replaceChildren();
  state.assets.forEach((row) => {
    const item = document.createElement("li");
    item.textContent = `${row.asset.role} · ${row.upload.mime_type} · ${row.upload.size_bytes} bytes · ${row.asset.content_hash}`;
    list.append(item);
  });
}

async function uploadReferences() {
  const input = byId("reference-files");
  const files = [...input.files];
  if (!files.length) {
    throw new Error("Choose at least one reference file.");
  }
  const role = byId("reference-role").value.trim();
  const rights = byId("rights-basis").value;
  setMessage(`Hashing and staging ${files.length} local reference${files.length === 1 ? "" : "s"}…`);
  for (const file of files) {
    const result = await fetchJSON("/v1/ui/upload", {
      method: "POST",
      headers: {
        "Content-Type": file.type,
        "X-CPCS-CSRF": state.csrf,
        "X-CPCS-Asset-Role": role,
        "X-CPCS-Rights-Basis": rights,
      },
      body: file,
    });
    if (!state.assets.some((row) => row.asset.asset_id === result.asset.asset_id)) {
      state.assets.push(result);
    }
  }
  input.value = "";
  renderReferences();
  setMessage("Reference bytes are staged for this local session.");
}

function operationChanged() {
  const operation = state.operations.get(byId("operation-select").value);
  if (!operation) {
    return;
  }
  byId("operation-description").textContent = operation.description;
  byId("operation-schema").textContent = jsonText(operation.input_schema);
  byId("approval-fields").hidden = !operation.authorization_required;
  byId("approval-confirmed").checked = false;
}

async function runOperation() {
  const operationName = byId("operation-select").value;
  const operation = state.operations.get(operationName);
  const argumentsValue = parseJSON("operation-arguments", "object", "Operation arguments");
  let approval = null;
  if (operation.authorization_required) {
    approval = {
      confirmed: byId("approval-confirmed").checked,
      reason: byId("approval-reason").value,
    };
  }
  setMessage(`Invoking ${operationName}…`);
  const result = await call(operationName, argumentsValue, approval);
  byId("operation-output").textContent = jsonText(result);
  setMessage(`${operationName} completed.`);
}

function selectPanel(name) {
  document.querySelectorAll(".mode-tab").forEach((tab) => {
    const selected = tab.dataset.panel === name;
    tab.classList.toggle("is-active", selected);
    tab.setAttribute("aria-selected", String(selected));
    byId(`panel-${tab.dataset.panel}`).hidden = !selected;
  });
}

async function renderCreate() {
  const buildId = byId("runtime-build-id").value.trim();
  if (!buildId) {
    throw new Error("Create a build or enter its build ID first.");
  }
  const result = await call("cpcs.render.create", {
    build_id: buildId,
    idempotency_key: `local-ui-${buildId}`,
  });
  byId("runtime-job-id").value = result.job.job_id;
  byId("operation-output").textContent = jsonText(result);
  setMessage("The journaled render job is registered. No provider call has occurred.");
}

async function renderAction(operation) {
  const jobId = byId("runtime-job-id").value.trim();
  if (!jobId) {
    throw new Error("Enter a render job ID first.");
  }
  const requiresApproval = operation !== "cpcs.render.show";
  const approval = requiresApproval ? {
    confirmed: true,
    reason: byId("runtime-approval-reason").value,
  } : null;
  setMessage(`${operation} is running…`);
  const result = await call(operation, { job_id: jobId }, approval);
  byId("operation-output").textContent = jsonText(result);
  setMessage(`${operation} completed.`);
}

function guarded(handler) {
  return async (event) => {
    event.preventDefault();
    const button = event.submitter || event.currentTarget;
    if (button instanceof HTMLButtonElement) {
      button.disabled = true;
    }
    try {
      await handler(event);
    } catch (error) {
      setMessage(error.message || String(error), true);
    } finally {
      if (button instanceof HTMLButtonElement) {
        button.disabled = false;
      }
    }
  };
}

function bindEvents() {
  document.querySelectorAll(".mode-tab").forEach((tab) => {
    tab.addEventListener("click", () => selectPanel(tab.dataset.panel));
    tab.addEventListener("keydown", (event) => {
      if (!["ArrowLeft", "ArrowRight"].includes(event.key)) {
        return;
      }
      const tabs = [...document.querySelectorAll(".mode-tab")];
      const offset = event.key === "ArrowRight" ? 1 : -1;
      const next = tabs[(tabs.indexOf(tab) + offset + tabs.length) % tabs.length];
      next.focus();
      next.click();
    });
  });
  byId("review-intent").addEventListener("click", guarded(reviewIntent));
  byId("guided-form").addEventListener("submit", guarded(prepareProduction));
  byId("upload-references").addEventListener("click", guarded(uploadReferences));
  byId("advanced-form").addEventListener("submit", guarded(prepareProduction));
  byId("operation-select").addEventListener("change", operationChanged);
  byId("operation-form").addEventListener("submit", guarded(runOperation));
  byId("render-create").addEventListener("click", guarded(renderCreate));
  byId("render-run").addEventListener("click", guarded(() => renderAction("cpcs.render.run")));
  byId("render-show").addEventListener("click", guarded(() => renderAction("cpcs.render.show")));
  byId("render-cancel").addEventListener("click", guarded(() => renderAction("cpcs.render.cancel")));
}

async function initialize() {
  try {
    const session = await fetchJSON("/v1/ui/session");
    state.session = session;
    state.csrf = session.csrf_token;
    session.operations.forEach((operation) => state.operations.set(operation.name, operation));
    byId("session-label").textContent = `${session.identity} · ${session.role} · local session`;
    byId("authority-role").textContent = session.role;
    const select = byId("operation-select");
    session.operations.forEach((operation) => {
      const option = document.createElement("option");
      option.value = operation.name;
      option.textContent = operation.name;
      select.append(option);
    });
    operationChanged();
    bindEvents();
    setMessage("Local session ready. No provider or authority write has occurred.");
  } catch (error) {
    setMessage(error.message || String(error), true);
  }
}

initialize();
