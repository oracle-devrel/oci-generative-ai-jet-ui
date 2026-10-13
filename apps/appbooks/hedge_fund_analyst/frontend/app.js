const $ = (s) => document.querySelector(s),
  esc = (v) =>
    String(v ?? "").replace(
      /[&<>"']/g,
      (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]
    );
const state = {
  thread: crypto.randomUUID(),
  models: [],
  turns: [],
  view: "tables",
  latest: {},
  busy: false,
  table: "hf_positions",
  offset: 0,
  defaultModel: null,
  runs: {},
  health: null,
  sim: null,
};
const persona = () => $("#persona").value;
// Chart roles: series colours validated for colour-blind separation on the light surface.
const COLORS = {
  plane: "#006b47",
  naive: "#bf714d",
  llm: "#2a78d6",
  retrieval: "#eda100",
  rerank: "#6250d6",
  other: "#b9bdb4",
};
async function api(path, opts) {
  const r = await fetch(path, opts);
  const j = await r.json();
  if (!r.ok) throw Error(typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail));
  return j;
}
function session() {
  state.thread = crypto.randomUUID();
  $("#session").textContent = "SESSION / " + state.thread.slice(0, 8);
  for (const kind of ["plane", "naive"])
    $("#" + kind + "-chat").innerHTML =
      '<div class="empty"><h3>New session</h3><p>Oracle memory persists. Conversation context starts fresh.</p></div>';
  state.latest = {};
}
function pretty(v) {
  return "<pre>" + esc(JSON.stringify(v, null, 2)) + "</pre>";
}
function table(rows) {
  if (!rows?.length)
    return '<p class="muted">No records returned under this database identity.</p>';
  const keys = [...new Set(rows.flatMap(Object.keys))];
  return (
    '<div class="table-wrap"><table><thead><tr>' +
    keys.map((k) => "<th>" + esc(k) + "</th>").join("") +
    "</tr></thead><tbody>" +
    rows
      .map(
        (r) =>
          "<tr>" +
          keys
            .map((k) => {
              const v =
                r[k] !== null && typeof r[k] === "object"
                  ? JSON.stringify(r[k])
                  : String(r[k] ?? "");
              return (
                "<td>" +
                (v.length > 160
                  ? "<details><summary>" +
                    esc(v.slice(0, 90)) +
                    "…</summary><pre>" +
                    esc(v) +
                    "</pre></details>"
                  : esc(v)) +
                "</td>"
              );
            })
            .join("") +
          "</tr>"
      )
      .join("") +
    "</tbody></table></div>"
  );
}
const view = (v) =>
  Array.isArray(v) && v.length && typeof v[0] === "object" ? table(v) : pretty(v);
