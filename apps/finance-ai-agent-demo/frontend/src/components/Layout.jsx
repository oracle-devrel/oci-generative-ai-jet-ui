import { useState, useCallback, useRef, useEffect } from "react";
import NavPane from "./NavPane";
import ChatPane from "./ChatPane";
import QueryStream from "./QueryStream";
import AppLogs from "./AppLogs";
import ContextActivity from "./ContextActivity";
import ArchitectureFlow from "./ArchitectureFlow";
import LatencyComparison from "./LatencyComparison";

export default function Layout({ connected, chat, socket, comparisonAvailable }) {
  const [navCollapsed, setNavCollapsed] = useState(false);
  const [rightPaneWidth, setRightPaneWidth] = useState(380);
  const [rightTab, setRightTab] = useState("database"); // "database" | "application" | "context" | "architecture" | "latency"
  const [archMode, setArchMode] = useState("converged"); // "converged" | "sprawl" | "comparison"
  const resizing = useRef(false);

  const handleClearThread = useCallback(
    (tid) => {
      fetch(`/api/threads/${tid}/messages`, {
        method: "DELETE",
        headers: { "X-Confirm-Delete": "true" },
      }).catch(() => {});
      if (tid === chat.threadId) {
        chat.dispatch({ type: "LOAD_MESSAGES", payload: [] });
      }
    },
    [chat]
  );

  const handleDeleteThread = useCallback(
    (tid) => {
      fetch(`/api/threads/${tid}/messages`, {
        method: "DELETE",
        headers: { "X-Confirm-Delete": "true" },
      }).catch(() => {});
      if (tid === chat.threadId) {
        chat.newThread();
      }
    },
    [chat]
  );

  const copyThreadId = useCallback(() => {
    navigator.clipboard.writeText(chat.threadId).catch(() => {});
  }, [chat.threadId]);

  // Drag handle for right pane resize
  const dragHandlersRef = useRef({ move: null, up: null });

  const handleMouseDown = useCallback(() => {
    resizing.current = true;
    const handleMouseMove = (e) => {
      if (!resizing.current) return;
      const newWidth = window.innerWidth - e.clientX;
      setRightPaneWidth(Math.max(280, Math.min(600, newWidth)));
    };
    const handleMouseUp = () => {
      resizing.current = false;
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
      dragHandlersRef.current = { move: null, up: null };
    };
    dragHandlersRef.current = { move: handleMouseMove, up: handleMouseUp };
    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);
  }, []);

  // Cleanup drag listeners on unmount to prevent leaks
  useEffect(() => {
    return () => {
      if (dragHandlersRef.current.move) {
        document.removeEventListener("mousemove", dragHandlersRef.current.move);
      }
      if (dragHandlersRef.current.up) {
        document.removeEventListener("mouseup", dragHandlersRef.current.up);
      }
    };
  }, []);

  return (
    <div className="flex flex-col h-screen bg-primary">
      {/* Top bar */}
      <header className="flex items-center justify-between px-4 py-2 bg-secondary border-b border-white/5 shrink-0">
        <div className="flex items-center gap-3">
          <button
            onClick={() => setNavCollapsed(!navCollapsed)}
            className="text-text-secondary hover:text-text-primary transition p-1"
          >
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <line x1="3" y1="6" x2="21" y2="6" />
              <line x1="3" y1="12" x2="21" y2="12" />
              <line x1="3" y1="18" x2="21" y2="18" />
            </svg>
          </button>
          <span className="text-text-accent font-semibold text-sm tracking-wide">AFSA</span>
          {/* Architecture mode toggle */}
          <div className="flex items-center bg-primary/60 rounded-md border border-white/5 overflow-hidden">
            <button
              onClick={() => setArchMode("converged")}
              className={`px-2.5 py-1 text-[10px] font-medium transition ${
                archMode === "converged"
                  ? "bg-accent-sql/20 text-blue-400 border-r border-white/10"
                  : "text-text-secondary/50 hover:text-text-secondary border-r border-white/5"
              }`}
              title="Oracle Converged Database — all paradigms in one engine"
            >
              Converged
            </button>
            <button
              onClick={() => setArchMode("sprawl")}
              className={`px-2.5 py-1 text-[10px] font-medium transition ${
                archMode === "sprawl"
                  ? "bg-accent-hybrid/20 text-amber-400 border-r border-white/10"
                  : "text-text-secondary/50 hover:text-text-secondary border-r border-white/5"
              }`}
              title="Sprawl — Postgres + Neo4j + MongoDB + Qdrant"
            >
              Sprawl
            </button>
            <button
              onClick={() => {
                if (!comparisonAvailable) return;
                setArchMode("comparison");
                setRightTab("latency");
                chat.checkHealth();
              }}
              disabled={!comparisonAvailable}
              className={`px-2.5 py-1 text-[10px] font-medium transition ${
                !comparisonAvailable
                  ? "text-text-secondary/20 cursor-not-allowed"
                  : archMode === "comparison"
                    ? "bg-purple-500/20 text-purple-400"
                    : "text-text-secondary/50 hover:text-text-secondary"
              }`}
              title={
                comparisonAvailable
                  ? "Compare — run query through both architectures and compare latency"
                  : "Comparison unavailable — start both Oracle and sprawl databases"
              }
            >
              Compare
            </button>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span
            className={`w-2 h-2 rounded-full ${connected ? "bg-green-500 animate-pulse" : "bg-red-500"}`}
          />
          <span className="text-text-secondary text-xs">
            {connected ? "Connected" : "Disconnected"}
          </span>
          <button
            onClick={copyThreadId}
            className="text-text-secondary text-xs border border-white/10 rounded px-2 py-0.5 hover:border-white/20 hover:text-text-primary transition"
            title="Click to copy Thread ID"
          >
            Thread: {chat.threadId}
          </button>
          {/* Clear conversation button */}
          <button
            onClick={() => handleClearThread(chat.threadId)}
            className="p-1 text-text-secondary/50 hover:text-red-400 transition"
            title="Clear conversation"
          >
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <polyline points="3 6 5 6 21 6" />
              <path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2" />
            </svg>
          </button>
        </div>
      </header>

      {/* Three-pane layout */}
      <div className="flex flex-1 overflow-hidden">
        <NavPane
          collapsed={navCollapsed}
          onNewThread={chat.newThread}
          onLoadThread={chat.loadThread}
          onClearThread={handleClearThread}
          onDeleteThread={handleDeleteThread}
          threadId={chat.threadId}
        />
        <ChatPane chat={chat} socket={socket} archMode={archMode} />

        {/* Resize drag handle */}
        <div
          onMouseDown={handleMouseDown}
          className="w-1 cursor-col-resize hover:bg-text-accent/20 transition shrink-0"
        />

        {/* Right pane with tabs */}
        <div
          className="bg-secondary border-l border-white/5 flex flex-col shrink-0 overflow-hidden"
          style={{ width: `${rightPaneWidth}px` }}
        >
          {/* Tab header */}
          <div className="flex items-center border-b border-white/5 shrink-0">
            <button
              onClick={() => setRightTab("database")}
              className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-2.5 text-xs font-medium transition ${
                rightTab === "database"
                  ? "text-text-accent border-b-2 border-text-accent"
                  : "text-text-secondary/50 hover:text-text-secondary"
              }`}
            >
              <svg
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
              >
                <ellipse cx="12" cy="5" rx="9" ry="3" />
                <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" />
                <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
              </svg>
              Database
              {chat.queries.length > 0 && (
                <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
              )}
            </button>
            <button
              onClick={() => setRightTab("application")}
              className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-2.5 text-xs font-medium transition ${
                rightTab === "application"
                  ? "text-text-accent border-b-2 border-text-accent"
                  : "text-text-secondary/50 hover:text-text-secondary"
              }`}
            >
              <svg
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
              >
                <polyline points="4 17 10 11 4 5" />
                <line x1="12" y1="19" x2="20" y2="19" />
              </svg>
              Application
              {chat.appLogs.length > 0 && chat.isLoading && (
                <span className="w-1.5 h-1.5 rounded-full bg-yellow-500 animate-pulse" />
              )}
            </button>
            <button
              onClick={() => {
                setRightTab("context");
                if (!chat.contextWindow) chat.requestContextWindow();
              }}
              className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-2.5 text-xs font-medium transition ${
                rightTab === "context"
                  ? "text-text-accent border-b-2 border-text-accent"
                  : "text-text-secondary/50 hover:text-text-secondary"
              }`}
            >
              <svg
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
              >
                <rect x="2" y="3" width="20" height="18" rx="2" />
                <line x1="2" y1="9" x2="22" y2="9" />
                <line x1="2" y1="15" x2="22" y2="15" />
              </svg>
              Context
            </button>
            <button
              onClick={() => setRightTab("architecture")}
              className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-2.5 text-xs font-medium transition ${
                rightTab === "architecture"
                  ? "text-text-accent border-b-2 border-text-accent"
                  : "text-text-secondary/50 hover:text-text-secondary"
              }`}
            >
              <svg
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
              >
                <circle cx="12" cy="4" r="2" />
                <circle cx="12" cy="12" r="2" />
                <circle cx="12" cy="20" r="2" />
                <line x1="12" y1="6" x2="12" y2="10" />
                <line x1="12" y1="14" x2="12" y2="18" />
              </svg>
              Architecture
              {chat.isLoading && (
                <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
              )}
            </button>
            {archMode === "comparison" && (
              <button
                onClick={() => setRightTab("latency")}
                className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-2.5 text-xs font-medium transition ${
                  rightTab === "latency"
                    ? "text-purple-400 border-b-2 border-purple-400"
                    : "text-text-secondary/50 hover:text-text-secondary"
                }`}
              >
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                >
                  <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
                </svg>
                Latency
                {chat.comparisonData?.latency_points?.length > 0 && (
                  <span className="w-1.5 h-1.5 rounded-full bg-purple-500 animate-pulse" />
                )}
              </button>
            )}
          </div>

          {/* Tab content — min-h-0 prevents flex child from overflowing */}
          <div className="flex-1 min-h-0 overflow-hidden">
            {rightTab === "database" ? (
              <QueryStream queries={chat.queries} querySummary={chat.querySummary} />
            ) : rightTab === "application" ? (
              <AppLogs logs={chat.appLogs} />
            ) : rightTab === "architecture" ? (
              <ArchitectureFlow
                archEvents={chat.archEvents}
                isLoading={chat.isLoading}
                archMode={archMode}
              />
            ) : rightTab === "latency" ? (
              <LatencyComparison
                comparisonData={chat.comparisonData}
                healthStatus={chat.healthStatus}
                onHealthCheck={chat.checkHealth}
              />
            ) : (
              <ContextActivity
                contextWindow={chat.contextWindow}
                onRefresh={chat.requestContextWindow}
                isLoading={chat.contextLoading}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
