import { useEffect, useRef, useState } from "react";
import { ArrowUp, Loader2, Sparkles, User } from "lucide-react";
import type { ChatTurn } from "../types";

interface Props {
  chat: ChatTurn[];
  connected: boolean;
  isThinking: boolean;
  onSend: (text: string) => void;
}

const STARTER_PROMPTS = [
  "I'm planner with user_id=priya. How aggressively should we stock soccer / football merchandise for the upcoming season? Respect my preferences and the standing policy.",
  "I'm user_id=michael. Push hard on kids' football cleats — I want a depth buy. Verify it against policy.",
  "How are our soccer merchandise comps performing? Just give me the data, no recommendation.",
];

export function ChatPane({ chat, connected, isThinking, onSend }: Props) {
  const [text, setText] = useState("");
  const endRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chat]);

  const submit = () => {
    const t = text.trim();
    if (!t || !connected) return;
    onSend(t);
    setText("");
  };

  return (
    <section className="pane flex-1 min-w-0">
      <div className="pane-header">
        <div className="pane-title">Chat</div>
        <div className="text-[11px] text-text-muted">supervisor + 2 specialists</div>
      </div>

      <div className="flex-1 overflow-y-auto px-5 py-4">
        <div className="max-w-3xl mx-auto space-y-4">
          {chat.length === 0 && (
            <div className="text-text-secondary text-sm space-y-3">
              <p className="text-text-primary">
                Ask the planner-assistant a question. Each turn fires the supervisor; the right pane
                fills in per-agent traces while the bottom panes light up tables and edges as tools
                execute.
              </p>
              <div className="text-[11px] uppercase tracking-wider text-text-muted">
                Starter prompts
              </div>
              <div className="space-y-2">
                {STARTER_PROMPTS.map((p, i) => (
                  <button
                    key={i}
                    onClick={() => setText(p)}
                    className="block w-full text-left px-3 py-2 rounded border border-border-subtle bg-bg-elev hover:border-accent-skill/40 hover:bg-overlay-soft text-[12px] text-text-accent transition-colors"
                  >
                    {p}
                  </button>
                ))}
              </div>
            </div>
          )}

          {chat.map((turn) => (
            <ChatMessage key={turn.id} turn={turn} />
          ))}

          {isThinking && (
            <div className="flex items-center gap-2 text-[12px] text-text-secondary">
              <Loader2 size={13} className="animate-spin text-accent-memory" />
              agent is thinking…
            </div>
          )}
          <div ref={endRef} />
        </div>
      </div>

      <form
        className="border-t border-border-subtle p-3"
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
      >
        <div className="max-w-3xl mx-auto flex gap-2 items-end">
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder={isThinking ? "Agent is working…" : "Ask the planner-assistant…"}
            rows={2}
            disabled={isThinking}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                submit();
              }
            }}
            className="flex-1 px-3 py-2 rounded border border-border-subtle bg-bg-elev text-text-primary text-sm font-sans placeholder:text-text-muted focus:outline-none focus:border-accent-skill resize-none"
          />
          <button
            type="submit"
            disabled={!connected || !text.trim() || isThinking}
            className="px-3 py-2 rounded bg-accent-skill hover:bg-accent-skill/80 disabled:opacity-30 disabled:cursor-not-allowed text-white transition-colors"
          >
            <ArrowUp size={16} />
          </button>
        </div>
        <div className="max-w-3xl mx-auto text-[10px] text-text-muted mt-1.5">
          Enter to send · Shift+Enter for newline
        </div>
      </form>
    </section>
  );
}

function ChatMessage({ turn }: { turn: ChatTurn }) {
  const isUser = turn.role === "user";
  return (
    <div className={`flex ${isUser ? "flex-row-reverse" : "flex-row"} gap-2 items-start`}>
      <div
        className={`w-7 h-7 rounded grid place-items-center shrink-0 ${
          isUser ? "bg-accent-skill/20 text-accent-skill" : "bg-accent-memory/20 text-accent-memory"
        }`}
      >
        {isUser ? <User size={14} /> : <Sparkles size={14} />}
      </div>
      <div
        className={`px-3 py-2 rounded-lg max-w-[80%] text-[14px] leading-relaxed whitespace-pre-wrap prose-msg ${
          isUser
            ? "bg-accent-skill/15 text-text-primary"
            : "bg-bg-elev text-text-accent border border-border-subtle"
        }`}
      >
        {turn.content || (turn.pending ? <span className="text-text-muted">…</span> : "")}
      </div>
    </div>
  );
}
