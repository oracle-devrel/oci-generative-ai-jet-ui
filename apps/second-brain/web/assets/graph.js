/* The graph view: a holographic star-map of the brain. Topic hubs glow amber-gold; the
   content items they cite are terracotta embers. Citation edges are faint holo-cyan;
   semantic edges (added on demand via /api/related) are dashed. A nebula + starfield is
   painted behind it. Renders with the vendored force-graph UMD global. */
(function () {
  "use strict";

  var CSS = getComputedStyle(document.documentElement);
  function v(name, fallback) { return (CSS.getPropertyValue(name).trim() || fallback); }
  var C_TOPIC = v('--topic', '#a78bfa'),
      C_ITEM = v('--item', '#f5b971'),
      C_EDGE = v('--topic-dim', '#6d5bd0'),
      C_BG = v('--bg', '#16161c'),
      C_TEXT = v('--text', '#d7d7e0');

  // content embers: warm hues only (terracotta -> amber, 14-40deg) with a stable per-platform
  // variation in hue + lightness, so sources read as stars at different distances — never the
  // cool pastels the brand rules reject.
  function platformColor(p) {
    if (!p) return C_ITEM;
    var h = 0, s = String(p);
    for (var i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) % 1000;
    var hue = 14 + (h % 26), lig = 54 + (Math.floor(h / 26) % 22);
    return 'hsl(' + hue + ',72%,' + lig + '%)';
  }

  var Graph = null, DATA = { nodes: [], links: [] }, IDS = {}, DEG = {};
  var FOCUS = false, FOCUS_ID = null;   // local-graph mode + the node it's centered on
  var HOVER = null, HOVERN = null;      // hovered node + its neighbor id set (for highlight)

  function recomputeDegree() {
    DEG = {};
    DATA.links.forEach(function (l) {
      var s = l.source.id || l.source, t = l.target.id || l.target;
      DEG[s] = (DEG[s] || 0) + 1; DEG[t] = (DEG[t] || 0) + 1;
    });
  }

  function neighborIds(id) {
    var set = {};
    DATA.links.forEach(function (l) {
      var s = l.source.id || l.source, t = l.target.id || l.target;
      if (s === id) set[t] = true; else if (t === id) set[s] = true;
    });
    return set;
  }

  // render the full graph, or just one node's neighborhood when Focus mode is centered on it
  function render() {
    if (FOCUS && FOCUS_ID) {
      var keep = neighborIds(FOCUS_ID); keep[FOCUS_ID] = true;
      Graph.graphData({
        nodes: DATA.nodes.filter(function (n) { return keep[n.id]; }),
        links: DATA.links.filter(function (l) {
          return keep[l.source.id || l.source] && keep[l.target.id || l.target]; }),
      });
    } else {
      Graph.graphData(DATA);
    }
  }

  function nodeRadius(n) {
    var base = n.type === 'topic' ? 4.5 : 2.8;
    return base + Math.min(6, Math.sqrt(DEG[n.id] || 0) * 1.3);
  }
  function nodeColor(n) { return n.type === 'topic' ? C_TOPIC : platformColor(n.platform); }

  function draw(node, ctx, scale) {
    var r = nodeRadius(node);
    // hover-highlight: dim everything that isn't the hovered node or a direct neighbor
    var dim = HOVER && node.id !== HOVER.id && !(HOVERN && HOVERN[node.id]);
    ctx.globalAlpha = dim ? 0.16 : 1;
    ctx.beginPath();
    ctx.arc(node.x, node.y, r, 0, 2 * Math.PI);
    var col = nodeColor(node);
    ctx.fillStyle = col;
    ctx.fill();
    if (!dim) {   // every node glows like a star; topic hubs burn brighter
      ctx.shadowColor = col; ctx.shadowBlur = node.type === 'topic' ? 20 : 9; ctx.fill();
      ctx.shadowBlur = 0;
    }
    // labels: topics always (when zoomed enough); items only when zoomed in close
    var show = node.type === 'topic' ? scale > 0.7 : scale > 2.4;
    if (show && node.label && !dim) {
      var fs = Math.max(3, (node.type === 'topic' ? 5 : 3.6));
      ctx.font = fs + 'px -apple-system, sans-serif';
      ctx.textAlign = 'center'; ctx.textBaseline = 'top';
      ctx.fillStyle = node.type === 'topic' ? C_TEXT : 'rgba(215,215,224,.7)';
      var label = node.label.length > 34 ? node.label.slice(0, 33) + '…' : node.label;
      ctx.fillText(label, node.x, node.y + r + 1);
    }
    ctx.globalAlpha = 1;
  }

  function linkColor(l) {   // holo-cyan hyperspace lanes
    if (HOVER) {   // on hover, only the hovered node's edges stay lit
      var s = l.source.id || l.source, t = l.target.id || l.target;
      if (s !== HOVER.id && t !== HOVER.id) return 'rgba(120,140,170,.05)';
      return l.type === 'semantic' ? 'rgba(87,214,255,.8)' : 'rgba(87,214,255,.45)';
    }
    return l.type === 'semantic' ? 'rgba(87,214,255,.55)' : 'rgba(87,214,255,.16)';
  }

  // a fixed faint starfield, generated once per canvas size (deterministic — no flicker)
  var STARS = null;
  function starfield(w, h) {
    if (STARS && STARS.w === w && STARS.h === h) return STARS.pts;
    var pts = [], seed = 20260713;
    function rnd() { seed = (seed * 1103515245 + 12345) & 0x7fffffff; return seed / 0x7fffffff; }
    for (var i = 0; i < 150; i++) pts.push([rnd() * w, rnd() * h, rnd() * 1.0 + 0.3, rnd() * 0.45 + 0.15, rnd() < 0.16]);
    STARS = { w: w, h: h, pts: pts };
    return pts;
  }
  // paint the deep-space backdrop (nebula glow + stars) in screen space, under the graph
  function paintSpace(ctx) {
    var w = Graph.width(), h = Graph.height();
    ctx.save();
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    var g = ctx.createRadialGradient(w * 0.5, h * 0.34, 0, w * 0.5, h * 0.34, Math.max(w, h) * 0.62);
    g.addColorStop(0, 'rgba(40,70,110,.20)'); g.addColorStop(1, 'rgba(40,70,110,0)');
    ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
    var pts = starfield(w, h);
    for (var i = 0; i < pts.length; i++) {
      ctx.globalAlpha = pts[i][3];
      ctx.fillStyle = pts[i][4] ? '#bcd6ff' : '#ffffff';
      ctx.beginPath(); ctx.arc(pts[i][0], pts[i][1], pts[i][2], 0, 2 * Math.PI); ctx.fill();
    }
    ctx.globalAlpha = 1; ctx.restore();
  }

  function init(container, onNode, onExpand) {
    Graph = ForceGraph()(container)
      .backgroundColor(C_BG)
      .onRenderFramePre(paintSpace)
      .nodeId('id')
      .nodeLabel(function (n) { return n.label + (n.type === 'item' && n.platform ? '  ·  ' + n.platform : ''); })
      .nodeRelSize(1)
      .nodeCanvasObject(draw)
      .nodePointerAreaPaint(function (node, color, ctx) {
        ctx.fillStyle = color;
        ctx.beginPath(); ctx.arc(node.x, node.y, nodeRadius(node) + 2, 0, 2 * Math.PI); ctx.fill();
      })
      .linkColor(linkColor)
      .linkWidth(function (l) { return l.type === 'semantic' ? 1.2 : 0.7; })
      .linkLineDash(function (l) { return l.type === 'semantic' ? [2, 2] : null; })
      .onNodeClick(function (n) {
        if (FOCUS) { FOCUS_ID = n.id; render(); }   // local-graph mode: center on this node
        onNode(n);
      })
      .onNodeRightClick(function (n) { onExpand(n); })
      .onBackgroundClick(function () { onNode(null); });
    // double-click grows the graph by meaning (force-graph zooms-to-fit on dblclick by
    // default; override it to our expand action — the on-camera moment)
    Graph.onNodeDrag(function () {}); // no-op keeps drag enabled
    container.addEventListener('dblclick', function () {
      var n = Graph.__lastHover; if (n) onExpand(n);
    });
    Graph.onNodeHover(function (n) {
      Graph.__lastHover = n;
      HOVER = n; HOVERN = n ? neighborIds(n.id) : null;
      container.style.cursor = n ? 'pointer' : 'default';
    });
    window.addEventListener('resize', function () {
      Graph.width(container.clientWidth).height(container.clientHeight);
    });
    Graph.width(container.clientWidth).height(container.clientHeight);
    return Graph;
  }

  function setData(d) {
    DATA = { nodes: d.nodes.slice(), links: d.links.slice() };
    IDS = {}; DATA.nodes.forEach(function (n) { IDS[n.id] = true; });
    recomputeDegree();
    render();
  }

  function toggleFocus() {
    FOCUS = !FOCUS;
    if (!FOCUS) FOCUS_ID = null;   // leaving focus mode restores the full graph
    render();
    return FOCUS;
  }

  // merge in nodes/links from /api/related without disturbing the running simulation
  function merge(anchorId, d) {
    var added = 0;
    d.nodes.forEach(function (n) { if (!IDS[n.id]) { IDS[n.id] = true; DATA.nodes.push(n); added++; } });
    var seen = {};
    DATA.links.forEach(function (l) { seen[(l.source.id || l.source) + '>' + (l.target.id || l.target)] = true; });
    d.links.forEach(function (l) {
      var key = l.source + '>' + l.target;
      if (!seen[key] && IDS[l.source] && IDS[l.target]) { seen[key] = true; DATA.links.push(l); }
    });
    recomputeDegree();
    render();
    return added;
  }

  function focus(id) {
    var n = DATA.nodes.filter(function (x) { return x.id === id; })[0];
    if (n && Graph) { Graph.centerAt(n.x, n.y, 600); Graph.zoom(3.5, 600); }
  }

  window.BrainGraph = { init: init, setData: setData, merge: merge, focus: focus,
    toggleFocus: toggleFocus, has: function (id) { return !!IDS[id]; } };
})();
