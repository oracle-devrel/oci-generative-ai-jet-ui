import { useState } from "react";

export default function TokenUsageBar({ tokenUsage, onCompact, isCompacting }) {
  const [showTooltip, setShowTooltip] = useState(false);

  if (!tokenUsage) return null;

  const { total_tokens, max_tokens, percentage, breakdown } = tokenUsage;

  const barColor =
    percentage > 80 ? "bg-red-500" : percentage > 60 ? "bg-amber-500" : "bg-text-accent/40";

  const glowClass = percentage > 80 ? "animate-pulse-glow" : "";

  return (
    <div className={`px-4 py-2 flex items-center gap-3 ${glowClass}`}>
      <span className="text-[10px] text-text-secondary/60 shrink-0">Context:</span>

      {/* Progress bar */}
      <div
        className="flex-1 h-1.5 bg-tertiary rounded-full overflow-hidden relative cursor-pointer"
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
      >
        {breakdown && (
          <>
            <div
              className="absolute h-full bg-accent-sql/40 rounded-full"
              style={{ width: `${Math.min(percentage, 100)}%` }}
            />
            {/* Segmented breakdown overlay */}
            <SegmentedBar breakdown={breakdown} maxTokens={max_tokens} />
          </>
        )}
        {!breakdown && (
          <div
            className={`h-full ${barColor} rounded-full transition-all duration-500`}
            style={{ width: `${Math.min(percentage, 100)}%` }}
          />
        )}

        {/* Tooltip */}
        {showTooltip && breakdown && (
          <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 bg-primary border border-white/10 rounded-lg p-3 shadow-xl z-50 min-w-48">
            <div className="text-[10px] text-text-secondary space-y-1">
              {Object.entries(breakdown).map(([key, val]) => (
                <div key={key} className="flex justify-between gap-4">
                  <span className="capitalize">{key.replace("_", " ")}:</span>
                  <span className="text-text-primary">{(val || 0).toLocaleString()} tokens</span>
                </div>
              ))}
              <div className="border-t border-white/10 pt-1 mt-1 flex justify-between font-medium">
                <span>Total:</span>
                <span className="text-text-accent">
                  {total_tokens.toLocaleString()} / {max_tokens.toLocaleString()}
                </span>
              </div>
            </div>
          </div>
        )}
      </div>

      <span
        className={`text-[10px] shrink-0 ${percentage > 80 ? "text-red-400" : percentage > 60 ? "text-amber-400" : "text-text-secondary/60"}`}
      >
        {percentage}%
      </span>

      {/* Compact button */}
      <button
        onClick={onCompact}
        disabled={isCompacting}
        className={`text-[10px] px-2 py-0.5 rounded border transition shrink-0 ${
          isCompacting
            ? "border-white/5 text-text-secondary/30 cursor-not-allowed"
            : percentage > 60
              ? "border-amber-500/30 text-amber-400 hover:bg-amber-500/10"
              : "border-white/10 text-text-secondary/60 hover:text-text-secondary hover:border-white/20"
        }`}
        title={isCompacting ? "Compacting..." : "Compact context"}
      >
        {isCompacting ? "Compacting..." : "Compact"}
      </button>
    </div>
  );
}

function SegmentedBar({ breakdown, maxTokens }) {
  if (!breakdown) return null;

  const colors = {
    conversation: "bg-accent-sql/50",
    knowledge_base: "bg-accent-vector/50",
    entities: "bg-accent-graph/50",
    workflows: "bg-accent-hybrid/50",
    system_prompt: "bg-text-secondary/30",
    summary_refs: "bg-accent-json/30",
  };

  let offset = 0;
  return (
    <>
      {Object.entries(breakdown).map(([key, val]) => {
        const width = ((val || 0) / maxTokens) * 100;
        const left = offset;
        offset += width;
        return (
          <div
            key={key}
            className={`absolute h-full ${colors[key] || "bg-white/10"}`}
            style={{ left: `${left}%`, width: `${width}%` }}
          />
        );
      })}
    </>
  );
}
