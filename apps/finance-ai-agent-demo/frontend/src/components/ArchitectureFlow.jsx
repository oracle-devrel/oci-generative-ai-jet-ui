import { useState, useEffect, useRef, useCallback, useMemo } from "react";

/*
 * ArchitectureFlow — real-time system architecture visualisation.
 *
 * Three vertical nodes:  Frontend  →  Backend / Agent  →  Oracle Database
 * Animated packets stream between nodes driven by live socket events.
 * Includes a replay timeline to scrub through past executions.
 */

// ─── Shared icons ────────────────────────────────────────────────────
const ICONS = {
  monitor: (
    <svg
      width="22"
      height="22"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
    >
      <rect x="2" y="3" width="20" height="14" rx="2" />
      <line x1="8" y1="21" x2="16" y2="21" />
      <line x1="12" y1="17" x2="12" y2="21" />
    </svg>
  ),
  cpu: (
    <svg
      width="22"
      height="22"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
    >
      <rect x="4" y="4" width="16" height="16" rx="2" />
      <path d="M9 9h6v6H9z" />
      <line x1="9" y1="2" x2="9" y2="4" />
      <line x1="15" y1="2" x2="15" y2="4" />
      <line x1="9" y1="20" x2="9" y2="22" />
      <line x1="15" y1="20" x2="15" y2="22" />
      <line x1="2" y1="9" x2="4" y2="9" />
      <line x1="2" y1="15" x2="4" y2="15" />
      <line x1="20" y1="9" x2="22" y2="9" />
      <line x1="20" y1="15" x2="22" y2="15" />
    </svg>
  ),
  db: (
    <svg
      width="22"
      height="22"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
    >
      <ellipse cx="12" cy="5" rx="9" ry="3" />
      <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" />
      <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
    </svg>
  ),
  dbSmall: (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
    >
      <ellipse cx="12" cy="5" rx="9" ry="3" />
      <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" />
      <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
    </svg>
  ),
  graph: (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
    >
      <circle cx="6" cy="6" r="3" />
      <circle cx="18" cy="6" r="3" />
      <circle cx="6" cy="18" r="3" />
      <circle cx="18" cy="18" r="3" />
      <line x1="9" y1="6" x2="15" y2="6" />
      <line x1="6" y1="9" x2="6" y2="15" />
      <line x1="18" y1="9" x2="18" y2="15" />
      <line x1="9" y1="18" x2="15" y2="18" />
    </svg>
  ),
  doc: (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
    >
      <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="16" y1="13" x2="8" y2="13" />
      <line x1="16" y1="17" x2="8" y2="17" />
    </svg>
  ),
  vector: (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
    >
      <circle cx="12" cy="12" r="10" />
      <path d="M12 2v10l7 4" />
    </svg>
  ),
};

// ─── Node definitions by architecture mode ───────────────────────────
const CONVERGED_NODES = [
  { id: "frontend", label: "Frontend", subtitle: "React · Chat UI", icon: ICONS.monitor },
  {
    id: "backend",
    label: "Backend / Agent",
    subtitle: "Flask · LLM Harness · Tools",
    icon: ICONS.cpu,
  },
  {
    id: "database",
    label: "Oracle AI Database",
    subtitle: "Vector · Relational · Graph · JSON · Spatial",
    icon: ICONS.db,
    color: "#DC2626",
  },
];

const SPRAWL_DB_NODES = [
  {
    id: "postgres",
    label: "PostgreSQL + PostGIS",
    subtitle: "Relational · Spatial",
    icon: ICONS.dbSmall,
    color: "#2563EB",
  },
  { id: "neo4j", label: "Neo4j CE", subtitle: "Graph", icon: ICONS.graph, color: "#059669" },
  {
    id: "mongodb",
    label: "MongoDB CE",
    subtitle: "JSON / Document",
    icon: ICONS.doc,
    color: "#D97706",
  },
  { id: "qdrant", label: "Qdrant", subtitle: "Vector", icon: ICONS.vector, color: "#7C3AED" },
];

// ─── Map event type to which node is "working" ──────────────────────
function getNodeForEvent(ev) {
  switch (ev?.type) {
    case "user_message":
      return "backend";
    case "tool_call":
      return "database";
    case "query_result":
      return "backend";
    case "response":
      return "frontend";
    default:
      return null;
  }
}

function getActiveNodesForEvent(ev) {
  switch (ev?.type) {
    case "user_message":
      return { frontend: true, backend: true };
    case "tool_call":
      return { backend: true, database: true };
    case "query_result":
      return { database: true, backend: true };
    case "response":
      return { backend: true, frontend: true };
    default:
      return {};
  }
}

