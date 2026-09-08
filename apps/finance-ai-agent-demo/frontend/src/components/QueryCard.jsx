import { useState } from "react";
import QueryBadge from "./QueryBadge";

export default function QueryCard({ query }) {
  const [expanded, setExpanded] = useState(false);
  const { type, sql, elapsed_ms, result_count, top_result_preview, description, error } = query;

  // Truncate SQL for display
  const sqlPreview = sql.length > 200 ? sql.slice(0, 200) + "..." : sql;
  const hasError = !!error;

  return (
    <div
      className={`query-card-enter rounded-lg glow-border overflow-hidden bg-[#0D0D0D] ${hasError ? "border-red-500/20" : ""}`}
    >
      {/* Header: badge + description + latency */}
      <div className="flex items-center justify-between px-3 py-2">
        <div className="flex items-center gap-2 min-w-0">
          <QueryBadge type={type} />
          {description && (
            <span className="text-[10px] text-text-secondary/50 truncate">{description}</span>
          )}
        </div>
        <span className="text-[10px] text-text-secondary/60 shrink-0 ml-2">{elapsed_ms}ms</span>
      </div>

      {/* SQL query */}
      <div className="px-3 pb-2">
        <pre className="text-[10px] font-mono text-text-secondary/80 whitespace-pre-wrap leading-relaxed overflow-hidden">
          {expanded ? sql : sqlPreview}
        </pre>
        {sql.length > 200 && (
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-[10px] text-text-accent/60 hover:text-text-accent mt-1 transition"
          >
            {expanded ? "Show less" : "Show more"}
          </button>
        )}
      </div>

      {/* Result summary or error */}
      <div className="border-t border-white/5 px-3 py-1.5 flex items-center gap-2">
        {hasError ? (
          <>
            <span className="text-[10px] text-red-400/80">&#10007;</span>
            <span className="text-[10px] text-red-400/60 truncate">{error.slice(0, 80)}</span>
          </>
        ) : (
          <>
            <span className="text-[10px] text-green-400/70">&#10003;</span>
            <span className="text-[10px] text-text-secondary/60">
              {result_count} result{result_count !== 1 ? "s" : ""} returned
            </span>
            {top_result_preview && top_result_preview[0] && (
              <span className="text-[10px] text-text-secondary/40 truncate ml-auto">
                {Object.values(top_result_preview[0])[1]?.slice(0, 40) || ""}
              </span>
            )}
          </>
        )}
      </div>
    </div>
  );
}
