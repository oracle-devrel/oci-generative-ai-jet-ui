// Layer X-ray: what the ontology and semantic layer changed for one plane answer.
// window.XRay.render(el, planeResult, naiveResult) — safe to call repeatedly; redraws on resize.
(() => {
  const C = {
    plane: "#006b47",
    planeWash: "rgba(0,107,71,0.08)",
    naive: "#bf714d",
    ink: "#162925",
    muted: "#6b7771",
    grid: "#e3e7dc",
    edge: "#aab4ad",
    step: "#8f9a93",
    delta: "#c3c9c2",
    alt: "#7d8781",
    surface: "#fffefa",
    hollow: "#8a958e",
  };
  const MINUS = "−";
  const esc = (v) =>
    String(v ?? "").replace(
      /[&<>"']/g,
      (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]
    );
  const ok = (v) => typeof v === "number" && isFinite(v);
  function money(v, sign) {
    if (!ok(v)) return "—";
    const a = Math.abs(v);
    const s =
      a >= 1e9
        ? "$" + (a / 1e9).toFixed(2) + "bn"
        : a >= 1e6
          ? "$" + (a / 1e6).toFixed(2) + "m"
          : a >= 1e3
            ? "$" + (a / 1e3).toFixed(1) + "k"
            : "$" + a.toFixed(0);
    return (v < 0 ? MINUS : sign && v > 0 ? "+" : "") + s;
  }
  function full(v) {
    if (!ok(v)) return "—";
    return (
      (v < 0 ? MINUS : "") +
      "$" +
      Math.abs(v).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })
    );
  }
  function fmt(v, unit, sign) {
    if (!ok(v)) return "—";
    if (unit === "percent")
      return (v < 0 ? MINUS : sign && v > 0 ? "+" : "") + Math.abs(v).toFixed(2) + "%";
    if (unit === "days") return v.toFixed(2) + " days";
    return money(v, sign);
  }
  function fmtFull(v, unit) {
    if (!ok(v)) return "—";
    if (unit === "percent") return v.toFixed(4) + "%";
    if (unit === "days") return v.toFixed(3) + " days";
    return full(v);
  }
  const ctx = document.createElement("canvas").getContext("2d");
  function textW(t, font) {
    ctx.font = font;
    return ctx.measureText(t).width;
  }
  function fit(t, font, max) {
    t = String(t);
    if (max <= 12) return "";
    if (textW(t, font) <= max) return t;
    let lo = 0,
      hi = t.length;
    while (lo < hi) {
      const m = (lo + hi + 1) >> 1;
      if (textW(t.slice(0, m) + "…", font) <= max) lo = m;
      else hi = m - 1;
    }
    return t.slice(0, lo).trimEnd() + "…";
  }
  const tip = (title, rows) =>
    "<b>" + esc(title) + "</b>" + rows.map((r) => "<br>" + esc(r)).join("");

  // Depth-first order so every child sits directly under its parent.
  function ordered(entities) {
    const by = {},
      kids = {},
      roots = [];
    entities.forEach((e) => {
      by[e.lei] = e;
    });
    entities.forEach((e) => {
      if (e.parent_lei && by[e.parent_lei]) (kids[e.parent_lei] = kids[e.parent_lei] || []).push(e);
      else roots.push(e);
    });
    const out = [];
    const walk = (e, d) => {
      out.push(Object.assign({}, e, { _d: d }));
      (kids[e.lei] || []).forEach((k) => walk(k, d + 1));
    };
    roots.sort((a, b) => (a.depth || 0) - (b.depth || 0)).forEach((r) => walk(r, 0));
    return out;
  }

  function drawTree(x, lens, width, fam) {
    const ents = ordered(x.ontology.entities || []);
    if (!ents.length) return '<p class="xray-muted">No legal entities resolved.</p>';
    const narrow = width < 430,
      indent = 24,
      gap = 20,
      boxH = narrow ? 60 : 46,
      pos = {};
    let y = 2;
    ents.forEach((e) => {
      const bx = 2 + e._d * indent;
      pos[e.lei] = { bx, by: y, bw: width - bx - 2 };
      y += boxH + gap;
    });
    const h = y - gap + 4;
    const F = (size, weight) => `${weight || 400} ${size}px ${fam}`;
    let s = `<svg class="xray-svg" width="${width}" height="${h}" viewBox="0 0 ${width} ${h}" role="img" aria-label="Legal entity tree for ${esc(x.group)}">`;
    ents.forEach((e) => {
      const p = pos[e.parent_lei];
      if (!p) return;
      const c = pos[e.lei],
        tx = p.bx + 12,
        missed = lens === "string" && !e.name_match;
      s += `<path d="M${tx} ${p.by + boxH} V${c.by + boxH / 2} H${c.bx}" fill="none" stroke="${C.edge}" stroke-width="1"${missed ? ' stroke-dasharray="4 3"' : ""}/>`;
      s += `<text x="${tx + 8}" y="${c.by - 6}" class="xray-edge">${esc(fit(e.relationship || "", F(9), c.bw - 12))}</text>`;
    });
    ents.forEach((e) => {
      const { bx, by, bw } = pos[e.lei],
        missed = lens === "string" && !e.name_match;
      const rows = [
        `LEI ${e.lei}`,
        `Depth ${e._d} · ${e._d ? e.relationship : "root of the group"}`,
        `${e.positions} positions on this desk`,
        `Gross ${full(e.gross_usd)}`,
        `Signed ${full(e.signed_usd)}`,
        `Net ${full(e.net_usd)}`,
        `Found by name match: ${e.name_match ? "yes" : "no"}`,
      ];
      s += `<g class="xray-node${missed ? " missed" : ""}" tabindex="0" data-xtip="${esc(tip(e.name, rows))}">`;
      if (missed)
        s += `<rect x="${bx + 0.5}" y="${by + 0.5}" width="${bw - 1}" height="${boxH - 1}" rx="6" fill="${C.surface}" stroke="${C.hollow}" stroke-dasharray="4 3"/>`;
      else
        s += `<rect x="${bx}" y="${by}" width="${bw}" height="${boxH}" rx="6" fill="${C.planeWash}"/><path d="M${bx + 4} ${by} V${by + boxH} H${bx + 4} Q${bx} ${by + boxH} ${bx} ${by + boxH - 4} V${by + 4} Q${bx} ${by} ${bx + 4} ${by} Z" fill="${C.plane}"/>`;
      const right = narrow ? 0 : 170,
        nameMax = bw - 14 - right - 8;
      s += `<text x="${bx + 14}" y="${by + 18}" class="xray-name">${esc(fit(e.name, F(12, 600), nameMax))}</text>`;
      const line2 = (e._d ? "" : "ROOT · ") + e.lei + " · " + e.positions + " positions";
      s += `<text x="${bx + 14}" y="${by + 34}" class="xray-sub">${esc(fit(line2, F(10), bw - 14 - right - 8))}</text>`;
      if (narrow) {
        const l3 = missed
          ? `✗ missed by name match · ${money(e.net_usd)} net`
          : `${money(e.net_usd)} net exposure`;
        s += `<text x="${bx + 14}" y="${by + 50}" class="${missed ? "xray-callout" : "xray-val-sm"}">${esc(fit(l3, F(11, 600), bw - 24))}</text>`;
      } else if (missed) {
        s += `<text x="${bx + bw - 12}" y="${by + 19}" text-anchor="end" class="xray-callout">✗ missed by name match</text><text x="${bx + bw - 12}" y="${by + 34}" text-anchor="end" class="xray-sub">${esc(money(e.net_usd))} net not counted</text>`;
      } else {
        s += `<text x="${bx + bw - 12}" y="${by + 20}" text-anchor="end" class="xray-val">${esc(money(e.net_usd))}</text><text x="${bx + bw - 12}" y="${by + 34}" text-anchor="end" class="xray-sub">net exposure</text>`;
      }
      s += "</g>";
    });
    return s + "</svg>";
  }

  function niceTicks(lo, hi, n) {
    const span = hi - lo || 1,
      raw = span / n,
      mag = Math.pow(10, Math.floor(Math.log10(raw)));
    const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((st) => st >= raw);
    const a = Math.floor(lo / step) * step,
      b = Math.ceil(hi / step) * step,
      t = [];
    for (let v = a; v <= b + step / 2; v += step) t.push(+v.toFixed(10));
    return t;
  }
  function barPath(xa, xb, y, h, roundLeft) {
    const x1 = Math.min(xa, xb),
      x2 = Math.max(xa, xb),
      r = Math.min(4, (x2 - x1) / 2, h / 2);
    return roundLeft
      ? `M${x2} ${y} H${x1 + r} Q${x1} ${y} ${x1} ${y + r} V${y + h - r} Q${x1} ${y + h} ${x1 + r} ${y + h} H${x2} Z`
      : `M${x1} ${y} H${x2 - r} Q${x2} ${y} ${x2} ${y + r} V${y + h - r} Q${x2} ${y + h} ${x2 - r} ${y + h} H${x1} Z`;
  }

  function semanticsModel(x, plane, naive) {
    const s = x.semantics;
    if (!s) return null;
    const unit = s.unit || "USD",
      isPct = unit === "percent",
      wf = s.waterfall || [];
    const total = wf.find((w) => w.total) || wf[wf.length - 1];
    const governed = total ? total.value : plane && plane.value;
    const nUnit = naive && (naive.unit || "none");
    const comparable = !!naive && ok(naive.value) && nUnit === unit;
    const alts = (s.alternatives || []).filter((a) => ok(a.value) && (a.unit || unit) === unit);
    return {
      s,
      unit,
      isPct,
      wf,
      governed,
      naive,
      comparable,
      alts,
      steps: !isPct && wf.length >= 2 ? wf : [],
    };
  }

  function drawSemantics(m, width, fam) {
    const narrow = width < 520,
      F = (size, weight) => `${weight || 400} ${size}px ${fam}`;
    const dots = [];
    if (!m.steps.length) dots.push({ label: "Governed (plane)", value: m.governed, kind: "plane" });
    if (m.comparable) dots.push({ label: "Naive answer", value: m.naive.value, kind: "naive" });
    m.alts.forEach((a) => dots.push({ label: a.label, value: a.value, kind: "alt" }));
    // Running totals for the waterfall rows.
    let run = 0;
    const rows = m.steps.map((w, i) => {
      let a, b, kind;
      if (w.total) {
        a = 0;
        b = w.value;
        kind = "total";
        run = w.value;
      } else if (i === 0) {
        a = 0;
        b = w.value;
        kind = "start";
        run = w.value;
      } else {
        a = run;
        b = run + w.value;
        kind = "delta";
        run = b;
      }
      return { label: w.label, value: w.value, a, b, kind };
    });
    const others = [
      ...rows.flatMap((r) => [r.a, r.b]),
      ...dots.filter((d) => d.kind !== "naive").map((d) => d.value),
      m.governed,
      0,
    ].filter(ok);
    const maxOther = Math.max(...others.map(Math.abs));
    let off = null;
    dots.forEach((d) => {
      if (d.kind === "naive" && Math.abs(d.value) > 3 * maxOther) off = d;
    });
    const vals = [...others, ...dots.filter((d) => d !== off).map((d) => d.value)];
    const ticks = niceTicks(Math.min(0, ...vals), Math.max(...vals), narrow ? 3 : 4),
      lo = ticks[0],
      hi = ticks[ticks.length - 1];
    const labelW = narrow ? 0 : Math.min(176, Math.round(width * 0.3)),
      x0 = narrow ? 4 : labelW + 12,
      x1 = width - (narrow ? 62 : 78);
    const sx = (v) => x0 + ((Math.max(lo, Math.min(hi, v)) - lo) / (hi - lo)) * (x1 - x0);
    const rowH = narrow ? 46 : 30,
      barH = 16,
      secH = 26;
    let y = 6;
    const items = [];
    rows.forEach((r) => {
      items.push({ type: "bar", r, y });
      y += rowH;
    });
    if (dots.length) {
      if (rows.length) {
        items.push({ type: "section", y });
        y += secH;
      }
      dots.forEach((d) => {
        items.push({ type: "dot", d, y });
        y += rowH + (d.kind === "naive" ? 14 : 0);
      });
    }
    const plotBottom = y,
      h = y + 22;
    let s = `<svg class="xray-svg" width="${width}" height="${h}" viewBox="0 0 ${width} ${h}" role="img" aria-label="How the governed ${esc(m.s.metric)} figure is built">`;
    ticks.forEach((t) => {
      const tx = sx(t);
      s += `<line x1="${tx}" y1="2" x2="${tx}" y2="${plotBottom}" stroke="${C.grid}" stroke-width="1"/><text x="${tx}" y="${plotBottom + 14}" text-anchor="middle" class="xray-tick">${esc(fmt(t, m.unit))}</text>`;
    });
    const labelAt = (text, yy) =>
      narrow
        ? `<text x="${x0}" y="${yy + 11}" class="xray-row-label">${esc(fit(text, F(11), width - 8))}</text>`
        : `<text x="0" y="${yy + barH / 2 + 4 + (rowH - barH) / 2 - 2}" class="xray-row-label">${esc(fit(text, F(11), labelW))}</text>`;
    const barY = (yy) => (narrow ? yy + 19 : yy + (rowH - barH) / 2);
    let prevEnd = null;
    items.forEach((it) => {
      if (it.type === "section") {
        s += `<text x="${narrow ? x0 : 0}" y="${it.y + 17}" class="xray-section">OTHER ANSWERS ON THE SAME SCALE</text>`;
        return;
      }
      const by = barY(it.y);
      if (it.type === "bar") {
        const r = it.r,
          fill = r.kind === "total" ? C.plane : r.kind === "delta" ? C.delta : C.step,
          neg = r.b < r.a;
        s += labelAt(r.label, it.y);
        if (prevEnd !== null)
          s += `<line x1="${sx(prevEnd.v)}" y1="${prevEnd.y}" x2="${sx(prevEnd.v)}" y2="${by}" stroke="${C.edge}" stroke-width="1"/>`;
        s += `<path d="${barPath(sx(r.a), sx(r.b), by, barH, neg)}" fill="${fill}"/>`;
        const end = sx(r.b),
          label = r.kind === "delta" ? fmt(r.value, m.unit, true) : fmt(r.b, m.unit);
        s += neg
          ? `<text x="${end - 6}" y="${by + 12}" text-anchor="end" class="xray-bar-val">${esc(label)}</text>`
          : `<text x="${end + 6}" y="${by + 12}" class="xray-bar-val${r.kind === "total" ? " strong" : ""}">${esc(label)}</text>`;
        s += `<rect x="0" y="${it.y}" width="${width}" height="${rowH}" fill="transparent" tabindex="0" data-xtip="${esc(tip(r.label, [fmtFull(r.value, m.unit) + (r.kind === "delta" ? " adjustment" : ""), r.kind === "total" ? "Approved definition result" : "Calculation step"]))}"/>`;
        prevEnd = { v: r.b, y: by + barH };
        return;
      }
      const d = it.d,
        cy = by + barH / 2,
        cx = d === off ? x1 : sx(d.value),
        color = d.kind === "plane" ? C.plane : d.kind === "naive" ? C.naive : C.alt;
      s += labelAt(d.label, it.y);
      s += `<line x1="${x0}" y1="${cy}" x2="${x1}" y2="${cy}" stroke="${C.grid}" stroke-width="1"/>`;
      if (d.kind === "naive" && d !== off && ok(m.governed)) {
        const g = sx(m.governed);
        if (Math.abs(g - cx) > 6) {
          const diff = d.value - m.governed,
            pctOff = m.governed ? (Math.abs(diff) / Math.abs(m.governed)) * 100 : 0;
          s += `<path d="M${g} ${cy + 11} V${cy + 15} H${cx} V${cy + 11}" fill="none" stroke="${C.ink}" stroke-width="1"/><text x="${(g + cx) / 2}" y="${cy + 27}" text-anchor="middle" class="xray-gap">${esc(fmt(diff, m.unit, true) + (m.unit === "percent" ? " pts" : " (" + pctOff.toFixed(0) + "%)"))}</text>`;
        }
      }
      s += `<circle cx="${cx}" cy="${cy}" r="${d.kind === "alt" ? 4.5 : 5.5}" fill="${color}" stroke="${C.surface}" stroke-width="2"/>`;
      const vl = d === off ? "→ " + fmt(d.value, m.unit) + " (off scale)" : fmt(d.value, m.unit);
      s +=
        cx + 8 + textW(vl, F(11, 600)) < width
          ? `<text x="${cx + 9}" y="${cy + 4}" class="xray-bar-val">${esc(vl)}</text>`
          : `<text x="${cx - 9}" y="${cy + 4}" text-anchor="end" class="xray-bar-val">${esc(vl)}</text>`;
      s += `<rect x="0" y="${it.y}" width="${width}" height="${rowH}" fill="transparent" tabindex="0" data-xtip="${esc(tip(d.label, [fmtFull(d.value, m.unit), d.kind === "naive" ? "Answer the naive agent returned" : d.kind === "plane" ? "Governed figure from approved SQL" : "Same data, different definition"]))}"/>`;
    });
    // Reference line at the governed figure, drawn last so it reads across rows.
    if (ok(m.governed) && m.steps.length)
      s += `<line x1="${sx(m.governed)}" y1="2" x2="${sx(m.governed)}" y2="${plotBottom}" stroke="${C.plane}" stroke-width="1.5"/>`;
    return s + "</svg>";
  }

  function formulaTiles(m) {
    if (!m.isPct && m.wf.length >= 2) return "";
    const tiles = m.wf
      .map((w, i) => {
        const unit = w.total ? m.unit : w.unit || "USD";
        return `<div class="xray-tile${w.total ? " total" : ""}"><span>${esc(w.label)}</span><b>${esc(w.total ? fmt(w.value, unit) : fmt(w.value, unit))}</b></div>`;
      })
      .join('<span class="xray-op" aria-hidden="true">→</span>');
    return `<div class="xray-formula">${tiles}</div>`;
  }

  function impactStrip(x, plane, naive, m) {
    const t = x.ontology.totals || {},
      g = t.graph || {},
      n = t.name_match || {};
    const missEnt = (g.entities || 0) - (n.entities || 0),
      missNet = (g.net_usd || 0) - (n.net_usd || 0);
    const chips = [];
    chips.push(
      `<div class="xray-chip"><span class="k">Ontology</span><b>${missEnt > 0 ? `+${missEnt} ${missEnt === 1 ? "entity" : "entities"} · ${esc(money(missNet, true))}` : "No gap"}</b><span class="s">${missEnt > 0 ? "found by the graph walk, missed by name match" : "name match finds every entity here"}</span></div>`
    );
    if (m) {
      let head, sub;
      const mids = m.wf.filter((w, i) => i > 0 && !w.total);
      if (m.isPct) {
        head =
          m.wf.length > 1
            ? esc(
                m.wf
                  .slice(1)
                  .filter((w) => !w.total)
                  .map((w) => w.label)
                  .join(" ") || "Ratio"
              )
            : "Ratio";
        sub = "firm ratio definition · v" + esc(m.s.version);
      } else if (mids.length) {
        const adj = mids.reduce((a, w) => a + w.value, 0);
        head = esc(money(adj, true));
        sub = esc(mids.map((w) => w.label.toLowerCase()).join(", ")) + " · v" + esc(m.s.version);
      } else {
        head = "As defined";
        sub = "no adjustment in this metric · v" + esc(m.s.version);
      }
      chips.push(
        `<div class="xray-chip"><span class="k">Semantics</span><b>${head}</b><span class="s">${sub}</span></div>`
      );
    }
    const verdict = (r, unit) => {
      const sc = r && r.accuracy ? r.accuracy.score : null;
      return sc === 1 ? "✓" : sc === 0 ? "✗" : "";
    };
    const pv = plane && ok(plane.value) ? plane.value : m && m.governed,
      unit = m ? m.unit : "USD";
    chips.push(
      `<div class="xray-chip"><span class="k"><i class="xray-key plane"></i>Plane answer</span><b>${verdict(plane)} ${esc(fmt(pv, unit))}</b><span class="s">${plane && plane.accuracy && plane.accuracy.score === 1 ? "correct against the golden answer" : plane && plane.accuracy && plane.accuracy.score === 0 ? "does not match the golden answer" : "unscored question"}</span></div>`
    );
    if (naive) {
      let head, sub;
      if (ok(naive.value) && m && m.comparable) {
        const diff = naive.value - m.governed;
        head = `${verdict(naive)} ${esc(fmt(naive.value, unit))}`;
        sub =
          Math.abs(diff) <= Math.max(1, Math.abs(m.governed) * 1e-6)
            ? "matches the governed figure"
            : `off by ${esc(fmt(diff, unit, true))}${unit === "percent" ? " pts" : ` (${((Math.abs(diff) / Math.abs(m.governed || 1)) * 100).toFixed(0)}%)`}`;
      } else if (ok(naive.value)) {
        head = `${verdict(naive)} ${esc(naive.value.toLocaleString("en-US"))} ${esc(naive.unit || "")}`;
        sub = "not in " + esc(unit) + "; cannot be compared";
      } else {
        head = `${verdict(naive)} No figure`;
        sub = "the naive agent returned no number";
      }
      chips.push(
        `<div class="xray-chip"><span class="k"><i class="xray-key naive"></i>Naive answer</span><b>${head}</b><span class="s">${sub}</span></div>`
      );
    }
    return `<div class="xray-impact">${chips.join("")}</div>`;
  }

  function ontologyLine(x) {
    const t = x.ontology.totals || {},
      g = t.graph || {},
      n = t.name_match || {};
    const me = (g.entities || 0) - (n.entities || 0),
      mn = (g.net_usd || 0) - (n.net_usd || 0);
    return me > 0
      ? `Graph walk finds <b>${g.entities}</b> entities; name matching finds <b>${n.entities}</b> and misses <b>${esc(money(mn))}</b> net exposure across <b>${me}</b> ${me === 1 ? "entity" : "entities"}.`
      : `Graph walk and name matching both find all <b>${g.entities}</b> entities for this group.`;
  }
  function semanticsLine(m) {
    if (!m) return "";
    const mids = m.wf.filter((w, i) => i > 0 && !w.total),
      adj = mids.reduce((a, w) => a + w.value, 0);
    let first = m.isPct
      ? `The firm definition divides by entitled desk NAV.`
      : mids.length
        ? `The firm definition ${adj < 0 ? "nets" : "adds"} <b>${esc(money(Math.abs(adj)))}</b> of ${esc(mids.map((w) => w.label.toLowerCase()).join(" and "))}.`
        : `The firm definition applies no adjustment.`;
    let second = "";
    if (m.naive) {
      if (m.comparable) {
        const diff = m.naive.value - m.governed;
        second =
          Math.abs(diff) <= Math.max(1, Math.abs(m.governed) * 1e-6)
            ? " The naive answer matches the governed figure."
            : ` The naive answer is off by <b>${esc(fmt(Math.abs(diff), m.unit))}</b>${m.unit === "percent" ? " pts" : ` (${((Math.abs(diff) / Math.abs(m.governed || 1)) * 100).toFixed(0)}%)`}.`;
      } else
        second = ok(m.naive.value)
          ? ` The naive answer (${esc(m.naive.value.toLocaleString("en-US"))} ${esc(m.naive.unit || "")}) is not in ${esc(m.unit)} and can’t be compared.`
          : " The naive agent returned no figure.";
    }
    return first + second;
  }

  function tables(x, m) {
    const ents = ordered(x.ontology.entities || []);
    const ot = `<details class="xray-table"><summary>Table view · legal entities</summary><div class="xray-table-wrap"><table><thead><tr><th>Entity</th><th>LEI</th><th>Depth</th><th>Relationship</th><th class="num">Positions</th><th class="num">Gross</th><th class="num">Net</th><th>Name match</th></tr></thead><tbody>${ents.map((e) => `<tr><td>${esc(e.name)}</td><td class="mono">${esc(e.lei)}</td><td class="num">${e._d}</td><td>${esc(e._d ? e.relationship : "root")}</td><td class="num">${esc(e.positions)}</td><td class="num">${esc(full(e.gross_usd))}</td><td class="num">${esc(full(e.net_usd))}</td><td>${e.name_match ? "found" : "missed"}</td></tr>`).join("")}</tbody></table></div></details>`;
    if (!m) return [ot, ""];
    const rowsS =
      m.wf
        .map(
          (w) =>
            `<tr><td>${esc(w.label)}</td><td class="num">${esc(fmtFull(w.value, w.total ? m.unit : m.isPct ? w.unit || "USD" : m.unit))}</td><td>${w.total ? "governed result" : "calculation step"}</td></tr>`
        )
        .join("") +
      m.alts
        .map(
          (a) =>
            `<tr><td>${esc(a.label)}</td><td class="num">${esc(fmtFull(a.value, m.unit))}</td><td>alternative definition</td></tr>`
        )
        .join("") +
      (m.naive
        ? `<tr><td>Naive answer</td><td class="num">${ok(m.naive.value) ? esc(m.comparable ? fmtFull(m.naive.value, m.unit) : m.naive.value + " " + (m.naive.unit || "")) : "no figure"}</td><td>${m.naive.accuracy && m.naive.accuracy.score === 1 ? "correct" : m.naive.accuracy && m.naive.accuracy.score === 0 ? "incorrect" : "unscored"}</td></tr>`
        : "");
    const st = `<details class="xray-table"><summary>Table view · definition and answers</summary><div class="xray-table-wrap"><table><thead><tr><th>Item</th><th class="num">Value</th><th>Role</th></tr></thead><tbody>${rowsS}</tbody></table></div></details>`;
    return [ot, st];
  }

  function bind(el) {
    if (el._xrayBound) return;
    el._xrayBound = true;
    const show = (html, x, y) => {
      const t = el.querySelector(".xray-tip");
      if (!t) return;
      t.innerHTML = html;
      t.hidden = false;
      const w = t.offsetWidth,
        h = t.offsetHeight;
      t.style.left = Math.max(8, Math.min(x + 14, innerWidth - w - 8)) + "px";
      t.style.top = (y + 16 + h > innerHeight ? y - h - 10 : y + 16) + "px";
    };
    const hide = () => {
      const t = el.querySelector(".xray-tip");
      if (t) t.hidden = true;
    };
    el.addEventListener("mousemove", (e) => {
      const t = e.target.closest && e.target.closest("[data-xtip]");
      if (t && el.contains(t)) show(t.getAttribute("data-xtip"), e.clientX, e.clientY);
      else hide();
    });
    el.addEventListener("mouseleave", hide);
    el.addEventListener("focusin", (e) => {
      const t = e.target.closest && e.target.closest("[data-xtip]");
      if (t) {
        const r = t.getBoundingClientRect();
        show(
          t.getAttribute("data-xtip"),
          r.left + Math.min(r.width / 2, 120),
          r.top + Math.min(r.height, 40)
        );
      }
    });
    el.addEventListener("focusout", hide);
    el.addEventListener("click", (e) => {
      const b = e.target.closest && e.target.closest("[data-lens]");
      if (!b) return;
      el._xrayLens = b.getAttribute("data-lens");
      paint(el);
    });
    if (window.ResizeObserver) {
      let last = 0;
      new ResizeObserver(() => {
        const w = el.clientWidth;
        if (w !== last) {
          last = w;
          requestAnimationFrame(() => paint(el));
        }
      }).observe(el);
    }
  }

  function paint(el) {
    const st = el._xray;
    if (!st || !st.x) return;
    const fam = getComputedStyle(el).fontFamily || "sans-serif";
    const lens = el._xrayLens || "graph";
    el.querySelectorAll("[data-lens]").forEach((b) =>
      b.setAttribute("aria-pressed", String(b.getAttribute("data-lens") === lens))
    );
    const legend = el.querySelector(".xray-tree-legend");
    if (legend)
      legend.innerHTML =
        lens === "graph"
          ? '<span><i class="sw solid"></i>Reached by walking parent/child links from the root LEI</span>'
          : '<span><i class="sw solid"></i>Found by name match</span><span><i class="sw hollow"></i>Missed by name match</span>';
    const th = el.querySelector(".xray-tree-host");
    if (th) th.innerHTML = drawTree(st.x, lens, Math.max(240, th.clientWidth), fam);
    const sh = el.querySelector(".xray-sem-host");
    if (sh && st.m) sh.innerHTML = drawSemantics(st.m, Math.max(240, sh.clientWidth), fam);
  }

  function render(el, plane, naive) {
    if (!el) return;
    bind(el);
    const x = plane && plane.inspector && plane.inspector.xray;
    el.classList.add("xray");
    if (!x || !x.ontology) {
      el._xray = null;
      el.innerHTML =
        '<p class="xray-empty">Ask a group exposure question to see what the ontology and semantic layer changed.</p><div class="xray-tip" role="tooltip" hidden></div>';
      return;
    }
    const m = semanticsModel(x, plane, naive);
    el._xray = { x, m };
    const [ot, stb] = tables(x, m);
    const legendSem = m
      ? `<div class="xray-legend">${m.steps.length ? '<span><i class="sw step"></i>Calculation step</span><span><i class="sw total"></i>Governed figure (bar and reference line)</span>' : '<span><i class="dotk plane"></i>Governed figure</span>'}${m.comparable ? '<span><i class="dotk naive"></i>Naive answer</span>' : ""}${m.alts.length ? '<span><i class="dotk alt"></i>Alternative definition</span>' : ""}</div>`
      : "";
    el.innerHTML = `<header class="xray-head"><span class="xray-eyebrow">LAYER X-RAY</span><h3>What the plane added · ${esc(x.group)} · ${esc(x.persona || plane.persona || "")}</h3></header>
  ${impactStrip(x, plane, naive, m)}
  <div class="xray-panels">
   <section class="xray-panel" aria-label="Ontology">
     <div class="xray-panel-head"><h4>Ontology <small>Who is the counterparty?</small></h4>
       <div class="xray-seg" role="group" aria-label="Lens"><button type="button" data-lens="graph" aria-pressed="true">Ontology (graph walk)</button><button type="button" data-lens="string" aria-pressed="false">String match</button></div></div>
     <p class="xray-line">${ontologyLine(x)}</p>
     <div class="xray-tree-legend xray-legend"></div>
     <div class="xray-tree-host"></div>
     <p class="xray-foot">Name rule: ${esc(x.ontology.name_match_rule || "")} · root LEI <span class="mono">${esc(x.ontology.root_lei || "")}</span></p>
     ${ot}
   </section>
   ${
     m
       ? `<section class="xray-panel" aria-label="Semantic layer">
     <div class="xray-panel-head"><h4>Semantic layer <small>What does “${esc(m.s.metric.replace(/_/g, " "))}” mean here?</small></h4></div>
     <p class="xray-line">${semanticsLine(m)}</p>
     ${legendSem}
     ${formulaTiles(m)}
     <div class="xray-sem-host"></div>
     <div class="xray-def"><p><b>${esc(m.s.metric)}</b> · version ${esc(m.s.version)} · source SQL_ID <span class="mono">${esc(m.s.source_sql_id)}</span></p><p>${esc(m.s.definition)}</p></div>
     ${stb}
   </section>`
       : ""
   }
  </div><div class="xray-tip" role="tooltip" hidden></div>`;
    paint(el);
  }
  window.XRay = { render };
})();
