// Agent Memory Checklist appbook: a dependency-free single-page app over the FastAPI server.
import { PARTS, TAKEAWAYS, SECTIONS, DEFAULTS, EXPLORER_TABLES } from "./content.js";

const app = document.getElementById("app");
const dockEl = document.getElementById("dock");
const savedDock = (() => {
  try {
    return JSON.parse(localStorage.getItem("appbook.dock") || "{}");
  } catch {
    return {};
  }
})();
const state = {
  status: null,
  results: {},
  answers: {},
  running: {},
  params: {},
  explorer: {
    table: savedDock.table || "memories",
    filters: { status: "all" },
    data: null,
    loading: false,
    error: null,
    open: !!savedDock.open,
    height: savedDock.height || 380,
  },
  runAll: null,
  rail: (() => {
    try {
      return localStorage.getItem("appbook.rail") === "1";
    } catch {
      return false;
    }
  })(),
};
const USERS = { user_ada: "Ada", user_bob: "Bob", user_cy: "Cy", global: "team" };

// ------------------------------------------------------------------------------------------------ helpers
function h(tag, props = {}, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(props || {})) {
    if (v === null || v === undefined || v === false) continue;
    if (k === "class") el.className = v;
    else if (k === "html")
      el.innerHTML = v; // trusted static copy from content.js only
    else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else el.setAttribute(k, v === true ? "" : v);
  }
  for (const kid of kids.flat(Infinity)) {
    if (kid === null || kid === undefined || kid === false) continue;
    el.append(kid instanceof Node ? kid : document.createTextNode(String(kid)));
  }
  return el;
}

async function api(path, body) {
  const init =
    body === undefined
      ? {}
      : {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        };
  const res = await fetch(path, init);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || res.statusText);
  return data;
}

function toast(message) {
  const t = document.getElementById("toast");
  t.textContent = message;
  t.classList.add("show");
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => t.classList.remove("show"), 3200);
}

const route = () => (location.hash || "#/").slice(2).split("/");
const sectionById = (id) => SECTIONS.find((s) => s.id === id);
const partOf = (s) => PARTS.find((p) => p.id === s.part);
const resultFor = (sid) => state.status?.results?.[sid];

function userChip(user) {
  if (!user) return null;
  return h("span", { class: `user u-${user}` }, USERS[user] || user);
}

function memoryChip(id) {
  return h(
    "button",
    { class: "mem-chip", title: "Open this memory", onclick: () => openMemory(id) },
    id
  );
}

function withCitations(text) {
  return String(text)
    .split(/(\[mem_[A-Za-z0-9_]+\])/g)
    .map((part) => {
      const m = part.match(/^\[(mem_[A-Za-z0-9_]+)\]$/);
      return m ? memoryChip(m[1]) : part;
    });
}

// ------------------------------------------------------------------------------------------------ status
async function refreshStatus() {
  try {
    state.status = await api("/api/status");
  } catch (e) {
    state.status = { connected: false, error: e.message, build: {}, results: {} };
  }
  if (state.status.build?.running) setTimeout(() => refreshStatus().then(render), 2000);
}

function statusPill() {
  const s = state.status;
  if (!s) return h("div", { class: "pill" }, "Connecting…");
  const db = s.build?.running
    ? ["busy", "Building the lab…"]
    : s.built
      ? ["ok", `Lab ready · ${s.counts?.n ?? 0} memories`]
      : s.connected
        ? ["warn", "Lab not built"]
        : ["bad", "Database not reachable"];
  const claudeText = s.claude ? `Claude · ${s.claude_model}` : "Claude off (no key)";
  return h(
    "div",
    { class: "pills" },
    h(
      "div",
      { class: `pill ${db[0]}`, title: db[1] },
      h("i"),
      h("span", { class: "pill-text" }, db[1])
    ),
    h(
      "div",
      { class: `pill ${s.claude ? "ok" : "warn"}`, title: claudeText },
      h("i"),
      h("span", { class: "pill-text" }, claudeText)
    )
  );
}

// ------------------------------------------------------------------------------------------------ layout
function setRail(rail) {
  state.rail = rail;
  try {
    localStorage.setItem("appbook.rail", rail ? "1" : "0");
  } catch {
    /* storage unavailable */
  }
  document.documentElement.classList.toggle("rail", rail);
  render();
}