// Status chips: what each component is, where it sits in the data flow (* marks the component), and why it matters.
const COMPONENTS = {
  database: {
    title: "Oracle AI Database 26ai Free",
    what: "The primary database of record: positions, prices, research vectors, the property graph, metric definitions, agent memory and audit live in one engine.",
    flow: ["Both agents (FastAPI)", "Primary · FREEPDB1*", "Rows · vectors · graph · memory"],
    benefit: "One engine instead of separate vector, graph, cache and memory stores kept in sync.",
  },
  deep_data_security: {
    title: "Deep Data Security",
    what: "Each analyst is a database end user (hf_credit / hf_markets) whose data role carries desk data grants. Oracle filters every statement, including the SQL a model writes.",
    flow: ["Model-written SQL", "Data grant · desk = signed-in desk*", "Only entitled rows"],
    benefit:
      "Prompt injection cannot widen access: the boundary lives in the database, not the prompt.",
  },
  graph_isolation: {
    title: "Graph isolation",
    what: "SQL property graphs run with definer rights, so desk vertices come from views bound to the authenticated end user. Checked live for both desks on every health poll.",
    flow: ["GRAPH_TABLE query", "Desk views · AUTHENTICATED_IDENTITY*", "Own-desk vertices only"],
    benefit: "The ontology can never become a side door around entitlements.",
  },
  embeddings: {
    title: "In-database embeddings",
    what: "Oracle’s all-MiniLM-L12-v2 ONNX model, loaded with DBMS_VECTOR.LOAD_ONNX_MODEL. Questions, passages and memories are embedded in SQL; question vectors are cached.",
    flow: ["Question text", "VECTOR_EMBEDDING(HF_EMBED)*", "384-dim vector → search & cache"],
    benefit: "No external embedding API: text and vectors never leave the database.",
  },
  rerank: {
    title: "In-database reranker",
    what: "An ONNX cross-encoder rescored the vector-search candidates with SQL PREDICTION before they reach the model.",
    flow: ["Top 8 by vector distance", "PREDICTION(RERANK_XENC)*", "Top 5 as evidence"],
    benefit: "Sharper evidence and fewer tokens, scored where the data lives.",
  },
  memory: {
    title: "Agent memory (OAMP 26.8)",
    what: "oracleagentmemory in a per-desk schema. A “Correction:” message becomes a durable fact with its source message; new sessions recall it and the answer cites it.",
    flow: [
      "Correction message",
      "Model extracts the fact",
      "OAMP · HF_*_MEM*",
      "Recalled next session",
    ],
    benefit: "The agent learns once, and every memory shows where it came from.",
  },
  true_cache: {
    title: "Oracle True Cache",
    what: "A read-only, in-memory Oracle instance kept current from the primary’s redo. It serves the cache tier and ontology/catalog reads; desk-entitled reads stay on the primary.",
    flow: [
      "Cache & ontology reads",
      "True Cache · HF_READS_TC*",
      "Miss → primary",
      "Primary redo → True Cache",
    ],
    benefit: "Read-heavy lookups leave the primary, with no cache-invalidation code.",
  },
  audit: {
    title: "Unified Auditing",
    what: "Audit policies on positions, collateral, research, semantics, memory and cache tables. Each turn tags its sessions with a request ID shown in the inspector.",
    flow: ["Statement + request ID", "Unified Audit trail*", "Inspector · Audit tab"],
    benefit: "Every read is attributable to the end user and the turn that made it.",
  },
  private_ai: {
    title: "Oracle Private AI Services",
    what: "A container serving a local open-weight model (Qwen 2.5 3B GGUF via llama.cpp). Prepared but deferred: the registry needs docker login.",
    flow: ["Agent prompt", "Private AI Services · llama.cpp*", "Local model answer"],
    benefit: "Local inference with no API cost and no data leaving the machine.",
  },
};
const ORDER = [
  "database",
  "deep_data_security",
  "graph_isolation",
  "embeddings",
  "rerank",
  "memory",
  "true_cache",
  "audit",
  "private_ai",
];
const card = document.createElement("div");
card.className = "comp-card";
card.hidden = true;
document.body.append(card);
function showCard(chip) {
  const c = COMPONENTS[chip.dataset.comp];
  if (!c) return;
  const flow = c.flow
    .map(
      (x) =>
        '<span class="cc-box' +
        (x.endsWith("*") ? " self" : "") +
        '">' +
        esc(x.replace(/\*$/, "")) +
        "</span>"
    )
    .join('<span class="cc-arrow">→</span>');
  card.innerHTML =
    '<div class="cc-head"><b>' +
    esc(c.title) +
    '</b><span class="cc-state ' +
    esc(chip.dataset.state.replace(" ", "-")) +
    '">' +
    esc(chip.dataset.state) +
    "</span></div><p>" +
    esc(c.what) +
    '</p><div class="cc-flow" aria-label="Data flow">' +
    flow +
    '</div><p class="cc-benefit">✓ ' +
    esc(c.benefit) +
    "</p>" +
    (chip.dataset.detail ? '<p class="cc-live">Live: ' + esc(chip.dataset.detail) + "</p>" : "");
  card.hidden = false;
  const r = chip.getBoundingClientRect();
  const left = Math.max(8, Math.min(r.left, innerWidth - card.offsetWidth - 8));
  card.style.left = left + "px";
  card.style.top =
    (r.bottom + 8 + card.offsetHeight > innerHeight
      ? r.top - card.offsetHeight - 8
      : r.bottom + 8) + "px";
}
function hideCard() {
  card.hidden = true;
}
function pinCard(chip) {
  document.querySelectorAll(".component.pinned").forEach((c) => c.classList.remove("pinned"));
  state.pinned = chip ? chip.dataset.comp : null;
  card.classList.toggle("pinned", !!chip);
  if (chip) {
    chip.classList.add("pinned");
    showCard(chip);
  } else hideCard();
}
document.addEventListener("click", (e) => {
  if (state.pinned && !card.contains(e.target) && !e.target.closest(".component")) pinCard(null);
});
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && state.pinned) pinCard(null);
});
window.addEventListener(
  "scroll",
  () => {
    const chip =
      state.pinned && document.querySelector('.component[data-comp="' + state.pinned + '"]');
    if (chip) showCard(chip);
  },
  { passive: true }
);
async function health() {
  try {
    const h = await api("/api/health");
    $("#connection").textContent = h.ready
      ? "● Oracle connected · live data"
      : "Oracle needs attention";
    $("#connection").classList.toggle("error", !h.ready);
    const iso = (h.isolation || []).every((c) => c.isolated);
    const comps = [...(h.components || [])];
    if (h.isolation)
      comps.push({
        component: "graph_isolation",
        state: iso ? "verified" : "failed",
        detail: (h.isolation || [])
          .map((c) => c.persona + " graph sees " + c.graph_desks.join(","))
          .join("; "),
      });
    comps.sort(
      (a, b) => ((ORDER.indexOf(a.component) + 99) % 99) - ((ORDER.indexOf(b.component) + 99) % 99)
    );
    $("#components").innerHTML = comps
      .map(
        (c) =>
          '<div class="component ' +
          esc(c.state.replace(" ", "-")) +
          (c.state === "verified" ? " running" : "") +
          '" tabindex="0" data-comp="' +
          esc(c.component) +
          '" data-state="' +
          esc(c.state) +
          '" data-detail="' +
          esc(c.detail || "") +
          '"><i></i><b>' +
          esc(c.component.replaceAll("_", " ")) +
          "</b><span>" +
          esc(c.state) +
          "</span></div>"
      )
      .join("");
    $("#components")
      .querySelectorAll(".component")
      .forEach((chip) => {
        if (state.pinned === chip.dataset.comp) {
          chip.classList.add("pinned");
          showCard(chip);
        }
        // Hover previews; a click (or Enter) pins the card until the user clicks elsewhere or presses Escape.
        chip.onmouseenter = () => {
          if (!state.pinned) showCard(chip);
        };
        chip.onmouseleave = () => {
          if (!state.pinned) hideCard();
        };
        chip.onfocus = () => {
          if (!state.pinned) showCard(chip);
        };
        chip.onblur = () => {
          if (!state.pinned) hideCard();
        };
        chip.onclick = (e) => {
          e.stopPropagation();
          pinCard(state.pinned === chip.dataset.comp ? null : chip);
        };
        chip.onkeydown = (e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            pinCard(state.pinned === chip.dataset.comp ? null : chip);
          }
        };
      });
    if (!h.ready)
      $("#status").textContent = h.error || "Entitlement check failed: answers are disabled.";
    state.health = h;
    personaNote();
    if (window.Architecture && state.archMounted) Architecture.update(h);
    else mountArchitecture();
    state.models = h.models || [];
    state.defaultModel = state.defaultModel || h.default_model;
    const old = $("#model").value || state.defaultModel;
    $("#model").innerHTML = state.models
      .map(
        (m) =>
          '<option value="' +
          esc(m.id) +
          '" ' +
          (!m.enabled ? "disabled" : "") +
          ">" +
          esc(m.label) +
          (m.enabled ? "" : " — " + esc(m.reason)) +
          "</option>"
      )
      .join("");
    const selected =
      state.models.find((m) => m.id === old && m.enabled) || state.models.find((m) => m.enabled);
    if (selected) $("#model").value = selected.id;
    modelNote();
    $("#send").disabled = !h.ready || !selected || state.busy;
  } catch (e) {
    $("#connection").textContent = "Connection failed";
    $("#status").textContent = e.message;
  }
}
// What the persona switch changes: the Oracle identity both agents use, and therefore which rows Deep Data Security returns.
function personaNote() {
  const p = persona(),
    other = p === "Credit" ? "Markets" : "Credit",
    user = "hf_" + p.toLowerCase(),
    live = (state.health?.entitlements || []).find((e) => e.persona === p);
  $("#persona-note").innerHTML =
    '<span class="pn-lock" aria-hidden="true">🔒</span> Both agents connect to Oracle as end user <code>' +
    user +
    "</code> (data role <code>HF_" +
    p.toUpperCase() +
    "_ROLE</code>). Deep Data Security returns only <b>" +
    p +
    "-desk</b> positions, collateral and research to every statement, including SQL the model writes" +
    (live ? " — live check: " + live.n + " positions, desk " + esc(live.desk) : "") +
    ". " +
    other +
    "-desk rows are invisible, even to <code>OR 1=1</code>. Shared reference data (legal entities, instruments, prices, metric catalog) is visible to both desks; memory and caches live in <code>HF_" +
    p.toUpperCase() +
    "_MEM</code>. Switching persona starts a new session under <code>hf_" +
    other.toLowerCase() +
    '</code> and reloads the data explorer. <a href="/primer">How it works →</a>';
}
function modelNote() {
  const m = state.models.find((m) => m.id === $("#model").value);
  $("#model-note").textContent = m
    ? m.note + " · " + m.context.toLocaleString() + " token context window."
    : "";
}
const short = (m) =>
  (m || "")
    .replace(/^xai\./, "")
    .replace("claude-", "")
    .replace(":latest", "")
    .replace("-instruct-q4_k_m", "");
