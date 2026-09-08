import { useState } from "react";

export default function ToolCallBubble({ toolCall }) {
  const [expanded, setExpanded] = useState(false);
  const { name, args, status, output, elapsed_ms } = toolCall;

  const statusIcon =
    status === "running" ? (
      <span className="inline-block w-3 h-3 border-2 border-text-accent/30 border-t-text-accent rounded-full animate-spin" />
    ) : status === "success" ? (
      <span className="text-green-400 text-xs">&#10003;</span>
    ) : (
      <span className="text-red-400 text-xs">&#10007;</span>
    );

  const argsStr = args
    ? Object.entries(args)
        .map(([k, v]) => `${k}="${v}"`)
        .join(", ")
    : "";

  return (
    <div className="bg-[#0D0D0D] rounded-lg border-l-2 border-text-accent/20 glow-border overflow-hidden text-xs animate-slide-in">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-text-secondary/60">Tool Call</span>
          <span className="font-mono text-text-accent truncate">
            {name}({argsStr})
          </span>
        </div>
        <div className="flex items-center gap-2 shrink-0 ml-2">
          {statusIcon}
          {status !== "running" && <span className="text-text-secondary/50">{elapsed_ms}ms</span>}
        </div>
      </div>

      {/* Expandable output */}
      {status !== "running" && output && (
        <div className="border-t border-white/5">
          <button
            onClick={() => setExpanded(!expanded)}
            className="w-full text-left px-3 py-1.5 text-text-secondary/60 hover:text-text-secondary transition"
          >
            {expanded ? "Hide" : "Show"} output
          </button>
          {expanded && (
            <div className="px-3 pb-2">
              <pre className="bg-primary/50 rounded p-2 text-[10px] text-text-secondary overflow-x-auto max-h-40 overflow-y-auto font-mono whitespace-pre-wrap">
                {formatOutput(output)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function formatOutput(output) {
  try {
    const parsed = JSON.parse(output);
    return JSON.stringify(parsed, null, 2);
  } catch {
    return output;
  }
}