function sidebar() {
  const [page, id] = route();
  const icon = (glyph) => h("span", { class: "nav-ico", "aria-hidden": "true" }, glyph);
  const link = (href, glyph, label, active) =>
    h(
      "a",
      { href, title: label, class: `nav-link${active ? " active" : ""}` },
      icon(glyph),
      h("span", { class: "nav-name" }, label)
    );
  return h(
    "aside",
    { class: "sidebar" },
    h(
      "div",
      { class: "brand-row" },
      h(
        "a",
        { class: "brand", href: "#/", title: "Overview" },
        h("span", { class: "brand-mark" }, "◆"),
        h(
          "span",
          { class: "brand-text" },
          h("b", {}, "Agent Memory Checklist"),
          h("small", {}, "Oracle AI Database 26ai · Claude")
        )
      ),
      h(
        "button",
        {
          class: "rail-toggle",
          onclick: () => setRail(!state.rail),
          "aria-expanded": String(!state.rail),
          "aria-label": state.rail ? "Expand the sidebar" : "Collapse the sidebar",
          title: `${state.rail ? "Expand" : "Collapse"} the sidebar  [`,
        },
        state.rail ? "»" : "«"
      )
    ),
    statusPill(),
    h(
      "nav",
      { "aria-label": "Sections" },
      link("#/", "⌂", "Overview", page === ""),
      h(
        "button",
        {
          class: "nav-link nav-btn",
          title: "Data explorer",
          onclick: () => setDock(!state.explorer.open),
        },
        icon("▤"),
        h("span", { class: "nav-name" }, "Data explorer"),
        h("span", { class: "nav-badge" }, "DOCK")
      ),
      PARTS.map((part) =>
        h(
          "div",
          { class: "nav-part", style: `--c:${part.color}` },
          h(
            "div",
            { class: "nav-part-title", title: `Part ${part.id} · ${part.name}` },
            `Part ${part.id} · ${part.name}`
          ),
          SECTIONS.filter((s) => s.part === part.id).map((s) => {
            const r = resultFor(s.id);
            return h(
              "a",
              {
                href: `#/s/${s.id}`,
                title: `§${s.n} ${s.name}${r ? ` · ${r[0]}` : ""}`,
                class: `nav-link sec${page === "s" && id === s.id ? " active" : ""}`,
              },
              h("span", { class: "nav-n" }, s.n),
              h("span", { class: "nav-name" }, s.name),
              h("span", { class: `dot ${r ? r[0] : ""}` })
            );
          })
        )
      ),
      link("#/scorecard", "✓", "Scorecard", page === "scorecard")
    )
  );
}

function render() {
  const [page, id] = route();
  if (page === "explorer") {
    // the explorer lives in the dock now
    history.replaceState(null, "", "#/");
    setDock(true);
  }
  let main;
  if (page === "s" && sectionById(id)) main = sectionPage(sectionById(id));
  else if (page === "scorecard") main = scorecardPage();
  else main = homePage();
  app.replaceChildren(sidebar(), h("main", { id: "main", tabindex: "-1" }, main));
}

function figure(file, caption) {
  return h(
    "figure",
    { class: "diagram" },
    h("img", {
      src: `/static/img/${file}`,
      alt: caption || "Diagram",
      loading: "lazy",
      onclick: () => zoom(file),
    }),
    h("figcaption", {}, "Click to enlarge")
  );
}

function zoom(file) {
  const d = document.getElementById("zoom-dialog");
  d.replaceChildren(
    h("img", { src: `/static/img/${file}`, alt: "Diagram, full size" }),
    h("button", { class: "close", onclick: () => d.close(), "aria-label": "Close" }, "×")
  );
  d.showModal();
}

// ------------------------------------------------------------------------------------------------ home
function labCard() {
  const s = state.status || {};
  const b = s.build || {};
  const rebuild = async () => {
    await api("/api/lab/build", {});
    await refreshStatus();
    render();
  };
  return h(
    "section",
    { class: "card lab-card" },
    h("div", { class: "card-head" }, h("h2", {}, "The lab"), statusPill()),
    s.connected === false && !b.running
      ? h(
          "p",
          { class: "warn-text" },
          `Can't reach schema ${s.schema || ""}: ${s.error || ""}. `,
          s.admin_route
            ? "The server will create it on start, or press Build."
            : "Set ORACLE_CONTAINER or ORACLE_ADMIN_PASSWORD in .env so the appbook can create it, then restart."
        )
      : null,
    h(
      "dl",
      { class: "facts" },
      h("dt", {}, "Schema"),
      h("dd", {}, s.schema || "…"),
      h("dt", {}, "Memories"),
      h("dd", {}, s.counts ? `${s.counts.n} (${s.counts.embedded} embedded)` : "…"),
      h("dt", {}, "Vector index"),
      h("dd", {}, s.index_kind || "…"),
      h("dt", {}, "Models in the database"),
      h("dd", {}, (s.models || []).join(", ") || "…"),
      h("dt", {}, "Network embedding (§2)"),
      h(
        "dd",
        {},
        s.hf ? "Hugging Face token found" : "no HF_TOKEN: §2 shows only the database side"
      )
    ),
    b.log?.length
      ? h(
          "ol",
          { class: "build-log" },
          b.log.map((l) => h("li", {}, l))
        )
      : null,
    b.error ? h("p", { class: "error-text" }, b.error) : null,
    h(
      "div",
      { class: "actions" },
      h(
        "button",
        { class: "btn", disabled: b.running || null, onclick: rebuild },
        b.running ? "Building…" : s.built ? "Rebuild the lab" : "Build the lab"
      ),
      h("button", { class: "btn ghost", onclick: () => setDock(true) }, "Open the data explorer")
    ),
    h(
      "p",
      { class: "muted small" },
      "Rebuilding drops and recreates every lab object from the corpus, so the without/with stories start from the beginning."
    )
  );
}

