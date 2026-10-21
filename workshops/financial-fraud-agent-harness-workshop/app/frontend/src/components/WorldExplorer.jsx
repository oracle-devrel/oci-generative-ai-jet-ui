import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Globe from "react-globe.gl";
import { Globe2, Search, Building2, Store, AlertTriangle, RefreshCw, Crosshair } from "lucide-react";

const LAYER_COLORS = {
  branch:             "#ffd166", // accent-tool
  merchant:           "#118ab2", // accent-skill
  suspicious_activity: "#f80000", // accent-oracle — red AML dots
  customer:           "#06d6a0", // accent-memory
  region:             "#3b82f6",
  coords:             "#a78bfa",
};

// Arc color by AML flag reason (activity_arcs).
const FLAG_ARC_COLOR = {
  STRUCTURING:        "#ef476f", // accent-sql
  GEO_VELOCITY:       "#06d6a0", // accent-memory
  HIGH_RISK_COUNTRY:  "#ffd166",
  RAPID_CASH_OUT:     "#118ab2",
  LARGE_CASH_DEPOSIT: "#f80000",
};

// Live-feed arcs are meant to be watched, not rebuilt: the newest LIVE_ARC_MAX
// stay on the globe, each halo keeps its own phase in the dash animation, the
// pulse intensity decays with age (recency), and the arc that gets pushed out
// dissipates instead of being cut mid-flight.
// three-globe keys its layers by datum *reference*, so an arc object that
// survives a data update also survives with its animation intact — see the
// registries in WorldExplorer.
const LIVE_ARC_MAX = 10;
const LIVE_ARC_TTL_MS = 180_000;    // 3 min — by then the pulse is ~6% of birth intensity
const LIVE_ARC_FADE_MS = 1_800;     // the silent dissipation of an arc leaving the window
const LIVE_FRESH_MS = 2_200;        // birth flash: white-hot, thicker, faster comet
const PULSE_HALF_LIFE_MS = 45_000;  // recency → intensity: alpha halves every 45 s
const LIVE_TICK_MS = 250;           // heartbeat that drives the flash/fade
const BASE_ARC_STROKE = 0.4;
const BASE_ARC_DASH_MS = 3_500;

const KIND_ICON = {
  branch:   Building2,
  merchant: Store,
  suspicious_activity: AlertTriangle,
};

/**
 * The World Explorer — a 3D globe that renders the Meridian Bank dataset
 * geographically. Branches, merchants, and the bank's suspicious-activity
 * layer (recent FLAGGED / BLOCKED transactions plotted at their merchant, with
 * arcs from the account's home branch to the merchant).
 *
 * It fills its parent container (the Instrument panel's World tab) instead of
 * being a collapsible bottom drawer, so it can sit in parallel with the chat.
 *
 * The globe respects the "Use As:" identity: switching personas re-fetches
 * /api/world with `as_user=` so an analyst.east user only sees EUROPE +
 * MIDDLE_EAST branches, merchants, and flagged activity.
 *
 * `agentFocus` / `focusTarget` come from the Layout-level useWorldFocus hook so
 * the agent's `focus_world` tool still flies the camera even though this
 * component may be mounted only while the World tab is active.
 */
