import { useState, useEffect } from "react";

const DEMO_THREADS = [
  { thread_id: "thread-demo-risk", title: "Portfolio Risk Analysis", icon: "chart" },
  { thread_id: "thread-demo-compliance", title: "Compliance Check", icon: "shield" },
  { thread_id: "thread-demo-account", title: "Account Details", icon: "user" },
  { thread_id: "thread-demo-research", title: "Market Research", icon: "search" },
];

export default function NavPane({
  collapsed,
  onNewThread,
  onLoadThread,
  onClearThread,
  onDeleteThread,
  threadId,
}) {
  const [loadInput, setLoadInput] = useState("");
  const [threads, setThreads] = useState(DEMO_THREADS);
  const [contextMenu, setContextMenu] = useState(null);
  const [showAbout, setShowAbout] = useState(false);

  useEffect(() => {
    fetch("/api/threads")
      .then((r) => {
        if (!r.ok) return [];
        return r.json();
      })
      .then((data) => {
        if (Array.isArray(data) && data.length > 0) {
          setThreads([
            ...DEMO_THREADS,
            ...data.filter((t) => !t.thread_id.startsWith("thread-demo-")),
          ]);
        }
      })
      .catch(() => {});
  }, []);

  // Close context menu on click outside
  useEffect(() => {
    const handleClick = () => setContextMenu(null);
    document.addEventListener("click", handleClick);
    return () => document.removeEventListener("click", handleClick);
  }, []);

  const handleLoad = () => {
    if (loadInput.trim()) {
      onLoadThread(loadInput.trim());
      setLoadInput("");
    }
  };

  const handleContextMenu = (e, thread) => {
    e.preventDefault();
    e.stopPropagation();
    setContextMenu({ x: e.clientX, y: e.clientY, thread });
  };

  const handleCopyThreadId = (tid) => {
    navigator.clipboard.writeText(tid).catch(() => {});
    setContextMenu(null);
  };

  const handleClearConversation = (tid) => {
    if (window.confirm("This will permanently clear all messages in this thread. Continue?")) {
      if (onClearThread) onClearThread(tid);
    }
    setContextMenu(null);
  };

  const handleDeleteThread = (tid) => {
    if (window.confirm("Delete this thread entirely?")) {
      if (onDeleteThread) onDeleteThread(tid);
      setThreads((prev) => prev.filter((t) => t.thread_id !== tid));
    }
    setContextMenu(null);
  };

  if (collapsed) {
    return (
      <div className="w-12 bg-secondary border-r border-white/5 flex flex-col items-center py-4 gap-4 shrink-0">
        <button
          onClick={onNewThread}
          className="w-8 h-8 rounded-lg bg-tertiary flex items-center justify-center text-text-secondary hover:text-text-primary hover:bg-white/10 transition"
          title="New Chat"
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
        </button>
        {threads.slice(0, 6).map((t) => (
          <button
            key={t.thread_id}
            onClick={() => onLoadThread(t.thread_id)}
            onContextMenu={(e) => handleContextMenu(e, t)}
            className={`w-8 h-8 rounded-lg flex items-center justify-center text-xs transition ${
              t.thread_id === threadId
                ? "bg-white/10 text-text-primary glow-border-active"
                : "text-text-secondary hover:bg-white/5"
            }`}
            title={t.title}
          >
            {t.title?.[0] || "T"}
          </button>
        ))}
        <div className="mt-auto">
          <button
            onClick={() => setShowAbout(true)}
            className="w-8 h-8 rounded-lg flex items-center justify-center text-text-secondary/50 hover:text-text-primary hover:bg-white/5 transition"
            title="About"
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="16" x2="12" y2="12" />
              <line x1="12" y1="8" x2="12.01" y2="8" />
            </svg>
          </button>
        </div>
        {showAbout && <AboutModal onClose={() => setShowAbout(false)} />}
      </div>
    );
  }

  return (
    <div className="w-56 bg-secondary border-r border-white/5 flex flex-col shrink-0">
      {/* New Chat */}
      <div className="p-3">
        <button
          onClick={onNewThread}
          className="w-full flex items-center gap-2 px-3 py-2 rounded-lg bg-tertiary text-text-secondary hover:text-text-primary hover:bg-white/10 glow-border glow-border-hover transition text-sm"
        >
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          New Chat
        </button>
      </div>

      {/* Load Thread */}
      <div className="px-3 pb-3">
        <div className="flex gap-1">
          <input
            type="text"
            value={loadInput}
            onChange={(e) => setLoadInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleLoad()}
            placeholder="Thread ID..."
            className="flex-1 bg-tertiary text-text-primary text-xs rounded px-2 py-1.5 glow-input placeholder:text-text-secondary/50"
          />
          <button
            onClick={handleLoad}
            className="px-2 py-1.5 bg-tertiary rounded text-text-secondary hover:text-text-primary text-xs glow-border-hover transition"
          >
            Go
          </button>
        </div>
      </div>

      <div className="border-t border-white/5" />

      {/* Thread list */}
      <div className="flex-1 overflow-y-auto py-2">
        {threads.map((t) => (
          <button
            key={t.thread_id}
            onClick={() => onLoadThread(t.thread_id)}
            onContextMenu={(e) => handleContextMenu(e, t)}
            className={`w-full text-left px-3 py-2 text-sm transition ${
              t.thread_id === threadId
                ? "bg-white/5 text-text-primary border-r-2 border-text-accent"
                : "text-text-secondary hover:bg-white/[0.03] hover:text-text-primary"
            }`}
          >
            <div className="truncate">{t.title || t.thread_id}</div>
            <div className="flex items-center gap-1 mt-0.5">
              <span className="text-[10px] text-text-secondary/60 truncate">{t.thread_id}</span>
              {t.updated_at && (
                <span className="text-[10px] text-text-secondary/40 ml-auto shrink-0">
                  {new Date(t.updated_at).toLocaleDateString()}
                </span>
              )}
            </div>
          </button>
        ))}
      </div>

      {/* About button */}
      <div className="border-t border-white/5 p-3">
        <button
          onClick={() => setShowAbout(true)}
          className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-text-secondary/60 hover:text-text-primary hover:bg-white/[0.03] transition text-xs"
        >
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
          >
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="16" x2="12" y2="12" />
            <line x1="12" y1="8" x2="12.01" y2="8" />
          </svg>
          About This Demo
        </button>
      </div>

      {/* Context menu */}
      {contextMenu && (
        <div
          className="fixed bg-primary border border-white/10 rounded-lg shadow-xl py-1 z-50 min-w-40"
          style={{ left: contextMenu.x, top: contextMenu.y }}
        >
          <button
            onClick={() => handleCopyThreadId(contextMenu.thread.thread_id)}
            className="w-full text-left px-3 py-1.5 text-xs text-text-secondary hover:bg-white/5 hover:text-text-primary transition"
          >
            Copy Thread ID
          </button>
          <button
            onClick={() => handleClearConversation(contextMenu.thread.thread_id)}
            className="w-full text-left px-3 py-1.5 text-xs text-text-secondary hover:bg-white/5 hover:text-text-primary transition"
          >
            Clear Conversation
          </button>
          <div className="border-t border-white/5 my-1" />
          <button
            onClick={() => handleDeleteThread(contextMenu.thread.thread_id)}
            className="w-full text-left px-3 py-1.5 text-xs text-red-400/80 hover:bg-red-500/10 hover:text-red-400 transition"
          >
            Delete Thread
          </button>
        </div>
      )}

      {/* About modal */}
      {showAbout && <AboutModal onClose={() => setShowAbout(false)} />}
    </div>
  );
}

