import { useEffect, useMemo, useRef, useState } from "react";
import Globe from "react-globe.gl";
import { ChevronUp, ChevronDown, Globe2, Search, Anchor, Ship, Building2, Boxes, Container as ContainerIcon, RefreshCw } from "lucide-react";

const LAYER_COLORS = {
  port:      "#ffd166", // accent-tool
  vessel:    "#06d6a0", // accent-memory
  carrier:   "#118ab2", // accent-skill
  voyage:    "#ef476f", // accent-sql
  cargo:     "#f80000", // accent-oracle
  container: "#e0e0e0", // text-accent — neutral so they read as cargo dots, not vessels
};

const REGION_ARC_COLOR = {
  PACIFIC:       "#118ab2",
  ATLANTIC:      "#06d6a0",
  INDIAN:        "#ffd166",
  MEDITERRANEAN: "#f80000",
};

const KIND_ICON = {
  port:      Anchor,
  vessel:    Ship,
  carrier:   Building2,
  cargo:     Boxes,
  container: ContainerIcon,
};

/**
 * The World Explorer — a 3D globe under the chat panes that renders the
 * supply-chain dataset geographically. Ports, vessels, carriers, voyage arcs.
 *
 * The globe respects the "Use As:" identity: switching personas re-fetches
 * /api/world with `as_user=` so an analyst.east user only sees ATLANTIC +
 * MEDITERRANEAN voyages.
 *
 * The search bar resolves a free-text query (port code, vessel name, carrier,
 * cargo description) and flies the camera to it.
 */