function renderTurn(r) {
  const target = $("#" + r.agent + "-chat");
  target.querySelector(".empty")?.remove();
  const div = document.createElement("section");
  div.className = "turn";
  const u = r.usage,
    a = r.accuracy,
    i = r.inspector;
  const verdict =
    a.score === null
      ? "Unscored"
      : a.score === 1
        ? "✓ Correct against the golden answer"
        : "✗ Does not match the golden answer";
  // Cache stack strip (plane): True Cache reads, exact response, embedding, semantic and provider prompt cache.
  const cs = i.cache_stack,
    sc = i.semantic_cache;
  let badge = "";
  if (r.agent === "plane" && (cs || sc)) {
    const chip = (cls, label, title) =>
      '<span class="chip ' + cls + '" title="' + esc(title || "") + '">' + label + "</span>";
    const parts = [];
    if (cs) {
      parts.push(
        chip(
          cs.true_cache && cs.true_cache.reads ? "on" : "off",
          "True Cache · " + ((cs.true_cache || {}).reads || 0) + " reads",
          "Reads served by Oracle True Cache (session role PHYSICAL STANDBY on HF_READS_TC); entitled reads stay on the primary under DDS"
        )
      );
      parts.push(
        chip(
          cs.exact.state === "hit" ? "hit" : "miss",
          "Exact " + (cs.exact.state === "hit" ? "hit · " + esc(cs.exact.tier) : "miss"),
          "SHA-256 key " +
            cs.exact.key +
            "… over desk, model, prompt version, question and recalled memories"
        )
      );
      parts.push(
        chip(
          cs.embedding.state === "hit" ? "hit" : "miss",
          "Embedding " + esc(cs.embedding.state),
          esc(cs.embedding.tier || "")
        )
      );
    }
    if (sc)
      parts.push(
        chip(
          sc.state === "hit" ? "hit" : sc.state === "near_miss" ? "near" : "miss",
          "Semantic " +
            (sc.state === "hit"
              ? "hit " + (sc.distance ?? "")
              : sc.state === "near_miss"
                ? "near miss · rejected"
                : esc(sc.state)),
          sc.reason || sc.reuse || ""
        )
      );
    if (u.cached_input_tokens || u.cache_write_tokens)
      parts.push(
        chip(
          "hit",
          "Prompt cache · " +
            (u.cached_input_tokens || 0).toLocaleString() +
            " read" +
            (u.cache_write_tokens
              ? " · " + u.cache_write_tokens.toLocaleString() + " written"
              : ""),
          "Provider prompt cache on the stable system prefix"
        )
      );
    badge = '<div class="cache-strip">' + parts.join("") + "</div>";
  } else if (r.agent === "naive" && (u.cached_input_tokens || u.cache_write_tokens))
    badge =
      '<div class="cache-strip"><span class="chip hit" title="Provider prompt cache, same settings as the plane">Prompt cache · ' +
      (u.cached_input_tokens || 0).toLocaleString() +
      " read</span></div>";
  div.innerHTML =
    '<p class="question">' +
    esc(r.question) +
    " · " +
    esc(r.persona) +
    " · " +
    esc(short(r.model)) +
    "</p>" +
    badge +
    '<div class="answer">' +
    esc(r.answer) +
    '</div><div class="tokens"><span>Input<b>' +
    u.input_tokens.toLocaleString() +
    "</b></span><span>Output<b>" +
    u.output_tokens.toLocaleString() +
    "</b></span><span>Cumulative<b>" +
    u.cumulative_tokens.toLocaleString() +
    "</b></span><span>Model calls<b>" +
    u.calls +
    "</b></span><span>Latency<b>" +
    (r.latency.total_ms / 1000).toFixed(2) +
    "s</b></span><span>Cost<b>" +
    (r.cost_usd === null ? "unconfigured" : "$" + r.cost_usd.toFixed(5)) +
    '</b></span></div><div class="gauge" title="' +
    u.context_tokens.toLocaleString() +
    " of " +
    u.max_context.toLocaleString() +
    ' tokens"><span>Context window</span><div class="track"><div class="fill" style="width:' +
    Math.max(Math.min(100, u.context_percent), u.context_tokens ? 0.6 : 0) +
    '%"></div></div><b>' +
    (u.context_percent < 1 ? u.context_percent.toFixed(2) : u.context_percent.toFixed(1)) +
    '%</b></div><div class="score ' +
    (a.score === 1 ? "good" : a.score === 0 ? "bad" : "") +
    '">' +
    verdict +
    " · " +
    esc(a.method) +
    (a.score === 0 && a.expected !== undefined
      ? " · expected " +
        Number(a.expected).toLocaleString() +
        ", got " +
        (a.actual === null ? "no figure" : Number(a.actual).toLocaleString())
      : "") +
    '</div><details class="inspector"><summary>' +
    (r.agent === "plane" ? "Inspect the intelligence plane" : "Inspect raw SQL & retrieval") +
    '</summary><div class="inspect-tabs"></div><div class="inspect-panel"></div></details>';
  const panels =
    r.agent === "plane"
      ? {
          Routing: i.routing,
          "Cache stack": i.cache_stack,
          "Semantic cache": i.semantic_cache,
          "Data flow": r.path,
          "Entities (graph)": i.entities?.map((e) => ({
            name: e.name,
            lei: e.lei,
            depth: e.depth,
            relationship: e.depth ? e.relationship : "root",
            positions: e.positions,
            gross_usd: Math.round(e.gross_usd).toLocaleString(),
          })),
          Semantics: i.semantic,
          "Executed SQL": i.sql?.map((q) => ({
            ms: q.ms,
            rows: q.rows,
            served_by: q.served_by,
            sql: q.sql,
            binds: q.binds,
          })),
          "Reranked passages": i.passages,
          "Memories recalled": i.memories,
          "New memory": i.memory_extracted,
          Validation: i.output_validation,
          "Model output": i.model_answer,
          "True Cache": i.cache,
          Audit: null,
          Measurements: { usage: u, latency: r.latency, accuracy: a, cost_note: r.cost_note },
        }
      : {
          "Generated SQL": i.naive_sql,
          "Data flow": r.path,
          "History window": i.history_truncated,
          "Executed SQL": i.sql?.map((q) => ({
            ms: q.ms,
            rows: q.rows,
            served_by: q.served_by,
            sql: q.sql,
            binds: q.binds,
          })),
          "Vector passages": i.passages,
          "Model output": i.model_answer,
          "True Cache": i.cache,
          Audit: null,
          Measurements: { usage: u, latency: r.latency, accuracy: a, cost_note: r.cost_note },
        };
  const panel = div.querySelector(".inspect-panel"),
    tabs = div.querySelector(".inspect-tabs");
  let first = null;
  for (const [label, data] of Object.entries(panels)) {
    if (
      label !== "Audit" &&
      (data === undefined || data === null || (Array.isArray(data) && !data.length))
    )
      continue;
    const b = document.createElement("button");
    b.textContent = label;
    b.onclick = async () => {
      tabs.querySelectorAll("button").forEach((x) => x.classList.toggle("selected", x === b));
      if (label === "Audit") {
        panel.innerHTML = '<p class="muted">Reading Unified Audit trail…</p>';
        try {
          const j = await api(
            "/api/audit?persona=" +
              encodeURIComponent(r.persona) +
              "&request_id=" +
              encodeURIComponent(r.request_id)
          );
          panel.innerHTML =
            '<p class="muted">' +
            esc(j.note) +
            " · request " +
            esc(r.request_id) +
            "</p>" +
            table(j.rows);
        } catch (e) {
          panel.innerHTML = pretty({ error: e.message });
        }
      } else panel.innerHTML = view(data);
    };
    tabs.append(b);
    first = first || b;
  }
  const labels = [...tabs.querySelectorAll("button")];
  const preferred = ["New memory", "Entities (graph)", "Generated SQL", "Routing"]
    .map((l) => labels.find((b) => b.textContent === l))
    .find(Boolean);
  (preferred || first)?.click();
  target.append(div);
  target.scrollTop = target.scrollHeight;
  state.latest[r.agent] = r;
  state.turns.push(r);
  (state.runs[r.run_id] = state.runs[r.run_id] || {})[r.agent] = r;
  charts();
  layers(r.run_id);
}
function mountArchitecture() {
  if (!window.Architecture || state.archMounted || !state.health || !$("#architecture").open)
    return;
  Architecture.mount($("#architecture-view"), state.health);
  state.archMounted = true;
  const last = Object.keys(state.runs).pop();
  if (last) layers(last);
}
$("#architecture").addEventListener("toggle", () => {
  try {
    localStorage.setItem("hf-arch-open", $("#architecture").open ? "1" : "0");
  } catch (e) {}
  mountArchitecture();
});
try {
  if (localStorage.getItem("hf-arch-open") === "1") $("#architecture").open = true;
} catch (e) {}
document.querySelectorAll('a[href="#architecture"]').forEach((a) =>
  a.addEventListener("click", () => {
    $("#architecture").open = true;
  })
);
// After each turn: the layer X-ray (ontology + semantics) and the architecture replay use both agents' results.
function layers(run) {
  const pair = state.runs[run] || {};
  if (window.XRay && pair.plane) XRay.render($("#xray-view"), pair.plane, pair.naive || null);
  if (window.Architecture && state.archMounted)
    Architecture.showTurn(pair.plane || null, pair.naive || null);
}