function AboutModal({ onClose }) {
  return (
    <div
      className="fixed inset-0 bg-black/60 flex items-center justify-center z-50"
      onClick={onClose}
    >
      <div
        className="bg-secondary border border-white/10 rounded-xl shadow-2xl max-w-lg w-full mx-4 max-h-[85vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/5">
          <div className="flex items-center gap-2">
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              className="text-text-accent"
            >
              <path d="M12 2L2 7l10 5 10-5-10-5z" />
              <path d="M2 17l10 5 10-5" />
              <path d="M2 12l10 5 10-5" />
            </svg>
            <span className="text-text-accent font-semibold text-sm">
              Agentic Financial Service Assistant
            </span>
          </div>
          <button
            onClick={onClose}
            className="text-text-secondary hover:text-text-primary transition p-1"
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="px-6 py-5 space-y-5 text-sm text-text-secondary leading-relaxed">
          <section>
            <h3 className="text-text-primary font-medium mb-2">What is this?</h3>
            <p>
              This is an AI-powered financial services assistant that answers questions about client
              portfolios, risk exposure, and regulatory compliance. Behind the scenes, it
              demonstrates how
              <span className="text-text-accent"> Oracle AI Database </span>
              serves as a <span className="text-text-accent">unified memory core</span> for AI
              agents -- replacing the need for separate vector databases, document stores, graph
              databases, and traditional databases.
            </p>
          </section>

          <section>
            <h3 className="text-text-primary font-medium mb-2">The Problem</h3>
            <p>
              Most AI applications today require a fragmented data architecture: a vector database
              for semantic search, a document store for unstructured data, a graph database for
              relationships, and a relational database for structured records. This creates
              operational complexity, data silos, and synchronization challenges.
            </p>
          </section>

          <section>
            <h3 className="text-text-primary font-medium mb-2">The Solution</h3>
            <p>
              Oracle AI Database converges all these capabilities into one. This demo shows a single
              database instance handling:
            </p>
            <ul className="mt-2 space-y-1.5 ml-1">
              <li className="flex items-start gap-2">
                <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-accent-sql/20 text-accent-sql shrink-0 mt-0.5">
                  SQL
                </span>
                <span>
                  <span className="text-text-primary">Relational queries</span> -- Client accounts,
                  holdings, transactions
                </span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-accent-vector/20 text-accent-vector shrink-0 mt-0.5">
                  VEC
                </span>
                <span>
                  <span className="text-text-primary">Vector search</span> -- Semantic similarity
                  across research documents (HNSW indexes)
                </span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-accent-graph/20 text-accent-graph shrink-0 mt-0.5">
                  GRAPH
                </span>
                <span>
                  <span className="text-text-primary">Graph traversal</span> -- Account
                  relationships and similar portfolios
                </span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-accent-json/20 text-accent-json shrink-0 mt-0.5">
                  JSON
                </span>
                <span>
                  <span className="text-text-primary">Document store</span> -- Investment
                  preferences stored as JSON metadata
                </span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-accent-text/20 text-accent-text shrink-0 mt-0.5">
                  TEXT
                </span>
                <span>
                  <span className="text-text-primary">Full-text search</span> -- Oracle Text
                  CONTAINS() with keyword matching
                </span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-accent-hybrid/20 text-accent-hybrid shrink-0 mt-0.5">
                  HYB
                </span>
                <span>
                  <span className="text-text-primary">Hybrid search</span> -- Combined vector +
                  keyword with RRF fusion
                </span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-accent-spatial/20 text-accent-spatial shrink-0 mt-0.5">
                  SPA
                </span>
                <span>
                  <span className="text-text-primary">Spatial queries</span> -- Geospatial proximity
                  search with SDO_GEOMETRY indexes
                </span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-[9px] font-bold px-1.5 py-0.5 rounded badge-convergent shrink-0 mt-0.5 text-[9px] font-bold px-1.5 py-0.5">
                  CVG
                </span>
                <span>
                  <span className="text-text-primary">Convergent query</span> -- Relational + Graph
                  + Vector + Spatial in a single SQL statement
                </span>
              </li>
            </ul>
          </section>

          <section>
            <h3 className="text-text-primary font-medium mb-2">Sample Data</h3>
            <p>The database is pre-loaded with simulated financial data:</p>
            <ul className="mt-2 space-y-1 text-text-secondary/80 ml-4 list-disc">
              <li>25 client accounts with geospatial coordinates and varying risk profiles</li>
              <li>273 portfolio holdings across equities, bonds, and alternatives</li>
              <li>52 knowledge base documents (risk research, regulatory briefs)</li>
              <li>15 compliance rules with thresholds</li>
              <li>35 relationship graph edges connecting accounts and managers</li>
              <li>5 relationship manager offices with geographic locations</li>
            </ul>
          </section>

          <section>
            <h3 className="text-text-primary font-medium mb-2">Try These Questions</h3>
            <ul className="space-y-2 text-text-secondary/80">
              <li className="bg-tertiary/50 rounded-lg px-3 py-2 text-xs">
                "Analyze the portfolio risk for ACC-001 and identify any concentration issues"
              </li>
              <li className="bg-tertiary/50 rounded-lg px-3 py-2 text-xs">
                "What compliance rules apply to accounts in the same network as ACC-003, and what do
                our research documents say about concentration risk?"
              </li>
              <li className="bg-tertiary/50 rounded-lg px-3 py-2 text-xs">
                <span className="badge-convergent text-[9px] font-bold px-1.5 py-0.5 rounded mr-1">
                  CONVERGENT
                </span>
                "Run a convergent search for ACC-003 to find connected accounts and relevant risk
                research"
              </li>
              <li className="bg-tertiary/50 rounded-lg px-3 py-2 text-xs">
                <span className="badge-spatial text-[9px] font-bold px-1.5 py-0.5 rounded mr-1">
                  SPATIAL
                </span>
                "Which clients are geographically near ACC-003 and do they share similar risk
                profiles?"
              </li>
              <li className="bg-tertiary/50 rounded-lg px-3 py-2 text-xs">
                "What are the investment preferences for the Smith Family Trust?"
              </li>
            </ul>
          </section>

          <section>
            <h3 className="text-text-primary font-medium mb-2">How to Use</h3>
            <ul className="mt-1 space-y-1 text-text-secondary/80 ml-4 list-disc">
              <li>
                Click a <span className="text-text-accent">starter query</span> or type your own
                question in the chat input
              </li>
              <li>
                Watch the <span className="text-text-accent">Database</span> tab to see every SQL
                query the agent executes in real-time (vector, graph, spatial, hybrid, convergent)
              </li>
              <li>
                Switch to the <span className="text-text-accent">Application</span> tab to see live
                agent logs (context building, tool calls, timing)
              </li>
              <li>
                Switch to the <span className="text-text-accent">Context</span> tab to inspect the
                agent's memory segments and token usage
              </li>
              <li>Drag-and-drop or upload PDF/DOCX/CSV files to ingest into the knowledge base</li>
              <li>Right-click threads to copy ID, clear messages, or delete</li>
              <li>
                Use the <span className="text-text-accent">Compact</span> button in the context bar
                to summarize long conversations
              </li>
            </ul>
          </section>
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-white/5 text-center">
          <p className="text-[10px] text-text-secondary/40">
            Powered by Oracle AI Database 26ai &middot; GPT-5 &middot; LangChain
          </p>
        </div>
      </div>
    </div>
  );
}