function homePage() {
  return h(
    "div",
    { class: "page home" },
    h(
      "header",
      { class: "hero" },
      h("div", { class: "kicker" }, "APPBOOK · ORACLE AI DATABASE 26ai · CLAUDE"),
      h("h1", {}, "Your agent memory might be in the wrong database"),
      h(
        "p",
        { class: "lede" },
        "The agent memory checklist, one section per item. Every section runs live against Oracle AI Database: first the way it goes wrong ",
        h("b", { class: "bad-text" }, "without"),
        " the capability, then ",
        h("b", { class: "good-text" }, "with"),
        " it. Ask Claude on either side and watch the answer change with nothing but the context the database returned."
      ),
      h(
        "div",
        { class: "actions" },
        h("a", { class: "btn", href: "#/s/s1" }, "Start with §1"),
        h("button", { class: "btn ghost", onclick: () => setDock(true) }, "Explore the data")
      )
    ),
    labCard(),
    h(
      "section",
      { class: "takeaways" },
      h("h2", {}, "Key takeaways"),
      h(
        "div",
        { class: "grid3" },
        TAKEAWAYS.map(([t, d]) =>
          h("div", { class: "card takeaway" }, h("b", {}, t), h("p", {}, d))
        )
      )
    ),
    figure("checklist_00_reference_architecture.png", "Reference architecture"),
    h(
      "section",
      {},
      h("h2", {}, "The checklist"),
      h(
        "div",
        { class: "parts" },
        PARTS.map((part) =>
          h(
            "div",
            { class: "card part", style: `--c:${part.color}` },
            h(
              "div",
              { class: "part-head" },
              h("span", { class: "part-id" }, `Part ${part.id}`),
              h("b", {}, part.name)
            ),
            h("p", { class: "muted" }, part.blurb),
            SECTIONS.filter((s) => s.part === part.id).map((s) =>
              h(
                "a",
                { class: "part-sec", href: `#/s/${s.id}` },
                h("span", { class: "nav-n" }, s.n),
                h("span", {}, s.name),
                h("span", { class: `dot ${resultFor(s.id)?.[0] || ""}` })
              )
            )
          )
        )
      )
    ),
    figure("checklist_01_notebook_map.png", "Map of the checklist")
  );
}

// ------------------------------------------------------------------------------------------------ sections
function field(s, params, f) {
  const set = (e) => {
    params[f.name] = e.target.value;
  };
  let control;
  if (f.type === "select") {
    control = h(
      "select",
      { onchange: set },
      f.options.map(([v, label]) =>
        h("option", { value: v, selected: params[f.name] === v || null }, label)
      )
    );
  } else if (f.type === "textarea") {
    control = h("textarea", { rows: 3, oninput: set });
    control.value = params[f.name] || "";
  } else {
    control = h("input", { type: f.type === "date" ? "date" : "text", oninput: set });
    control.value = params[f.name] || "";
  }
  return h("label", { class: `field ${f.type}` }, h("span", {}, f.label), control);
}

function sectionPage(s) {
  const part = partOf(s);
  const params = (state.params[s.id] ||= { ...(DEFAULTS[s.id] || {}) });
  const i = SECTIONS.indexOf(s);
  return h(
    "div",
    { class: "page section", style: `--part:${part.color}` },
    h(
      "div",
      { class: "crumbs" },
      h("a", { href: "#/" }, "Overview"),
      " / ",
      `Part ${part.id} · ${part.name}`
    ),
    h("div", { class: "kicker" }, `§${s.n} · ${s.eyebrow}`),
    h("h1", {}, s.title),
    h("p", { class: "lede", html: s.intro }),
    h(
      "div",
      { class: s.img2 ? "figs two" : "figs" },
      figure(s.img),
      s.img2 ? figure(s.img2) : null
    ),
    s.inputs
      ? h(
          "div",
          { class: "card inputs" },
          h("div", { class: "inputs-title" }, "Inputs, shared by both sides"),
          h(
            "div",
            { class: "fields" },
            s.inputs.map((f) => field(s, params, f))
          ),
          s.suggestions
            ? h(
                "div",
                { class: "suggestions" },
                h("span", { class: "muted small" }, "Try:"),
                s.suggestions.map((text) =>
                  h(
                    "button",
                    {
                      class: "suggestion",
                      onclick: () => {
                        params.message = text;
                        render();
                      },
                    },
                    text
                  )
                )
              )
            : null
        )
      : null,
    h("div", { class: "versus" }, sideCard(s, "without", params), sideCard(s, "with", params)),
    h("div", { class: "notice" }, h("b", {}, "What to notice. "), h("span", { html: s.notice })),
    h(
      "div",
      { class: "pager" },
      i > 0
        ? h(
            "a",
            { class: "btn ghost", href: `#/s/${SECTIONS[i - 1].id}` },
            `← §${SECTIONS[i - 1].n} ${SECTIONS[i - 1].name}`
          )
        : h("span"),
      i < SECTIONS.length - 1
        ? h(
            "a",
            { class: "btn ghost", href: `#/s/${SECTIONS[i + 1].id}` },
            `§${SECTIONS[i + 1].n} ${SECTIONS[i + 1].name} →`
          )
        : h("a", { class: "btn ghost", href: "#/scorecard" }, "Scorecard →")
    )
  );
}