export default function WorldExplorer({
  identityId, agentFocus, focusTarget, lastActivity,
  autoFollow, onToggleAutoFollow, onDismissFocus,
  touched = {}, trace = [], isThinking = false,
  live, identity,
}) {
  const [data, setData] = useState({
    branches: [], merchants: [], suspicious_activity: [], activity_arcs: [],
    customers_forbidden: false,
    stats: { branches: 0, merchants: 0, suspicious_activity: 0, activity_arcs: 0 },
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [searchQ, setSearchQ] = useState("");
  const [searchResult, setSearchResult] = useState(null);
  const [searchError, setSearchError] = useState(null);
  const [layers, setLayers] = useState({
    branches: true, merchants: true, suspicious_activity: true,
  });
  // Briefly true after the agent moves the globe, so the live strip can pulse.
  const [activityFresh, setActivityFresh] = useState(false);

  const globeRef = useRef(null);
  const wrapRef = useRef(null);
  const [globeSize, setGlobeSize] = useState({ w: 720, h: 480 });

  useEffect(() => {
    if (!lastActivity) return;
    setActivityFresh(true);
    const t = window.setTimeout(() => setActivityFresh(false), 5000);
    return () => window.clearTimeout(t);
  }, [lastActivity]);

  // ---- Live reaction to the tool calls streaming in from the chat ----------
  // The backend emits `tables_touched` (a map of SCHEMA.TABLE → {action, ts})
  // plus tool_started / tool_finished events. We turn those into visible
  // motion: the layer the agent is reading pulses, a radar sweep runs while it
  // works, and a ticker names the current tool — so the globe reads as live
  // even when a query has no single location to fly to.
  const pulseLayers = useMemo(() => {
    const out = new Set();
    for (const key of Object.keys(touched || {})) {
      const t = key.toUpperCase();
      if (t.endsWith(".*")) {
        out.add("branches"); out.add("merchants"); out.add("suspicious_activity");
        continue;
      }
      if (t.includes("TRANSACTION") || t.includes("SAR") || t.includes("SANCTION")) out.add("suspicious_activity");
      if (t.includes("MERCHANT")) out.add("merchants");
      if (t.includes("BRANCH") || t.includes("ACCOUNT") || t.includes("CUSTOMER") || t.includes("LOAN")) out.add("branches");
    }
    return out;
  }, [touched]);
  const pulseKey = useMemo(() => [...pulseLayers].sort().join(","), [pulseLayers]);
  const [pulseOn, setPulseOn] = useState(false);

  useEffect(() => {
    if (!pulseKey) { setPulseOn(false); return; }
    const id = window.setInterval(() => setPulseOn((v) => !v), 550);
    return () => window.clearInterval(id);
  }, [pulseKey]);

  const liveTool = useMemo(() => {
    const evs = (trace || []).filter((t) => t.type === "tool_started" || t.type === "tool_finished");
    const last = evs[evs.length - 1];
    if (!last) return null;
    return {
      name: last.name,
      done: last.type === "tool_finished",
      tables: Object.keys(touched || {}),
    };
  }, [trace, touched]);

  // ---- Live data feed ------------------------------------------------------
  // The backend streams simulated banking activity. We keep only the events
  // this persona is allowed to see (same region contract as /api/world) and
  // render them as fresh, pulsing markers + arcs on top of the fetched layers.
  const amountMasked = useMemo(() => {
    const masks = identity?.mask_cols || [];
    return masks.some((m) => String(m).toUpperCase().endsWith("AMOUNT_CENTS"));
  }, [identity]);

  // Heartbeat for the live layer. `nowRef` is what the pulse/birth accessors
  // read, so the animation advances without React having to re-render — only a
  // membership change (or an arc in flight, which forces the globe's arc layer
  // to re-evaluate its colors) bumps state.
  const nowRef = useRef(Date.now());
  const [liveVersion, setLiveVersion] = useState(0); // arrivals, dissipations, flips
  const [arcTick, setArcTick] = useState(0);          // 250 ms while arcs are in flight

  // Region-gated (for the ticker + counters) — no time window.
  const liveAllowed = useMemo(() => {
    const regs = identity?.regions;
    return (live?.events || []).filter((e) => !regs || regs.includes(e.region));
  }, [live?.events, identity]);

  // Newest-first flagged/blocked events, stabilised by id set: any re-render
  // that doesn't change membership must hand the globe the *same* array, or
  // the layer treats every entry as new and restarts the dash animation.
  const liveFlaggedRef = useRef({ key: "", arr: [] });
  const liveFlagged = useMemo(() => {
    const next = liveAllowed.filter((e) => e.status === "FLAGGED" || e.status === "BLOCKED");
    const key = next.map((e) => e.txn_id).join(",");
    if (key === liveFlaggedRef.current.key) return liveFlaggedRef.current.arr;
    liveFlaggedRef.current = { key, arr: next };
    return next;
  }, [liveAllowed]);

  // One stable object per live transaction, keyed by txn_id. The globe updates
  // its arc/point layers with a data join keyed by the datum *reference*, so an
  // object that survives an update keeps its three.js arc — and the dash phase
  // animating inside it — alive. Building new objects on every tick (what the
  // old `.map()` did) destroyed and rebuilt every halo at once, which is why a
  // single arriving transaction used to reset the whole constellation.
  const liveArcsRef = useRef(new Map());
  const livePointsRef = useRef(new Map());
  const liveRingsRef = useRef(new Map());
  // Transactions whose halo already dissipated: the feed keeps their event in
  // the buffer, and without this they would be re-created (and flash again) the
  // moment the registry dropped them.
  const retiredRef = useRef(new Set());
  const flaggedRef = useRef(liveFlagged);
  flaggedRef.current = liveFlagged;

  const syncLive = useCallback(() => {
    const now = nowRef.current;
    let changed = false;

    // Rank is recency: index 0 is the arrival, index 10 is the one that must go.
    const candidates = flaggedRef.current.filter((e) => e.origin && e.lat != null);
    const alive = new Set();
    candidates.forEach((e, rank) => {
      alive.add(e.txn_id);
      let arc = liveArcsRef.current.get(e.txn_id);
      if (!arc && !retiredRef.current.has(e.txn_id)) {
        const bornAt = e.receivedAt || now;
        arc = {
          kind: "activity_arc",
          id: `live-${e.txn_id}`,
          live: true,
          txn_id: e.txn_id,
          status: e.status,
          flag_reason: e.flag_reason,
          region: e.region,
          branch: e.origin.branch,
          branch_code: e.origin.branch_code,
          merchant: e.merchant,
          startLat: e.origin.lat,
          startLng: e.origin.lng,
          endLat: e.lat,
          endLng: e.lng,
          color: FLAG_ARC_COLOR[e.flag_reason] || "#ffffff",
          bornAt,
          fadeAt: null,
        };
        liveArcsRef.current.set(e.txn_id, arc);
        livePointsRef.current.set(e.txn_id, {
          kind: "suspicious_activity",
          id: `live-${e.txn_id}`,
          live: true,
          txn_id: e.txn_id,
          txn_ts: e.txn_ts,
          amount_cents: e.amount_cents,
          status: e.status,
          flag_reason: e.flag_reason,
          channel: e.channel,
          region: e.region,
          merchant: e.merchant,
          merchant_category: e.merchant_category,
          lat: e.lat,
          lng: e.lng,
          color: FLAG_ARC_COLOR[e.flag_reason] || "#f80000",
          bornAt,
          fadeAt: null,
        });
        // Birth ping: the one cue that reads as "this just landed", gone after
        // the flash so it never competes with the steady halos.
        liveRingsRef.current.set(e.txn_id, {
          live: true,
          lat: e.lat,
          lng: e.lng,
          color: FLAG_ARC_COLOR[e.flag_reason] || "#f80000",
          bornAt,
        });
        changed = true;
      }
      // Pushed past the cap, or aged out of the window: start the fade once —
      // the arc keeps gliding while it dissipates instead of being cut.
      // (`arc` is null for a transaction whose halo already dissipated: the
      // feed still buffers its event, and nothing about it is drawn again.)
      if (arc && !arc.fadeAt && (rank >= LIVE_ARC_MAX || now - arc.bornAt > LIVE_ARC_TTL_MS)) {
        arc.fadeAt = now;
        const point = livePointsRef.current.get(e.txn_id);
        if (point) point.fadeAt = now;
        changed = true;
      }
    });

    for (const [txnId, arc] of liveArcsRef.current) {
      if (!alive.has(txnId) && !arc.fadeAt) {
        arc.fadeAt = now;
        const point = livePointsRef.current.get(txnId);
        if (point) point.fadeAt = now;
        changed = true;
      }
      if (arc.fadeAt && now - arc.fadeAt > LIVE_ARC_FADE_MS) {
        liveArcsRef.current.delete(txnId);
        livePointsRef.current.delete(txnId);
        retiredRef.current.add(txnId);
        changed = true;
      }
    }
    // Once an event has aged out of the feed buffer there is nothing left to
    // guard against, so the retired set stays bounded by the buffer size.
    for (const txnId of retiredRef.current) {
      if (!alive.has(txnId)) retiredRef.current.delete(txnId);
    }

    for (const [txnId, ring] of liveRingsRef.current) {
      if (now - ring.bornAt > LIVE_FRESH_MS + 700) {
        liveRingsRef.current.delete(txnId);
        changed = true;
      }
    }
    return changed;
  }, []);

  useEffect(() => {
    const id = window.setInterval(() => {
      nowRef.current = Date.now();
      if (syncLive()) setLiveVersion((v) => v + 1);
      if (liveArcsRef.current.size) setArcTick((t) => t + 1);
    }, LIVE_TICK_MS);
    return () => window.clearInterval(id);
  }, [syncLive]);

  // A feed event can land between ticks — pull it in immediately so the birth
  // flash starts on arrival rather than up to 250 ms later.
  useEffect(() => {
    nowRef.current = Date.now();
    if (syncLive()) setLiveVersion((v) => v + 1);
  }, [liveFlagged, syncLive]);

  // Arrays are rebuilt per tick on purpose (that is what makes the globe
  // re-read the arc accessors); the *objects* inside them never change
  // identity, which is what keeps the halos in flight.
  const liveArcs = useMemo(() => [...liveArcsRef.current.values()], [arcTick, liveVersion]);
  const livePoints = useMemo(() => [...livePointsRef.current.values()], [liveVersion]);
  const liveRings = useMemo(() => [...liveRingsRef.current.values()], [liveVersion, arcTick]);

  // Persona switches can overlap; a slow response for the previous identity
  // must never replace the current identity's (possibly stricter) world.
  const worldReq = useRef(0);
  const fetchWorld = () => {
    const req = ++worldReq.current;
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
        if (req !== worldReq.current) return;
        if (d && d.error) {
          setError(d.error);
          return;
        }
        setData(d);
      })
      .catch((e) => {
        if (req === worldReq.current) setError(String(e?.message || e));
      })
      .finally(() => {
        if (req === worldReq.current) setLoading(false);
      });
  };

  // Fetch on mount and whenever the acting identity changes.
  useEffect(() => {
    fetchWorld();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [identityId]);

  // When the agent resolves a focus target, fly the camera to it. Runs on mount
  // too, so a focus that arrived while the tab was hidden still applies.
  useEffect(() => {
    if (!focusTarget || focusTarget.lat == null || focusTarget.lng == null) return;
    const t = window.setTimeout(() => {
      if (globeRef.current) {
        globeRef.current.pointOfView(
          { lat: focusTarget.lat, lng: focusTarget.lng, altitude: focusTarget.altitude || 1.5 },
          1500,
        );
      }
    }, 60);
    setSearchResult({
      kind: focusTarget.kind,
      id: focusTarget.target,
      name: focusTarget.label,
      lat: focusTarget.lat,
      lng: focusTarget.lng,
      region: focusTarget.region,
    });
    return () => window.clearTimeout(t);
  }, [focusTarget]);

  // react-globe.gl wants explicit pixel dimensions; measure the canvas wrapper.
  useEffect(() => {
    if (!wrapRef.current) return;
    const ro = new ResizeObserver(() => {
      // The observer can fire once more after the panel unmounts (tab switch),
      // when the wrapper ref is already gone.
      if (!wrapRef.current) return;
      const rect = wrapRef.current.getBoundingClientRect();
      setGlobeSize({
        w: Math.max(240, Math.round(rect.width)),
        h: Math.max(240, Math.round(rect.height)),
      });
    });
    ro.observe(wrapRef.current);
    return () => ro.disconnect();
  }, []);

  // Base markers are built once per dataset/layer change; their live values
  // (size, colour) come from accessors so re-renders never re-create them —
  // a re-created marker is a destroyed and re-animated cylinder.
  const basePoints = useMemo(() => {
    const out = [];
    if (layers.branches) {
      for (const b of data.branches) {
        out.push({ ...b, _layer: "branches", size: 0.18, color: LAYER_COLORS.branch });
      }
    }
    if (layers.merchants) {
      for (const m of data.merchants) {
        out.push({ ...m, _layer: "merchants", size: 0.12, color: LAYER_COLORS.merchant });
      }
    }
    if (layers.suspicious_activity) {
      for (const s of data.suspicious_activity || []) {
        out.push({ ...s, _layer: "suspicious_activity", size: 0.3, color: LAYER_COLORS.suspicious_activity });
      }
    }
    if (searchResult) {
      out.push({
        ...searchResult,
        kind: searchResult.kind,
        color: LAYER_COLORS[searchResult.kind] || "#ffffff",
        searchAnchor: true,
      });
    }
    return out;
  }, [data, layers, searchResult]);

  // pulseLayers/pulseOn are dependencies on purpose: the accessors read them
  // through a ref, so the *array* has to change identity for the globe to
  // re-evaluate the markers while the agent's layer pulse breathes.
  const points = useMemo(
    () => [...basePoints, ...livePoints],
    [basePoints, livePoints, pulseKey, pulseOn],
  );

  // Base arcs keep their identity across live updates too — otherwise every
  // arriving transaction would rebuild the fetched arcs along with the live
  // ones (and restart their halos).
  const baseArcs = useMemo(
    () => (data.activity_arcs || [])
      .filter((a) => a.origin && a.destination)
      .map((a) => ({
        startLat: a.origin.lat,
        startLng: a.origin.lng,
        endLat: a.destination.lat,
        endLng: a.destination.lng,
        color: FLAG_ARC_COLOR[a.flag_reason] || "#ffffff",
        live: false,
        ...a,
      })),
    [data.activity_arcs],
  );

  const arcs = useMemo(() => {
    if (!layers.suspicious_activity) return [];
    return [...baseArcs, ...liveArcs];
  }, [baseArcs, layers.suspicious_activity, liveArcs]);

  // Ripples: the anchor the agent flew to (steady ping) plus the birth ping of
  // the freshest live AML hits — so a detection pulses once as it arrives and
  // then settles into the arc.
  const searchRing = useMemo(
    () => (searchResult && searchResult.lat != null && searchResult.lng != null
      ? { lat: searchResult.lat, lng: searchResult.lng, color: LAYER_COLORS[searchResult.kind] || "#ffd166", anchor: true, bornAt: 0 }
      : null),
    [searchResult],
  );

  const rings = useMemo(
    () => (searchRing ? [searchRing, ...liveRings] : liveRings),
    [searchRing, liveRings],
  );

  const onSearch = (e) => {
    e.preventDefault();
    const raw = searchQ.trim();
    if (!raw) return;
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
          globeRef.current.pointOfView({ lat: body.lat, lng: body.lng, altitude: 1.6 }, 1500);
        }
      })
      .catch((e) => {
        setSearchError(String(e?.message || e));
        setSearchResult(null);
      });
  };

  // ---- Globe accessors -----------------------------------------------------
  // Stable callbacks on purpose: react-kapsule re-applies a prop only when its
  // identity changes, so a heartbeat re-render can never re-enter the point
  // layer (hundreds of markers) — the live arc layer gets a fresh data array
  // instead (see `arcs`), which is all the pulse needs to re-read `nowRef`.
  const pulseRef = useRef({ layers: pulseLayers, on: pulseOn });
  pulseRef.current = { layers: pulseLayers, on: pulseOn };

  const pointAltitudeOf = useCallback(
    (d) => (d.searchAnchor ? 0.06 : d.kind === "suspicious_activity" ? 0.012 : 0.008),
    [],
  );

  const pointRadiusOf = useCallback((d) => {
    if (d.searchAnchor) return 0.9;
    if (d.live) return _livePointRadius(d, nowRef.current);
    const pulse = pulseRef.current;
    const grow = pulse.layers.has(d._layer) ? (pulse.on ? 1.9 : 1.35) : 1;
    return d.size * grow;
  }, []);

  const pointColorOf = useCallback((d) => {
    if (!d.live) return d.color;
    const now = nowRef.current;
    const age = Math.max(0, now - d.bornAt);
    if (age < LIVE_FRESH_MS) return _rgbaMix("#ffffff", d.color, age / LIVE_FRESH_MS, 1);
    return _rgba(d.color, _liveAlpha(d, now, 0.18));
  }, []);

  const pointLabelOf = useCallback((d) => buildLabel(d), []);

  const onPointClick = useCallback((d) => {
    if (globeRef.current) {
      globeRef.current.pointOfView({ lat: d.lat, lng: d.lng, altitude: 1.4 }, 1000);
    }
  }, []);

  // Arc colours carry the recency signal: the arrival is white-hot for a couple
  // of seconds, then cools into its AML colour and decays on a 45 s half-life.
  const arcColorOf = useCallback((d) => {
    if (!d.live) return d.color;
    const now = nowRef.current;
    const age = Math.max(0, now - d.bornAt);
    if (age < LIVE_FRESH_MS) return _rgbaMix("#ffffff", d.color, age / LIVE_FRESH_MS, 1);
    return _rgba(d.color, _liveAlpha(d, now, 0.1));
  }, []);

  const arcStrokeOf = useCallback((d) => {
    if (!d.live) return BASE_ARC_STROKE;
    const now = nowRef.current;
    const age = Math.max(0, now - d.bornAt);
    if (age < LIVE_FRESH_MS) return 0.85 - 0.45 * (age / LIVE_FRESH_MS);
    if (!d.fadeAt) return BASE_ARC_STROKE;
    return Math.max(0.02, BASE_ARC_STROKE * (1 - (now - d.fadeAt) / LIVE_ARC_FADE_MS));
  }, []);

  // The arrival comet runs hot (fast dash) and settles into the steady glide.
  const arcDashAnimateOf = useCallback(
    (d) => (d.live && nowRef.current - d.bornAt < LIVE_FRESH_MS ? 1_200 : BASE_ARC_DASH_MS),
    [],
  );

  const arcDashLengthOf = useCallback(
    (d) => (d.live && nowRef.current - d.bornAt < LIVE_FRESH_MS ? 0.6 : 0.45),
    [],
  );

  const arcLabelOf = useCallback((d) =>
    `<div style="font-family:ui-monospace,Menlo,monospace;font-size:11px;color:#f5f5f5;background:#0a0a0acc;padding:6px 8px;border:1px solid rgba(255,255,255,0.1);border-radius:4px">
               <strong>txn ${_txt(d.id)}</strong> · ${_txt(d.status)}<br/>
               ${_txt(d.branch)} → ${_txt(d.merchant)}<br/>
               <span style="color:#888">${_txt(d.flag_reason, "AML")} · ${_txt(d.region)}</span>
             </div>`, []);

  // Birth ping: white, fast, gone in ~3 s; the search anchor keeps its steady
  // ripple.
  const ringColorOf = useCallback((d) => {
    if (!d.live) return d.color;
    const t = Math.min(1, Math.max(0, nowRef.current - d.bornAt) / (LIVE_FRESH_MS + 700));
    return _rgbaMix("#ffffff", d.color, t, 1 - 0.8 * t);
  }, []);
  const ringMaxRadiusOf = useCallback((d) => (d.anchor ? 4 : 3.2), []);
  const ringSpeedOf = useCallback((d) => (d.anchor ? 2.2 : 3.6), []);
  const ringRepeatOf = useCallback((d) => (d.anchor ? 800 : 520), []);

  const noFeatures = !loading && !error && data.stats.branches === 0;

  return (
    <div className="h-full flex flex-col min-h-0">
      {/* Toolbar — search, layer toggles, refresh */}
      <div className="shrink-0 border-b border-white/5 bg-bg-panel/60 px-3 py-2 space-y-2">
        <form onSubmit={onSearch} className="flex items-center gap-2">
          <Search size={12} className="text-text-muted shrink-0" />
          <input
            type="text"
            value={searchQ}
            onChange={(e) => setSearchQ(e.target.value)}
            placeholder="fly to — branch, merchant, customer, or region (Wall Street · BitVault Exchange · EUROPE)"
            className="flex-1 min-w-0 bg-transparent text-[11px] font-mono text-text-primary placeholder:text-text-muted focus:outline-none"
          />
          <button
            type="submit"
            className="text-[10px] px-2 py-0.5 rounded border border-white/10 text-text-secondary hover:text-text-primary hover:border-accent-skill/40"
          >
            fly
          </button>
          <button
            type="button"
            onClick={fetchWorld}
            className="p-1 rounded text-text-muted hover:text-text-primary hover:bg-white/5"
            title="refresh world data"
          >
            <RefreshCw size={12} className={loading ? "animate-spin" : ""} />
          </button>
        </form>

        <div className="flex items-center gap-2 flex-wrap">
          {Object.entries(layers).map(([k, v]) => {
            const Icon = KIND_ICON[k] || Building2;
            return (
              <button
                key={k}
                onClick={() => setLayers((s) => ({ ...s, [k]: !s[k] }))}
                className={`flex items-center gap-1 px-1.5 py-0.5 rounded border text-[10px] font-mono ${
                  v
                    ? "border-white/10 bg-white/[0.05] text-text-primary"
                    : "border-white/5 text-text-muted hover:text-text-secondary"
                } ${pulseLayers.has(k) ? "data-explorer-pulse-read" : ""}`}
                title={`toggle ${k} layer`}
              >
                <Icon size={10} style={{ color: LAYER_COLORS[k] || "#888" }} />
                {k === "suspicious_activity" ? "flagged" : k}
              </button>
            );
          })}
          <button
            onClick={onToggleAutoFollow}
            className={`flex items-center gap-1 px-1.5 py-0.5 rounded border text-[10px] font-mono ${
              autoFollow
                ? "border-accent-skill/40 bg-accent-skill/10 text-accent-skill"
                : "border-white/5 text-text-muted hover:text-text-secondary"
            }`}
            title={
              autoFollow
                ? "auto-follow on — the globe flies to the regions the agent queries"
                : "auto-follow off — only explicit focus_world calls move the globe"
            }
          >
            <Crosshair size={10} />
            auto-follow {autoFollow ? "on" : "off"}
          </button>
          <span className="ml-auto text-[10px] text-text-muted font-mono">
            {data.stats.branches} br · {data.stats.merchants} merch ·{" "}
            {data.stats.suspicious_activity + livePoints.length} flagged · {data.stats.activity_arcs} recent arcs
            {live?.counts?.total > 0 && (
              <> · <span className="text-accent-oracle">+{live.counts.total} live</span></>
            )}
          </span>
        </div>

        {(searchError || searchResult) && (
          <div className="text-[10px] font-mono">
            {searchError ? (
              <span className="text-accent-sql">{searchError}</span>
            ) : (
              <span className="text-accent-memory">
                → {searchResult.kind}: {searchResult.name || searchResult.description || searchResult.id}{" "}
                ({_fix(searchResult.lat, 2)}, {_fix(searchResult.lng, 2)})
              </span>
            )}
          </div>
        )}
      </div>

      {/* Live data feed — new transactions streaming in */}
      {live?.enabled && liveAllowed.length > 0 && (
        <div className="shrink-0 px-3 py-1 border-b border-white/5 flex items-center gap-2 text-[10px] font-mono">
          <span className="inline-block w-1.5 h-1.5 rounded-full bg-accent-oracle animate-pulse shrink-0" />
          <span className="text-accent-oracle shrink-0">live</span>
          {liveAllowed[0].status !== "COMPLETED" ? (
            <span className="truncate">
              <span className="text-accent-sql">
                {liveAllowed[0].status} · {liveAllowed[0].flag_reason}
              </span>
              <span className="text-text-muted">
                {" · "}
                {amountMasked ? "[REDACTED]" : `$${(liveAllowed[0].amount_cents / 100).toLocaleString()}`}
                {" · "}
                {liveAllowed[0].merchant || liveAllowed[0].origin?.branch || liveAllowed[0].region}
              </span>
            </span>
          ) : (
            <span className="truncate text-text-muted">
              txn {liveAllowed[0].txn_id} ·{" "}
              {amountMasked ? "[REDACTED]" : `$${(liveAllowed[0].amount_cents / 100).toLocaleString()}`}
              {" · "}
              {liveAllowed[0].merchant || liveAllowed[0].region}
            </span>
          )}
          <span className="ml-auto text-text-muted shrink-0">
            +{live.counts.total} · {live.counts.flagged + live.counts.blocked} AML
          </span>
        </div>
      )}

      {/* Live tool ticker — what the agent is doing right now */}
      {isThinking && liveTool && (
        <div className="shrink-0 px-3 py-1 border-b border-white/5 flex items-center gap-2 text-[10px] font-mono bg-accent-skill/[0.04]">
          <span className="inline-block w-1.5 h-1.5 rounded-full bg-accent-skill animate-pulse shrink-0" />
          <span className="text-accent-skill shrink-0">
            {liveTool.done ? "✓" : "▶"} {liveTool.name}
          </span>
          {liveTool.tables.length > 0 && (
            <span className="text-text-muted truncate">
              {liveTool.tables.map((t) => t.split(".").pop()).join(", ")}
            </span>
          )}
          <span className="ml-auto text-text-muted shrink-0">agent working…</span>
        </div>
      )}

      {/* Live activity — what the agent is looking at right now */}
      {lastActivity && lastActivity.lat != null && (
        <div className="shrink-0 px-3 py-1 border-b border-white/5 flex items-center gap-2 text-[10px] font-mono">
          <span
            className={`inline-block w-1.5 h-1.5 rounded-full shrink-0 ${
              activityFresh ? "bg-accent-skill animate-pulse" : "bg-text-muted/40"
            }`}
          />
          <span className="text-text-muted shrink-0">
            {lastActivity.source === "explicit" ? "agent" : "auto"}
          </span>
          <span className="text-text-primary truncate">
            {lastActivity.kind}: {lastActivity.label || lastActivity.target}
          </span>
          <span className="text-text-muted truncate ml-auto">
            {_fix(lastActivity.lat, 2)}, {_fix(lastActivity.lng, 2)}
          </span>
          {!autoFollow && lastActivity.source === "auto" && (
            <span className="text-text-muted/70 shrink-0">· auto-follow off</span>
          )}
        </div>
      )}

      {/* Agent-driven focus banner */}
      {agentFocus && (
        <div className="shrink-0 px-3 py-1.5 border-b border-accent-oracle/30 bg-accent-oracle/10 flex items-center gap-2 text-[11px] font-mono">
          <Globe2 size={11} className="text-accent-oracle shrink-0" />
          {agentFocus.pending ? (
            <>
              <span className="text-accent-oracle">agent is flying the globe</span>
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-accent-oracle animate-pulse" />
              <span className="text-text-muted truncate">
                {agentFocus.kind}: {agentFocus.target || "…"}
              </span>
            </>
          ) : (
            <>
              <span className="text-accent-oracle shrink-0">agent flew the globe →</span>
              <span className="text-text-primary truncate">{agentFocus.label || agentFocus.target}</span>
              <span className="text-text-muted truncate">
                ({agentFocus.kind} · {_fix(agentFocus.lat, 2)}, {_fix(agentFocus.lng, 2)})
              </span>
            </>
          )}
          <button
            className="ml-auto text-[10px] text-text-muted hover:text-text-primary shrink-0"
            onClick={onDismissFocus}
            title="dismiss"
          >
            ×
          </button>
        </div>
      )}

      {/* Globe canvas */}
      <div ref={wrapRef} className="flex-1 relative overflow-hidden bg-[#000308] min-h-0">
        {noFeatures && (
          <div className="absolute inset-0 flex items-center justify-center text-text-muted text-xs">
            no geo features available — has the FINANCE seed run?
          </div>
        )}
        {error && (
          <div className="absolute inset-0 flex items-center justify-center px-6 text-center text-accent-sql text-[11px] font-mono">
            {String(error).slice(0, 200)}
          </div>
        )}
        {/* Earth textures are served from public/globe so the globe renders
            offline and over plain http:// — protocol-relative unpkg.com URLs
            resolve to http:// and die on unpkg's cross-origin https redirect. */}
        <Globe
          ref={globeRef}
          width={globeSize.w}
          height={globeSize.h}
          backgroundColor="#000308"
          globeImageUrl="/globe/earth-night.jpg"
          bumpImageUrl="/globe/earth-topology.png"
          showAtmosphere={true}
          atmosphereColor="#3b82f6"
          atmosphereAltitude={0.18}
          pointsData={points}
          pointLat="lat"
          pointLng="lng"
          pointColor={pointColorOf}
          pointAltitude={pointAltitudeOf}
          pointRadius={pointRadiusOf}
          pointLabel={pointLabelOf}
          onPointClick={onPointClick}
          ringsData={rings}
          ringLat="lat"
          ringLng="lng"
          ringColor={ringColorOf}
          ringMaxRadius={ringMaxRadiusOf}
          ringPropagationSpeed={ringSpeedOf}
          ringRepeatPeriod={ringRepeatOf}
          ringAltitude={0.006}
          arcsData={arcs}
          arcStartLat="startLat"
          arcStartLng="startLng"
          arcEndLat="endLat"
          arcEndLng="endLng"
          arcColor={arcColorOf}
          arcAltitudeAutoScale={0.4}
          arcStroke={arcStrokeOf}
          arcDashLength={arcDashLengthOf}
          arcDashGap={0.15}
          arcDashAnimateTime={arcDashAnimateOf}
          arcLabel={arcLabelOf}
        />
        {/* Radar sweep — runs while the agent works so the globe reads as
            live even when the query has no single location to fly to. */}
        <div
          className="pointer-events-none absolute rounded-full"
          style={{
            width: Math.round(Math.min(globeSize.w, globeSize.h) * 0.96),
            height: Math.round(Math.min(globeSize.w, globeSize.h) * 0.96),
            left: "50%",
            top: "50%",
            transform: "translate(-50%, -50%) rotate(0deg)",
            background:
              "conic-gradient(from 0deg, rgba(17,138,178,0) 0deg, rgba(17,138,178,0.30) 22deg, rgba(17,138,178,0) 46deg)",
            animation: "globe-sweep 4s linear infinite",
            opacity: isThinking ? 0.9 : 0,
            transition: "opacity 400ms ease",
          }}
        />
      </div>
    </div>
  );
}

