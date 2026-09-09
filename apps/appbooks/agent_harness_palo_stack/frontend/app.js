/* Total Recall — Appbook
   Vanilla JS. Hash router, theme toggle, SSE-over-fetch. One chapter per harness
   layer: narrative (what it is · why it matters · what to watch) + a live demo. */

const I = {
  brain:
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M9 3a3 3 0 0 0-3 3 3 3 0 0 0-2 5 3 3 0 0 0 1 5 3 3 0 0 0 5 1V4a1 1 0 0 0-1-1Z"/><path d="M15 3a3 3 0 0 1 3 3 3 3 0 0 1 2 5 3 3 0 0 1-1 5 3 3 0 0 1-5 1V4a1 1 0 0 1 1-1Z"/></svg>',
  home: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="m3 10 9-7 9 7"/><path d="M5 9v11h14V9"/></svg>',
  db: '<svg viewBox="0 0 24 24" fill="currentColor"><ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 8.4c1.6 1.2 4.6 1.9 8 1.9s6.4-.7 8-1.9v9.1c0 1.66-3.58 3-8 3s-8-1.34-8-3V8.4Z" opacity=".7"/></svg>',
  file: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M14 3v5h5"/><path d="M14 3H6v18h12V8z"/></svg>',
  search:
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/></svg>',
  chat: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H8l-5 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>',
  map: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="m9 4-6 2v14l6-2 6 2 6-2V4l-6 2-6-2z"/><path d="M9 4v14M15 6v14"/></svg>',
  tool: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M14.7 6.3a4 4 0 0 0-5.4 5.4L3 18v3h3l6.3-6.3a4 4 0 0 0 5.4-5.4l-2.5 2.5-2-2 2.5-2.5z"/></svg>',
  loop: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 0 1 15-6.7L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-15 6.7L3 16"/><path d="M3 21v-5h5"/></svg>',
  gauge:
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 13 16 9"/><path d="M5 19a9 9 0 1 1 14 0"/></svg>',
  send: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M22 2 11 13M22 2l-7 20-4-9-9-4 20-7z"/></svg>',
  bot: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="8" width="16" height="11" rx="3"/><path d="M12 8V4M9 13h.01M15 13h.01"/></svg>',
  sun: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M4.9 4.9l1.4 1.4m11.4 11.4 1.4 1.4M2 12h2m16 0h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>',
  moon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg>',
  menu: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M3 6h18M3 12h18M3 18h18"/></svg>',
  chevron:
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m11 17-5-5 5-5M18 17l-5-5 5-5"/></svg>',
  expand:
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M8 3H5a2 2 0 0 0-2 2v3"/><path d="M21 8V5a2 2 0 0 0-2-2h-3"/><path d="M3 16v3a2 2 0 0 0 2 2h3"/><path d="M16 21h3a2 2 0 0 0 2-2v-3"/></svg>',
  collapse:
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M8 3v3a2 2 0 0 1-2 2H3"/><path d="M21 8h-3a2 2 0 0 1-2-2V3"/><path d="M3 16h3a2 2 0 0 1 2 2v3"/><path d="M16 21v-3a2 2 0 0 1 2-2h3"/></svg>',
};
const MAXBTN = `<button class="panel-max-btn" onclick="toggleMax(this)" aria-label="Expand panel" title="Expand / collapse"><span class="i-max">${I.expand}</span><span class="i-min">${I.collapse}</span></button>`;

// ── chapters = harness layers ───────────────────────────────────────────
const LAYERS = [
  {
    id: "foundation",
    n: 1,
    nav: "Foundation & Models",
    icon: I.db,
    accent: "#6aa9ff",
    title: "Foundation & Models",
    kicker: "Layer 1 — Agent = Model + Harness",
    desc: "Everything starts on one database with the models loaded inside it. The chat LLM is a frozen reasoning utility; the harness is everything we build around it. Crucially, an embedding here is a SQL expression — produced in-engine by a loaded ONNX model.",
    term: "<b>In-database embeddings.</b> Instead of calling an external service to turn text into a vector, we load a small ONNX model into the database. The write path itself computes the vector — no data leaves the engine.",
    adv: "One model serves every store, so everything shares one 384-dim space (no dimension mismatches), and no text ever leaves the security/backup boundary to be vectorised.",
    watch:
      "Type any text and watch it become a 384-dim vector, computed by <code>VECTOR_EMBEDDING(...)</code> inside Oracle — the same call every later layer uses.",
  },
  {
    id: "substrate",
    n: 2,
    nav: "Memory Substrate",
    icon: I.file,
    accent: "#7ed0a5",
    title: "The Memory Substrate",
    kicker: "Layer 2 — Where memory physically lives",
    desc: "Before deciding how to write memory, decide where it lives. The old debate is filesystem vs. database; we resolve it with both, inside one database. The agent gets a POSIX-like scratch filesystem (SecureFile LOBs) with file ergonomics and database guarantees.",
    term: "<b>Filesystem-as-memory, inside the DB.</b> Agents reach for files because LLMs are pretrained on filesystems and reading a slice beats embedding everything. We keep that ergonomics — but the files are rows, so they are ACID and survive process death.",
    adv: "Progressive-disclosure reads (peek, then read more), durability across sessions, and ACID isolation under concurrency — all under one backup/security boundary, with no second system to reconcile.",
    watch:
      "Write a note, read it back (full / tail / grep), then run the ACID race: a plain OS file silently loses updates; the database counts every one.",
  },
  {
    id: "retrieval",
    n: 3,
    nav: "Encoding & Retrieval",
    icon: I.search,
    accent: "#c79cff",
    title: "Encoding & Retrieval",
    kicker: "Layer 3 — Turn a question into the right rows",
    desc: "The read path: a retrieval ladder of increasing power over the vector store. Each rung hands the model a small, relevant slice instead of everything — retrieval is progressive disclosure for tables.",
    term: "<b>The ladder.</b> keyword → vector → hybrid (Reciprocal Rank Fusion) → rerank (a cross-encoder). Retrieve cheaply with the bi-encoder, then rerank precisely with the cross-encoder that reads query and document together.",
    adv: "Hybrid fuses exact-match and paraphrase with no weight tuning; the in-database cross-encoder reranker fixes the last-mile ordering that vectors alone get wrong.",
    watch:
      "Switch techniques on the same question. Watch the order change — and on <b>rerank</b>, watch the cross-encoder's relevance score appear next to each row.",
  },
  {
    id: "memory",
    n: 4,
    nav: "Cognitive Memory",
    icon: I.chat,
    accent: "#ff9e64",
    title: "Cognitive Memory (OAMP)",
    kicker: "Layer 4 — A persistent identity",
    desc: "Storage becomes memory when it has a taxonomy the agent reasons about: episodic (conversation), semantic (facts), working (a rolling summary), procedural (skills). Backed by the Oracle AI Agent Memory package, embedded in-database.",
    term: "<b>The context card.</b> One call assembles working memory for the prompt — a synthesized summary, the most relevant durable memories, and the last few turns — into a compact, prompt-ready block. It is context engineering, done by the memory library.",
    adv: "The agent stops being an amnesiac: facts and conversation survive process death, and the context card keeps history bounded instead of resending the full transcript.",
    watch:
      "Chat across turns, then open the <b>context card</b> — see topics, a summary, retrieved memories, and recent turns assembled automatically. Save a durable fact and recall it by meaning.",
  },
  {
    id: "semantic",
    n: 5,
    nav: "Semantic Layer",
    icon: I.map,
    accent: "#5fd0d0",
    title: "The Semantic Layer",
    kicker: "Layer 5 — Grounding in your data's meaning",
    desc: "Teach the agent what your schema means — column comments, foreign keys, and workload — turned into an embedded catalog it searches before writing SQL, so it stops guessing column names.",
    term: "<b>Metadata as the map.</b> The database's own description of itself becomes searchable grounding. Good metadata is, literally, prompt engineering for your database — and a scheduled refresh keeps it fresh as the schema drifts.",
    adv: "This is what separates a demo that hard-codes one query from an agent that answers new questions over a real schema, grounded in trusted joins and meanings.",
    watch:
      "Ask which objects hold a signal (revenue, risk, discounts). The catalog returns the right tables/columns — by meaning, not string match.",
  },
  {
    id: "skills",
    n: 6,
    nav: "Skills & Automations",
    icon: I.tool,
    accent: "#ffd166",
    title: "Skills & Automations",
    kicker: "Layer 6 — The agent improves itself",
    desc: "Same raw material, three lifecycles: a workflow is what the agent did once; a skill is the reusable how-to it distils; an automation is the scheduled execution of a proven workflow. Tools and skills live in first-class registry tables, retrieved by meaning.",
    term: "<b>Continual learning in token space.</b> A frozen model can't update its weights — so the agent writes skills as SKILL.md documents, stores them (with a SHA + source URL), and retrieves the relevant ones back into context when a task recurs. Learning lives in tokens it can recall.",
    adv: "Tool JSON schemas live in the database and are retrieved by intent, so the registry grows without bloating the prompt; skills stay in sync with an upstream source via a SHA check; proven queries become standing, scheduled deliverables.",
    watch:
      "Search tools by meaning and see their JSON schemas; import a skill from a source, change it, and watch the SHA-gated refresh update it; build an automation (a materialized view + a scheduler job).",
  },
  {
    id: "agent",
    n: 7,
    nav: "The Agent Loop",
    icon: I.loop,
    accent: "#f78fb3",
    title: "The Agent Loop",
    kicker: "Layer 7 — What drives everything",
    desc: "The loop assembles grounded context (catalog + skills + context card), selects the top-k relevant tools, calls the model, runs the tools it asks for, and persists — looping under a budget. The loop is what turns a model into an agent.",
    term: "<b>Tools are the only way it acts.</b> The model chooses the trajectory; every action goes through a validated tool. Graph/working state is checkpointed into Oracle, so runs are durable and resumable.",
    adv: "One driver ties every layer together: it grounds, recalls, acts, and learns — getting faster at tasks it has done before because the workflow and skills pay off.",
    watch:
      "Ask an analytical question. Watch the live trace: context assembled → tools selected → SQL run → answer. Ask it to make a result a daily automation and watch it build one.",
  },
  {
    id: "context",
    n: 8,
    nav: "Context Engineering",
    icon: I.gauge,
    accent: "#a0e060",
    title: "Context Engineering",
    kicker: "Layer 8 — Keeping the window flat",
    desc: "Sessions grow; a naive loop re-sends the whole transcript and every full tool result until quality falls off a cliff. Two moves keep the window flat: compaction (the context card) and offloading (large results leave the window, leaving a reference).",
    term: "<b>Context rot.</b> Model quality degrades non-linearly well before the hard token limit. What matters is keeping the relevant context dense — not how much fits. Compact at ~60–70%, offload the rest.",
    adv: "The difference between an agent that's sharp for three turns and one that stays sharp for three hours — and it's the same harness, just managed.",
    watch:
      "The money shot: a long session charted twice — context engineering OFF (climbs without bound) vs ON (flat). Same loop, managed context.",
  },
  {
    id: "mission",
    n: 9,
    nav: "Mission Control",
    icon: I.bot,
    accent: "#8b9cff",
    title: "Mission Control — The Full Agent",
    kicker: "Layer 9 — Everything, working together",
    desc: "The whole harness in one console: a full chat agent grounded in memory, retrieval, the semantic layer and skills; the live context window it assembles on every turn; and the automations it can build, run, pause and resume — by button, or just by asking it.",
    term: "<b>One agent, every layer.</b> This is not a new capability — it is Layers 1–8 wired together and made operable. The chat drives the loop; the context panel shows exactly what entered the window this turn; the automations pane is the standing, scheduled work the agent produces.",
    adv: "It is the difference between eight demos and one product: a grounded analyst you can talk to, watch think, and hand standing jobs — all on one database, with the model never changing.",
    watch:
      "Chat with the agent and watch the <b>context window</b> repaint each turn (tools, catalog, skills, recipes, the card, an estimated token budget). Then build an automation — type &ldquo;make monthly revenue by channel a daily automation&rdquo;, or use the form — and <b>start/stop/run</b> it in the bottom pane.",
  },
];
const BY_ID = Object.fromEntries(LAYERS.map((l) => [l.id, l]));