// ---- Tokenomics charts: inline SVG, one shared tooltip, legend always present ----
const tip = document.createElement("div");
tip.className = "tip";
tip.hidden = true;
document.body.append(tip);
document.addEventListener("mousemove", (e) => {
  const t = e.target.closest?.("[data-tip]");
  if (!t) {
    tip.hidden = true;
    return;
  }
  tip.innerHTML = t.dataset.tip;
  tip.hidden = false;
  const x = Math.min(e.clientX + 14, innerWidth - tip.offsetWidth - 8);
  tip.style.left = x + "px";
  tip.style.top = e.clientY + 14 + "px";
});
// Chart geometry in viewBox units; the modal re-renders at a larger size instead of stretching the small chart.
let W = 300,
  H = 150,
  L = 38,
  R = 8,
  T = 10,
  B = 30;
function frame(max, fmt, runs) {
  let s = '<svg viewBox="0 0 ' + W + " " + H + '" role="img">';
  for (let k = 0; k <= 2; k++) {
    const y = T + ((H - T - B) * k) / 2;
    s +=
      '<line x1="' +
      L +
      '" y1="' +
      y +
      '" x2="' +
      (W - R) +
      '" y2="' +
      y +
      '" class="grid"/><text x="' +
      (L - 5) +
      '" y="' +
      (y + 3) +
      '" text-anchor="end">' +
      fmt(max * (1 - k / 2)) +
      "</text>";
  }
  const step = (W - L - R) / Math.max(runs.length, 1),
    every = Math.ceil(runs.length / 12);
  runs.forEach((run, k) => {
    const x = L + step * (k + 0.5);
    if (k % every === 0)
      s +=
        '<text x="' + x + '" y="' + (H - B + 12) + '" text-anchor="middle">' + (k + 1) + "</text>";
    if (k === 0 || run.model !== runs[k - 1].model)
      s +=
        '<text x="' +
        x +
        '" y="' +
        (H - B + 23) +
        '" text-anchor="middle" class="tick-model">' +
        esc(short(run.model).slice(0, 12)) +
        "</text>";
  });
  return [s, step];
}
const yOf = (v, max) => T + (H - T - B) * (1 - v / max);
// Line charts: one full-height hover column per turn with a crosshair, so close points never hide each other.
const columns = (runs, step, tip) =>
  runs
    .map((run, k) => {
      const x = L + step * k;
      return (
        '<g class="col"><line class="xhair" x1="' +
        (x + step / 2) +
        '" x2="' +
        (x + step / 2) +
        '" y1="' +
        T +
        '" y2="' +
        (H - B) +
        '"/><rect x="' +
        x +
        '" y="' +
        T +
        '" width="' +
        step +
        '" height="' +
        (H - T - B) +
        '" fill="transparent" data-tip="' +
        esc(tip(run, k)) +
        '"/></g>'
      );
    })
    .join("");