async function runAction(s, action, params) {
  const key = `${s.id}:${action}`;
  state.running[key] = true;
  delete state.answers[key];
  render();
  try {
    state.results[key] = await api(`/api/run/${s.id}/${action}`, params);
  } catch (e) {
    state.results[key] = { status: "error", verdict: "bad", summary: e.message };
  }
  state.running[key] = false;
  await refreshStatus();
  render();
  if (state.explorer.open)
    loadExplorer(); // show what the run changed in the database
  else renderDock();
}

function sideCard(s, side, params) {
  const cfg = s[side];
  const actions = [{ action: side, label: cfg.action, claude: cfg.claude }, ...(cfg.extra || [])];
  const needsClaude = (a) => a.claude && !state.status?.claude;
  return h(
    "section",
    { class: `side ${side}` },
    h("div", { class: "side-tag" }, side === "without" ? "✗ Without" : "✓ With Oracle AI Database"),
    h("p", { class: "side-text", html: cfg.text }),
    cfg.inputs
      ? h(
          "div",
          { class: "fields" },
          cfg.inputs.map((f) => field(s, params, f))
        )
      : null,
    h(
      "div",
      { class: "actions" },
      actions.map((a) =>
        h(
          "button",
          {
            class: `btn ${side === "without" ? "btn-bad" : "btn-good"}${a.action !== side ? " ghost" : ""}`,
            disabled: state.running[`${s.id}:${a.action}`] || needsClaude(a) || null,
            title: needsClaude(a) ? "Set ANTHROPIC_API_KEY to run this" : null,
            onclick: () => runAction(s, a.action, params),
          },
          state.running[`${s.id}:${a.action}`] ? "Running…" : `▶ ${a.label}`
        )
      )
    ),
    actions.map((a) => resultView(s, `${s.id}:${a.action}`))
  );
}

function table(rows, opts = {}) {
  if (!rows?.length) return h("p", { class: "muted small" }, "(no rows)");
  const cols = Object.keys(rows[0]);
  const cell = (col, v) => {
    if (v === null || v === undefined || v === "") return h("td", { class: "null" }, "—");
    if (
      ["memory_id", "src_id", "dst_id", "seed_id", "related_id"].includes(col) &&
      String(v).startsWith("mem_")
    )
      return h("td", {}, memoryChip(v));
    if (col === "user_id" || col === "end_user_name") return h("td", {}, userChip(v));
    if (col === "artifact_id")
      return h(
        "td",
        {},
        h(
          "a",
          { href: `/api/artifact/${encodeURIComponent(v)}`, target: "_blank", rel: "noopener" },
          v
        )
      );
    if (col === "pathname" && opts.files)
      return h("td", {}, h("button", { class: "link", onclick: () => openFile(v) }, v));
    if (col === "document") return h("td", {}, h("pre", { class: "json" }, v));
    if (typeof v === "object") return h("td", {}, h("code", {}, JSON.stringify(v)));
    const text = String(v);
    return h(
      "td",
      { title: text.length > 120 ? text : null, class: text.length > 120 ? "long" : null },
      text.length > 220 ? text.slice(0, 220) + "…" : text
    );
  };
  return h(
    "div",
    { class: "table-wrap" },
    h(
      "table",
      {},
      h(
        "thead",
        {},
        h(
          "tr",
          {},
          cols.map((c) => h("th", {}, c))
        )
      ),
      h(
        "tbody",
        {},
        rows.map((r) =>
          h(
            "tr",
            {},
            cols.map((c) => cell(c, r[c]))
          )
        )
      )
    )
  );
}

