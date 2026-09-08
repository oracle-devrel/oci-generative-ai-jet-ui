import type { ChatMsg } from "../types";
import { ChartRenderer } from "./ChartRenderer";

export function ChatMessage({ msg }: { msg: ChatMsg }) {
  return (
    <div
      className={`p-3 rounded-lg ${msg.role === "user" ? "bg-oracle-ink/5" : "bg-white border border-oracle-ink/10"}`}
    >
      <div className="text-xs uppercase tracking-wide opacity-50 mb-1">{msg.role}</div>
      {msg.tool_statuses && msg.tool_statuses.length > 0 && (
        <div className="mb-2">
          {msg.tool_statuses.map((s, i) => (
            <div key={i} className="text-xs italic text-oracle-ink/50 leading-relaxed">
              &#8627; {s}
            </div>
          ))}
        </div>
      )}
      <div className="whitespace-pre-wrap">{msg.text}</div>
      {msg.chart && <ChartRenderer chart={msg.chart} />}
    </div>
  );
}