function charts(nested) {
  const runs = [...new Map(state.turns.map((r) => [r.run_id, r])).values()];
  const get = (run, agent) => state.turns.find((r) => r.run_id === run.run_id && r.agent === agent);
  const empty = (id, msg) =>
    ($("#" + id + "-chart").innerHTML = '<div class="placeholder">' + msg + "</div>");
  if (!runs.length) {
    ["accuracy", "latency", "cost", "context"].forEach((id) =>
      empty(id, id === "accuracy" ? "No scored golden answers yet" : "Run a comparison to measure")
    );
    $("#turn-table").innerHTML = "";
    return;
  }
  // Accuracy: running % correct over scored golden questions, per agent.
  {
    const pts = { plane: [], naive: [] };
    for (const agent of ["plane", "naive"]) {
      let n = 0,
        ok = 0;
      runs.forEach((run, k) => {
        const r = get(run, agent);
        if (r && r.accuracy.score !== null) {
          n++;
          ok += r.accuracy.score;
          pts[agent].push({ k, v: (ok / n) * 100, r, n, ok });
        }
      });
    }
    if (!pts.plane.length && !pts.naive.length) empty("accuracy", "No scored golden answers yet");
    else {
      let [s, step] = frame(100, (v) => v.toFixed(0) + "%", runs);
      for (const agent of ["plane", "naive"]) {
        const p = pts[agent].map((q) => [L + step * (q.k + 0.5), yOf(q.v, 100), q]);
        if (p.length > 1)
          s +=
            '<polyline fill="none" stroke="' +
            COLORS[agent] +
            '" stroke-width="2" points="' +
            p.map((q) => q[0] + "," + q[1]).join(" ") +
            '"/>';
        p.forEach(([x, y, q]) => {
          s +=
            '<circle cx="' +
            x +
            '" cy="' +
            y +
            '" r="4.5" fill="' +
            COLORS[agent] +
            '" stroke="#fffefa" stroke-width="2"/>';
        });
      }
      s += columns(runs, step, (run, k) => {
        const at = (a) => pts[a].find((q) => q.k === k);
        return (
          "<b>Turn " +
          (k + 1) +
          "</b> · " +
          esc(short(run.model)) +
          ["plane", "naive"]
            .map((a) => {
              const q = at(a);
              return (
                "<br><span class='tip-key " +
                a +
                "'></span>" +
                (a === "plane" ? "Plane" : "Naive") +
                ": " +
                (q
                  ? (q.r.accuracy.score === 1 ? "correct" : "incorrect") +
                    " · running " +
                    q.ok +
                    "/" +
                    q.n +
                    " = " +
                    q.v.toFixed(0) +
                    "%"
                  : "unscored")
              );
            })
            .join("") +
          "<br>" +
          esc(run.question)
        );
      });
      $("#accuracy-chart").innerHTML = s + "</svg>";
    }
  }
  // Latency: per turn, plane and naive bars stacked by phase.
  {
    const phases = ["llm", "retrieval", "rerank", "other"],
      parts = (r) => {
        const l = r.latency;
        return {
          llm: l.llm_ms,
          retrieval: l.retrieval_ms,
          rerank: l.rerank_ms,
          other: Math.max(0, l.total_ms - l.llm_ms - l.retrieval_ms - l.rerank_ms),
        };
      };
    const max = Math.max(...state.turns.map((r) => r.latency.total_ms), 1) * 1.1;
    let [s, step] = frame(max / 1000, (v) => v.toFixed(v < 10 ? 1 : 0) + "s", runs);
    const bw = Math.max(1.5, Math.min(W * 0.047, step / 2 - 2));
    runs.forEach((run, k) =>
      ["plane", "naive"].forEach((agent, j) => {
        const r = get(run, agent);
        if (!r) return;
        const x = L + step * (k + 0.5) + (j ? 1 : -1 - bw) * 1;
        let y0 = H - B;
        const p = parts(r);
        phases.forEach((ph) => {
          const h = ((H - T - B) * p[ph]) / max;
          if (h < 0.5) return;
          s +=
            '<rect x="' +
            x +
            '" y="' +
            (y0 - h) +
            '" width="' +
            bw +
            '" height="' +
            Math.max(h - 1, 0.5) +
            '" fill="' +
            COLORS[ph] +
            '"/>';
          y0 -= h;
        });
        s +=
          '<rect x="' +
          x +
          '" y="' +
          T +
          '" width="' +
          bw +
          '" height="' +
          (H - T - B) +
          '" fill="transparent" data-tip="' +
          esc(
            "<b>" +
              (agent === "plane" ? "Plane" : "Naive") +
              " · turn " +
              (k + 1) +
              " · " +
              (r.latency.total_ms / 1000).toFixed(2) +
              "s</b><br>LLM " +
              (p.llm / 1000).toFixed(2) +
              "s · retrieval " +
              (p.retrieval / 1000).toFixed(2) +
              "s · rerank " +
              (p.rerank / 1000).toFixed(2) +
              "s · other " +
              (p.other / 1000).toFixed(2) +
              "s"
          ) +
          '"/>';
        s +=
          '<text x="' +
          (x + bw / 2) +
          '" y="' +
          (H - B - 3 - ((H - T - B) * r.latency.total_ms) / max) +
          '" text-anchor="middle" class="bar-tag">' +
          (agent === "plane" ? "P" : "N") +
          "</text>";
      })
    );
    $("#latency-chart").innerHTML = s + "</svg>";
  }
  // Cost: per turn, side-by-side bars per agent.
  {
    const max = Math.max(...state.turns.map((r) => r.cost_usd || 0), 0.000001) * 1.15;
    let [s, step] = frame(
      max,
      (v) => (v === 0 ? "$0" : v < 0.01 ? "$" + v.toFixed(4) : "$" + v.toFixed(3)),
      runs
    );
    const bw = Math.max(1.5, Math.min(W * 0.047, step / 2 - 2));
    runs.forEach((run, k) =>
      ["plane", "naive"].forEach((agent, j) => {
        const r = get(run, agent);
        if (!r || r.cost_usd === null) return;
        const h = Math.max(((H - T - B) * r.cost_usd) / max, r.cost_usd > 0 ? 1.5 : 0);
        const x = L + step * (k + 0.5) + (j ? 1 : -1 - bw);
        if (h > 0)
          s +=
            '<rect x="' +
            x +
            '" y="' +
            (H - B - h) +
            '" width="' +
            bw +
            '" height="' +
            h +
            '" rx="2" fill="' +
            COLORS[agent] +
            '"/>';
        else
          s +=
            '<text x="' +
            (x + bw / 2) +
            '" y="' +
            (H - B - 3) +
            '" text-anchor="middle" class="bar-tag">$0</text>';
        s +=
          '<rect x="' +
          x +
          '" y="' +
          T +
          '" width="' +
          bw +
          '" height="' +
          (H - T - B) +
          '" fill="transparent" data-tip="' +
          esc(
            "<b>" +
              (agent === "plane" ? "Plane" : "Naive") +
              " · turn " +
              (k + 1) +
              "</b><br>$" +
              r.cost_usd.toFixed(6) +
              " · " +
              r.usage.total_tokens.toLocaleString() +
              " tokens · " +
              esc(short(r.model)) +
              (r.cache_state === "hit" ? "<br>⚡ semantic cache hit" : "") +
              ((r.inspector.cache_stack || {}).exact &&
              r.inspector.cache_stack.exact.state === "hit"
                ? "<br>⚡ exact response cache hit"
                : "") +
              (r.usage.cached_input_tokens
                ? "<br>" + r.usage.cached_input_tokens.toLocaleString() + " prompt-cached tokens"
                : "") +
              "<br>" +
              esc(r.cost_note)
          ) +
          '"/>';
      })
    );
    $("#cost-chart").innerHTML = s + "</svg>";
  }
  // Context: tokens in the largest single model call each turn.
  {
    const max = Math.max(...state.turns.map((r) => r.usage.context_tokens), 1) * 1.15;
    let [s, step] = frame(
      max,
      (v) => (v >= 1000 ? (v / 1000).toFixed(1) + "k" : v.toFixed(0)),
      runs
    );
    for (const agent of ["plane", "naive"]) {
      const p = runs
        .map((run, k) => [k, get(run, agent)])
        .filter(([, r]) => r)
        .map(([k, r]) => [L + step * (k + 0.5), yOf(r.usage.context_tokens, max), r, k]);
      if (p.length > 1)
        s +=
          '<polyline fill="none" stroke="' +
          COLORS[agent] +
          '" stroke-width="2" points="' +
          p.map((q) => q[0] + "," + q[1]).join(" ") +
          '"/>';
      p.forEach(([x, y, r, k]) => {
        s +=
          '<circle cx="' +
          x +
          '" cy="' +
          y +
          '" r="4.5" fill="' +
          COLORS[agent] +
          '" stroke="#fffefa" stroke-width="2"/>';
      });
    }
    s += columns(
      runs,
      step,
      (run, k) =>
        "<b>Turn " +
        (k + 1) +
        "</b> · " +
        esc(short(run.model)) +
        ["plane", "naive"]
          .map((a) => {
            const r = get(run, a);
            return (
              "<br><span class='tip-key " +
              a +
              "'></span>" +
              (a === "plane" ? "Plane" : "Naive") +
              ": " +
              (r
                ? r.usage.context_tokens.toLocaleString() +
                  " tokens = " +
                  r.usage.context_percent +
                  "% of " +
                  r.usage.max_context.toLocaleString()
                : "—")
            );
          })
          .join("") +
        "<br>" +
        esc(run.question)
    );
    $("#context-chart").innerHTML = s + "</svg>";
  }
  if (state.modal && !nested) openChart(state.modal);
  $("#turn-table").innerHTML = table(
    state.turns.map((r, n) => ({
      turn: runs.findIndex((x) => x.run_id === r.run_id) + 1,
      agent: r.agent,
      persona: r.persona,
      model: short(r.model),
      question: r.question,
      correct: r.accuracy.score === null ? "unscored" : r.accuracy.score ? "yes" : "no",
      tokens: r.usage.total_tokens,
      context_tokens: r.usage.context_tokens,
      latency_s: (r.latency.total_ms / 1000).toFixed(2),
      llm_s: (r.latency.llm_ms / 1000).toFixed(2),
      retrieval_s: (r.latency.retrieval_ms / 1000).toFixed(2),
      rerank_s: (r.latency.rerank_ms / 1000).toFixed(2),
      cost_usd: r.cost_usd,
      cache: r.cache_state || "",
    }))
  );
  summary();
}