function contextList(items) {
  if (!items) return null;
  return h(
    "div",
    { class: "context" },
    h(
      "div",
      { class: "context-title" },
      `What the agent sees · ${items.length} ${items.length === 1 ? "memory" : "memories"}`
    ),
    items.length
      ? h(
          "ol",
          {},
          items.map((m) =>
            h(
              "li",
              { class: "memory" },
              h(
                "div",
                { class: "memory-meta" },
                memoryChip(m.memory_id),
                userChip(m.user_id),
                ["score", "relevance", "vector_rank", "text_rank", "via"]
                  .filter((k) => m[k] !== undefined && m[k] !== null)
                  .map((k) => h("span", { class: "metric-chip" }, `${k} ${m[k]}`))
              ),
              h("div", { class: "memory-text" }, m.content)
            )
          )
        )
      : h(
          "p",
          { class: "empty-context" },
          "(nothing recalled: the agent has no context to answer from)"
        )
  );
}

function vectorBars(values) {
  const nums = values.filter((v) => typeof v === "number");
  const max = Math.max(...nums.map(Math.abs), 0.0001);
  return h(
    "div",
    { class: "vector" },
    h("span", { class: "muted small" }, "first dimensions"),
    h(
      "div",
      { class: "bars" },
      nums.map((v) =>
        h("span", {
          class: v < 0 ? "neg" : "pos",
          style: `height:${Math.round((Math.abs(v) / max) * 100)}%`,
          title: v,
        })
      )
    )
  );
}

function resultView(s, key) {
  const res = state.results[key];
  if (state.running[key])
    return h(
      "div",
      { class: "result running" },
      h("div", { class: "spinner" }),
      "Running against the database…"
    );
  if (!res) return null;
  const extra = res.extra || {};
  const answer = state.answers[key];
  const canAsk = s.ask && res.status === "ok" && res.question && state.status?.claude;
  return h(
    "div",
    { class: `result ${res.status === "ok" ? res.verdict : res.status}` },
    h("div", { class: "summary" }, res.summary),
    res.metrics?.length
      ? h(
          "div",
          { class: "metrics" },
          res.metrics.map(([k, v]) =>
            h("span", { class: "metric" }, h("small", {}, k), h("b", {}, v))
          )
        )
      : null,
    extra.answer
      ? h(
          "div",
          { class: "claude-answer" },
          h("div", { class: "claude-tag" }, "Claude"),
          h("p", {}, withCitations(extra.answer))
        )
      : null,
    contextList(res.context),
    res.rows ? table(res.rows) : null,
    extra.vector ? vectorBars(extra.vector) : null,
    extra.image
      ? h("img", {
          class: "artifact-img",
          src: extra.image,
          alt: "A PNG artifact read back from a BLOB column",
        })
      : null,
    (extra.files || []).map((f) =>
      h("div", { class: "file" }, h("div", { class: "file-path" }, f.path), h("pre", {}, f.content))
    ),
    extra.spec
      ? h(
          "details",
          {},
          h("summary", {}, "The hybrid search spec"),
          h("pre", { class: "json" }, JSON.stringify(extra.spec, null, 2))
        )
      : null,
    extra.document
      ? h(
          "details",
          { open: true },
          h("summary", {}, "The document, as the duality view returns it"),
          h("pre", { class: "json" }, JSON.stringify(extra.document, null, 2))
        )
      : null,
    res.log?.length
      ? h(
          "ul",
          { class: "log" },
          res.log.map((l) => h("li", {}, l))
        )
      : null,
    res.note ? h("p", { class: "note" }, res.note) : null,
    res.sql
      ? h("details", { class: "sql" }, h("summary", {}, "SQL that ran"), h("pre", {}, res.sql))
      : null,
    canAsk
      ? h(
          "div",
          { class: "ask" },
          answer?.pending
            ? h(
                "div",
                { class: "result running small" },
                h("div", { class: "spinner" }),
                "Asking Claude…"
              )
            : answer?.text
              ? h(
                  "div",
                  { class: "claude-answer" },
                  h(
                    "div",
                    { class: "claude-tag" },
                    `Claude · from ${res.context?.length === 1 ? "this memory" : `these ${res.context?.length ?? 0} memories`}`
                  ),
                  h("p", {}, withCitations(answer.text))
                )
              : answer?.error
                ? h("p", { class: "error-text" }, answer.error)
                : null,
          h(
            "button",
            { class: "btn claude", onclick: () => askClaude(key, res) },
            answer?.text ? "Ask again" : `Ask Claude: “${res.question}”`
          )
        )
      : null
  );
}

async function askClaude(key, res) {
  state.answers[key] = { pending: true };
  render();
  try {
    const out = await api("/api/ask", {
      question: res.question,
      memory_ids: (res.context || []).map((m) => m.memory_id),
      user: res.user || null,
    });
    state.answers[key] = { text: out.answer };
  } catch (e) {
    state.answers[key] = { error: e.message };
  }
  render();
}

