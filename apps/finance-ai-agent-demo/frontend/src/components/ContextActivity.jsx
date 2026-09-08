import { useState } from "react";

const SEGMENT_COLORS = {
  system_prompt: { bg: "bg-text-secondary/20", text: "text-text-secondary", label: "SYS" },
  conversation: { bg: "bg-accent-sql/20", text: "text-accent-sql", label: "CONV" },
  knowledge_base: { bg: "bg-accent-vector/20", text: "text-accent-vector", label: "KB" },
  workflows: { bg: "bg-accent-hybrid/20", text: "text-accent-hybrid", label: "WF" },
  toolbox: { bg: "bg-accent-text/20", text: "text-accent-text", label: "TOOL" },
  entities: { bg: "bg-accent-graph/20", text: "text-accent-graph", label: "ENT" },
  summary_refs: { bg: "bg-accent-json/20", text: "text-accent-json", label: "SUM" },
};

function SegmentCard({ segment }) {
  const [expanded, setExpanded] = useState(false);
  const colors = SEGMENT_COLORS[segment.key] || {
    bg: "bg-white/10",
    text: "text-text-secondary",
    label: "?",
  };

  return (
    <div className="rounded-lg glow-border overflow-hidden bg-[#0D0D0D]">
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-3 py-2.5 hover:bg-white/[0.02] transition"
      >
        <div className="flex items-center gap-2">
          <span
            className={`text-[9px] font-bold px-1.5 py-0.5 rounded ${colors.bg} ${colors.text}`}
          >
            {colors.label}
          </span>
          <span className="text-xs text-text-accent">{segment.name}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-text-secondary/50">
            {segment.tokens.toLocaleString()} tokens
          </span>
          <svg
            width="12"
            height="12"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            className={`text-text-secondary/40 transition-transform ${expanded ? "rotate-180" : ""}`}
          >
            <polyline points="6 9 12 15 18 9" />
          </svg>
        </div>
      </button>

      {/* Content */}
      {expanded && (
        <div className="border-t border-white/5 px-3 py-2">
          <pre className="text-[10px] font-mono text-text-secondary/70 whitespace-pre-wrap leading-relaxed max-h-80 overflow-y-auto">
            {segment.content}
          </pre>
        </div>
      )}
    </div>
  );
}

export default function ContextActivity({ contextWindow, onRefresh, isLoading }) {
  const segments = contextWindow?.segments || [];
  const totalTokens = contextWindow?.total_tokens || 0;

  return (
    <div className="flex flex-col h-full">
      {/* Segment cards */}
      <div className="flex-1 overflow-y-auto px-3 py-2 space-y-2">
        {segments.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-text-secondary/40">
            <svg
              width="32"
              height="32"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1"
              className="mb-2"
            >
              <rect x="2" y="3" width="20" height="18" rx="2" />
              <line x1="2" y1="9" x2="22" y2="9" />
              <line x1="2" y1="15" x2="22" y2="15" />
            </svg>
            <p className="text-xs mb-2">No context data yet</p>
            <button
              onClick={onRefresh}
              className="text-[10px] px-3 py-1 rounded border border-white/10 text-text-secondary hover:text-text-primary hover:border-white/20 transition"
            >
              Load Context
            </button>
          </div>
        )}

        {segments.map((seg) => (
          <SegmentCard key={seg.key} segment={seg} />
        ))}
      </div>

      {/* Footer */}
      {segments.length > 0 && (
        <div className="border-t border-white/5 px-4 py-2 bg-primary/50">
          <div className="flex items-center justify-between">
            <div className="text-[11px] text-text-secondary">
              <span className="text-text-accent">{segments.length}</span> segments &middot;{" "}
              <span className="text-text-accent">{totalTokens.toLocaleString()}</span> tokens
            </div>
            <button
              onClick={onRefresh}
              disabled={isLoading}
              className="text-[10px] px-2 py-0.5 rounded border border-white/10 text-text-secondary/60 hover:text-text-secondary hover:border-white/20 transition disabled:opacity-30"
            >
              {isLoading ? "Loading..." : "Refresh"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
