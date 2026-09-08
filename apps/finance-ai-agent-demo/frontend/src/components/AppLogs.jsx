import { useRef, useEffect } from "react";

const LOG_HIGHLIGHTS = {
  "TOOL CALL:": "text-accent-vector",
  "TOOL OK:": "text-green-400",
  "TOOL FAIL:": "text-red-400",
  "LLM ERROR:": "text-red-400",
  TIMEOUT: "text-red-400",
  "DONE:": "text-accent-sql",
  "--- New request ---": "text-text-accent",
  "Building context": "text-accent-hybrid",
  "Starting Agent Loop": "text-accent-hybrid",
  "Final answer": "text-green-400",
  Iteration: "text-text-secondary/80",
  "Stream complete": "text-text-secondary/70",
};

function highlightLine(line) {
  for (const [pattern, color] of Object.entries(LOG_HIGHLIGHTS)) {
    if (line.includes(pattern)) return color;
  }
  return "text-text-secondary/60";
}

export default function AppLogs({ logs }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto px-3 py-2">
        {logs.length === 0 && (
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
              <polyline points="4 17 10 11 4 5" />
              <line x1="12" y1="19" x2="20" y2="19" />
            </svg>
            <p className="text-xs">Agent logs will appear here</p>
          </div>
        )}

        <div className="space-y-0">
          {logs.map((log, i) => (
            <div
              key={i}
              className={`text-[10px] font-mono leading-relaxed py-0.5 ${highlightLine(log.line)}`}
            >
              {log.line}
            </div>
          ))}
          <div ref={bottomRef} />
        </div>
      </div>

      {/* Footer */}
      {logs.length > 0 && (
        <div className="border-t border-white/5 px-4 py-2 bg-primary/50">
          <div className="text-[11px] text-text-secondary text-center">
            <span className="text-text-accent">{logs.length}</span> log entries
          </div>
        </div>
      )}
    </div>
  );
}