// ------------------------------------------------------------------------------------------------ memory drawer and files
async function openMemory(id) {
  const d = document.getElementById("drawer");
  d.replaceChildren(h("div", { class: "drawer-body" }, h("div", { class: "spinner" })));
  if (!d.open) d.showModal();
  try {
    const m = await api(`/api/memory/${encodeURIComponent(id)}`);
    const mem = m.memory;
    d.replaceChildren(
      h(
        "div",
        { class: "drawer-body" },
        h("button", { class: "close", onclick: () => d.close(), "aria-label": "Close" }, "×"),
        h("div", { class: "kicker" }, "MEMORY"),
        h("h2", {}, mem.memory_id, " ", userChip(mem.user_id)),
        h("p", { class: "memory-text big" }, mem.content),
        h(
          "dl",
          { class: "facts" },
          [
            "agent_id",
            "memory_type",
            "importance",
            "created_at",
            "valid_from",
            "valid_to",
            "source_thread_id",
          ].map((k) => [h("dt", {}, k), h("dd", {}, mem[k] ?? "open")])
        ),
        h("h3", {}, "metadata (JSON column)"),
        h("pre", { class: "json" }, JSON.stringify(mem.metadata, null, 2)),
        h("h3", {}, `embedding (VECTOR, norm ${mem.norm})`),
        vectorBars(mem.embedding_preview || []),
        h("h3", {}, "entities it mentions"),
        m.entities.length
          ? h(
              "div",
              { class: "chips" },
              m.entities.map((e) => h("span", { class: "metric-chip" }, `${e.name} · ${e.kind}`))
            )
          : h("p", { class: "muted small" }, "none"),
        h("h3", {}, "links"),
        m.links.length
          ? h(
              "ul",
              { class: "log" },
              m.links.map((l) =>
                h("li", {}, memoryChip(l.src_id), ` ${l.link_type} `, memoryChip(l.dst_id))
              )
            )
          : h("p", { class: "muted small" }, "none"),
        h("h3", {}, "artifacts"),
        m.artifacts.length
          ? h(
              "ul",
              { class: "log" },
              m.artifacts.map((a) =>
                h(
                  "li",
                  {},
                  h(
                    "a",
                    {
                      href: `/api/artifact/${encodeURIComponent(a.artifact_id)}`,
                      target: "_blank",
                      rel: "noopener",
                    },
                    a.file_name || a.artifact_id
                  ),
                  ` · ${a.mime_type}`
                )
              )
            )
          : h("p", { class: "muted small" }, "none"),
        h("h3", {}, "nearest current memories (by vector)"),
        h(
          "ul",
          { class: "log" },
          m.neighbours.map((n) =>
            h("li", {}, memoryChip(n.memory_id), ` ${n.score} · ${n.content.slice(0, 90)}…`)
          )
        )
      )
    );
  } catch (e) {
    d.replaceChildren(
      h(
        "div",
        { class: "drawer-body" },
        h("p", { class: "error-text" }, e.message),
        h("button", { class: "btn", onclick: () => d.close() }, "Close")
      )
    );
  }
}

async function openFile(path) {
  const d = document.getElementById("drawer");
  const res = await fetch(`/api/file?path=${encodeURIComponent(path)}`);
  d.replaceChildren(
    h(
      "div",
      { class: "drawer-body" },
      h("button", { class: "close", onclick: () => d.close(), "aria-label": "Close" }, "×"),
      h("div", { class: "kicker" }, "DBFS FILE"),
      h("h2", {}, path),
      h("pre", {}, await res.text())
    )
  );
  if (!d.open) d.showModal();
}

// ------------------------------------------------------------------------------------------------ data explorer dock
// Fixed to the bottom of every page: collapsed to a bar, or open and resizable by dragging its top edge.
const BAR_H = 46;
const maxDock = () => window.innerHeight - 80;

function saveDock() {
  const { open, height, table } = state.explorer;
  try {
    localStorage.setItem("appbook.dock", JSON.stringify({ open, height, table }));
  } catch {
    /* storage unavailable */
  }
}

function applyDockHeight() {
  const ex = state.explorer;
  const height = ex.open ? Math.max(160, Math.min(ex.height, maxDock())) : BAR_H;
  dockEl.style.height = `${height}px`;
  document.documentElement.style.setProperty("--dock-h", `${height}px`);
}

function setDock(open, table) {
  const ex = state.explorer;
  if (table && table !== ex.table) {
    ex.table = table;
    ex.data = null;
    ex.error = null;
  }
  ex.open = open;
  saveDock();
  renderDock();
  if (open && !ex.data && !ex.loading) loadExplorer();
}

async function loadExplorer() {
  const ex = state.explorer;
  ex.loading = true;
  ex.error = null;
  renderDock();
  const qs = new URLSearchParams(ex.table === "memories" ? ex.filters : {}).toString();
  try {
    ex.data = await api(`/api/explorer/${ex.table}${qs ? "?" + qs : ""}`);
  } catch (e) {
    ex.error = e.message;
    ex.data = null;
  }
  ex.loading = false;
  renderDock();
}

