import QueryCard from "./QueryCard";

export default function QueryStream({ queries, querySummary }) {
  return (
    <div className="flex flex-col h-full">
      {/* Query cards feed */}
      <div className="flex-1 overflow-y-auto px-3 py-2 space-y-2">
        {queries.length === 0 && (
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
              <ellipse cx="12" cy="5" rx="9" ry="3" />
              <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" />
              <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
            </svg>
            <p className="text-xs">Queries will appear here</p>
          </div>
        )}

        {queries.map((q) => (
          <QueryCard key={q.id} query={q} />
        ))}
      </div>

      {/* Summary footer */}
      {querySummary && querySummary.query_count > 0 && (
        <div className="border-t border-white/5 px-4 py-2 bg-primary/50">
          <div className="text-[11px] text-text-secondary text-center">
            <span className="text-text-accent">{querySummary.query_count}</span> queries &middot;{" "}
            <span className="text-text-accent">{querySummary.type_count}</span> data types &middot;{" "}
            <span className="text-text-accent">{querySummary.total_ms}ms</span> total &middot;{" "}
            <span className="text-text-accent">1</span> database
          </div>
        </div>
      )}
    </div>
  );
}