export default function WorldExplorer({ identityId, socket }) {
  const [open, setOpen] = useState(false);
  const [height, setHeight] = useState(560);
  // Banner shown when the chat agent drives the globe via focus_world.
  // Disappears after a few seconds so it doesn't clutter the view.
  const [agentFocus, setAgentFocus] = useState(null);
  const [data, setData] = useState({
    ports: [], vessels: [], voyages: [], carriers: [], containers: [],
    containers_forbidden: false,
    stats: { ports: 0, vessels: 0, voyages: 0, carriers: 0, containers: 0 },
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [searchQ, setSearchQ] = useState("");
  const [searchResult, setSearchResult] = useState(null);
  const [searchError, setSearchError] = useState(null);
  const [layers, setLayers] = useState({
    ports: true, vessels: true, voyages: true, carriers: true, containers: true,
  });

  const resizing = useRef(false);
  const globeRef = useRef(null);
  const wrapRef = useRef(null);
  const [globeWidth, setGlobeWidth] = useState(800);
  const [globeHeight, setGlobeHeight] = useState(480);

  const fetchWorld = () => {
    setLoading(true);
    setError(null);
    fetch(`/api/world?as_user=${encodeURIComponent(identityId || "agent")}`)
      .then(async (r) => {
        const text = await r.text();
        // If the dev server fell through to index.html (because the backend's
        // /api/world endpoint isn't registered yet — usually means the Flask
        // process needs a restart), produce a useful error instead of a JSON
        // parse error.
        if (text.startsWith("<")) {
          throw new Error(
            "/api/world returned HTML — backend likely needs a restart so the new world routes register."
          );
        }
        try {
          return JSON.parse(text);
        } catch {
          throw new Error(`/api/world returned non-JSON: ${text.slice(0, 120)}`);
        }
      })
      .then((d) => {
        if (d && d.error) {
          setError(d.error);
          return;
        }
        setData(d);
      })
      .catch((e) => setError(String(e?.message || e)))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    if (open) fetchWorld();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, identityId]);

  // When the chat agent calls `focus_world(...)`, the backend emits a
  // 'focus_world' Socket.IO event. Auto-open the panel, fly the globe, and
  // show a banner with the resolved label so the user can see the agent's
  // intent. The banner clears itself after a few seconds.
  //
  // We *also* listen for `tool_started` so we can open the panel as soon as
  // the agent dispatches focus_world — that way the globe canvas is mounted
  // and the data fetch is in flight by the time the resolved focus_world
  // payload lands. Without this pre-open, the user sees a brief flicker
  // because the panel only opens AFTER the camera-move command arrives.
  useEffect(() => {
    if (!socket) return;

    const onToolStarted = (p) => {
      if (p && p.name === "focus_world") {
        setOpen(true);
        // Pre-arm the banner with the args the agent sent, so the user sees
        // "agent flew the globe → ..." even before the tool resolves a
        // lat/lng. The full payload (with coords) replaces this in onFocus.
        const args = p.args || {};
        setAgentFocus({
          kind: args.target_kind || "—",
          target: args.target || "",
          label: `resolving ${args.target_kind || ""} ${args.target || ""}…`.trim(),
          lat: 0,
          lng: 0,
          altitude: args.altitude,
          pending: true,
        });
      }
    };

    const onFocus = (p) => {
      setOpen(true);
      setAgentFocus(p);
      setSearchResult({
        kind: p.kind,
        id: p.target,
        name: p.label,
        lat: p.lat,
        lng: p.lng,
        ocean_region: p.region,
      });
      // Defer until after open=true triggers the globe to mount/resize.
      setTimeout(() => {
        if (globeRef.current && p.lat != null && p.lng != null) {
          globeRef.current.pointOfView(
            { lat: p.lat, lng: p.lng, altitude: p.altitude || 1.5 },
            1500,
          );
        }
      }, 60);
      window.setTimeout(() => setAgentFocus(null), 6000);
    };

    socket.on("tool_started", onToolStarted);
    socket.on("focus_world", onFocus);
    return () => {
      socket.off("tool_started", onToolStarted);
      socket.off("focus_world", onFocus);
    };
  }, [socket]);

  // Resize observer for the globe canvas — react-globe.gl wants explicit pixels.
  useEffect(() => {
    if (!open || !wrapRef.current) return;
    const ro = new ResizeObserver(() => {
      const rect = wrapRef.current.getBoundingClientRect();
      setGlobeWidth(Math.max(320, rect.width));
      setGlobeHeight(Math.max(280, rect.height - 92)); // minus toolbar + search
    });
    ro.observe(wrapRef.current);
    return () => ro.disconnect();
  }, [open]);

  const onMouseDownResize = (e) => {
    resizing.current = true;
    const onMove = (ev) => {
      if (!resizing.current) return;
      const newH = window.innerHeight - ev.clientY - 60;
      setHeight(Math.max(340, Math.min(900, newH)));
    };
    const onUp = () => {
      resizing.current = false;
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseup", onUp);
    };
    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", onUp);
    e.preventDefault();
  };

  const points = useMemo(() => {
    const out = [];
    if (layers.ports) {
      for (const p of data.ports) {
        out.push({
          ...p,
          size: 0.18,
          color: LAYER_COLORS.port,
        });
      }
    }
    if (layers.vessels) {
      for (const v of data.vessels) {
        out.push({
          ...v,
          size: 0.32,
          color: LAYER_COLORS.vessel,
        });
      }
    }
    if (layers.carriers) {
      for (const c of data.carriers) {
        out.push({
          ...c,
          size: 0.5,
          color: LAYER_COLORS.carrier,
        });
      }
    }
    if (layers.containers) {
      for (const c of data.containers || []) {
        out.push({
          ...c,
          size: 0.12,
          color: LAYER_COLORS.container,
        });
      }
    }
    if (searchResult) {
      out.push({
        ...searchResult,
        kind: searchResult.kind,
        size: 0.9,
        color: LAYER_COLORS[searchResult.kind] || "#ffffff",
        searchAnchor: true,
      });
    }
    return out;
  }, [data, layers, searchResult]);

  const arcs = useMemo(() => {
    if (!layers.voyages) return [];
    return data.voyages
      .filter((v) => v.origin && v.destination)
      .map((v) => ({
        startLat: v.origin.lat,
        startLng: v.origin.lng,
        endLat: v.destination.lat,
        endLng: v.destination.lng,
        color: REGION_ARC_COLOR[v.ocean_region] || "#ffffff",
        ...v,
      }));
  }, [data.voyages, layers.voyages]);

  const onSearch = (e) => {
    e.preventDefault();
    const raw = searchQ.trim();
    if (!raw) return;
    // Be forgiving: if the user typed something like "container (MSCU9745959)"
    // — copying the placeholder verbatim — strip the descriptive prefix and
    // the parens before sending the query.
    const cleaned = sanitizeQuery(raw);
    setSearchError(null);
    fetch(
      `/api/world/search?q=${encodeURIComponent(cleaned)}&as_user=${encodeURIComponent(identityId || "agent")}`
    )
      .then(async (r) => {
        const text = await r.text();
        if (text.startsWith("<")) {
          return { ok: false, body: { error: "backend missing /api/world/search — restart backend" } };
        }
        let body;
        try {
          body = JSON.parse(text);
        } catch {
          body = { error: `non-JSON response: ${text.slice(0, 120)}` };
        }
        return { ok: r.ok, body };
      })
      .then(({ ok, body }) => {
        if (!ok || body.error) {
          setSearchError(body.error || "search failed");
          setSearchResult(null);
          return;
        }
        setSearchResult(body);
        if (globeRef.current && body.lat != null && body.lng != null) {
          globeRef.current.pointOfView(
            { lat: body.lat, lng: body.lng, altitude: 1.6 },
            1500
          );
        }
      })
      .catch((e) => {
        setSearchError(String(e?.message || e));
        setSearchResult(null);
      });
  };

  return (
    <section className="border-t border-white/5 bg-bg-base">
      <div className="h-9 flex items-center px-3 gap-3 border-b border-white/5 bg-bg-panel">
        <button
          onClick={() => setOpen(!open)}
          className="flex items-center gap-1.5 text-xs text-text-secondary hover:text-text-primary"
        >
          {open ? <ChevronDown size={12} /> : <ChevronUp size={12} />}
          <Globe2 size={12} className="text-accent-skill" />
          <span className="uppercase tracking-wider">World Explorer</span>
        </button>
        <span className="text-[10px] text-text-muted">
          {data.stats.ports} ports · {data.stats.vessels} vessels · {data.stats.voyages} voyages · {data.stats.carriers} carriers ·{" "}
          {data.containers_forbidden ? (
            <span className="text-accent-sql">containers DENIED for current identity</span>
          ) : (
            <>{data.stats.containers ?? 0} containers</>
          )}
        </span>
        {open && (
          <>
            {loading && <span className="ml-auto text-[10px] text-text-muted italic">loading...</span>}
            {!loading && error && (
              <span className="ml-auto text-[10px] text-accent-sql font-mono">
                error: {String(error).slice(0, 80)}
              </span>
            )}
            {!loading && !error && (
              <span className="ml-auto" />
            )}
            <button
              onMouseDown={onMouseDownResize}
              className="text-[10px] text-text-muted hover:text-text-secondary cursor-ns-resize"
              title="drag to resize"
            >
              ═
            </button>
            <button
              onClick={fetchWorld}
              className="text-text-muted hover:text-text-primary"
              title="refresh"
            >
              <RefreshCw size={12} />
            </button>
          </>
        )}
      </div>

      {open && (
        <div ref={wrapRef} className="flex flex-col" style={{ height }}>
          {/* Search + layer toggles */}
          <div className="px-3 py-1.5 border-b border-white/5 bg-bg-panel/40 flex items-center gap-3 flex-wrap">
            <form onSubmit={onSearch} className="flex items-center gap-2 flex-1 min-w-[260px]">
              <Search size={12} className="text-text-muted" />
              <input
                type="text"
                value={searchQ}
                onChange={(e) => setSearchQ(e.target.value)}
                placeholder="fly to — type a port code, vessel name, carrier, container number, or cargo keyword (e.g. SGSIN · Maersk Edinburgh · MSCU6634586 · electronics)"
                className="flex-1 bg-transparent text-[11px] font-mono text-text-primary placeholder:text-text-muted focus:outline-none"
              />
              <button
                type="submit"
                className="text-[10px] px-2 py-0.5 rounded border border-white/10 text-text-secondary hover:text-text-primary hover:border-accent-skill/40"
              >
                fly
              </button>
            </form>
            {searchError && (
              <span className="text-[10px] font-mono text-accent-sql">{searchError}</span>
            )}
            {searchResult && (
              <span className="text-[10px] font-mono text-accent-memory">
                → {searchResult.kind}: {searchResult.name || searchResult.description || searchResult.id}{" "}
                ({searchResult.lat.toFixed(2)}, {searchResult.lng.toFixed(2)})
              </span>
            )}
            <div className="flex items-center gap-2 text-[10px] font-mono">
              {Object.entries(layers).map(([k, v]) => {
                const Icon = KIND_ICON[k] || Anchor;
                return (
                  <button
                    key={k}
                    onClick={() => setLayers((s) => ({ ...s, [k]: !s[k] }))}
                    className={`flex items-center gap-1 px-1.5 py-0.5 rounded border ${
                      v
                        ? "border-white/10 bg-white/[0.05] text-text-primary"
                        : "border-white/5 text-text-muted hover:text-text-secondary"
                    }`}
                    title={`toggle ${k} layer`}
                  >
                    <Icon size={10} style={{ color: LAYER_COLORS[k] || "#888" }} />
                    {k}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Agent-driven focus banner. While the focus_world tool is still
              running we render a "resolving…" state with a pulsing dot;
              once the resolved payload arrives (lat/lng populated, !pending)
              the banner switches to "agent flew the globe → ..." with coords. */}
          {agentFocus && (
            <div className="px-3 py-1.5 border-b border-accent-oracle/30 bg-accent-oracle/10 flex items-center gap-2 text-[11px] font-mono">
              <Globe2 size={11} className="text-accent-oracle" />
              {agentFocus.pending ? (
                <>
                  <span className="text-accent-oracle">agent is flying the globe</span>
                  <span className="inline-block w-1.5 h-1.5 rounded-full bg-accent-oracle animate-pulse" />
                  <span className="text-text-muted">
                    {agentFocus.kind}: {agentFocus.target || "…"}
                  </span>
                </>
              ) : (
                <>
                  <span className="text-accent-oracle">agent flew the globe →</span>
                  <span className="text-text-primary">{agentFocus.label || agentFocus.target}</span>
                  <span className="text-text-muted">
                    ({agentFocus.kind} · {agentFocus.lat.toFixed(2)}, {agentFocus.lng.toFixed(2)})
                  </span>
                </>
              )}
              <button
                className="ml-auto text-[10px] text-text-muted hover:text-text-primary"
                onClick={() => setAgentFocus(null)}
                title="dismiss"
              >
                ×
              </button>
            </div>
          )}

          {/* Globe canvas */}
          <div className="flex-1 relative overflow-hidden bg-[#000308]">
            {!loading && data.stats.ports === 0 && !error && (
              <div className="absolute inset-0 flex items-center justify-center text-text-muted text-xs">
                no geo features available — has the SUPPLYCHAIN seed run?
              </div>
            )}
            <Globe
              ref={globeRef}
              width={globeWidth}
              height={globeHeight}
              backgroundColor="#000308"
              globeImageUrl="//unpkg.com/three-globe/example/img/earth-night.jpg"
              bumpImageUrl="//unpkg.com/three-globe/example/img/earth-topology.png"
              showAtmosphere={true}
              atmosphereColor="#3b82f6"
              atmosphereAltitude={0.18}
              pointsData={points}
              pointLat="lat"
              pointLng="lng"
              pointColor="color"
              pointAltitude={(d) =>
                d.searchAnchor ? 0.06 : d.kind === "vessel" ? 0.012 : 0.008
              }
              pointRadius={(d) => d.size}
              pointLabel={(d) => buildLabel(d)}
              onPointClick={(d) => {
                if (globeRef.current) {
                  globeRef.current.pointOfView({ lat: d.lat, lng: d.lng, altitude: 1.4 }, 1000);
                }
              }}
              arcsData={arcs}
              arcStartLat="startLat"
              arcStartLng="startLng"
              arcEndLat="endLat"
              arcEndLng="endLng"
              arcColor={(d) => d.color}
              arcAltitudeAutoScale={0.4}
              arcStroke={0.4}
              arcDashLength={0.45}
              arcDashGap={0.15}
              arcDashAnimateTime={3500}
              arcLabel={(d) =>
                `<div style="font-family:ui-monospace,Menlo,monospace;font-size:11px;color:#f5f5f5;background:#0a0a0acc;padding:6px 8px;border:1px solid rgba(255,255,255,0.1);border-radius:4px">
                   <strong>voyage ${d.id}</strong> · ${d.status}<br/>
                   ${d.vessel} (${d.carrier})<br/>
                   ${d.origin.port_code} → ${d.destination.port_code}<br/>
                   <span style="color:#888">${d.ocean_region}</span>
                 </div>`
              }
            />
          </div>
        </div>
      )}
    </section>
  );
}

// Pull out the value the user actually meant when they typed something like
// "port (SGSIN)", "container: MSCU9745959", or just "Singapore". The backend's
// LIKE is wide so we mostly need to drop the descriptive label and parens.
function sanitizeQuery(raw) {
  let q = raw;
  // 1. If there's a parenthesized fragment, prefer that — "port (SGSIN)" → "SGSIN".
  const paren = q.match(/\(([^)]+)\)/);
  if (paren) {
    q = paren[1];
  } else {
    // 2. Strip a leading "kind:" / "kind -" prefix.
    q = q.replace(/^\s*(port|vessel|carrier|cargo|container)s?\s*[:\-]\s*/i, "");
  }
  return q.trim();
}

// Defensive helpers: tooltips can fire on points whose payloads are sparse —
// in particular `searchAnchor` markers from the chat agent's focus_world call,
// which only carry kind/lat/lng/name/region until the world fetch completes
// and replaces them with the full record. Crashing on `undefined.toLocaleString`
// would break the whole globe canvas, so we guard every numeric/string read.
const _num = (v, fallback = "—") => {
  if (v == null || (typeof v === "number" && !Number.isFinite(v))) return fallback;
  try { return Number(v).toLocaleString(); } catch { return String(v); }
};
const _fix = (v, digits = 1, fallback = "—") => {
  const n = typeof v === "number" ? v : (v != null ? Number(v) : NaN);
  return Number.isFinite(n) ? n.toFixed(digits) : fallback;
};
const _txt = (v, fallback = "—") =>
  v == null || v === "" ? fallback : String(v);

function buildLabel(d) {
  const styles =
    'font-family:ui-monospace,Menlo,monospace;font-size:11px;color:#f5f5f5;background:#0a0a0acc;padding:6px 8px;border:1px solid rgba(255,255,255,0.1);border-radius:4px;max-width:280px';

  // The agent-driven focus marker is intentionally lighter than a full record;
  // render a short tooltip rather than the per-kind detailed one (which would
  // miss most fields and just print "—" everywhere).
  if (d.searchAnchor) {
    const coord = `${_fix(d.lat, 2)}, ${_fix(d.lng, 2)}`;
    return `<div style="${styles}"><strong>${_txt(d.name || d.id)}</strong><br/>` +
           `<span style="color:#888">${_txt(d.kind, "anchor")}</span> · ${coord}` +
           (d.ocean_region ? `<br/>region: ${_txt(d.ocean_region)}` : "") +
           "</div>";
  }

  if (d.kind === "port") {
    return `<div style="${styles}"><strong>${_txt(d.name)}</strong> (${_txt(d.id)})<br/>` +
           `${_txt(d.country)} · ${_txt(d.ocean_region)}<br/>` +
           `terminals: ${_num(d.terminals, "—")}</div>`;
  }
  if (d.kind === "vessel") {
    return `<div style="${styles}"><strong>${_txt(d.name)}</strong><br/>` +
           `${_txt(d.vessel_type)} · ${_txt(d.flag_country)}<br/>` +
           `carrier: ${_txt(d.carrier)}<br/>` +
           `capacity: ${_num(d.capacity_teu)} TEU<br/>` +
           `speed: ${_fix(d.speed_knots, 1)} kts · heading ${_fix(d.heading_deg, 0)}°<br/>` +
           `region: ${_txt(d.ocean_region)}</div>`;
  }
  if (d.kind === "carrier") {
    return `<div style="${styles}"><strong>${_txt(d.name)}</strong><br/>` +
           `HQ: ${_txt(d.country)}<br/>` +
           `active vessels (visible to you): ${_num(d.active_vessels, "—")}</div>`;
  }
  if (d.kind === "cargo") {
    return `<div style="${styles}"><strong>cargo ${_txt(d.id)}</strong><br/>` +
           `HS ${_txt(d.hs_code)}<br/>` +
           `${(d.description || "").slice(0, 80)}<br/>` +
           `→ ${_txt(d.destination_port)}</div>`;
  }
  if (d.kind === "container") {
    return `<div style="${styles}"><strong>${_txt(d.container_no)}</strong> · ${_txt(d.container_type)}<br/>` +
           `status: ${_txt(d.status)} · region: ${_txt(d.ocean_region)}<br/>` +
           `voyage ${_txt(d.voyage_id)} · ${_txt(d.origin_code)} → ${_txt(d.dest_code)}<br/>` +
           `vessel: ${_txt(d.vessel)} (${_txt(d.carrier)})<br/>` +
           `consignor: ${_txt(d.consignor)}<br/>` +
           `consignee: ${_txt(d.consignee)}<br/>` +
           `cargo items: ${_num(d.cargo_count, 0)}</div>`;
  }
  return `<div style="${styles}">${_txt(d.name || d.id)}</div>`;
}