function startResize(e) {
  e.preventDefault();
  const ex = state.explorer;
  const startY = e.clientY;
  const startH = ex.open ? Math.min(ex.height, maxDock()) : BAR_H;
  dockEl.classList.add("resizing");
  const move = (ev) => {
    const height = Math.max(BAR_H, Math.min(maxDock(), startH + startY - ev.clientY));
    if (height < BAR_H + 50) {
      if (ex.open) {
        ex.open = false;
        renderDock();
      }
    } else {
      ex.height = height;
      if (!ex.open) setDock(true);
    }
    applyDockHeight();
  };
  window.addEventListener("pointermove", move);
  window.addEventListener(
    "pointerup",
    () => {
      window.removeEventListener("pointermove", move);
      dockEl.classList.remove("resizing");
      saveDock();
    },
    { once: true }
  );
}

function gripKeys(e) {
  const ex = state.explorer;
  if (e.key !== "ArrowUp" && e.key !== "ArrowDown") return;
  e.preventDefault();
  if (!ex.open) {
    if (e.key === "ArrowUp") setDock(true);
    return;
  }
  ex.height = Math.max(160, Math.min(maxDock(), ex.height + (e.key === "ArrowUp" ? 40 : -40)));
  applyDockHeight();
  saveDock();
}

function toggleMax() {
  const ex = state.explorer;
  if (ex.open && ex.height >= maxDock() - 10) ex.height = ex.restore || 380;
  else {
    ex.restore = ex.height;
    ex.height = maxDock();
  }
  setDock(true);
}

function dockBody() {
  const ex = state.explorer;
  const f = ex.filters;
  const sel = (name, label, options) =>
    h(
      "label",
      { class: "field select" },
      h("span", {}, label),
      h(
        "select",
        {
          onchange: (e) => {
            f[name] = e.target.value;
            loadExplorer();
          },
        },
        options.map(([v, l]) =>
          h("option", { value: v, selected: (f[name] || "") === v || null }, l)
        )
      )
    );
  const search = h("input", {
    type: "text",
    placeholder: "e.g. how do we roll back a deploy",
    onkeydown: (e) => {
      if (e.key === "Enter") {
        f.search = e.target.value;
        loadExplorer();
      }
    },
  });
  search.value = f.search || "";
  const desc = EXPLORER_TABLES.find(([t]) => t === ex.table)?.[1];
  return h(
    "div",
    { class: "dock-body" },
    h(
      "p",
      { class: "dock-desc" },
      h("code", {}, ex.table),
      " ",
      desc,
      ex.data ? h("span", { class: "muted" }, ` · ${ex.data.rows.length} rows`) : null,
      ex.loading && ex.data ? h("span", { class: "muted" }, " · refreshing…") : null
    ),
    ex.table === "memories"
      ? h(
          "div",
          { class: "fields filters" },
          sel("user", "User", [
            ["", "all"],
            ["user_ada", "Ada"],
            ["user_bob", "Bob"],
            ["user_cy", "Cy"],
            ["global", "team (global)"],
          ]),
          sel("memory_type", "Type", [
            ["", "all"],
            ["semantic", "semantic"],
            ["episodic", "episodic"],
            ["procedural", "procedural"],
          ]),
          sel("project", "Project", [
            ["", "all"],
            ["cairn", "cairn"],
            ["beacon", "beacon"],
            ["comet", "comet"],
          ]),
          sel("status", "Status", [
            ["all", "all"],
            ["current", "current (valid_to IS NULL)"],
            ["closed", "closed"],
          ]),
          h(
            "label",
            { class: "field text grow" },
            h("span", {}, "Search by meaning (VECTOR_EMBEDDING in the query)"),
            search
          ),
          h(
            "button",
            {
              class: "btn small",
              onclick: () => {
                f.search = search.value;
                loadExplorer();
              },
            },
            "Search"
          )
        )
      : null,
    ex.loading && !ex.data
      ? h("div", { class: "result running" }, h("div", { class: "spinner" }), "Querying…")
      : ex.error
        ? h("p", { class: "error-text" }, ex.error)
        : ex.data
          ? [
              table(ex.data.rows, { files: ex.table === "scratchpad" }),
              h(
                "details",
                { class: "sql" },
                h("summary", {}, "SQL that ran"),
                h("pre", {}, ex.data.sql)
              ),
            ]
          : null
  );
}

