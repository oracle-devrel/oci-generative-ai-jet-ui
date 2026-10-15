/* Interactive reference architecture for "The Intelligence Plane".
   window.Architecture = { mount(el, health), update(health), showTurn(planeResult, naiveResult) }
   Plane lane on top, naive lane below, shared model and Oracle tier on the right.
   Node ids match the step ids the backend emits in result.path. */
(function () {
  const NS = "http://www.w3.org/2000/svg",
    W = 1430,
    H = 742;
  const esc = (v) =>
    String(v ?? "").replace(
      /[&<>"']/g,
      (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]
    );
  const RM = () =>
    window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // ---- Nodes: geometry on a fixed grid, plus what each component is and which Oracle feature implements it ----
  const N = {
    ui: {
      x: 10,
      y: 378,
      w: 140,
      h: 84,
      lane: "entry",
      title: "Browser",
      sub: "1 question · 2 panes",
      role: "One input box sends the same question, persona and model to both agents; two panes stream the answers side by side.",
      feature: "Single page app over SSE",
    },
    api: {
      x: 214,
      y: 386,
      w: 140,
      h: 68,
      lane: "entry",
      title: "FastAPI",
      sub: "orchestrator · SSE",
      role: "Runs both agents in parallel on the selected desk identity and streams each result as it finishes.",
      feature: "Python service; one Oracle connection per agent turn",
    },
    memory: {
      x: 812,
      y: 14,
      w: 150,
      h: 72,
      lane: "plane",
      title: "Agent memory",
      sub: "OAMP 26.8 · per desk",
      component: "memory",
      role: "Recalls durable facts and preferences (with their source message and thread) before routing; saves the turn afterwards.",
      feature: "oracleagentmemory 26.8 in a per-desk Oracle schema; in-database embeddings",
    },
    guard: {
      x: 400,
      y: 128,
      w: 150,
      h: 72,
      lane: "plane",
      title: "Control guard",
      sub: "before any model call",
      role: "Refuses cross-desk, credential and destructive requests before any model sees them.",
      feature: "Policy check in the plane; Oracle still enforces rows underneath",
    },
    semantic_cache: {
      x: 606,
      y: 128,
      w: 150,
      h: 72,
      lane: "plane",
      title: "Semantic cache",
      sub: "HF_SEMCACHE vectors",
      role: "Reuses a previous plan or answer for a semantically similar question, only if the ontology entity and semantic vocabulary still match.",
      feature: "VECTOR column + VECTOR_DISTANCE in the desk memory schema",
    },
    router: {
      x: 812,
      y: 128,
      w: 150,
      h: 72,
      lane: "plane",
      title: "Model router",
      sub: "LLM picks the tool",
      role: "The model chooses an approved tool, metric and group. It never writes a governed number.",
      feature: "Selected model with a strict JSON schema",
    },
    ontology: {
      x: 1018,
      y: 128,
      w: 150,
      h: 72,
      lane: "plane",
      title: "Ontology",
      sub: "SQL/PGQ · LEI parent/child",
      role: "Resolves a counterparty to every legal entity reachable from its root LEI through GLEIF-style parent/child links.",
      feature: "SQL property graph HF_GRAPH (GRAPH_TABLE, variable-length ParentOf path)",
    },
    render: {
      x: 606,
      y: 250,
      w: 150,
      h: 72,
      lane: "plane",
      title: "Governed render",
      sub: "figure from SQL",
      role: "Renders the answer from the approved SQL result and its units, applying remembered format preferences.",
      feature: "Output validation; the model only routes",
    },
    semantic_layer: {
      x: 1018,
      y: 250,
      w: 150,
      h: 72,
      lane: "plane",
      title: "Semantic layer",
      sub: "HF_SEMANTICS · SQL_ID",
      role: "Supplies the firm definition of each metric as approved SQL, mined from V$SQL with its source SQL_ID.",
      feature: "HF_SEMANTICS table + schema annotations + V$SQL lineage",
    },
    vector: {
      x: 400,
      y: 376,
      w: 150,
      h: 88,
      lane: "shared",
      title: "Vector search",
      sub: "VECTOR_EMBEDDING",
      component: "embeddings",
      role: "Finds the nearest research passages. Both agents use it; only the plane reranks.",
      feature: "ONNX all-MiniLM-L12-v2 loaded with DBMS_VECTOR.LOAD_ONNX_MODEL; VECTOR_DISTANCE",
    },
    rerank: {
      x: 606,
      y: 376,
      w: 150,
      h: 88,
      lane: "plane",
      title: "Rerank",
      sub: "ONNX cross-encoder",
      component: "rerank",
      role: "Reorders retrieved passages by relevance before they reach the model as evidence.",
      feature: "In-database ONNX cross-encoder scored with SQL PREDICTION",
    },
    llm: {
      x: 812,
      y: 376,
      w: 150,
      h: 88,
      lane: "shared",
      title: "Model providers",
      sub: "same model, both lanes",
      role: "One selected model serves both agents with the same limits: OpenAI GPT-6.1 Sol, Claude Opus 5.5, OCI Grok 4.3, local Llama 3.2 or Private AI.",
      feature:
        "OCI Generative AI, OpenAI, Anthropic, local fallback; Oracle Private AI Services when running",
    },
    history: {
      x: 400,
      y: 556,
      w: 150,
      h: 72,
      lane: "naive",
      title: "History",
      sub: "append-only turns",
      role: "Every previous message is appended to the next prompt, so the naive context grows each turn.",
      feature: "HF_HISTORY table in Oracle",
    },
    text_to_sql: {
      x: 812,
      y: 556,
      w: 150,
      h: 72,
      lane: "naive",
      title: "Text-to-SQL",
      sub: "model writes SQL",
      role: "The model writes its own SQL over the raw tables (one repair on error) and writes the answer.",
      feature: "Selected model; read-only SELECT tool",
    },
    raw_sql: {
      x: 1018,
      y: 556,
      w: 150,
      h: 72,
      lane: "naive",
      title: "Raw SQL",
      sub: "raw tables only",
      role: "Runs the model-written SELECT against raw tables: no ontology, no metric definitions.",
      feature: "Read-only SQL under the same desk identity",
    },
    true_cache: {
      x: 1222,
      y: 120,
      w: 190,
      h: 88,
      lane: "db",
      title: "True Cache",
      sub: "read-only cache instance",
      component: "true_cache",
      role: "Serves read-heavy agent queries from an in-memory, read-only cache kept current by redo from the primary.",
      feature: "Oracle True Cache (Free)",
    },
    primary: {
      x: 1222,
      y: 262,
      w: 190,
      h: 120,
      lane: "db",
      title: "Primary database",
      sub: "26ai Free · all data",
      component: "database",
      role: "Holds every table, vector, graph, metric definition, memory and audit record. Takes all writes.",
      feature: "Oracle AI Database 26ai Free on a persistent volume",
    },
    dds: {
      x: 1222,
      y: 430,
      w: 190,
      h: 88,
      lane: "db",
      title: "Deep Data Security",
      sub: "end-user data grants",
      component: "governance",
      role: "Filters every row by the signed-in desk identity (hf_credit / hf_markets). Identical SQL returns different, entitled rows.",
      feature: "Deep Data Security end users, data roles and CREATE DATA GRANT",
    },
    audit: {
      x: 1222,
      y: 566,
      w: 190,
      h: 88,
      lane: "db",
      title: "Unified Auditing",
      sub: "records per request",
      component: "audit",
      role: "Records each audited read and write with the request ID, so every answer links to its audit trail.",
      feature: "Unified Auditing policies on positions, semantics, memory and history",
    },
  };
  const SHARED = new Set(["ui", "vector", "llm", "true_cache", "primary", "dds", "audit"]);
  const READERS = { ontology: "plane", semantic_layer: "plane", vector: "both", raw_sql: "naive" };
  const BUS = 1186,
    WBUS = 1202;
  const STUB = {
    ontology: [
      [1168, 164],
      [BUS, 164],
    ],
    semantic_layer: [
      [1168, 286],
      [BUS, 286],
    ],
    raw_sql: [
      [1168, 592],
      [BUS, 592],
    ],
    vector: [
      [475, 464],
      [475, 496],
      [BUS, 496],
    ],
  };

  // ---- Edges: orthogonal waypoints; lane says who may light it up ----
  const E = [
    {
      id: "ui_api",
      from: "ui",
      to: "api",
      lane: "both",
      pts: [
        [150, 420],
        [214, 420],
      ],
      label: "question",
      lx: 182,
      ly: 411,
    },
    {
      id: "api_guard",
      from: "api",
      to: "guard",
      lane: "plane",
      pts: [
        [284, 386],
        [284, 164],
        [400, 164],
      ],
      label: "plane",
      lx: 342,
      ly: 156,
      halo: 1,
    },
    {
      id: "guard_cache",
      from: "guard",
      to: "semantic_cache",
      lane: "plane",
      pts: [
        [550, 164],
        [606, 164],
      ],
      label: "allowed",
      lx: 578,
      ly: 156,
    },
    {
      id: "cache_router",
      from: "semantic_cache",
      to: "router",
      lane: "plane",
      pts: [
        [756, 164],
        [812, 164],
      ],
      label: "miss",
      lx: 784,
      ly: 156,
    },
    {
      id: "router_ontology",
      from: "router",
      to: "ontology",
      lane: "plane",
      pts: [
        [962, 164],
        [1018, 164],
      ],
      label: "group",
      lx: 990,
      ly: 156,
    },
    {
      id: "memory_router",
      from: "memory",
      to: "router",
      lane: "plane",
      pts: [
        [887, 86],
        [887, 128],
      ],
      label: "recalled facts",
      lx: 895,
      ly: 111,
      anchor: "start",
    },
    {
      id: "ontology_semantic",
      from: "ontology",
      to: "semantic_layer",
      lane: "plane",
      pts: [
        [1093, 200],
        [1093, 250],
      ],
      label: "resolved LEIs",
      lx: 1101,
      ly: 229,
      anchor: "start",
    },
    {
      id: "cache_render",
      from: "semantic_cache",
      to: "render",
      lane: "plane",
      pts: [
        [681, 200],
        [681, 250],
      ],
      label: "hit: cached plan",
      lx: 689,
      ly: 229,
      anchor: "start",
    },
    {
      id: "guard_render",
      from: "guard",
      to: "render",
      lane: "plane",
      pts: [
        [475, 200],
        [475, 268],
        [606, 268],
      ],
      label: "refused",
      lx: 540,
      ly: 260,
    },
    {
      id: "semantic_render",
      from: "semantic_layer",
      to: "render",
      lane: "plane",
      pts: [
        [1018, 286],
        [756, 286],
      ],
      label: "approved SQL result",
      lx: 897,
      ly: 278,
      anchor: "start",
    },
    {
      id: "answer_plane",
      from: "render",
      to: "ui",
      lane: "plane",
      pts: [
        [606, 286],
        [80, 286],
        [80, 378],
      ],
      label: "answer",
      lx: 340,
      ly: 278,
      halo: 1,
    },
    {
      id: "router_llm",
      from: "router",
      to: "llm",
      lane: "plane",
      pts: [
        [887, 200],
        [887, 376],
      ],
      label: "routing call",
      lx: 879,
      ly: 352,
      anchor: "end",
      bidir: 1,
      halo: 1,
    },
    {
      id: "vector_rerank",
      from: "vector",
      to: "rerank",
      lane: "plane",
      pts: [
        [550, 420],
        [606, 420],
      ],
      label: "top-k",
      lx: 578,
      ly: 412,
    },
    {
      id: "rerank_llm",
      from: "rerank",
      to: "llm",
      lane: "plane",
      pts: [
        [756, 420],
        [812, 420],
      ],
      label: "evidence",
      lx: 784,
      ly: 412,
    },
    {
      id: "api_history",
      from: "api",
      to: "history",
      lane: "naive",
      pts: [
        [284, 454],
        [284, 592],
        [400, 592],
      ],
      label: "naive",
      lx: 342,
      ly: 584,
    },
    {
      id: "history_t2s",
      from: "history",
      to: "text_to_sql",
      lane: "naive",
      pts: [
        [550, 592],
        [812, 592],
      ],
      label: "full history",
      lx: 681,
      ly: 584,
    },
    {
      id: "t2s_llm",
      from: "text_to_sql",
      to: "llm",
      lane: "naive",
      pts: [
        [887, 556],
        [887, 464],
      ],
      label: "SQL + answer calls",
      lx: 879,
      ly: 532,
      anchor: "end",
      bidir: 1,
      halo: 1,
    },
    {
      id: "t2s_raw",
      from: "text_to_sql",
      to: "raw_sql",
      lane: "naive",
      pts: [
        [962, 592],
        [1018, 592],
      ],
      label: "SQL",
      lx: 990,
      ly: 584,
    },
    {
      id: "answer_naive",
      from: "text_to_sql",
      to: "ui",
      lane: "naive",
      pts: [
        [850, 628],
        [850, 716],
        [80, 716],
        [80, 462],
      ],
      label: "answer",
      lx: 340,
      ly: 708,
      halo: 1,
    },
    // Oracle tier
    {
      id: "stub_ontology",
      from: "ontology",
      to: "bus",
      lane: "plane",
      pts: STUB.ontology,
      noArrow: 1,
    },
    {
      id: "stub_semantic",
      from: "semantic_layer",
      to: "bus",
      lane: "plane",
      pts: STUB.semantic_layer,
      noArrow: 1,
    },
    { id: "stub_raw", from: "raw_sql", to: "bus", lane: "naive", pts: STUB.raw_sql, noArrow: 1 },
    {
      id: "stub_vector",
      from: "vector",
      to: "bus",
      lane: "both",
      pts: STUB.vector,
      noArrow: 1,
      halo: 1,
    },
    {
      id: "bus",
      from: "bus",
      to: "bus",
      lane: "both",
      pts: [
        [BUS, 164],
        [BUS, 592],
      ],
      noArrow: 1,
    },
    {
      id: "read_tc",
      from: "bus",
      to: "true_cache",
      lane: "both",
      pts: [
        [BUS, 164],
        [1222, 164],
      ],
      kind: "tc",
    },
    {
      id: "read_primary",
      from: "bus",
      to: "primary",
      lane: "both",
      pts: [
        [BUS, 300],
        [1222, 300],
      ],
      kind: "direct",
    },
    {
      id: "tc_primary",
      from: "true_cache",
      to: "primary",
      lane: "both",
      pts: [
        [1317, 208],
        [1317, 262],
      ],
      label: "miss · redo apply",
      lx: 1325,
      ly: 239,
      anchor: "start",
      kind: "tc",
    },
    {
      id: "primary_dds",
      from: "primary",
      to: "dds",
      lane: "both",
      pts: [
        [1317, 382],
        [1317, 430],
      ],
      label: "per-identity rows",
      lx: 1325,
      ly: 410,
      anchor: "start",
    },
    {
      id: "dds_audit",
      from: "dds",
      to: "audit",
      lane: "both",
      pts: [
        [1317, 518],
        [1317, 566],
      ],
      label: "audit records",
      lx: 1325,
      ly: 546,
      anchor: "start",
    },
    {
      id: "w_memory",
      from: "memory",
      to: "primary",
      lane: "plane",
      pts: [
        [962, 50],
        [WBUS, 50],
        [WBUS, 360],
        [1222, 360],
      ],
      label: "writes",
      lx: 1100,
      ly: 42,
      halo: 1,
    },
    {
      id: "w_history",
      from: "history",
      to: "primary",
      lane: "naive",
      pts: [
        [475, 628],
        [475, 676],
        [WBUS, 676],
        [WBUS, 368],
        [1222, 368],
      ],
      halo: 1,
    },
  ];
  const EDGE = Object.fromEntries(E.map((e) => [e.id, e]));
  const d = (pts) => "M" + pts.map((p) => p.join(" ")).join(" L");
  function el(tag, attrs, parent) {
    const n = document.createElementNS(NS, tag);
    for (const [k, v] of Object.entries(attrs || {}))
      if (v !== undefined && v !== null) n.setAttribute(k, v);
    if (parent) parent.append(n);
    return n;
  }
  function fit(text, px, width) {
    const max = Math.max(4, Math.floor(width / (px * 0.56)));
    text = String(text ?? "");
    return text.length > max ? text.slice(0, max - 1) + "…" : text;
  }

  let root,
    svg,
    tip,
    detailsEl,
    summaryEl,
    replayBtn,
    G = {},
    state = {
      health: null,
      turn: { plane: null, naive: null },
      selected: null,
      timers: [],
      tc: false,
      privateAi: false,
    };

  function marker(id, color) {
    const m = el("marker", {
      id,
      viewBox: "0 0 10 10",
      refX: 9,
      refY: 5,
      markerWidth: 7,
      markerHeight: 7,
      orient: "auto-start-reverse",
      markerUnits: "userSpaceOnUse",
    });
    el("path", { d: "M0 0 L10 5 L0 10 z", fill: color }, m);
    return m;
  }

  function build() {
    svg = el("svg", {
      viewBox: `0 0 ${W} ${H}`,
      role: "img",
      "aria-label":
        "Reference architecture: the plane agent routes a question through a control guard, semantic cache, agent memory, model router, ontology and semantic layer to a governed answer; the naive agent appends history and writes its own SQL. Both share the model and Oracle AI Database, where reads go through True Cache when it runs, Deep Data Security filters rows per desk and Unified Auditing records each request.",
    });
    const defs = el("defs", {}, svg);
    for (const [id, c] of [
      ["arch-a", "#a9b2a6"],
      ["arch-a-plane", "#006b47"],
      ["arch-a-naive", "#bf714d"],
      ["arch-a-both", "#162925"],
      ["arch-a-off", "#c3c9bf"],
    ])
      defs.append(marker(id, c));
    const bands = el("g", {}, svg);
    el("rect", { class: "band plane", x: 380, y: 4, width: 798, height: 332, rx: 10 }, bands);
    el("text", { class: "band-label plane", x: 394, y: 24 }, bands).textContent =
      "PLANE AGENT · KNOWLEDGE + MEMORY + CONTROL";
    el("rect", { class: "band shared", x: 380, y: 346, width: 798, height: 140, rx: 10 }, bands);
    el("text", { class: "band-label", x: 394, y: 368 }, bands).textContent = "SHARED · SAME MODEL";
    el("rect", { class: "band naive", x: 380, y: 500, width: 798, height: 236, rx: 10 }, bands);
    el("text", { class: "band-label naive", x: 394, y: 521 }, bands).textContent =
      "NAIVE AGENT · RAW SCHEMA + HISTORY";
    el("rect", { class: "db-box", x: 1212, y: 76, width: 210, height: 590, rx: 10 }, bands);
    el("text", { class: "db-title", x: 1222, y: 96 }, bands).textContent =
      "ORACLE AI DATABASE 26ai";
    G.halos = el("g", {}, svg);
    G.edges = el("g", {}, svg);
    G.overlays = el("g", {}, svg);
    G.labels = el("g", {}, svg);
    G.nodes = el("g", {}, svg);
    G.pulses = el("g", {}, svg);
    for (const e of E) {
      if (e.halo) el("path", { class: "edge-halo", d: d(e.pts) }, G.halos);
      e.el = el(
        "path",
        {
          class: "edge",
          d: d(e.pts),
          "marker-end": e.noArrow ? null : "url(#arch-a)",
          "marker-start": e.bidir ? "url(#arch-a)" : null,
        },
        G.edges
      );
      if (e.label) {
        e.labelEl = el(
          "text",
          { class: "edge-label", x: e.lx, y: e.ly, "text-anchor": e.anchor || "middle" },
          G.labels
        );
        e.labelEl.textContent = e.label;
      }
    }
    G.busLabel = el(
      "text",
      {
        class: "edge-label",
        x: 0,
        y: 0,
        "text-anchor": "middle",
        transform: `translate(${BUS + 8} 380) rotate(-90)`,
      },
      G.labels
    );
    for (const [id, n] of Object.entries(N)) {
      const g = el(
        "g",
        {
          class: "node",
          "data-id": id,
          tabindex: 0,
          role: "button",
          "aria-label": `${n.title}: ${n.role}`,
        },
        G.nodes
      );
      el(
        "rect",
        { class: "focus", x: n.x - 4, y: n.y - 4, width: n.w + 8, height: n.h + 8, rx: 10 },
        g
      );
      el("rect", { class: "box", x: n.x, y: n.y, width: n.w, height: n.h, rx: 8 }, g);
      el(
        "rect",
        {
          class: "stripe plane",
          x: n.x,
          y: n.y + 8,
          width: 4,
          height: SHARED.has(id) ? (n.h - 16) / 2 : n.h - 16,
          rx: 2,
        },
        g
      );
      el(
        "rect",
        {
          class: "stripe naive",
          x: n.x,
          y: SHARED.has(id) ? n.y + 8 + (n.h - 16) / 2 : n.y + 8,
          width: 4,
          height: SHARED.has(id) ? (n.h - 16) / 2 : n.h - 16,
          rx: 2,
        },
        g
      );
      el("text", { class: "title", x: n.x + 14, y: n.y + 24 }, g).textContent = n.title;
      n.subEl = el("text", { class: "sub", x: n.x + 14, y: n.y + 42 }, g);
      n.subEl.textContent = n.sub;
      n.badge = el("g", { class: "badge", visibility: "hidden" }, g);
      n.badgeRect = el("rect", { x: n.x + n.w - 70, y: n.y + 8, width: 62, height: 16 }, n.badge);
      n.badgeText = el(
        "text",
        { x: n.x + n.w - 39, y: n.y + 20, "text-anchor": "middle" },
        n.badge
      );
      n.steps = [];
      const lines = SHARED.has(id) ? 2 : id === "api" ? 0 : 1;
      for (let i = 0; i < lines; i++) {
        const y = n.y + 61 + i * 17;
        const dot = el(
          "circle",
          { class: "dot", cx: n.x + 18, cy: y - 4, r: 3.5, visibility: "hidden" },
          g
        );
        const t = el("text", { class: "step", x: n.x + 27, y }, g);
        n.steps.push({ dot, t });
      }
      n.g = g;
      g.addEventListener("mouseenter", (ev) => showTip(id, ev));
      g.addEventListener("mousemove", (ev) => moveTip(ev));
      g.addEventListener("mouseleave", hideTip);
      g.addEventListener("click", () => {
        select(id);
        if (window.matchMedia && matchMedia("(hover: none)").matches) hideTip();
      });
      g.addEventListener("keydown", (ev) => {
        if (ev.key === "Enter" || ev.key === " ") {
          ev.preventDefault();
          select(id);
        }
      });
      g.addEventListener("focus", () => {
        const r = g.getBoundingClientRect();
        showTip(id, { clientX: r.left + r.width / 2, clientY: r.bottom });
      });
      g.addEventListener("blur", hideTip);
    }
    N.llm.subBadge = el(
      "rect",
      {
        class: "",
        x: N.llm.x + 10,
        y: N.llm.y + 30,
        width: N.llm.w - 20,
        height: 17,
        rx: 3,
        fill: "none",
      },
      N.llm.g
    );
    N.llm.g.insertBefore(N.llm.subBadge, N.llm.subEl);
  }

  // ---- Health: not-running components are drawn dashed and never as active; reads route around a stopped True Cache ----
  function applyHealth() {
    const comps = Object.fromEntries((state.health?.components || []).map((c) => [c.component, c]));
    state.tc = comps.true_cache?.state === "running";
    state.privateAi = comps.private_ai?.state === "running";
    for (const [id, n] of Object.entries(N)) {
      const c = n.component && comps[n.component];
      const off = c && c.state !== "running";
      n.g.classList.toggle("off", !!off);
      n.off = !!off;
      n.offState = c?.state;
      n.detail = c?.detail;
      if (off && !n.turnBadge)
        setBadge(
          n,
          c.state === "failed" ? "error" : "off",
          c.state === "failed" ? "FAILED" : "NOT RUNNING"
        );
      else if (!off && !n.turnBadge) setBadge(n, null);
    }
    N.llm.subEl.textContent = state.privateAi ? "Private AI · running" : "Private AI · not running";
    N.llm.subBadge.setAttribute("class", state.privateAi ? "subbadge-on" : "");
    N.llm.subBadge.setAttribute("fill", state.privateAi ? "#e7efdf" : "#eceee7");
    N.llm.subBadge.setAttribute("stroke", state.privateAi ? "#006b47" : "#9aa497");
    N.llm.subBadge.setAttribute("stroke-dasharray", state.privateAi ? "" : "3 2");
    N.llm.subEl.setAttribute("x", N.llm.x + 18);
    for (const e of E) {
      if (e.kind === "tc") e.inactive = !state.tc;
      if (e.kind === "direct") e.inactive = state.tc;
    }
    G.busLabel.textContent = state.tc ? "reads → True Cache" : "reads → primary";
    paintEdges();
  }
  // Badges straddle the node's top border so they never cover the title.
  function setBadge(n, kind, text) {
    if (!kind) {
      n.badge.setAttribute("visibility", "hidden");
      return;
    }
    n.badge.setAttribute("class", "badge " + kind);
    n.badgeText.textContent = text;
    const w = Math.max(34, text.length * 6.4 + 12);
    n.badgeRect.setAttribute("width", w);
    n.badgeRect.setAttribute("x", n.x + n.w - w - 10);
    n.badgeRect.setAttribute("y", n.y - 8);
    n.badgeText.setAttribute("x", n.x + n.w - 10 - w / 2);
    n.badgeText.setAttribute("y", n.y + 3.5);
    n.badge.setAttribute("visibility", "visible");
  }
  // Trim to the measured width when the SVG is laid out; fall back to a character estimate when hidden.
  function fitText(t, full, width) {
    t.textContent = full;
    let len;
    try {
      len = t.getComputedTextLength();
    } catch (e) {
      len = 0;
    }
    if (!len) {
      t.textContent = fit(full, 11.5, width);
      return;
    }
    if (len <= width) return;
    let lo = 1,
      hi = full.length;
    while (lo < hi) {
      const mid = Math.ceil((lo + hi) / 2);
      t.textContent = full.slice(0, mid) + "…";
      if (t.getComputedTextLength() <= width) lo = mid;
      else hi = mid - 1;
    }
    t.textContent = full.slice(0, lo) + "…";
  }

  // ---- Turn model: which nodes and edges each lane touched, in order ----
  function laneModel(result, lane) {
    const m = { visited: new Map(), order: new Map(), edges: [], overlays: [], steps: new Map() };
    if (!result || !Array.isArray(result.path)) return m;
    const path = result.path;
    path.forEach((s, i) => {
      if (!N[s.id]) return;
      if (!m.order.has(s.id)) m.order.set(s.id, i);
      if (!m.steps.has(s.id)) m.steps.set(s.id, []);
      m.steps.get(s.id).push(s);
      if (s.state !== "skipped") m.visited.set(s.id, true);
    });
    const st = (id) => (m.steps.get(id) || [])[0]?.state;
    const has = (id) => m.visited.has(id);
    const at = (id) => (m.order.has(id) ? m.order.get(id) : 99);
    if (has("ui") || path.length) {
      m.visited.set("api", true);
      m.order.set("api", m.order.has("ui") ? m.order.get("ui") + 0.5 : -0.5);
    }
    const routed = has("router") && st("router") !== "skipped";
    if (lane === "plane" && routed && !m.visited.has("llm")) {
      m.visited.set("llm", "implied");
      m.order.set("llm", at("router") + 0.1);
    }
    const add = (id, when) => {
      if (when && EDGE[id])
        m.edges.push({
          id,
          order: Math.max(
            at(EDGE[id].from === "bus" ? EDGE[id].to : EDGE[id].from),
            at(EDGE[id].to === "bus" ? EDGE[id].from : EDGE[id].to)
          ),
        });
    };
    add("ui_api", has("ui"));
    if (lane === "plane") {
      add("api_guard", has("guard"));
      add("guard_cache", has("semantic_cache") && st("guard") !== "refused");
      add("guard_render", st("guard") === "refused" && has("render"));
      add("cache_router", st("semantic_cache") === "miss" && routed);
      add("cache_render", st("semantic_cache") === "hit");
      add("memory_router", has("memory") && routed);
      add("router_ontology", routed && has("ontology"));
      add("router_llm", routed);
      add("ontology_semantic", has("ontology") && has("semantic_layer"));
      add("semantic_render", has("semantic_layer") && has("render"));
      add("vector_rerank", has("vector") && has("rerank"));
      add("rerank_llm", has("rerank") && m.visited.get("llm") === true);
      add("answer_plane", has("render") || (has("guard") && st("guard") === "refused"));
      add("w_memory", has("memory") && has("primary"));
    } else {
      add("api_history", has("history"));
      add("history_t2s", has("history") && has("text_to_sql"));
      add("t2s_llm", has("text_to_sql") && has("llm"));
      add("t2s_raw", has("text_to_sql") && has("raw_sql"));
      add("answer_naive", has("llm") || has("text_to_sql"));
      add("w_history", has("history") && has("primary"));
    }
    const dest = has("true_cache") ? "true_cache" : has("primary") ? "primary" : null;
    for (const [reader, who] of Object.entries(READERS)) {
      if (!(who === "both" || who === lane) || !has(reader) || !dest) continue;
      const off = lane === "plane" ? -2 : 2;
      const stub = STUB[reader].map((p) => p.slice());
      stub[stub.length - 1][0] = BUS + off;
      const tail =
        dest === "true_cache"
          ? [
              [BUS + off, 164],
              [1222, 164],
            ]
          : [
              [BUS + off, 300],
              [1222, 300],
            ];
      const ry = stub[stub.length - 1][1];
      const pts = stub.concat(ry === tail[0][1] ? [tail[1]] : tail);
      m.overlays.push({ pts, order: Math.max(at(reader), at(dest)), to: dest });
    }
    add("tc_primary", has("true_cache") && has("primary"));
    add("primary_dds", has("primary") && has("dds"));
    add("dds_audit", has("dds") && has("audit"));
    m.edges.sort((a, b) => a.order - b.order);
    return m;
  }

  function clearTimers() {
    state.timers.forEach((t) => clearTimeout(t));
    state.timers = [];
    G.pulses.replaceChildren();
  }
  function paintEdges(models) {
    const lit = new Map();
    if (models)
      for (const lane of ["plane", "naive"])
        for (const x of models[lane].edges.filter((x) => x.shown)) {
          lit.set(x.id, lit.has(x.id) && lit.get(x.id) !== lane ? "both" : lane);
        }
    const turnShown = !!models;
    for (const e of E) {
      const on = lit.get(e.id);
      const cls = ["edge"];
      if (on) cls.push("on-" + on);
      else {
        if (e.inactive) cls.push("inactive");
        if (turnShown) cls.push("faded");
      }
      e.el.setAttribute("class", cls.join(" "));
      const mk = on ? "url(#arch-a-" + on + ")" : e.inactive ? "url(#arch-a-off)" : "url(#arch-a)";
      if (!e.noArrow) e.el.setAttribute("marker-end", mk);
      if (e.bidir) e.el.setAttribute("marker-start", mk);
      if (e.labelEl)
        e.labelEl.setAttribute("class", "edge-label" + (turnShown && !on ? " faded" : ""));
    }
  }
  function paintNodes(models, visibleUpTo) {
    const turnShown = !!models;
    for (const [id, n] of Object.entries(N)) {
      const vp =
        models &&
        models.plane.visited.has(id) &&
        (visibleUpTo ? visibleUpTo.plane >= (models.plane.order.get(id) ?? 99) : true);
      const vn =
        models &&
        models.naive.visited.has(id) &&
        (visibleUpTo ? visibleUpTo.naive >= (models.naive.order.get(id) ?? 99) : true);
      n.g.classList.toggle("v-plane", !!vp);
      n.g.classList.toggle("v-naive", !!vn);
      n.g.classList.toggle("faded", turnShown && !vp && !vn && !n.off);
    }
  }
  function stepText(steps, lane, id) {
    if (!steps || !steps.length) return null;
    const parts = [];
    let ms = 0;
    for (const s of steps) {
      if (s.label) parts.push(s.label);
      else if (s.state && s.state !== "ok") parts.push(s.state);
      if (typeof s.ms === "number") ms += s.ms;
    }
    let t = parts.join(" → ") || "visited";
    if (ms) t += ` · ${ms >= 1000 ? (ms / 1000).toFixed(1) + " s" : Math.round(ms) + " ms"}`;
    return t;
  }
  function writeSteps(models) {
    for (const [id, n] of Object.entries(N)) {
      const rows = [];
      const plane = models?.plane.steps.get(id),
        naive = models?.naive.steps.get(id);
      const pt =
        stepText(plane, "plane", id) ||
        (models?.plane.visited.get(id) === "implied" ? "routing call" : null);
      if (id === "ui") {
        const q = (state.turn.plane || state.turn.naive)?.question;
        if (q) rows.push({ lane: null, text: "“" + q + "”", muted: true });
      } else if (SHARED.has(id)) {
        if (pt) rows.push({ lane: "plane", text: pt });
        const nt = stepText(naive, "naive", id);
        if (nt) rows.push({ lane: "naive", text: nt });
      } else if (n.lane === "plane") {
        if (pt) rows.push({ lane: "plane", text: pt });
      } else if (n.lane === "naive") {
        const nt = stepText(naive, "naive", id);
        if (nt) rows.push({ lane: "naive", text: nt });
      }
      n.steps.forEach((s, i) => {
        const r = rows[i];
        if (!r || !r.text) {
          s.t.textContent = "";
          s.dot.setAttribute("visibility", "hidden");
          return;
        }
        const width = n.w - (r.lane ? 36 : 26);
        s.t.setAttribute("x", n.x + (r.lane ? 27 : 14));
        s.t.setAttribute("class", "step" + (r.muted ? " muted" : ""));
        fitText(s.t, r.text, width);
        const title = el("title", {}, s.t);
        title.textContent = r.text;
        if (r.lane) {
          s.dot.setAttribute("class", "dot " + r.lane);
          s.dot.setAttribute("visibility", "visible");
        } else s.dot.setAttribute("visibility", "hidden");
      });
      // State badges from the turn (cache hit, refusal, skip, error) take precedence over health badges.
      const states = [...(plane || []), ...(naive || [])].map((s) => s.state);
      const pick = ["refused", "blocked", "error", "hit", "miss", "skipped"].find((k) =>
        states.includes(k)
      );
      n.turnBadge = !!pick;
      if (pick) setBadge(n, pick, pick.toUpperCase());
      else if (n.off)
        setBadge(
          n,
          n.offState === "failed" ? "error" : "off",
          n.offState === "failed" ? "FAILED" : "NOT RUNNING"
        );
      else setBadge(n, null);
    }
  }

  // ---- Animation: a pulse runs along each traversed edge in path order, both lanes at once ----
  function pulse(pathEl, lane, dur) {
    const len = pathEl.getTotalLength();
    if (!len) return;
    const dot = el("circle", { class: "pulse " + lane, r: 5 }, G.pulses);
    const t0 = performance.now();
    const tick = (now) => {
      const k = Math.min(1, (now - t0) / dur);
      const p = pathEl.getPointAtLength(len * k);
      dot.setAttribute("cx", p.x);
      dot.setAttribute("cy", p.y);
      if (k < 1) requestAnimationFrame(tick);
      else dot.remove();
    };
    requestAnimationFrame(tick);
  }
  function render(animate) {
    clearTimers();
    G.overlays.replaceChildren();
    const has = state.turn.plane || state.turn.naive;
    if (!has) {
      paintEdges();
      paintNodes();
      writeSteps();
      summary();
      return;
    }
    const models = {
      plane: laneModel(state.turn.plane, "plane"),
      naive: laneModel(state.turn.naive, "naive"),
    };
    state.models = models;
    writeSteps(models);
    summary();
    const overlays = { plane: [], naive: [] };
    for (const lane of ["plane", "naive"])
      for (const o of models[lane].overlays) {
        o.el = el(
          "path",
          {
            class: "overlay " + lane,
            d: d(o.pts),
            "marker-end": `url(#arch-a-${lane})`,
            visibility: "hidden",
          },
          G.overlays
        );
        overlays[lane].push(o);
      }
    const reveal = (lane, item) => {
      if (item.el) item.el.setAttribute("visibility", "visible");
      else item.shown = true;
    };
    if (!animate || RM()) {
      for (const lane of ["plane", "naive"]) {
        models[lane].edges.forEach((x) => (x.shown = true));
        overlays[lane].forEach((o) => reveal(lane, o));
      }
      paintEdges(models);
      paintNodes(models);
      return;
    }
    const step = 380,
      upTo = { plane: -1, naive: -1 };
    paintEdges(models);
    paintNodes(models, upTo);
    for (const lane of ["plane", "naive"]) {
      const seq = [
        ...models[lane].edges.map((x) => ({ kind: "edge", x, order: x.order })),
        ...overlays[lane].map((o) => ({ kind: "overlay", x: o, order: o.order })),
      ].sort((a, b) => a.order - b.order);
      upTo[lane] = 0.5;
      paintNodes(models, upTo);
      seq.forEach((s, i) =>
        state.timers.push(
          setTimeout(() => {
            if (s.kind === "edge") {
              s.x.shown = true;
              paintEdges(models);
              pulse(EDGE[s.x.id].el, lane, step * 0.9);
            } else {
              reveal(lane, s.x);
              pulse(s.x.el, lane, step * 0.9);
            }
            upTo[lane] = Math.max(upTo[lane], s.order);
            paintNodes(models, upTo);
          }, i * step)
        )
      );
      state.timers.push(
        setTimeout(() => {
          upTo[lane] = 99;
          paintNodes(models, upTo);
        }, seq.length * step)
      );
    }
  }

  // ---- Summary, tooltip, details ----
  function fmtMs(ms) {
    return ms >= 1000 ? (ms / 1000).toFixed(1) + " s" : Math.round(ms) + " ms";
  }
  function summary() {
    if (!summaryEl) return;
    const parts = ["plane", "naive"].map((lane) => {
      const r = state.turn[lane];
      if (!r) return "";
      const a = r.accuracy?.score;
      const acc =
        a === 1
          ? '<span class="ok">✓ correct</span>'
          : a === 0
            ? '<span class="no">✗ wrong</span>'
            : "unscored";
      return `<div class="arch-lane-summary ${lane}"><i></i><b>${lane === "plane" ? "Plane" : "Naive"}</b>${esc(r.model || "")} · ${(r.usage?.total_tokens ?? 0).toLocaleString()} tokens · ${fmtMs(r.latency?.total_ms || 0)} · ${acc}</div>`;
    });
    summaryEl.innerHTML =
      parts.join("") ||
      '<span class="arch-lane-summary">Ask a question to trace both lanes through the architecture.</span>';
    if (replayBtn) replayBtn.disabled = !(state.turn.plane || state.turn.naive);
  }
  function showTip(id, ev) {
    const n = N[id];
    tip.innerHTML = `<b>${esc(n.title)}</b>${esc(n.role)}<em>${esc(n.feature)}</em>${n.off ? "<em>Status: " + esc(n.offState) + "</em>" : ""}`;
    tip.hidden = false;
    moveTip(ev);
  }
  function moveTip(ev) {
    if (tip.hidden) return;
    const x = Math.min(ev.clientX + 14, innerWidth - tip.offsetWidth - 8),
      y = Math.min(ev.clientY + 14, innerHeight - tip.offsetHeight - 8);
    tip.style.left = x + "px";
    tip.style.top = y + "px";
  }
  function hideTip() {
    tip.hidden = true;
  }
  function select(id) {
    state.selected = id;
    for (const [k, n] of Object.entries(N)) n.g.classList.toggle("selected", k === id);
    details();
  }
  function details() {
    const id = state.selected;
    if (!id) {
      detailsEl.innerHTML =
        '<p class="hint">Select a component (click, or Tab then Enter) to see its role, the Oracle feature behind it and what each agent did there on the last turn.</p>';
      return;
    }
    const n = N[id];
    const lane = (key) => {
      const steps = state.models?.[key]?.steps.get(id);
      const implied = state.models?.[key]?.visited.get(id) === "implied";
      const body =
        steps && steps.length
          ? steps
              .map(
                (s) =>
                  `<p>${esc(s.label || s.id)}<span class="state ${esc(s.state || "")}">${esc((s.state || "").toUpperCase())}</span>${typeof s.ms === "number" ? " · " + fmtMs(s.ms) : ""}${s.detail ? '<br><span class="hint">' + esc(typeof s.detail === "string" ? s.detail : JSON.stringify(s.detail)) + "</span>" : ""}</p>`
              )
              .join("")
          : implied
            ? "<p>Routing call from the model router</p>"
            : '<p class="none">Not used on the last turn.</p>';
      return `<div class="lane ${key}"><b>${key === "plane" ? "Plane agent" : "Naive agent"}</b>${body}</div>`;
    };
    detailsEl.innerHTML = `<h4>${esc(n.title)}</h4><p class="role">${esc(n.role)}</p><p class="feature"><b>Oracle / implementation:</b> ${esc(n.feature)}${n.off ? " · <b>status:</b> " + esc(n.offState) + (n.detail ? " — " + esc(n.detail) : "") : ""}</p><div class="lanes">${lane("plane")}${lane("naive")}</div>`;
  }

  window.Architecture = {
    mount(container, health) {
      root = document.createElement("div");
      root.className = "arch";
      root.innerHTML =
        '<div class="arch-head"><div class="arch-summary"></div><div class="arch-actions"><button type="button" class="arch-replay" disabled>↻ Replay last turn</button></div></div><figure><div class="arch-scroll"></div><figcaption></figcaption></figure><div class="arch-legend"><span class="lg-plane"><i></i>Plane lane</span><span class="lg-naive"><i></i>Naive lane</span><span class="lg-shared"><i></i>Shared: both lanes</span><span class="lg-off"><i></i>Not running</span><span class="lg-hit"><i></i>Cache hit</span></div><div class="arch-details" aria-live="polite"></div>';
      container.replaceChildren(root);
      summaryEl = root.querySelector(".arch-summary");
      replayBtn = root.querySelector(".arch-replay");
      detailsEl = root.querySelector(".arch-details");
      root.querySelector("figcaption").textContent =
        "Hover a component for what it is; click it for the last turn’s data. After each question both lanes light up in the order they ran: the plane resolves entities and firm definitions before answering, the naive agent carries its whole history into the model. Dashed parts are not running.";
      build();
      root.querySelector(".arch-scroll").append(svg);
      tip = document.createElement("div");
      tip.className = "arch-tip";
      tip.hidden = true;
      document.body.append(tip);
      replayBtn.addEventListener("click", () => render(true));
      state.health = health || null;
      applyHealth();
      render(false);
      details();
      requestAnimationFrame(() => {
        for (const n of Object.values(N)) if (n !== N.llm) fitText(n.subEl, n.sub, n.w - 16);
      });
      return this;
    },
    update(health) {
      if (!svg) return;
      state.health = health || state.health;
      applyHealth();
      if (state.turn.plane || state.turn.naive) {
        render(false);
      }
      details();
    },
    showTurn(planeResult, naiveResult) {
      if (!svg) return;
      if (planeResult !== undefined) state.turn.plane = planeResult;
      if (naiveResult !== undefined) state.turn.naive = naiveResult;
      render(true);
      details();
    },
  };
})();