const CONTROLS = [
  "#send",
  "#persona",
  "#model",
  "#new-session",
  "#reset-memory",
  "#reset-cache",
  "#sim-run",
  "#sim-turns",
  "#sim-mix",
];
function lock(on) {
  state.busy = on;
  for (const id of CONTROLS) $(id).disabled = on;
}
// One SSE reader for single turns and simulations; every event is rendered as it arrives.
async function consume(response, on) {
  const reader = response.body.getReader(),
    decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let split;
    while ((split = buffer.indexOf("\n\n")) >= 0) {
      const frame = buffer.slice(0, split);
      buffer = buffer.slice(split + 2);
      const event = frame.match(/^event: (.+)$/m)?.[1],
        raw = frame.match(/^data: (.+)$/m)?.[1];
      if (raw) on(event, JSON.parse(raw));
    }
  }
}
function handle(errors) {
  return (event, data) => {
    if (event === "answer") {
      renderTurn(data);
      if (!state.sim)
        $("#status").textContent =
          (data.agent === "plane" ? "Plane" : "Naive") + " agent finished · waiting for the other…";
    }
    if (event === "agent_error") {
      errors.push(data.agent + ": " + data.error);
      const box = $("#" + data.agent + "-chat");
      box.querySelector(".empty")?.remove();
      const d = document.createElement("div");
      d.className = "turn error";
      d.textContent = data.error;
      box.append(d);
    }
    if (event === "sim_start") {
      state.sim.total = data.turns;
      state.sim.thread = data.thread_id;
      $(".sim-bar").hidden = false;
    }
    if (event === "sim_turn") {
      state.sim.index = data.index;
      $("#sim-progress").textContent = "Turn " + data.index + " of " + data.of + " · " + data.kind;
      $(".sim-bar div").style.width = ((data.index - 1) / data.of) * 100 + "%";
      $("#status").textContent =
        "Simulating turn " + data.index + "/" + data.of + ": “" + data.question + "”";
    }
    if (event === "sim_done") {
      $(".sim-bar div").style.width = "100%";
      $("#sim-progress").textContent =
        "Completed " + data.completed + " of " + state.sim.total + " turns";
    }
  };
}
$("#ask").onsubmit = async (e) => {
  e.preventDefault();
  if (state.busy) return;
  lock(true);
  $("#status").textContent = "Both agents are running on " + persona() + " database identities…";
  const body = {
    question: $("#question").value,
    persona: persona(),
    model_id: $("#model").value,
    thread_id: state.thread,
  };
  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!response.ok) {
      const j = await response.json();
      throw Error(j.detail || "Request failed");
    }
    const errors = [];
    await consume(response, handle(errors));
    $("#status").textContent = errors.length
      ? errors.join(" | ")
      : "Comparison complete. Open the inspector to follow the evidence.";
  } catch (e) {
    $("#status").textContent = e.message;
  } finally {
    lock(false);
  }
};
// Simulation: N generated turns in one session; Stop closes the stream and the server stops after the current turn.
$("#sim-run").onclick = async () => {
  if (state.busy) return;
  const turns = Math.max(1, Math.min(50, parseInt($("#sim-turns").value || "10", 10)));
  lock(true);
  $("#sim-stop").hidden = false;
  $("#sim-stop").disabled = false;
  const controller = new AbortController();
  state.sim = { controller, total: turns, index: 0, started: state.turns.length };
  $("#sim-progress").textContent = "Generating " + turns + " questions…";
  const body = {
    turns,
    persona: persona(),
    model_id: $("#model").value,
    mix: $("#sim-mix").value,
    thread_id: state.thread,
  };
  const errors = [];
  try {
    const response = await fetch("/api/simulate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: controller.signal,
    });
    if (!response.ok) {
      const j = await response.json();
      throw Error(j.detail || "Request failed");
    }
    await consume(response, handle(errors));
    $("#status").textContent = errors.length
      ? "Simulation finished with errors: " + errors.join(" | ")
      : "Simulation complete. See Tokenomics for the session summary.";
  } catch (e) {
    $("#status").textContent =
      e.name === "AbortError"
        ? "Simulation stopped after turn " + state.sim.index + "."
        : e.message;
  } finally {
    $("#sim-stop").hidden = true;
    lock(false);
    state.sim = null;
    summary();
  }
};
$("#sim-stop").onclick = () => {
  if (state.sim) {
    $("#sim-stop").disabled = true;
    $("#sim-progress").textContent = "Stopping after the current turn…";
    state.sim.controller.abort();
  }
};
// Session summary per agent across every turn shown: accuracy, tokens, cost, latency, cache and context.
function summary() {
  const el = $("#sim-summary");
  if (!state.turns.length) {
    el.innerHTML = "";
    return;
  }
  const stats = ["plane", "naive"].map((agent) => {
    const rs = state.turns.filter((r) => r.agent === agent),
      scored = rs.filter((r) => r.accuracy.score !== null),
      hits = rs.filter((r) => r.cache_state === "hit").length;
    return {
      agent,
      turns: rs.length,
      accuracy: scored.length
        ? Math.round((scored.reduce((a, r) => a + r.accuracy.score, 0) / scored.length) * 100) +
          "% of " +
          scored.length
        : "—",
      tokens: rs.reduce((a, r) => a + r.usage.total_tokens, 0),
      cost: rs.reduce((a, r) => a + (r.cost_usd || 0), 0),
      latency: rs.length ? rs.reduce((a, r) => a + r.latency.total_ms, 0) / rs.length / 1000 : 0,
      context: Math.max(0, ...rs.map((r) => r.usage.context_tokens)),
      cache: agent === "plane" ? hits + " of " + rs.length : "n/a",
      near: rs.filter((r) => (r.inspector.semantic_cache || {}).state === "near_miss").length,
      refused: rs.filter((r) =>
        ((r.inspector.routing || {}).decided_by || "").startsWith("control guard")
      ).length,
      exact:
        agent === "plane"
          ? rs.filter(
              (r) => r.inspector.cache_stack && r.inspector.cache_stack.exact.state === "hit"
            ).length +
            " of " +
            rs.length
          : "n/a",
      tc: rs.reduce(
        (a, r) => a + (((r.inspector.cache_stack || {}).true_cache || {}).reads || 0),
        0
      ),
      prompt: rs.reduce((a, r) => a + (r.usage.cached_input_tokens || 0), 0),
    };
  });
  const row = (label, f) =>
    "<tr><th>" + label + "</th>" + stats.map((s) => "<td>" + f(s) + "</td>").join("") + "</tr>";
  el.innerHTML =
    "<h3>Session summary <small>" +
    new Set(state.turns.map((r) => r.run_id)).size +
    ' turns shown on this page</small></h3><div class="table-wrap"><table class="summary"><thead><tr><th></th><th><span class="dot plane"></span>Plane</th><th><span class="dot naive"></span>Naive</th></tr></thead><tbody>' +
    row("Accuracy (golden)", (s) => s.accuracy) +
    row("Total tokens", (s) => s.tokens.toLocaleString()) +
    row("Total cost", (s) => "$" + s.cost.toFixed(4)) +
    row("Average latency", (s) => s.latency.toFixed(1) + " s") +
    row("Largest context", (s) => s.context.toLocaleString() + " tokens") +
    row("Exact response cache hits", (s) => s.exact) +
    row("Semantic cache hits", (s) => s.cache) +
    row("Near misses rejected (would have been wrong)", (s) =>
      s.agent === "plane" ? s.near + " · semantic-layer and ontology checks" : "n/a"
    ) +
    row("Refused before any model call", (s) =>
      s.agent === "plane" ? s.refused + " · control guard" : "n/a"
    ) +
    row("Reads served by True Cache", (s) =>
      s.agent === "plane" ? s.tc.toLocaleString() : "0 (no cache tier)"
    ) +
    row("Prompt-cached input tokens", (s) => s.prompt.toLocaleString()) +
    "</tbody></table></div>";
}
$("#new-session").onclick = session;
$("#persona").onchange = () => {
  session();
  loadData();
  personaNote();
};
$("#model").onchange = modelNote;
document.querySelectorAll("[data-q]").forEach(
  (b) =>
    (b.onclick = () => {
      if (b.dataset.newSession) session();
      $("#question").value = b.dataset.q;
      $("#question").focus();
    })
);
// Two-step reset: the first click arms, the second deletes this desk's durable memories.
let armed = null;
$("#reset-memory").onclick = async () => {
  const b = $("#reset-memory");
  if (!armed) {
    b.textContent = "Confirm: delete " + persona() + " memories";
    b.classList.add("armed");
    armed = setTimeout(() => {
      armed = null;
      b.textContent = "Reset desk memory";
      b.classList.remove("armed");
    }, 4000);
    return;
  }
  clearTimeout(armed);
  armed = null;
  b.classList.remove("armed");
  b.textContent = "Reset desk memory";
  try {
    const j = await api("/api/memory/reset?persona=" + encodeURIComponent(persona()), {
      method: "POST",
    });
    $("#status").textContent =
      "Deleted " +
      j.deleted.length +
      " durable " +
      persona() +
      " memories from Oracle. Start a new session for a clean scene 3.";
    if (state.view === "memory") loadData();
  } catch (e) {
    $("#status").textContent = e.message;
  }
};
// Two-step reset for the desk's semantic cache, mirroring the memory reset.
let cacheArmed = null;
$("#reset-cache").onclick = async () => {
  const b = $("#reset-cache");
  if (!cacheArmed) {
    b.textContent = "Confirm: clear " + persona() + " cache";
    b.classList.add("armed");
    cacheArmed = setTimeout(() => {
      cacheArmed = null;
      b.textContent = "Reset caches";
      b.classList.remove("armed");
    }, 4000);
    return;
  }
  clearTimeout(cacheArmed);
  cacheArmed = null;
  b.classList.remove("armed");
  b.textContent = "Reset caches";
  try {
    const j = await api("/api/semcache/reset?persona=" + encodeURIComponent(persona()), {
      method: "POST",
    });
    $("#status").textContent =
      "Deleted " +
      j.deleted +
      " cache entries for " +
      persona() +
      " (exact " +
      j.tables.HF_RESPONSE_CACHE +
      ", embedding " +
      j.tables.HF_EMBED_CACHE +
      ", semantic " +
      j.tables.HF_SEMCACHE +
      ").";
    if (state.view === "semcache") loadData();
  } catch (e) {
    $("#status").textContent = e.message;
  }
};
async function loadData() {
  const p = encodeURIComponent(persona()),
    controls = $("#data-controls"),
    content = $("#data-content");
  controls.innerHTML = "";
  content.innerHTML = '<p class="muted">Reading Oracle as ' + esc(persona()) + "…</p>";
  try {
    if (state.view === "tables") {
      const j = await api("/api/data/tables?persona=" + p);
      const sel = document.createElement("select");
      sel.setAttribute("aria-label", "Database table");
      sel.innerHTML = j.tables
        .map(
          (t) =>
            '<option value="' +
            t.id +
            '">' +
            t.name +
            " / " +
            t.row_count.toLocaleString() +
            " rows</option>"
        )
        .join("");
      sel.value = state.table;
      sel.onchange = () => {
        state.table = sel.value;
        state.offset = 0;
        loadData();
      };
      controls.append(sel);
      for (const [label, d] of [
        ["← Previous", -50],
        ["Next →", 50],
      ]) {
        const b = document.createElement("button");
        b.textContent = label;
        b.disabled = d < 0 && state.offset === 0;
        b.onclick = () => {
          state.offset = Math.max(0, state.offset + d);
          loadData();
        };
        controls.append(b);
      }
      const rows = await api(
        "/api/data/" + state.table + "?persona=" + p + "&offset=" + state.offset
      );
      content.innerHTML =
        '<p class="muted">' +
        esc(rows.source) +
        " · signed in as " +
        esc(persona()) +
        " · offset " +
        state.offset +
        "</p>" +
        table(rows.rows);
    } else if (state.view === "graph") {
      const sel = document.createElement("select");
      sel.setAttribute("aria-label", "Issuer group");
      sel.innerHTML = ["Acme", "Northwind", "Contoso", "Fabrikam"]
        .map((g) => "<option>" + g + "</option>")
        .join("");
      controls.append(sel);
      const show = async () => {
        const g = await api("/api/graph?persona=" + p + "&group=" + encodeURIComponent(sel.value));
        content.innerHTML =
          '<p class="muted">' +
          esc(g.source) +
          " · " +
          esc(g.scope) +
          " · holdings visible to " +
          esc(persona()) +
          '</p><div class="graph-tree">' +
          g.nodes
            .map(
              (n) =>
                '<div class="entity ' +
                (n.depth > 0 ? "child" : "") +
                '"><b>' +
                esc(n.name) +
                '</b> <span class="muted">' +
                (n.depth > 0 ? esc(n.relationship) : "root") +
                " · " +
                n.positions +
                " positions · $" +
                Math.round(n.gross_usd).toLocaleString() +
                ' gross</span><br><span class="mono">' +
                esc(n.lei) +
                "</span></div>"
            )
            .join("") +
          "</div><h3>Issuer → legal entity → instrument → position → portfolio → desk</h3>" +
          table(g.paths);
      };
      sel.onchange = () => show().catch((e) => (content.textContent = e.message));
      await show();
    } else if (state.view === "vectors") {
      controls.innerHTML =
        '<input id="vector-q" aria-label="Vector query" value="rate rise and collateral risk"><button id="vector-search">Find neighbours</button>';
      const show = async () => {
        const v = await api(
          "/api/vectors?persona=" + p + "&q=" + encodeURIComponent($("#vector-q").value)
        );
        content.innerHTML =
          '<p class="muted">' +
          esc(v.embedding_source) +
          " · " +
          esc(v.rerank.method) +
          " · " +
          esc(v.rerank.model) +
          "</p><h3>Nearest neighbours (cosine distance)</h3>" +
          table(v.nearest) +
          "<h3>Reranked by the in-database cross-encoder</h3>" +
          table(v.reranked);
      };
      $("#vector-search").onclick = () => show().catch((e) => (content.textContent = e.message));
      await show();
    } else if (state.view === "memory") {
      const m = await api("/api/memory?persona=" + p);
      content.innerHTML =
        '<p class="muted">OAMP 26.8 store in the ' +
        esc(persona()) +
        " desk memory schema.</p><h3>Extracted facts & original sources</h3>" +
        table(
          m.facts.map((f) => ({
            id: f.id,
            type: f.type,
            content: f.content,
            source_message_id: f.metadata?.source_message_id,
            source_thread_id: f.metadata?.source_thread_id,
            source_text: f.metadata?.source_text,
            extraction_model: f.metadata?.extraction_model,
          }))
        ) +
        "<h3>Threads</h3>" +
        table(m.threads);
    } else if (state.view === "semcache") {
      const c = await api("/api/semcache?persona=" + p);
      content.innerHTML =
        '<p class="muted">HF_SEMCACHE in the ' +
        esc(persona()) +
        " desk memory schema. Hits must be within distance " +
        0.18 +
        " and pass the semantic-layer vocabulary and ontology group checks. Metric plans are reused and the figure is recomputed from governed SQL; research answers are reused for 30 minutes.</p>" +
        table(c.rows);
    } else if (state.view === "audit") {
      const r = state.latest.plane || state.latest.naive;
      if (!r) {
        content.innerHTML =
          '<p class="muted">Run a comparison to obtain a real audit request ID.</p>';
        return;
      }
      controls.innerHTML = '<span class="mono">' + esc(r.request_id) + "</span>";
      const a = await api(
        "/api/audit?persona=" + p + "&request_id=" + encodeURIComponent(r.request_id)
      );
      content.innerHTML = '<p class="muted">' + esc(a.note) + "</p>" + table(a.rows);
    } else {
      const path =
        state.view === "semantics"
          ? "/api/data/hf_semantics"
          : state.view === "golden"
            ? "/api/data/hf_golden"
            : "/api/sql";
      const d = await api(path + "?persona=" + p + (state.view === "golden" ? "&limit=100" : ""));
      content.innerHTML =
        (state.view === "sql"
          ? '<p class="muted">Statements tagged /* HF:… */ in V$SQL. Semantic definitions keep the SQL_ID they were mined from.</p>'
          : "") + table(d.rows);
    }
  } catch (e) {
    content.innerHTML = '<p class="error">' + esc(e.message) + "</p>";
  }
}
document.querySelectorAll("[data-view]").forEach(
  (b) =>
    (b.onclick = () => {
      state.view = b.dataset.view;
      document
        .querySelectorAll("[data-view]")
        .forEach((x) => x.classList.toggle("selected", x === b));
      loadData();
    })
);
$("#refresh-data").onclick = loadData;
session();
health();
loadData();
charts();
setInterval(() => {
  if (!state.busy) health();
}, 60000);