function renderDock() {
  const ex = state.explorer;
  const count = state.status?.counts?.n;
  dockEl.className = `dock ${ex.open ? "open" : "closed"}`;
  dockEl.replaceChildren(
    h(
      "div",
      {
        class: "dock-grip",
        role: "separator",
        "aria-orientation": "horizontal",
        "aria-label": "Resize the data explorer",
        tabindex: "0",
        title: "Drag to resize (or use the arrow keys)",
        onpointerdown: startResize,
        onkeydown: gripKeys,
      },
      h("span")
    ),
    h(
      "div",
      { class: "dock-bar" },
      h(
        "button",
        {
          class: "dock-toggle",
          "aria-expanded": String(ex.open),
          onclick: () => setDock(!ex.open),
        },
        h("span", { class: "chev" }, ex.open ? "▾" : "▴"),
        "Data explorer",
        count !== undefined ? h("span", { class: "nav-badge" }, `${count} memories`) : null
      ),
      h(
        "div",
        { class: "dock-tabs", role: "tablist" },
        EXPLORER_TABLES.map(([t]) =>
          h(
            "button",
            {
              class: `dock-tab${ex.table === t ? " active" : ""}`,
              role: "tab",
              "aria-selected": String(ex.table === t),
              onclick: () => setDock(true, t),
            },
            t
          )
        )
      ),
      h(
        "div",
        { class: "dock-actions" },
        ex.open
          ? h(
              "button",
              {
                class: "icon-btn",
                title: "Refresh",
                "aria-label": "Refresh",
                onclick: loadExplorer,
              },
              "↻"
            )
          : null,
        h(
          "button",
          {
            class: "icon-btn",
            title: "Maximise or restore",
            "aria-label": "Maximise or restore",
            onclick: toggleMax,
          },
          "⤢"
        ),
        h(
          "button",
          {
            class: "icon-btn",
            title: ex.open ? "Collapse" : "Expand",
            "aria-label": ex.open ? "Collapse" : "Expand",
            onclick: () => setDock(!ex.open),
          },
          ex.open ? "▾" : "▴"
        )
      )
    ),
    ex.open ? dockBody() : null
  );
  applyDockHeight();
}

// ------------------------------------------------------------------------------------------------ scorecard
async function runEverything() {
  const todo = SECTIONS.flatMap((s) =>
    ["without", "with"].filter((side) => !s[side].claude).map((side) => [s, side])
  );
  state.runAll = { done: 0, total: todo.length };
  render();
  for (const [s, side] of todo) {
    const params = (state.params[s.id] ||= { ...(DEFAULTS[s.id] || {}) });
    try {
      state.results[`${s.id}:${side}`] = await api(`/api/run/${s.id}/${side}`, params);
    } catch (e) {
      toast(`§${s.n}: ${e.message}`);
    }
    state.runAll.done += 1;
    await refreshStatus();
    render();
  }
  state.runAll = null;
  render();
}

function scorecardPage() {
  const results = state.status?.results || {};
  const proved = SECTIONS.filter((s) => results[s.id]?.[0] === "proved").length;
  return h(
    "div",
    { class: "page scorecard" },
    h("div", { class: "kicker" }, "SCORECARD"),
    h("h1", {}, `${proved} of ${SECTIONS.length} checklist items proved on this database`),
    h(
      "p",
      { class: "lede" },
      'Generated from the runs in this browser session: an item is proved when its "with" run succeeds. Run them one by one, or all at once (the Claude-only runs are left for you).'
    ),
    h(
      "div",
      { class: "actions" },
      h(
        "button",
        { class: "btn", disabled: state.runAll || null, onclick: runEverything },
        state.runAll
          ? `Running ${state.runAll.done} / ${state.runAll.total}…`
          : "▶ Run every section"
      )
    ),
    h(
      "div",
      { class: "table-wrap" },
      h(
        "table",
        { class: "score" },
        h(
          "thead",
          {},
          h(
            "tr",
            {},
            h("th", {}, "§"),
            h("th", {}, "Checklist item"),
            h("th", {}, "Oracle AI Database"),
            h("th", {}, "Evidence")
          )
        ),
        h(
          "tbody",
          {},
          SECTIONS.map((s) => {
            const r = results[s.id];
            return h(
              "tr",
              {},
              h("td", {}, s.n),
              h("td", {}, h("a", { href: `#/s/${s.id}` }, s.name)),
              h(
                "td",
                {},
                h("span", { class: `status-chip ${r?.[0] || "none"}` }, r?.[0] || "not run")
              ),
              h("td", { class: "muted" }, r?.[1] || "")
            );
          })
        )
      )
    )
  );
}

// ------------------------------------------------------------------------------------------------ boot
window.addEventListener("hashchange", () => {
  render();
  document.getElementById("main")?.focus();
  window.scrollTo(0, 0);
});
for (const id of ["drawer", "zoom-dialog"]) {
  document.getElementById(id).addEventListener("click", (e) => {
    if (e.target.id === id) e.target.close();
  });
}
window.addEventListener("resize", applyDockHeight);
window.addEventListener("keydown", (e) => {
  // [ collapses or expands the sidebar
  if (
    e.key === "[" &&
    !e.metaKey &&
    !e.ctrlKey &&
    !e.altKey &&
    !/^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement?.tagName || "")
  ) {
    setRail(!state.rail);
  }
});
document.documentElement.classList.toggle("rail", state.rail);
refreshStatus().then(() => {
  render();
  renderDock();
  if (state.explorer.open) loadExplorer();
});
