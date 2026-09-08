import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import ToolCallBubble from "./ToolCallBubble";
import { User, Bot } from "lucide-react";

export default function ChatMessage({ message }) {
  const isUser = message.role === "user";
  return (
    <div className={`flex gap-3 ${isUser ? "flex-row-reverse" : ""}`}>
      <div className="shrink-0 w-7 h-7 rounded-full flex items-center justify-center bg-bg-elev">
        {isUser ? <User size={14} /> : <Bot size={14} className="text-accent-memory" />}
      </div>
      <div className={`flex-1 ${isUser ? "text-right" : ""}`}>
        <div
          className={`inline-block px-4 py-3 rounded-lg ${
            isUser
              ? "bg-accent-skill/15 text-text-primary"
              : "bg-bg-panel border border-white/5 text-text-accent"
          } max-w-full text-left`}
        >
          {isUser ? (
            <div className="text-sm whitespace-pre-wrap">{message.content}</div>
          ) : (
            <div className="prose-msg">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
            </div>
          )}
        </div>

        {!isUser && message.trace && message.trace.length > 0 && (
          <details className="mt-1">
            <summary className="text-[10px] text-text-muted cursor-pointer hover:text-text-secondary">
              show {message.trace.length} step trace · {message.elapsed?.toFixed(1)}s
            </summary>
            <div className="mt-2 space-y-1.5">
              {message.trace.map((t, i) => (
                <ToolCallBubble key={i} event={t} compact />
              ))}
            </div>
          </details>
        )}
      </div>
    </div>
  );
}