// ── utils ────────────────────────────────────────────────────────────────
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const esc = (s) =>
  String(s ?? "").replace(
    /[&<>"']/g,
    (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]
  );
const uid = () => Math.random().toString(36).slice(2) + Date.now().toString(36);

// Dependency-free Markdown → HTML: headings, fenced code, GFM tables, lists,
// blockquotes, and inline bold/italic/code/links. Used by every chat surface.
function renderRich(text) {
  let src = String(text ?? "").replace(/\r\n/g, "\n");
  const codes = [];
  src = src.replace(/```(\w*)\n?([\s\S]*?)```/g, (_, lang, body) => {
    codes.push(`<pre class="md-pre"><code>${esc(body.replace(/\n$/, ""))}</code></pre>`);
    return `\n@@CODE${codes.length - 1}@@\n`;
  });
  const inline = (s) => {
    let h = esc(s);
    h = h.replace(/`([^`]+?)`/g, "<code>$1</code>");
    h = h.replace(
      /\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g,
      '<a href="$2" target="_blank" rel="noopener">$1</a>'
    );
    h = h.replace(/\*\*([^*]+?)\*\*/g, "<strong>$1</strong>");
    h = h.replace(/(^|[^*])\*([^*\n]+?)\*(?!\*)/g, "$1<em>$2</em>");
    return h;
  };
  const sep = (s) => /^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)+\|?\s*$/.test(s);
  const cells = (r) =>
    r
      .replace(/^\s*\|/, "")
      .replace(/\|\s*$/, "")
      .split("|")
      .map((c) => c.trim());
  const blockStart = /^(#{1,4}\s|\s*[-*+]\s|\s*\d+[.)]\s|\s*>\s?)/;
  const lines = src.split("\n"),
    out = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    const cm = /^@@CODE(\d+)@@$/.exec(line.trim());
    if (cm) {
      out.push(codes[+cm[1]]);
      i++;
      continue;
    }
    if (!line.trim()) {
      i++;
      continue;
    }
    let m = /^(#{1,4})\s+(.*)$/.exec(line);
    if (m) {
      const lv = m[1].length;
      out.push(`<h${lv} class="md-h md-h${lv}">${inline(m[2])}</h${lv}>`);
      i++;
      continue;
    }
    if (line.includes("|") && i + 1 < lines.length && sep(lines[i + 1])) {
      const head = cells(line);
      i += 2;
      const rows = [];
      while (i < lines.length && lines[i].includes("|") && lines[i].trim()) {
        rows.push(cells(lines[i]));
        i++;
      }
      out.push(
        `<div class="md-tablewrap"><table class="md-table"><thead><tr>${head.map((c) => `<th>${inline(c)}</th>`).join("")}</tr></thead><tbody>${rows.map((r) => `<tr>${r.map((c) => `<td>${inline(c)}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`
      );
      continue;
    }
    if (/^\s*>\s?/.test(line)) {
      const buf = [];
      while (i < lines.length && /^\s*>\s?/.test(lines[i])) {
        buf.push(lines[i].replace(/^\s*>\s?/, ""));
        i++;
      }
      out.push(`<blockquote class="md-quote">${inline(buf.join(" "))}</blockquote>`);
      continue;
    }
    if (/^\s*[-*+]\s+/.test(line)) {
      const buf = [];
      while (i < lines.length && /^\s*[-*+]\s+/.test(lines[i])) {
        buf.push(`<li>${inline(lines[i].replace(/^\s*[-*+]\s+/, ""))}</li>`);
        i++;
      }
      out.push(`<ul class="md-ul">${buf.join("")}</ul>`);
      continue;
    }
    if (/^\s*\d+[.)]\s+/.test(line)) {
      const buf = [];
      while (i < lines.length && /^\s*\d+[.)]\s+/.test(lines[i])) {
        buf.push(`<li>${inline(lines[i].replace(/^\s*\d+[.)]\s+/, ""))}</li>`);
        i++;
      }
      out.push(`<ol class="md-ol">${buf.join("")}</ol>`);
      continue;
    }
    const buf = [];
    while (
      i < lines.length &&
      lines[i].trim() &&
      !blockStart.test(lines[i]) &&
      !/^@@CODE\d+@@$/.test(lines[i].trim())
    ) {
      if (lines[i].includes("|") && i + 1 < lines.length && sep(lines[i + 1])) break;
      buf.push(lines[i]);
      i++;
    }
    out.push(`<p>${inline(buf.join("\n")).replace(/\n/g, "<br>")}</p>`);
  }
  return out.join("\n");
}
async function getJSON(url) {
  const r = await fetch(url);
  return r.json();
}
async function postJSON(url, body) {
  const r = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return r.json();
}
async function streamSSE(url, body, onEvent, signal) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
  if (!res.ok || !res.body) throw new Error("HTTP " + res.status);
  const reader = res.body.getReader(),
    dec = new TextDecoder();
  let buf = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    let m;
    const SEP = /\r?\n\r?\n/;
    while ((m = SEP.exec(buf))) {
      const block = buf.slice(0, m.index);
      buf = buf.slice(m.index + m[0].length);
      let event = "message",
        data = "";
      for (const line of block.split(/\r?\n/)) {
        if (line.startsWith(":")) continue;
        if (line.startsWith("event:")) event = line.slice(6).trim();
        else if (line.startsWith("data:")) data += line.slice(5).replace(/^\s/, "");
      }
      if (event === "end") return;
      if (data) {
        try {
          onEvent(JSON.parse(data));
        } catch (_) {}
      }
    }
  }
}

const state = {
  health: null,
  abort: null,
  route: "",
  chat: uid(),
  agent: uid(),
  mission: "mc-" + uid(),
};
function cancelStream() {
  if (state.abort) {
    try {
      state.abort.abort();
    } catch (_) {}
    state.abort = null;
  }
}

// ── sidebar + status ───────────────────────────────────────────────────
function renderSidebar(activeId) {
  const items = [
    `<a class="nav-item nav-home ${activeId === "home" ? "active" : ""}" href="#/" style="--c:var(--text-2)"><span class="nav-node">${I.home}</span><span class="nav-label">Overview</span></a>`,
    ...LAYERS.map(
      (l, i) =>
        `<a class="nav-item ${activeId === l.id ? "active" : ""}" href="#/${l.id}" style="--c:${l.accent};animation-delay:${(i + 1) * 45}ms"><span class="nav-node">${l.n}</span><span class="nav-label">${l.nav}</span><span class="nav-rung">${l.icon}</span></a>`
    ),
  ].join("");
  $("#sidebar").innerHTML = `
    <div class="brand"><span class="brand-glyph">${I.brain}</span><span class="brand-text"><b>Total Recall</b><span>Agent memory &amp; harness</span></span><button class="rail-toggle" id="rail-toggle" onclick="toggleRail()" title="Collapse sidebar" aria-label="Collapse sidebar">${I.chevron}</button></div>
    <div class="rail-label">The Harness — layer by layer</div>
    <nav class="nav">${items}</nav>
    <div class="rail-foot">
      <div class="status-card" id="status-card">${statusInner()}</div>
      <button class="theme-toggle" id="theme-toggle" onclick="toggleTheme()">${themeIcon()}<span>${themeLabel()}</span></button>
    </div>`;
}
function statusInner() {
  const h = state.health,
    harn = h && h.harness;
  const dot = (ok) => `<span class="sdot ${ok ? "ok" : "off"}"></span>`;
  if (!h) return `<div class="status-row">${dot(false)} connecting…</div>`;
  return `
    <div class="status-row">${dot(harn && harn.oracle)} Oracle AI Database</div>
    <div class="status-row">${dot(harn && harn.ready)} harness ${harn && harn.ready ? "ready" : "warming…"}</div>
    <div class="status-row">${dot(harn && harn.rerank)} reranker ${harn && harn.rerank ? "live" : "fallback"}</div>
    <div class="status-row">${dot(h.api_key_set)} ${esc(h.model || "model")}</div>`;
}
function refreshStatus() {
  const c = $("#status-card");
  if (c) c.innerHTML = statusInner();
}
function themeIcon() {
  return document.documentElement.getAttribute("data-theme") === "light" ? I.sun : I.moon;
}
function themeLabel() {
  return document.documentElement.getAttribute("data-theme") === "light" ? "Light" : "Dark";
}
function toggleTheme() {
  const next = document.documentElement.getAttribute("data-theme") === "light" ? "dark" : "light";
  document.documentElement.setAttribute("data-theme", next);
  try {
    localStorage.setItem("tr-theme", next);
  } catch (_) {}
  const t = $("#theme-toggle");
  if (t) t.innerHTML = themeIcon() + `<span>${themeLabel()}</span>`;
}
function toggleRail() {
  const railed = document.documentElement.classList.toggle("rail");
  try {
    localStorage.setItem("tr-rail", railed ? "1" : "0");
  } catch (_) {}
}
let _maxState = null; // {panel, parent, next} — remembers where to put a portaled panel back
function collapseMax() {
  if (_maxState) {
    const { panel, parent, next } = _maxState;
    panel.classList.remove("panel-max");
    panel.style.removeProperty("--accent");
    try {
      if (parent && parent.isConnected) parent.insertBefore(panel, next);
    } catch (_) {}
    _maxState = null;
  }
  document.querySelectorAll(".panel.panel-max").forEach((x) => x.classList.remove("panel-max"));
  document.body.classList.remove("has-panel-max");
  const s = document.getElementById("panel-scrim");
  if (s) s.remove();
}
function toggleMax(btn) {
  const p = btn.closest(".panel");
  if (!p) return;
  const already = p.classList.contains("panel-max");
  collapseMax(); // only one panel maximized at a time
  if (already) return;
  // Portal the panel to <body> so fixed-positioning escapes the stage's stacking/transform
  // context and can sit above the body-level scrim.
  _maxState = { panel: p, parent: p.parentNode, next: p.nextSibling };
  const stage = document.getElementById("stage"); // carry the view's accent onto the portaled panel
  const acc = stage ? getComputedStyle(stage).getPropertyValue("--accent").trim() : "";
  if (acc) p.style.setProperty("--accent", acc);
  const scrim = document.createElement("div");
  scrim.id = "panel-scrim";
  scrim.className = "panel-scrim";
  scrim.onclick = collapseMax;
  document.body.appendChild(scrim);
  document.body.appendChild(p); // moved after the scrim → paints above it
  p.classList.add("panel-max");
  document.body.classList.add("has-panel-max");
}

// ── chapter header (the narrative) ──────────────────────────────────────
function header(l) {
  return `
    <header class="ff-head">
      <div class="ff-numeral">${l.n}</div>
      <div class="ff-head-body">
        <div class="ff-kicker">${esc(l.kicker)}</div>
        <h1 class="ff-title">${esc(l.title)}</h1>
        <p class="ff-desc">${esc(l.desc)}</p>
        <div class="ff-term">${l.term}</div>
        <div class="notes">
          <div class="note note-adv"><span class="note-tag">Why this layer</span>${esc(l.adv)}</div>
          <div class="note note-watch"><span class="note-tag">What to watch</span>${l.watch}</div>
        </div>
      </div>
    </header>`;
}
function setStage(html, accent) {
  const s = $("#stage");
  s.style.setProperty("--accent", accent || "#6aa9ff");
  s.innerHTML = `<div class="view view-enter">${html}</div>`;
  s.scrollTop = 0;
}
function panel(title, body, icon) {
  return `<div class="panel"><div class="panel-head"><span class="panel-title">${icon || ""} ${esc(title)}</span></div><div class="panel-body">${body}</div></div>`;
}
const empty = (t) => `<div class="empty">${esc(t)}</div>`;
const spin = `<span class="spinner" style="display:inline-block"></span>`;

// ── HOME ────────────────────────────────────────────────────────────────
function viewHome() {
  setStage(
    `
    <header class="hero">
      <div class="hero-eq">Agent = Model + <span class="hl">Harness</span></div>
      <h1 class="hero-title">Total Recall</h1>
      <p class="hero-sub">An interactive appbook. We build an agent harness <b>layer by layer</b> on one Oracle AI Database — and at each layer you can poke the running agent and watch the advantage show up. The model never changes; everything that makes it useful, and everything that makes it <i>get better</i>, is the harness.</p>
    </header>
    <div class="lgrid">
      ${LAYERS.map(
        (
          l,
          i
        ) => `<a class="lcard" href="#/${l.id}" style="--c:${l.accent};animation-delay:${i * 50}ms">
        <span class="lcard-num">${l.n}</span><span class="lcard-icon">${l.icon}</span>
        <span class="lcard-name">${esc(l.nav)}</span><span class="lcard-desc">${esc(l.desc.split(".")[0])}.</span></a>`
      ).join("")}
    </div>
    <p class="home-foot">Start at <a href="#/foundation">Layer 1</a> and climb. Each chapter explains the layer, why it matters, and what to watch — then lets you try it live against the database.</p>`,
    "#6aa9ff"
  );
}

// ── L1 FOUNDATION ───────────────────────────────────────────────────────
function viewFoundation() {
  const l = BY_ID.foundation;
  setStage(
    `${header(l)}
    <div class="grid-2">
      ${panel(
        "Embed text in the database",
        `
        <div class="field"><textarea id="fx-in" rows="2" placeholder="Type any text to embed…">Supplier concentration is the top operational risk.</textarea>
        <button class="btn btn-accent" id="fx-go">${I.send} Embed</button></div>
        <div id="fx-out" class="mono small" style="margin-top:12px">${empty("The 384-dim vector (first values) appears here — computed in-engine.")}</div>`,
        I.search
      )}
      ${panel("Models loaded in the database", `<div id="fx-models">${empty("loading…")}</div>`, I.db)}
    </div>`,
    l.accent
  );
  async function go() {
    const t = $("#fx-in").value.trim();
    if (!t) return;
    $("#fx-out").innerHTML = spin + " embedding…";
    const d = await postJSON("/api/foundation/embed", { text: t });
    $("#fx-out").innerHTML =
      `<b>${d.dims}</b>-dim vector via <code>VECTOR_EMBEDDING(${esc(d.model)} …)</code><br><span class="dim">[ ${(d.head || []).join(",  ")},  … ]</span>`;
  }
  $("#fx-go").addEventListener("click", go);
  getJSON("/api/foundation/models").then((d) => {
    $("#fx-models").innerHTML =
      (d.models || [])
        .map(
          (m) =>
            `<div class="kv"><span class="mono">${esc(m.MODEL_NAME)}</span><span class="tag">${esc(m.MINING_FUNCTION)}</span></div>`
        )
        .join("") || empty("no models");
  });
}

// ── L2 SUBSTRATE ────────────────────────────────────────────────────────
function viewSubstrate() {
  const l = BY_ID.substrate;
  setStage(
    `${header(l)}
    <div class="grid-2">
      ${panel(
        "The in-database scratch filesystem",
        `
        <div class="field"><input id="sb-path" value="/notes/review.md" /></div>
        <div class="field" style="margin-top:8px"><textarea id="sb-body" rows="4"># Q3 review
Revenue grew 12% QoQ, led by Outdoors.
Risk: one supplier covers 40% of Outdoors COGS.</textarea></div>
        <div class="row" style="margin-top:8px">
          <button class="btn btn-accent" id="sb-write">Write</button>
          <button class="btn btn-ghost" id="sb-read">Read full</button>
          <button class="btn btn-ghost" id="sb-tail">Tail 2</button>
          <button class="btn btn-ghost" id="sb-grep">Grep "risk"</button>
        </div>
        <pre class="out" id="sb-out">—</pre>`,
        I.file
      )}
      ${panel(
        "ACID vs. a plain file (lost-update race)",
        `
        <p class="small">Two writers each increment a counter 300×. A plain OS file with no lock loses updates; an atomic database <code>UPDATE</code> counts every one — concurrency safety, by default.</p>
        <button class="btn btn-accent" id="sb-acid">Run the race</button>
        <div id="sb-acid-out" style="margin-top:12px">${empty("results appear here")}</div>`,
        I.db
      )}
    </div>`,
    l.accent
  );
  const path = () => $("#sb-path").value.trim();
  $("#sb-write").addEventListener("click", async () => {
    await postJSON("/api/substrate/write", { path: path(), content: $("#sb-body").value });
    $("#sb-out").textContent = "written ✓  (it is a row in the DB — it will survive process death)";
  });
  $("#sb-read").addEventListener("click", async () => {
    const d = await getJSON("/api/substrate/read?path=" + encodeURIComponent(path()));
    $("#sb-out").textContent = d.text || d.error || "—";
  });
  $("#sb-tail").addEventListener("click", async () => {
    const d = await getJSON("/api/substrate/read?mode=tail&n=2&path=" + encodeURIComponent(path()));
    $("#sb-out").textContent = d.text || d.error || "—";
  });
  $("#sb-grep").addEventListener("click", async () => {
    const d = await getJSON(
      "/api/substrate/read?mode=grep&pattern=risk&path=" + encodeURIComponent(path())
    );
    $("#sb-out").textContent = JSON.stringify(d.hits || d.error, null, 2);
  });
  $("#sb-acid").addEventListener("click", async () => {
    $("#sb-acid-out").innerHTML = spin + " racing two writers…";
    const d = await getJSON("/api/substrate/acid");
    const bar = (v, max) =>
      `<div class="meter"><div class="meter-fill" style="width:${Math.round((100 * v) / max)}%"></div></div>`;
    $("#sb-acid-out").innerHTML = `
      <div class="kv"><span>OS file (no lock)</span><b class="${d.os_file < d.target ? "bad" : ""}">${d.os_file} / ${d.target}</b></div>${bar(d.os_file, d.target)}
      <div class="kv" style="margin-top:10px"><span>Database (atomic UPDATE)</span><b class="good">${d.database} / ${d.target}</b></div>${bar(d.database, d.target)}
      <p class="small" style="margin-top:10px">${d.os_file < d.target ? "The OS file lost updates. " : ""}The database is exact — ACID isolation.</p>`;
  });
}

// ── L3 RETRIEVAL ────────────────────────────────────────────────────────
const TECHS = [
  ["keyword", "Keyword"],
  ["vector", "Vector"],
  ["hybrid", "Hybrid (RRF)"],
  ["rerank", "Rerank"],
];
function viewRetrieval() {
  const l = BY_ID.retrieval;
  let tech = "hybrid";
  setStage(
    `${header(l)}
    ${panel(
      "The retrieval ladder",
      `
      <div class="row spread"><div class="seg" id="rt-seg">${TECHS.map(([t, n], i) => `<button class="${t === "hybrid" ? "active" : ""}" data-t="${t}">${n}</button>`).join("")}</div><span class="hint" id="rt-note"></span></div>
      <div class="field" style="margin-top:12px"><textarea id="rt-in" rows="1" placeholder="Ask the knowledge store…">What is the main operational risk?</textarea><button class="btn btn-accent" id="rt-go">${I.search} Search</button></div>
      <div id="rt-out" style="margin-top:14px">${empty("Results appear here. Switch techniques to see the order change.")}</div>`,
      I.search
    )}`,
    l.accent
  );
  $("#rt-seg").addEventListener("click", (e) => {
    const b = e.target.closest("button");
    if (!b) return;
    tech = b.dataset.t;
    $$("#rt-seg button").forEach((x) => x.classList.toggle("active", x === b));
    go();
  });
  async function go() {
    const q = $("#rt-in").value.trim();
    if (!q) return;
    $("#rt-out").innerHTML = spin + " retrieving…";
    const d = await postJSON("/api/retrieval/search", { query: q, technique: tech, k: 5 });
    $("#rt-note").textContent =
      tech === "rerank" && !d.rerank_available ? "reranker not loaded · showing hybrid order" : "";
    $("#rt-out").innerHTML =
      (d.hits || [])
        .map((h, i) => {
          const sc =
            h.rerank_score != null
              ? `rerank ${h.rerank_score}`
              : h.rrf != null
                ? `rrf ${h.rrf}`
                : h.dist != null
                  ? `dist ${(+h.dist).toFixed(3)}`
                  : h.score != null
                    ? `score ${(+h.score).toFixed(2)}`
                    : "";
          return `<div class="rrow" style="animation-delay:${i * 40}ms"><span class="rrank">${i + 1}</span><span class="rtext">${esc(h.content)}</span><span class="rscore">${sc}</span></div>`;
        })
        .join("") || empty("no matches");
  }
  $("#rt-go").addEventListener("click", go);
  $("#rt-in").addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      go();
    }
  });
  go();
}

// ── L4 MEMORY ───────────────────────────────────────────────────────────
function viewMemory() {
  const l = BY_ID.memory;
  setStage(
    `${header(l)}
    <div class="mem-layout">
      ${panel(
        "Chat (remembers across turns)",
        `
        <div id="mm-log" class="chatlog"><div class="empty">Say something — then check the context card.</div></div>
        <div class="field" style="margin-top:10px"><textarea id="mm-in" rows="1" placeholder="e.g. My name is Ada and I care about churn."></textarea><button class="btn btn-accent" id="mm-send">${I.send}</button></div>
        <div class="row" style="margin-top:8px"><button class="btn btn-ghost" id="mm-card">Show context card</button><button class="btn btn-ghost" id="mm-new">New session</button></div>`,
        I.chat
      )}
      ${panel(
        "Durable memory & the context card",
        `
        <div class="field"><input id="mm-fact" placeholder="Save a durable fact…" value="Refunds over $500 require manager approval." /><button class="btn" id="mm-remember">Remember</button></div>
        <div class="field" style="margin-top:8px"><input id="mm-q" placeholder="Recall by meaning…" value="approval threshold for big refunds" /><button class="btn" id="mm-recall">Recall</button></div>
        <div id="mm-recall-out" class="small" style="margin-top:8px"></div>
        <div class="card-title">OAMP context card</div>
        <pre class="out card" id="mm-card-out">${esc("Chat a little, then press “Show context card”.")}</pre>`,
        I.bot
      )}
    </div>`,
    l.accent
  );
  const log = $("#mm-log");
  function add(role, text) {
    if (log.querySelector(".empty")) log.innerHTML = "";
    const d = document.createElement("div");
    d.className = "msg " + role;
    d.innerHTML = renderRich(text);
    log.appendChild(d);
    log.scrollTop = log.scrollHeight;
    return d;
  }
  async function send() {
    const t = $("#mm-in").value.trim();
    if (!t || state.abort) return;
    add("user", t);
    $("#mm-in").value = "";
    const out = add("bot", "");
    let acc = "";
    state.abort = new AbortController();
    try {
      await streamSSE(
        "/api/memory/chat",
        { message: t, thread_id: state.chat },
        (ev) => {
          if (ev.type === "delta") {
            acc += ev.text;
            out.innerHTML = renderRich(acc);
            log.scrollTop = log.scrollHeight;
          } else if (ev.type === "done") {
            $("#mm-card-out").textContent = ev.card || "(empty)";
          }
        },
        state.abort.signal
      );
    } catch (e) {
      out.innerHTML = `<span class="bad">Error: ${esc(e.message)}</span>`;
    } finally {
      state.abort = null;
    }
  }
  $("#mm-send").addEventListener("click", send);
  $("#mm-in").addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  });
  $("#mm-card").addEventListener("click", async () => {
    const d = await getJSON("/api/memory/card?thread_id=" + state.chat);
    $("#mm-card-out").textContent = d.card || "(empty — chat first)";
  });
  $("#mm-new").addEventListener("click", () => {
    state.chat = uid();
    log.innerHTML = `<div class="empty">New session. Durable memories persist; conversation starts fresh.</div>`;
    $("#mm-card-out").textContent = "(new session)";
  });
  $("#mm-remember").addEventListener("click", async () => {
    await postJSON("/api/memory/remember", { fact: $("#mm-fact").value });
    $("#mm-recall-out").innerHTML = `<span class="good">saved to long-term memory ✓</span>`;
  });
  $("#mm-recall").addEventListener("click", async () => {
    $("#mm-recall-out").innerHTML = spin + " recalling…";
    const d = await postJSON("/api/memory/recall", { query: $("#mm-q").value });
    $("#mm-recall-out").innerHTML =
      (d.hits || [])
        .map(
          (h) =>
            `<div class="rrow"><span class="rtext">${esc(h.content)}</span><span class="rscore">d ${h.distance}</span></div>`
        )
        .join("") || empty("nothing yet — save a fact first");
  });
}

// ── L5 SEMANTIC ─────────────────────────────────────────────────────────
function viewSemantic() {
  const l = BY_ID.semantic;
  setStage(
    `${header(l)}
    ${panel(
      "Ask the schema what it means",
      `
      <div class="field"><textarea id="se-in" rows="1" placeholder="Which columns hold…">which columns hold revenue or money?</textarea><button class="btn btn-accent" id="se-go">${I.search} Search catalog</button></div>
      <div class="chips" style="margin-top:10px">${["which columns hold revenue or money?", "how do orders join to customers?", "where is the discount stored?", "what describes a product category?"].map((s) => `<button class="chip">${esc(s)}</button>`).join("")}</div>
      <div id="se-out" style="margin-top:14px">${empty("The catalog returns the right tables/columns — by meaning.")}</div>`,
      I.map
    )}`,
    l.accent
  );
  async function go() {
    const q = $("#se-in").value.trim();
    if (!q) return;
    $("#se-out").innerHTML = spin + " searching the catalog…";
    const d = await postJSON("/api/semantic/search", { query: q, technique: "vector", k: 6 });
    $("#se-out").innerHTML =
      (d.hits || [])
        .map(
          (h, i) =>
            `<div class="rrow" style="animation-delay:${i * 40}ms"><span class="rrank">${i + 1}</span><span class="rtext mono">${esc(h.content)}</span><span class="rscore">d ${(+h.dist).toFixed(3)}</span></div>`
        )
        .join("") || empty("no matches");
  }
  $("#se-go").addEventListener("click", go);
  $$(".chip", $("#stage")).forEach((c) =>
    c.addEventListener("click", () => {
      $("#se-in").value = c.textContent;
      go();
    })
  );
  go();
}

// ── L6 SKILLS ───────────────────────────────────────────────────────────
function viewSkills() {
  const l = BY_ID.skills;
  setStage(
    `${header(l)}
    <div class="grid-2">
      ${panel(
        "Tool registry — JSON schemas, retrieved by meaning",
        `
        <div class="field"><textarea id="sk-tq" rows="1">make a result refresh on a schedule</textarea><button class="btn btn-accent" id="sk-tgo">Find tools</button></div>
        <div id="sk-tools" style="margin-top:12px">${empty("Matching tools + their JSON schemas appear here.")}</div>`,
        I.tool
      )}
      ${panel(
        "Skills — SKILL.md, versioned by SHA",
        `
        <div class="field"><input id="sk-sname" value="forecast_revenue" /></div>
        <div class="field" style="margin-top:6px"><input id="sk-sdesc" value="Forecast next-quarter revenue from trailing trend" /></div>
        <div class="field" style="margin-top:6px"><textarea id="sk-sbody" rows="3">## Steps
1. pull trailing 4 quarters
2. fit a trend, project next quarter</textarea></div>
        <div class="row" style="margin-top:8px"><button class="btn btn-accent" id="sk-reg">Register from source</button><button class="btn btn-ghost" id="sk-refresh">Refresh (SHA-gated)</button></div>
        <div id="sk-skout" class="small" style="margin-top:10px"></div>`,
        I.tool
      )}
    </div>
    <div class="grid-2" style="margin-top:16px">
      ${panel(
        "Build an automation (MV + scheduler job)",
        `
        <div class="field"><input id="sk-aname" value="revenue_by_category" /></div>
        <div class="field" style="margin-top:6px"><textarea id="sk-asql" rows="2">SELECT category, ROUND(SUM(net_revenue),2) revenue FROM v_revenue WHERE order_date >= SYSDATE-90 GROUP BY category</textarea></div>
        <button class="btn btn-accent" id="sk-acreate">Create automation</button>
        <div id="sk-aout" class="small" style="margin-top:10px"></div>
        <div class="card-title">Registered automations</div><div id="sk-alist">${empty("none yet")}</div>`,
        I.loop
      )}
      ${panel(
        "Workflows → skills (the harvester)",
        `
        <p class="small">Workflows the agent captured. Promote one into a reusable SKILL.md.</p>
        <div id="sk-wf">${empty("Run the agent (Layer 7) to capture workflows.")}</div>
        <div class="card-title">Skill registry</div><div id="sk-slist">${empty("loading…")}</div>`,
        I.brain
      )}
    </div>`,
    l.accent
  );
  // tools
  $("#sk-tgo").addEventListener("click", async () => {
    $("#sk-tools").innerHTML = spin + " searching tools…";
    const d = await postJSON("/api/skills/tools", { query: $("#sk-tq").value });
    $("#sk-tools").innerHTML =
      (d.tools || [])
        .map(
          (t) =>
            `<div class="toolcard"><div class="kv"><b class="mono">${esc(t.name)}</b><span class="tag">d ${(+t.dist).toFixed(3)}</span></div><div class="small">${esc(t.description)}</div><pre class="schema">${esc(JSON.stringify((t.schema && t.schema.parameters) || {}, null, 0))}</pre></div>`
        )
        .join("") || empty("no tools");
  });
  // skills source + refresh
  $("#sk-reg").addEventListener("click", async () => {
    const d = await postJSON("/api/skills/register_source", {
      name: $("#sk-sname").value,
      description: $("#sk-sdesc").value,
      body: $("#sk-sbody").value,
    });
    $("#sk-skout").innerHTML =
      `<span class="good">registered ${esc(d.skill)} · sha ${esc(d.sha)}</span> — now edit the body and press Refresh to see the SHA change.`;
    loadSkills();
  });
  $("#sk-refresh").addEventListener("click", async () => {
    const d = await postJSON("/api/skills/refresh", {});
    $("#sk-skout").innerHTML =
      d.updated && d.updated.length
        ? `<span class="good">refreshed (SHA changed): ${esc(d.updated.join(", "))}</span>`
        : "no changes detected (SHA identical)";
    loadSkills();
  });
  // automation
  $("#sk-acreate").addEventListener("click", async () => {
    $("#sk-aout").innerHTML = spin + " building MV + scheduler job…";
    const d = await postJSON("/api/skills/create_automation", {
      name: $("#sk-aname").value,
      select_sql: $("#sk-asql").value,
      cadence_hours: 24,
      description: "Daily " + $("#sk-aname").value,
    });
    $("#sk-aout").innerHTML = d.error
      ? `<span class="bad">${esc(d.error)}</span>`
      : `<span class="good">built ${esc(d.artifact)} + job ${esc(d.job)} every ${d.cadence_hours}h ✓</span>`;
    loadAutos();
  });
  async function loadAutos() {
    const d = await getJSON("/api/skills/automations");
    $("#sk-alist").innerHTML =
      (d.automations || [])
        .map(
          (a) =>
            `<div class="kv"><span class="mono">${esc(a.NAME)}</span><span class="tag">${esc(a.ARTIFACT)} · ${a.CADENCE_HOURS}h</span></div>`
        )
        .join("") || empty("none yet");
  }
  async function loadSkills() {
    const d = await getJSON("/api/skills/list");
    $("#sk-slist").innerHTML =
      (d.skills || [])
        .map(
          (s) =>
            `<div class="kv"><span class="mono">${esc(s.NAME)}</span><span class="tag">${s.SOURCE_URL ? "sourced" : "distilled"} · ${esc(s.SHA || "")}</span></div>`
        )
        .join("") || empty("none");
  }
  async function loadWf() {
    const d = await getJSON("/api/skills/workflows");
    $("#sk-wf").innerHTML =
      (d.workflows || [])
        .map(
          (w) =>
            `<div class="kv"><span class="rtext">${esc(w.INTENT)}</span>${w.PROMOTED === "Y" ? '<span class="tag">promoted</span>' : `<button class="btn btn-sm" data-wf="${w.ID}">promote ↗ (×${w.OCCURRENCES})</button>`}</div>`
        )
        .join("") || empty("no workflows yet — run the agent in Layer 7");
    $$("#sk-wf [data-wf]").forEach((b) =>
      b.addEventListener("click", async () => {
        b.textContent = "promoting…";
        await postJSON("/api/skills/promote", { workflow_id: b.dataset.wf });
        loadWf();
        loadSkills();
      })
    );
  }
  loadAutos();
  loadSkills();
  loadWf();
}

// ── L7 AGENT ────────────────────────────────────────────────────────────
const AGENT_SAMPLES = [
  "Show total revenue by product category for the last 90 days.",
  "Which sales channel has the highest revenue this quarter?",
  "Make monthly revenue by channel a daily automation.",
];
function viewAgent() {
  const l = BY_ID.agent;
  setStage(
    `${header(l)}
    ${panel(
      "Ask the agent",
      `
      <div class="field"><textarea id="ag-in" rows="1" placeholder="Ask an analytical question…">${esc(AGENT_SAMPLES[0])}</textarea><button class="btn btn-accent" id="ag-go">${I.send} Run</button></div>
      <div class="chips" style="margin-top:10px">${AGENT_SAMPLES.map((s) => `<button class="chip">${esc(s)}</button>`).join("")}</div>`,
      I.loop
    )}
    <div class="grid-2" style="margin-top:16px">
      ${panel("Answer", `<div id="ag-answer" class="bubble">${empty("The grounded answer appears here.")}</div>`, I.bot)}
      ${panel("Live trace", `<div id="ag-trace" class="trace">${empty("context assembled → tools → answer")}</div>`, I.loop)}
    </div>`,
    l.accent
  );
  $$(".chip", $("#stage")).forEach((c) =>
    c.addEventListener("click", () => {
      $("#ag-in").value = c.textContent;
      go();
    })
  );
  $("#ag-go").addEventListener("click", go);
  $("#ag-in").addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      go();
    }
  });
  async function go() {
    const p = $("#ag-in").value.trim();
    if (!p || state.abort) return;
    const trace = $("#ag-trace"),
      ans = $("#ag-answer");
    trace.innerHTML = "";
    ans.innerHTML = '<span class="caret"></span>';
    let acc = "";
    const ev = (cls, html) => {
      const d = document.createElement("div");
      d.className = "tev " + cls;
      d.innerHTML = html;
      trace.appendChild(d);
      trace.scrollTop = trace.scrollHeight;
    };
    state.abort = new AbortController();
    try {
      await streamSSE(
        "/api/agent/run",
        { prompt: p, thread_id: state.agent },
        (e) => {
          if (e.type === "context") {
            ev(
              "ctx",
              `<b>assemble_context</b> · ${e.tools.length} tools · ${e.catalog.length} catalog hits`
            );
            if (e.card)
              ev(
                "ctx dim",
                "context card: " + esc((e.card || "").replace(/\s+/g, " ").slice(0, 90)) + "…"
              );
          } else if (e.type === "tool_call")
            ev("call", `→ <b>${esc(e.name)}</b>(${esc(JSON.stringify(e.args).slice(0, 80))})`);
          else if (e.type === "tool_result")
            ev(
              "res",
              `← ${esc(e.name)}: <span class="dim">${esc((e.preview || "").slice(0, 110))}</span>`
            );
          else if (e.type === "delta") {
            acc += e.text;
            ans.innerHTML = renderRich(acc) + '<span class="caret"></span>';
          } else if (e.type === "done") {
            ans.innerHTML = renderRich(acc) || empty("(no answer)");
            ev("done", `✓ done · tools used: ${(e.tools_used || []).join(", ") || "none"}`);
          }
        },
        state.abort.signal
      );
    } catch (e) {
      ans.innerHTML = `<span class="bad">Error: ${esc(e.message)}</span>`;
    } finally {
      state.abort = null;
    }
  }
}

// ── L8 CONTEXT ──────────────────────────────────────────────────────────
function viewContext() {
  const l = BY_ID.context;
  setStage(
    `${header(l)}
    ${panel(
      "Context size over a long session",
      `
      <p class="small">Same loop, run twice. <b style="color:#f7768e">OFF</b>: resend the full transcript + every full tool result. <b style="color:#9ece6a">ON</b>: inject the bounded context card + offload large results to a reference.</p>
      <button class="btn btn-accent" id="cx-go">Simulate 16 turns</button>
      <div id="cx-chart" style="margin-top:16px">${empty("press simulate")}</div>`,
      I.gauge
    )}`,
    l.accent
  );
  $("#cx-go").addEventListener("click", async () => {
    $("#cx-chart").innerHTML = spin + " simulating…";
    const d = await getJSON("/api/context/series");
    const off = d.off,
      on = d.on,
      max = Math.max(...off),
      W = 640,
      H = 220,
      n = off.length;
    const pts = (arr) =>
      arr
        .map((v, i) => `${((i / (n - 1)) * W).toFixed(1)},${(H - (v / max) * (H - 10)).toFixed(1)}`)
        .join(" ");
    $("#cx-chart").innerHTML = `
      <svg viewBox="0 0 ${W} ${H}" class="chart" preserveAspectRatio="none">
        <polyline points="${pts(off)}" fill="none" stroke="#f7768e" stroke-width="3"/>
        <polyline points="${pts(on)}" fill="none" stroke="#9ece6a" stroke-width="3"/>
      </svg>
      <div class="row spread" style="margin-top:8px"><span class="hint"><span class="leg" style="background:#f7768e"></span>OFF — ends at ${off[off.length - 1].toLocaleString()}</span><span class="hint"><span class="leg" style="background:#9ece6a"></span>ON — ends flat at ${on[on.length - 1].toLocaleString()}</span></div>
      <p class="small" style="margin-top:10px">Flat context is what keeps a long session both affordable and sharp.</p>`;
  });
}

// ── L9 MISSION CONTROL ───────────────────────────────────────────────────
const MC_SAMPLES = [
  "Show total revenue by product category for the last 90 days.",
  "Make monthly revenue by channel a daily automation.",
  "Which sales channel grew fastest this quarter?",
];
function viewMission() {
  const l = BY_ID.mission;
  setStage(
    `${header(l)}
    <div class="mc-threads">
      <span class="thlabel">${I.chat} Conversations</span>
      <div id="mc-thlist" class="thlist"><span class="dim small">loading…</span></div>
      <button class="btn btn-ghost btn-sm" id="mc-thnew">+ New chat</button>
    </div>
    <div class="mc">
      <div class="panel mc-chat">
        <div class="panel-head"><span class="panel-title">${I.chat} Chat with the agent</span><span class="panel-tools"><button class="btn btn-ghost btn-sm" id="mc-new">New session</button>${MAXBTN}</span></div>
        <div class="panel-body">
          <div id="mc-log" class="chatlog mc-log"><div class="empty">Ask an analytical question, or tell it to build an automation.</div></div>
          <div class="field" style="margin-top:10px"><textarea id="mc-in" rows="1" placeholder="Ask the agent…">${esc(MC_SAMPLES[0])}</textarea><button class="btn btn-accent" id="mc-go">${I.send}</button></div>
          <div class="chips" style="margin-top:8px">${MC_SAMPLES.map((s) => `<button class="chip">${esc(s)}</button>`).join("")}</div>
        </div>
      </div>
      <div class="panel mc-ctx">
        <div class="panel-head"><span class="panel-title">${I.gauge} Context window (live)</span><span class="panel-tools"><span class="hint" id="mc-tok"></span>${MAXBTN}</span></div>
        <div class="panel-body" id="mc-ctx-body">${empty("The context the agent assembles will appear here — repainting on every turn.")}</div>
      </div>
    </div>
    <div class="panel mc-autos">
      <div class="panel-head"><span class="panel-title">${I.loop} Automations — standing, scheduled work</span><span class="panel-tools"><button class="btn btn-ghost btn-sm" id="mc-areload">Refresh</button>${MAXBTN}</span></div>
      <div class="panel-body">
        <div class="mc-acreate">
          <div class="acfield">
            <label class="aclabel" for="mc-aname">Name</label>
            <input id="mc-aname" class="acinput acmono" placeholder="revenue_by_channel" value="revenue_by_channel" spellcheck="false" autocomplete="off" />
          </div>
          <div class="acfield">
            <label class="aclabel" for="mc-asql">Query <span class="acdim">SELECT only</span></label>
            <input id="mc-asql" class="acinput acmono" placeholder="SELECT … FROM v_revenue …" value="SELECT channel, ROUND(SUM(net_revenue),2) revenue FROM v_revenue WHERE order_date >= SYSDATE-90 GROUP BY channel" spellcheck="false" autocomplete="off" />
          </div>
          <div class="acfield">
            <label class="aclabel" for="mc-acad">Every</label>
            <div class="acnum"><input id="mc-acad" class="acinput" type="number" min="1" value="24" /><span class="acsuffix">hrs</span></div>
          </div>
          <button class="btn btn-accent acbuild" id="mc-acreate-btn">${I.loop} Build automation</button>
        </div>
        <div id="mc-aout" class="small" style="margin-top:8px"></div>
        <div id="mc-alist" class="mc-alist" style="margin-top:10px">${empty("none yet — build one above, or ask the agent")}</div>
      </div>
    </div>`,
    l.accent
  );

  // ── chat → the agent loop, multi-turn over one thread ──
  const log = $("#mc-log");
  function add(role, html) {
    if (log.querySelector(".empty")) log.innerHTML = "";
    const d = document.createElement("div");
    d.className = "msg " + role;
    d.innerHTML = html;
    log.appendChild(d);
    log.scrollTop = log.scrollHeight;
    return d;
  }
  function renderCtx(e) {
    const cap = 4000,
      pct = Math.min(100, Math.round((100 * (e.est_tokens || 0)) / cap));
    $("#mc-tok").textContent = e.est_tokens ? "~" + e.est_tokens.toLocaleString() + " tokens" : "";
    const list = (arr, cls) =>
      arr && arr.length
        ? arr.map((s) => `<div class="ctx-item ${cls || ""}">${esc(s)}</div>`).join("")
        : '<div class="dim small">none</div>';
    $("#mc-ctx-body").innerHTML = `
      <div class="ctx-gauge" title="estimated prompt size"><div class="ctx-gauge-fill" style="width:${pct}%"></div></div>
      <div class="ctx-sec"><div class="ctx-h">Tools selected · ${(e.tools || []).length}</div><div class="chips">${(e.tools || []).map((t) => `<span class="chip chip-static">${esc(t)}</span>`).join("") || '<span class="dim small">none</span>'}</div></div>
      <div class="ctx-sec"><div class="ctx-h">Schema catalog · ${(e.catalog || []).length}</div>${list(e.catalog, "mono")}</div>
      <div class="ctx-sec"><div class="ctx-h">Skills (manifest)</div><pre class="ctx-pre">${esc(e.skills || "(none)")}</pre></div>
      ${e.recipes && e.recipes.length ? `<div class="ctx-sec"><div class="ctx-h">Proven recipes</div>${list(e.recipes)}</div>` : ""}
      <div class="ctx-sec"><div class="ctx-h">Working memory · context card</div><pre class="ctx-pre">${esc((e.card || "(empty)").trim())}</pre></div>`;
  }
  async function send() {
    const p = $("#mc-in").value.trim();
    if (!p || state.abort) return;
    add("user", esc(p));
    $("#mc-in").value = "";
    if (log.querySelector(".empty")) log.innerHTML = "";
    const bot = document.createElement("div");
    bot.className = "msg bot mc-msg";
    bot.innerHTML =
      '<div class="msg-body"><span class="caret"></span></div>' +
      '<details class="msg-trace" hidden><summary><span class="tr-n">0</span> steps · agent trace</summary><div class="tr-items"></div></details>';
    log.appendChild(bot);
    log.scrollTop = log.scrollHeight;
    const body = bot.querySelector(".msg-body"),
      det = bot.querySelector(".msg-trace"),
      items = bot.querySelector(".tr-items"),
      trn = bot.querySelector(".tr-n");
    let acc = "",
      n = 0;
    const step = (cls, label, detail) => {
      det.hidden = false;
      trn.textContent = ++n;
      const s = document.createElement("div");
      s.className = "tr-step " + cls;
      s.innerHTML =
        `<span class="tr-k">${label}</span>` +
        (detail ? `<span class="tr-v">${detail}</span>` : "");
      items.appendChild(s);
    };
    state.abort = new AbortController();
    try {
      await streamSSE(
        "/api/agent/run",
        { prompt: p, thread_id: state.mission },
        (e) => {
          if (e.type === "context") renderCtx(e);
          else if (e.type === "tool_call")
            step("call", "→ " + esc(e.name), esc(JSON.stringify(e.args || {}).slice(0, 120)));
          else if (e.type === "tool_result") {
            step(
              "res",
              "✓ " + esc(e.name),
              esc((e.preview || "").replace(/\s+/g, " ").slice(0, 140))
            );
            if (
              e.name === "create_automation" ||
              e.name === "toggle_automation" ||
              e.name === "run_automation_now"
            )
              loadAutos();
          } else if (e.type === "delta") {
            acc += e.text;
            body.innerHTML = renderRich(acc) + '<span class="caret"></span>';
            log.scrollTop = log.scrollHeight;
          } else if (e.type === "done") {
            body.innerHTML = renderRich(acc) || empty("(no answer)");
            loadAutos();
            loadThreads();
          }
        },
        state.abort.signal
      );
    } catch (err) {
      body.innerHTML = `<span class="bad">Error: ${esc(err.message)}</span>`;
    } finally {
      state.abort = null;
    }
  }
  $("#mc-go").addEventListener("click", send);
  $("#mc-in").addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  });
  $$(".mc-chat .chip", $("#stage")).forEach((c) =>
    c.addEventListener("click", () => {
      $("#mc-in").value = c.textContent;
      send();
    })
  );
  function markActiveThread() {
    $$("#mc-thlist .thchip").forEach((c) =>
      c.classList.toggle("active", c.dataset.tid === state.mission)
    );
  }
  function newSession() {
    cancelStream();
    state.mission = "mc-" + uid();
    log.innerHTML =
      '<div class="empty">New session. Durable memory + automations persist; the conversation starts fresh.</div>';
    $("#mc-ctx-body").innerHTML = empty("Context will appear on the next turn.");
    $("#mc-tok").textContent = "";
    markActiveThread();
  }
  async function loadThreads() {
    let d;
    try {
      d = await getJSON("/api/memory/threads");
    } catch (_) {
      return;
    }
    const T = (d && d.threads) || [],
      host = $("#mc-thlist");
    if (!host) return;
    if (!T.length) {
      host.innerHTML = '<span class="dim small">No past conversations yet.</span>';
      return;
    }
    host.innerHTML = T.map(
      (t) =>
        `<button class="thchip ${t.THREAD_ID === state.mission ? "active" : ""}" data-tid="${esc(t.THREAD_ID)}" title="${esc((t.PREVIEW || "").replace(/\s+/g, " "))} · ${esc(t.LAST_AT || "")}"><span class="thchip-t">${esc((t.PREVIEW || "conversation").replace(/\s+/g, " ").slice(0, 42))}</span><span class="thchip-m">${t.MSGS}</span></button>`
    ).join("");
    $$("#mc-thlist .thchip").forEach((c) =>
      c.addEventListener("click", () => openThread(c.dataset.tid))
    );
  }
  async function openThread(id) {
    if (state.abort) return;
    state.mission = id;
    markActiveThread();
    log.innerHTML = '<div class="empty">loading…</div>';
    let d;
    try {
      d = await getJSON("/api/memory/thread?thread_id=" + encodeURIComponent(id));
    } catch (_) {
      log.innerHTML = '<div class="empty">could not load conversation</div>';
      return;
    }
    const msgs = (d && d.messages) || [];
    log.innerHTML = msgs.length ? "" : '<div class="empty">Empty conversation.</div>';
    for (const m of msgs) {
      if ((m.MESSAGE_ROLE || "").toLowerCase() === "user") add("user", esc(m.CONTENT));
      else {
        const b = document.createElement("div");
        b.className = "msg bot mc-msg";
        b.innerHTML = `<div class="msg-body">${renderRich(m.CONTENT || "")}</div>`;
        log.appendChild(b);
      }
    }
    log.scrollTop = log.scrollHeight;
    $("#mc-ctx-body").innerHTML = empty("Send a message to refresh the context window.");
    $("#mc-tok").textContent = "";
  }
  $("#mc-new").addEventListener("click", newSession);
  $("#mc-thnew").addEventListener("click", newSession);

  // ── automations pane ──
  function renderTable(rows, error) {
    if (error) return `<span class="bad">${esc(error)}</span>`;
    if (!rows || !rows.length) return empty("(no rows)");
    const cols = Object.keys(rows[0]);
    return `<table class="rtable"><thead><tr>${cols.map((c) => `<th>${esc(c)}</th>`).join("")}</tr></thead><tbody>${rows
      .slice(0, 12)
      .map((r) => `<tr>${cols.map((c) => `<td>${esc(r[c])}</td>`).join("")}</tr>`)
      .join("")}</tbody></table>`;
  }
  let knownAutos = null; // null until first load, so we only flash genuinely new rows
  async function loadAutos() {
    let d;
    try {
      d = await getJSON("/api/automations");
    } catch (_) {
      return;
    }
    const A = (d && d.automations) || [];
    if (!A.length) {
      $("#mc-alist").innerHTML = empty("none yet — build one above, or ask the agent");
      knownAutos = new Set();
      return;
    }
    $("#mc-alist").innerHTML = A.map((a) => {
      const on = String(a.ENABLED).toUpperCase() === "TRUE";
      const isNew = knownAutos && !knownAutos.has(a.NAME);
      return `<div class="auto${isNew ? " just-added" : ""}" data-n="${esc(a.NAME)}">
        <div class="auto-head">
          <span class="sdot ${on ? "ok" : "off"}"></span>
          <b class="mono">${esc(a.NAME)}</b>
          <span class="tag">${esc(a.ARTIFACT)} · ${a.CADENCE_HOURS}h</span>
          <span class="auto-state">${on ? "running" : "stopped"}${a.NEXT_RUN ? " · next " + esc(a.NEXT_RUN) : ""}</span>
          <span class="auto-btns">
            <button class="btn btn-sm" data-act="run">Run now</button>
            <button class="btn btn-sm ${on ? "btn-warn" : "btn-accent"}" data-act="toggle" data-on="${on}">${on ? "Stop" : "Start"}</button>
          </span>
        </div>
        <div class="auto-res" hidden></div>
      </div>`;
    }).join("");
    knownAutos = new Set(A.map((a) => a.NAME));
    $$("#mc-alist .auto").forEach((row) => {
      const name = row.dataset.n,
        res = row.querySelector(".auto-res");
      row.querySelector('[data-act="run"]').addEventListener("click", async (e) => {
        e.target.textContent = "running…";
        const d = await postJSON("/api/automations/run", { name });
        e.target.textContent = "Run now";
        res.hidden = false;
        res.innerHTML = renderTable(d.rows, d.error);
      });
      row.querySelector('[data-act="toggle"]').addEventListener("click", async () => {
        const on = row.querySelector('[data-act="toggle"]').dataset.on === "true";
        await postJSON("/api/automations/toggle", { name, enable: !on });
        loadAutos();
      });
    });
  }
  $("#mc-acreate-btn").addEventListener("click", async () => {
    $("#mc-aout").innerHTML = spin + " building materialized view + scheduler job…";
    const d = await postJSON("/api/automations/create", {
      name: $("#mc-aname").value,
      select_sql: $("#mc-asql").value,
      cadence_hours: +$("#mc-acad").value || 24,
      description: "Built from Mission Control",
    });
    $("#mc-aout").innerHTML = d.error
      ? `<span class="bad">${esc(d.error)}</span>`
      : `<span class="good">built ${esc(d.artifact)} + job ${esc(d.job)} every ${d.cadence_hours}h ✓</span>`;
    loadAutos();
  });
  $("#mc-areload").addEventListener("click", loadAutos);
  loadAutos();
  loadThreads();
}

// ── router ──────────────────────────────────────────────────────────────
const ROUTES = {
  "": viewHome,
  foundation: viewFoundation,
  substrate: viewSubstrate,
  retrieval: viewRetrieval,
  memory: viewMemory,
  semantic: viewSemantic,
  skills: viewSkills,
  agent: viewAgent,
  context: viewContext,
  mission: viewMission,
};
function route() {
  cancelStream();
  collapseMax();
  const id = location.hash.replace(/^#\/?/, "").trim() || "";
  state.route = id || "home";
  renderSidebar(id || "home");
  (ROUTES[id] || viewHome)();
  if (window.innerWidth <= 760) closeMenu();
}
function openMenu() {
  $("#sidebar").classList.add("open");
  $("#scrim").hidden = false;
}
function closeMenu() {
  $("#sidebar").classList.remove("open");
  $("#scrim").hidden = true;
}

async function boot() {
  try {
    if (localStorage.getItem("tr-rail") === "1") document.documentElement.classList.add("rail");
  } catch (_) {}
  const mb = document.createElement("button");
  mb.className = "menu-btn";
  mb.innerHTML = I.menu;
  mb.addEventListener("click", openMenu);
  document.body.appendChild(mb);
  $("#scrim").addEventListener("click", closeMenu);
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") collapseMax();
  });
  window.addEventListener("hashchange", route);
  route();
  async function poll() {
    try {
      state.health = await getJSON("/api/health");
      refreshStatus();
    } catch (_) {}
    const h = state.health && state.health.harness;
    if (!h || !h.ready) setTimeout(poll, 2000);
  }
  poll();
}
boot();
