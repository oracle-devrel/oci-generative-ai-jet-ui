import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

function timeAgo(timestamp) {
  if (!timestamp) return "";
  const diff = Date.now() - new Date(timestamp).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

export default function ChatMessage({ message }) {
  const { role, content, timestamp } = message;

  if (role === "system") {
    return (
      <div className="flex justify-center py-1">
        <div className="text-xs text-text-secondary/70 bg-tertiary/50 rounded-full px-3 py-1 border border-white/5">
          {content}
        </div>
      </div>
    );
  }

  const isUser = role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} animate-slide-in`}>
      <div className={`max-w-[80%] ${isUser ? "" : "flex gap-2"}`}>
        {/* Agent avatar */}
        {!isUser && (
          <div className="w-7 h-7 rounded-full bg-tertiary border border-white/10 flex items-center justify-center shrink-0 mt-1">
            <svg
              width="14"
              height="14"
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
          </div>
        )}

        <div>
          <div
            className={`rounded-xl px-4 py-3 text-sm leading-relaxed ${
              isUser
                ? "bg-tertiary text-text-primary"
                : "bg-secondary glow-border text-text-primary"
            }`}
          >
            {isUser ? (
              <p className="whitespace-pre-wrap">{content}</p>
            ) : (
              <div className="prose prose-invert prose-sm max-w-none prose-p:my-1.5 prose-li:my-0.5 prose-ul:my-1 prose-ol:my-1 prose-headings:text-text-accent prose-headings:mt-3 prose-headings:mb-1.5 prose-h2:text-base prose-h3:text-sm prose-strong:text-text-primary prose-code:text-text-accent prose-code:bg-tertiary prose-code:px-1 prose-code:rounded prose-table:text-xs prose-th:text-text-accent prose-th:border-white/10 prose-td:border-white/10 prose-hr:border-white/10">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
              </div>
            )}
          </div>
          <div className={`text-[10px] text-text-secondary/50 mt-1 ${isUser ? "text-right" : ""}`}>
            {timeAgo(timestamp)}
          </div>
        </div>
      </div>
    </div>
  );
}