// Chart modal: click a tokenomics chart to see it large, with its legend and a table of the plotted values.
const CHART_ROWS = {
  accuracy: (r) => ({
    correct: r.accuracy.score === null ? "unscored" : r.accuracy.score ? "yes" : "no",
    method: r.accuracy.method,
  }),
  latency: (r) => ({
    total_s: (r.latency.total_ms / 1000).toFixed(2),
    llm_s: (r.latency.llm_ms / 1000).toFixed(2),
    retrieval_s: (r.latency.retrieval_ms / 1000).toFixed(2),
    rerank_s: (r.latency.rerank_ms / 1000).toFixed(2),
  }),
  cost: (r) => ({
    cost_usd: r.cost_usd,
    tokens: r.usage.total_tokens,
    prompt_cached: r.usage.cached_input_tokens || 0,
  }),
  context: (r) => ({
    context_tokens: r.usage.context_tokens,
    percent_of_window: r.usage.context_percent,
  }),
};
const modal = document.createElement("div");
modal.className = "chart-modal";
modal.hidden = true;
modal.setAttribute("role", "dialog");
modal.setAttribute("aria-modal", "true");
modal.innerHTML =
  '<div class="cm-panel"><button class="cm-close" aria-label="Close">×</button><div class="cm-body"></div></div>';