// ─── Packet component (the animated dot that flows between nodes) ────
function Packet({ direction, segment, color, label }) {
  const topPx = segment === 0 ? 0 : 140;

  return (
    <div
      className="arch-packet"
      style={{
        "--packet-color": color,
        "--start-y": direction === "down" ? `${topPx}px` : `${topPx + 140}px`,
        "--end-y": direction === "down" ? `${topPx + 140}px` : `${topPx}px`,
      }}
    >
      <div className="arch-packet-dot" />
      {label && <span className="arch-packet-label">{label}</span>}
    </div>
  );
}

// ─── Event → Packet mapper ──────────────────────────────────────────
function eventToPacket(ev, id) {
  switch (ev.type) {
    case "user_message":
      return { id, direction: "down", segment: 0, color: "#C0C0C0", label: "query" };
    case "tool_call":
      return {
        id,
        direction: "down",
        segment: 1,
        color: "#7C3AED",
        label: ev.label || "tool call",
      };
    case "query_result":
      return { id, direction: "up", segment: 1, color: "#059669", label: ev.label || "result" };
    case "response":
      return { id, direction: "up", segment: 0, color: "#2563EB", label: "response" };
    default:
      return null;
  }
}

// ─── Main component ──────────────────────────────────────────────────
export default function ArchitectureFlow({ archEvents, isLoading, archMode = "converged" }) {
  const isSprawl = archMode === "sprawl" || archMode === "comparison";
  const [packets, setPackets] = useState([]);
  const processedRef = useRef(new Set());
  const packetIdRef = useRef(0);

  // ── Replay state ──────────────────────────────────────────────────
  const [replayMode, setReplayMode] = useState(false); // true = replaying, false = live
  const [replayIndex, setReplayIndex] = useState(0); // current step in replay
  const [replayPlaying, setReplayPlaying] = useState(false);
  const replayTimerRef = useRef(null);
  const replayPacketIdRef = useRef(10000);

  const allEvents = archEvents || [];
  const totalSteps = allEvents.length;

  // ── Live mode: derive packets from new events ─────────────────────
  useEffect(() => {
    if (replayMode) return; // don't process live events during replay
    if (!archEvents || archEvents.length === 0) return;

    const newPackets = [];
    for (const ev of archEvents) {
      if (processedRef.current.has(ev.id)) continue;
      processedRef.current.add(ev.id);

      const pktId = ++packetIdRef.current;
      const pkt = eventToPacket(ev, pktId);
      if (pkt) newPackets.push(pkt);
    }

    if (newPackets.length > 0) {
      setPackets((prev) => [...prev, ...newPackets]);
    }
  }, [archEvents, replayMode]);

  // Auto-clean old packets after animation ends
  useEffect(() => {
    if (packets.length === 0) return;
    const timer = setTimeout(() => {
      setPackets((prev) => prev.slice(-20));
    }, 1400);
    return () => clearTimeout(timer);
  }, [packets]);

  // ── Replay auto-play timer ────────────────────────────────────────
  useEffect(() => {
    if (!replayMode || !replayPlaying) return;
    if (replayIndex >= totalSteps - 1) {
      setReplayPlaying(false);
      return;
    }

    replayTimerRef.current = setTimeout(() => {
      setReplayIndex((i) => Math.min(i + 1, totalSteps - 1));
      // Fire a replay packet
      const ev = allEvents[replayIndex + 1];
      if (ev) {
        const pkt = eventToPacket(ev, ++replayPacketIdRef.current);
        if (pkt) setPackets((prev) => [...prev, pkt]);
      }
    }, 600);

    return () => clearTimeout(replayTimerRef.current);
  }, [replayMode, replayPlaying, replayIndex, totalSteps, allEvents]);

  // ── Replay controls ───────────────────────────────────────────────
  const enterReplay = useCallback(() => {
    setReplayMode(true);
    setReplayIndex(0);
    setReplayPlaying(false);
    setPackets([]);
  }, []);

  const exitReplay = useCallback(() => {
    setReplayMode(false);
    setReplayPlaying(false);
    setReplayIndex(0);
    setPackets([]);
    // Reset processed ref so live events can re-trigger if needed
  }, []);

  const togglePlay = useCallback(() => {
    if (replayIndex >= totalSteps - 1) {
      // Restart from beginning
      setReplayIndex(0);
      setReplayPlaying(true);
    } else {
      setReplayPlaying((p) => !p);
    }
  }, [replayIndex, totalSteps]);

  const stepForward = useCallback(() => {
    setReplayPlaying(false);
    setReplayIndex((i) => {
      const next = Math.min(i + 1, totalSteps - 1);
      const ev = allEvents[next];
      if (ev) {
        const pkt = eventToPacket(ev, ++replayPacketIdRef.current);
        if (pkt) setPackets((prev) => [...prev, pkt]);
      }
      return next;
    });
  }, [totalSteps, allEvents]);

  const stepBackward = useCallback(() => {
    setReplayPlaying(false);
    setReplayIndex((i) => Math.max(i - 1, 0));
    setPackets([]);
  }, []);

  const scrubTo = useCallback(
    (idx) => {
      setReplayPlaying(false);
      setReplayIndex(idx);
      // Fire packet for the scrubbed-to event
      const ev = allEvents[idx];
      if (ev) {
        const pkt = eventToPacket(ev, ++replayPacketIdRef.current);
        if (pkt) setPackets([pkt]);
      }
    },
    [allEvents]
  );

  // ── Determine active nodes + spinner ──────────────────────────────
  let activeNodes = {};
  let spinnerNode = null;

  if (replayMode) {
    // In replay, derive from current replay event
    const currentEvent = allEvents[replayIndex];
    if (currentEvent) {
      activeNodes = getActiveNodesForEvent(currentEvent);
      spinnerNode = getNodeForEvent(currentEvent);
    }
  } else {
    // Live mode
    if (isLoading) {
      activeNodes.frontend = true;
      activeNodes.backend = true;
      spinnerNode = "backend";
    }

    if (archEvents?.length) {
      const recent = archEvents.slice(-5);
      for (const ev of recent) {
        const age = Date.now() - ev.timestamp;
        if (age < 3000) {
          const nodes = getActiveNodesForEvent(ev);
          Object.assign(activeNodes, nodes);
          if (isLoading) spinnerNode = getNodeForEvent(ev);
        }
      }
    }
  }

  // ── Visible events (for the log) ──────────────────────────────────
  const visibleEvents = replayMode
    ? allEvents
        .slice(0, replayIndex + 1)
        .slice(-30)
        .reverse()
    : allEvents.slice(-30).reverse();

  // ── Timeline tick marks ───────────────────────────────────────────
  const timelineTicks = useMemo(() => {
    return allEvents.map((ev, i) => ({
      index: i,
      type: ev.type,
      color: EVENT_STYLES[ev.type]?.color || "#C0C0C0",
    }));
  }, [allEvents]);

  // ── Helper: render a single node card ──────────────────────────────
  const renderNode = (node, extraClass = "") => (
    <div
      className={`arch-node ${activeNodes[node.id] ? "arch-node-active" : ""} ${spinnerNode === node.id ? "arch-node-spinning" : ""} ${extraClass}`}
      style={
        node.color ? { "--node-accent": node.color, borderColor: `${node.color}50` } : undefined
      }
    >
      <div
        className="arch-node-icon"
        style={node.color ? { color: node.color, borderColor: `${node.color}40` } : undefined}
      >
        {spinnerNode === node.id ? (
          <svg
            className="arch-spinner"
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <path d="M12 2a10 10 0 0 1 10 10" strokeLinecap="round" />
          </svg>
        ) : (
          node.icon
        )}
      </div>
      <div className="arch-node-info">
        <div className="arch-node-label">{node.label}</div>
        <div className="arch-node-subtitle">{node.subtitle}</div>
      </div>
      {activeNodes[node.id] && <div className="arch-node-pulse" />}
    </div>
  );

  const renderConnector = () => (
    <div className="arch-connector">
      <div className="arch-connector-line" />
      <div className="arch-connector-arrow">
        <svg width="10" height="10" viewBox="0 0 10 10">
          <path d="M2 2 L5 8 L8 2" fill="none" stroke="rgba(192,192,192,0.3)" strokeWidth="1.5" />
        </svg>
      </div>
    </div>
  );

  return (
    <div className="flex flex-col h-full">
      {/* Visualization area */}
      <div className="flex-1 flex flex-col items-center justify-center relative px-6 py-4 min-h-0 overflow-y-auto">
        {!isSprawl ? (
          /* ── Converged layout: vertical stack ────────────────── */
          <div className="arch-container">
            {CONVERGED_NODES.map((node, idx) => (
              <div key={node.id}>
                {renderNode(node)}
                {idx < CONVERGED_NODES.length - 1 && renderConnector()}
              </div>
            ))}
            <div className="arch-packets-layer">
              {packets.map((pkt) => (
                <Packet key={pkt.id} {...pkt} />
              ))}
            </div>
          </div>
        ) : (
          /* ── Sprawl layout: fan-out to 4 databases ──────────── */
          <div className="arch-sprawl-container">
            {/* Frontend */}
            {renderNode({
              id: "frontend",
              label: "Frontend",
              subtitle: "React · Chat UI",
              icon: ICONS.monitor,
            })}
            {renderConnector()}
            {/* Backend */}
            {renderNode({
              id: "backend",
              label: "Backend / Agent",
              subtitle: "Flask · LLM Harness · Tools",
              icon: ICONS.cpu,
            })}

            {/* Fan-out connector */}
            <div className="arch-fanout">
              <svg width="100%" height="32" viewBox="0 0 280 32" preserveAspectRatio="none">
                <path
                  d="M140 0 L35 32"
                  fill="none"
                  stroke="rgba(192,192,192,0.2)"
                  strokeWidth="1"
                  strokeDasharray="4 4"
                />
                <path
                  d="M140 0 L105 32"
                  fill="none"
                  stroke="rgba(192,192,192,0.2)"
                  strokeWidth="1"
                  strokeDasharray="4 4"
                />
                <path
                  d="M140 0 L175 32"
                  fill="none"
                  stroke="rgba(192,192,192,0.2)"
                  strokeWidth="1"
                  strokeDasharray="4 4"
                />
                <path
                  d="M140 0 L245 32"
                  fill="none"
                  stroke="rgba(192,192,192,0.2)"
                  strokeWidth="1"
                  strokeDasharray="4 4"
                />
              </svg>
            </div>

            {/* 4 database nodes in a 2x2 grid */}
            <div className="arch-sprawl-grid">
              {SPRAWL_DB_NODES.map((node) => (
                <div key={node.id}>{renderNode(node, "arch-node-compact")}</div>
              ))}
            </div>

            {/* Sprawl cost label */}
            <div className="mt-3 text-center">
              <span className="text-[9px] text-text-secondary/40 uppercase tracking-wider">
                4 engines · 4 connections · 4 failure domains
              </span>
            </div>

            <div className="arch-packets-layer">
              {packets.map((pkt) => (
                <Packet key={pkt.id} {...pkt} />
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Replay timeline */}
      <div className="border-t border-white/5 shrink-0 px-3 py-2">
        <div className="flex items-center gap-2">
          {/* Replay / Live toggle */}
          {!replayMode ? (
            <button
              onClick={enterReplay}
              disabled={totalSteps === 0}
              className="arch-timeline-btn"
              title="Replay execution"
            >
              <svg
                width="12"
                height="12"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path d="M1 4v6h6" />
                <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10" />
              </svg>
              <span>Replay</span>
            </button>
          ) : (
            <button
              onClick={exitReplay}
              className="arch-timeline-btn arch-timeline-btn-active"
              title="Back to live"
            >
              <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
              <span>Live</span>
            </button>
          )}

          {replayMode && (
            <>
              {/* Step backward */}
              <button
                onClick={stepBackward}
                disabled={replayIndex <= 0}
                className="arch-timeline-btn"
                title="Step back"
              >
                <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M19 20L9 12l10-8v16zM7 19H5V5h2v14z" />
                </svg>
              </button>

              {/* Play / Pause */}
              <button
                onClick={togglePlay}
                className="arch-timeline-btn"
                title={replayPlaying ? "Pause" : "Play"}
              >
                {replayPlaying ? (
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
                    <rect x="6" y="4" width="4" height="16" />
                    <rect x="14" y="4" width="4" height="16" />
                  </svg>
                ) : (
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M8 5v14l11-7z" />
                  </svg>
                )}
              </button>

              {/* Step forward */}
              <button
                onClick={stepForward}
                disabled={replayIndex >= totalSteps - 1}
                className="arch-timeline-btn"
                title="Step forward"
              >
                <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M5 4l10 8-10 8V4zM17 5h2v14h-2V5z" />
                </svg>
              </button>

              {/* Step counter */}
              <span className="text-[10px] text-text-secondary/50 font-mono tabular-nums shrink-0">
                {replayIndex + 1}/{totalSteps}
              </span>
            </>
          )}
        </div>

        {/* Draggable timeline scrubber */}
        {replayMode && totalSteps > 0 && (
          <DraggableTimeline
            ticks={timelineTicks}
            currentIndex={replayIndex}
            totalSteps={totalSteps}
            onScrub={scrubTo}
          />
        )}
      </div>

      {/* Event log */}
      <div className="border-t border-white/5 shrink-0">
        <div className="px-3 py-1.5 text-[10px] text-text-secondary/50 uppercase tracking-wider font-medium">
          {replayMode ? "Replay Events" : "Live Event Stream"}
        </div>
        <div className="overflow-y-auto max-h-[140px] px-3 pb-2 space-y-0.5">
          {visibleEvents.length === 0 ? (
            <div className="text-text-secondary/30 text-[11px] py-4 text-center">
              Send a message to see request flow
            </div>
          ) : (
            visibleEvents.map((ev, i) => (
              <EventRow key={ev.id} event={ev} highlight={replayMode && i === 0} />
            ))
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Draggable timeline ──────────────────────────────────────────────
function DraggableTimeline({ ticks, currentIndex, totalSteps, onScrub }) {
  const trackRef = useRef(null);
  const draggingRef = useRef(false);

  const indexFromEvent = useCallback(
    (e) => {
      const track = trackRef.current;
      if (!track || totalSteps === 0) return 0;
      const rect = track.getBoundingClientRect();
      const x = Math.max(0, Math.min(e.clientX - rect.left, rect.width));
      const ratio = x / rect.width;
      return Math.round(ratio * (totalSteps - 1));
    },
    [totalSteps]
  );

  const handlePointerDown = useCallback(
    (e) => {
      e.preventDefault();
      draggingRef.current = true;
      trackRef.current?.setPointerCapture(e.pointerId);
      onScrub(indexFromEvent(e));
    },
    [indexFromEvent, onScrub]
  );

  const handlePointerMove = useCallback(
    (e) => {
      if (!draggingRef.current) return;
      onScrub(indexFromEvent(e));
    },
    [indexFromEvent, onScrub]
  );

  const handlePointerUp = useCallback((e) => {
    draggingRef.current = false;
    trackRef.current?.releasePointerCapture(e.pointerId);
  }, []);

  const progressPct = totalSteps > 1 ? (currentIndex / (totalSteps - 1)) * 100 : 0;
  const currentColor = ticks[currentIndex]?.color || "#C0C0C0";

  return (
    <div className="mt-2 pb-1">
      <div
        ref={trackRef}
        className="arch-drag-track"
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerCancel={handlePointerUp}
      >
        {/* Filled portion */}
        <div className="arch-drag-fill" style={{ width: `${progressPct}%` }} />

        {/* Tick marks */}
        <div className="arch-drag-ticks">
          {ticks.map((tick) => (
            <div
              key={tick.index}
              className={`arch-drag-tick ${tick.index <= currentIndex ? "arch-drag-tick-past" : ""}`}
              style={{
                left: totalSteps > 1 ? `${(tick.index / (totalSteps - 1)) * 100}%` : "0%",
                "--tick-color": tick.color,
              }}
            />
          ))}
        </div>

        {/* Playhead */}
        <div
          className="arch-drag-playhead"
          style={{
            left: `${progressPct}%`,
            "--playhead-color": currentColor,
          }}
        />
      </div>
    </div>
  );
}

// ─── Event log row ───────────────────────────────────────────────────
const EVENT_STYLES = {
  user_message: { color: "#C0C0C0", icon: "\u2193", tag: "REQ" },
  tool_call: { color: "#7C3AED", icon: "\u2193", tag: "TOOL" },
  query_result: { color: "#059669", icon: "\u2191", tag: "DATA" },
  response: { color: "#2563EB", icon: "\u2191", tag: "RES" },
};

function EventRow({ event, highlight }) {
  const style = EVENT_STYLES[event.type] || EVENT_STYLES.user_message;
  const time = new Date(event.timestamp).toLocaleTimeString("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });

  return (
    <div
      className={`flex items-center gap-2 text-[11px] font-mono arch-event-enter ${highlight ? "arch-event-highlight" : ""}`}
    >
      <span className="text-text-secondary/40 w-[56px] shrink-0">{time}</span>
      <span
        className="w-[38px] shrink-0 text-center rounded px-1 py-0.5 text-[9px] font-bold uppercase"
        style={{
          backgroundColor: `${style.color}20`,
          color: style.color,
          border: `1px solid ${style.color}40`,
        }}
      >
        {style.tag}
      </span>
      <span className="text-text-secondary/60 truncate">
        {style.icon} {event.label || event.type}
      </span>
    </div>
  );
}