// Pull out the value the user actually meant when they typed something like
// "branch (Wall Street)", "merchant: BitVault", or just "EUROPE". The backend's
// LIKE is wide so we mostly need to drop the descriptive label and parens.
function sanitizeQuery(raw) {
  let q = raw;
  const paren = q.match(/\(([^)]+)\)/);
  if (paren) {
    q = paren[1];
  } else {
    q = q.replace(/^\s*(branch|merchant|customer|region)s?\s*[:\-]\s*/i, "");
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
// Tooltip strings are rendered as HTML by three-globe; DB values (merchant and
// customer names) must be escaped.
const _esc = (s) =>
  String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const _txt = (v, fallback = "—") =>
  v == null || v === "" ? fallback : _esc(v);

const _usd = (cents) => {
  if (cents == null || !Number.isFinite(Number(cents))) return "—";
  return "$" + (Number(cents) / 100).toLocaleString("en-US", {
    minimumFractionDigits: 2, maximumFractionDigits: 2,
  });
};

// three-globe parses per-vertex `rgba(r, g, b, a)` colours, so the live layer's
// recency intensity rides on the alpha channel and never has to touch materials
// or geometry.
const _hexToRgb = (hex) => {
  const h = String(hex || "#ffffff").replace("#", "");
  const n = parseInt(h.length === 3 ? h.split("").map((c) => c + c).join("") : h, 16);
  return Number.isFinite(n) ? [(n >> 16) & 255, (n >> 8) & 255, n & 255] : [255, 255, 255];
};
const _clamp01 = (v) => Math.max(0, Math.min(1, v));
// Alpha is quantised to 1%: the points layer caches one material per colour
// string, so continuous alphas would grow that cache without bound.
const _q = (a) => Math.round(_clamp01(a) * 100) / 100;
const _rgba = (hex, alpha) => {
  const [r, g, b] = _hexToRgb(hex);
  return `rgba(${r}, ${g}, ${b}, ${_q(alpha).toFixed(2)})`;
};
const _rgbaMix = (fromHex, toHex, t, alpha) => {
  const a = _hexToRgb(fromHex);
  const b = _hexToRgb(toHex);
  const k = _clamp01(t);
  const c = [0, 1, 2].map((i) => Math.round(a[i] + (b[i] - a[i]) * k));
  return `rgba(${c[0]}, ${c[1]}, ${c[2]}, ${_q(alpha).toFixed(2)})`;
};

// Live markers are slightly larger at birth and shrink back to the steady size.
const _livePointRadius = (d, now) => {
  const age = Math.max(0, now - d.bornAt);
  const base = age < LIVE_FRESH_MS ? 0.62 - 0.17 * (age / LIVE_FRESH_MS) : 0.45;
  return d.fadeAt ? Math.max(0.02, base * (1 - (now - d.fadeAt) / LIVE_ARC_FADE_MS)) : base;
};

// Recency → intensity, shared by arcs and markers: exponential decay with a
// 45 s half-life. The floor keeps an aged detection faintly visible; a fading
// entry then multiplies down to zero, which is what makes it dissipate instead
// of blinking out.
const _liveAlpha = (d, now, floor) => {
  const age = Math.max(0, now - d.bornAt);
  const recency = Math.max(floor, 0.5 ** (age / PULSE_HALF_LIFE_MS));
  if (!d.fadeAt) return recency;
  return recency * Math.max(0, 1 - (now - d.fadeAt) / LIVE_ARC_FADE_MS);
};

function buildLabel(d) {
  const styles =
    'font-family:ui-monospace,Menlo,monospace;font-size:11px;color:#f5f5f5;background:#0a0a0acc;padding:6px 8px;border:1px solid rgba(255,255,255,0.1);border-radius:4px;max-width:280px';

  if (d.searchAnchor) {
    const coord = `${_fix(d.lat, 2)}, ${_fix(d.lng, 2)}`;
    return `<div style="${styles}"><strong>${_txt(d.name || d.id)}</strong><br/>` +
           `<span style="color:#888">${_txt(d.kind, "anchor")}</span> · ${coord}` +
           (d.region ? `<br/>region: ${_txt(d.region)}` : "") +
           "</div>";
  }

  if (d.kind === "branch") {
    return `<div style="${styles}"><strong>${_txt(d.name)}</strong> (${_txt(d.branch_code)})<br/>` +
           `${_txt(d.city)}, ${_txt(d.country)} · ${_txt(d.region)}<br/>` +
           `opened: ${_txt(d.opened_year, "—")}</div>`;
  }
  if (d.kind === "merchant") {
    return `<div style="${styles}"><strong>${_txt(d.name)}</strong><br/>` +
           `MCC ${_txt(d.mcc_code)} · ${_txt(d.category)}<br/>` +
           `${_txt(d.country)} · ${_txt(d.region)}</div>`;
  }
  if (d.kind === "suspicious_activity") {
    return `<div style="${styles}"><strong>${_txt(d.flag_reason, "AML")}</strong> · ${_txt(d.status)}<br/>` +
           `${_usd(d.amount_cents)} via ${_txt(d.channel)}<br/>` +
           `merchant: ${_txt(d.merchant, "branch cash")} (${_txt(d.merchant_category, "—")})<br/>` +
           `txn #${_txt(d.txn_id)} · ${_txt(d.region)}</div>`;
  }
  if (d.kind === "customer") {
    return `<div style="${styles}"><strong>${_txt(d.name)}</strong><br/>` +
           `branch: ${_txt(d.branch)} (${_txt(d.city)})<br/>` +
           `region: ${_txt(d.region)}</div>`;
  }
  return `<div style="${styles}">${_txt(d.name || d.id)}</div>`;
}