document.body.append(modal);
function openChart(id) {
  const card = $("#" + id + "-chart").closest("article");
  state.modal = id;
  const runs = [...new Map(state.turns.map((r) => [r.run_id, r])).values()];
  const rows = state.turns.map((r) => ({
    turn: runs.findIndex((x) => x.run_id === r.run_id) + 1,
    agent: r.agent,
    model: short(r.model),
    question: r.question,
    ...CHART_ROWS[id](r),
  }));
  const legend = card.querySelector(".phase-legend")
    ? card.querySelector(".phase-legend").outerHTML
    : '<div class="legend"><span class="plane-dot">Plane</span><span class="naive-dot">Naive</span></div>';
  [W, H, L, B] = [960, 400, 64, 44];
  charts(true);
  const big = $("#" + id + "-chart").innerHTML;
  [W, H, L, B] = [300, 150, 38, 30];
  charts(true);
  modal.querySelector(".cm-body").innerHTML =
    "<h2>" +
    card.querySelector("h3").innerHTML +
    "</h2>" +
    legend +
    '<div class="cm-chart">' +
    big +
    "</div><details><summary>Table view · " +
    rows.length +
    " results</summary>" +
    table(rows) +
    "</details>";
  if (modal.hidden) {
    modal.hidden = false;
    modal.querySelector(".cm-close").focus();
  }
}
function closeChart() {
  modal.hidden = true;
  state.modal = null;
}
modal.querySelector(".cm-close").onclick = closeChart;
modal.onclick = (e) => {
  if (e.target === modal) closeChart();
};
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && !modal.hidden) closeChart();
});
document.querySelectorAll(".charts article").forEach((card) => {
  const id = card.querySelector(".chart").id.replace("-chart", "");
  card.tabIndex = 0;
  card.title = "Click to enlarge";
  card.onclick = () => {
    if (state.turns.length) openChart(id);
  };
  card.onkeydown = (e) => {
    if ((e.key === "Enter" || e.key === " ") && state.turns.length) {
      e.preventDefault();
      openChart(id);
    }
  };
});
