import { Wrench, Check } from "lucide-react";

const TOOL_COLORS = {
  search_knowledge: "text-accent-memory",
  run_sql: "text-accent-sql",
  exec_js: "text-accent-tool",
  remember: "text-accent-memory",
  scan_database: "text-accent-skill",
  load_skill: "text-accent-skill",
  list_skills: "text-accent-skill",
  fetch_tool_output: "text-text-secondary",
};

export default function ToolCallBubble({ event, compact = false }) {
  const finished = event.type === "tool_finished";
  const colorCls = TOOL_COLORS[event.name] || "text-text-secondary";
  return (
    <div className={`flex items-start gap-2 ${compact ? "px-2 py-1" : "px-3 py-2"} rounded bg-bg-elev border border-white/5`}>
      <div className={`shrink-0 mt-0.5 ${colorCls}`}>
        {finished ? <Check size={12} /> : <Wrench size={12} />}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className={`text-[11px] font-mono font-semibold ${colorCls}`}>{event.name}</span>
          {event.tool_call_id && (
            <span className="text-[9px] text-text-muted font-mono">{event.tool_call_id.slice(0, 12)}</span>
          )}
        </div>
        {event.args && (
          <pre className="text-[10px] font-mono text-text-secondary/80 mt-0.5 whitespace-pre-wrap break-all">
            {JSON.stringify(event.args, null, 0).slice(0, 240)}
          </pre>
        )}
        {finished && event.preview && !compact && (
          <pre className="text-[10px] font-mono text-text-secondary/60 mt-1 whitespace-pre-wrap max-h-24 overflow-y-auto">
            {event.preview}
          </pre>
        )}
      </div>
    </div>
  );
}
