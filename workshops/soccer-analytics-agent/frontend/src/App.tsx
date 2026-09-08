import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { motion } from "framer-motion";
import { ArrowsClockwiseIcon } from "@phosphor-icons/react";
import { HealthPill } from "./components/HealthPill";
import { ChatColumn } from "./components/ChatColumn";
import { AnalyticsPanel } from "./components/AnalyticsPanel";
import { getHealth, sendChat, clearMemory, AgentApiError } from "./lib/api";
import { buildSnapshot } from "./lib/analytics";
import type { HealthStatus, Message } from "./lib/types";

let msgCounter = 0;
const nextId = () => `m${++msgCounter}-${Date.now()}`;

// Brand mark — inline SVG soccer-pitch motif (no emoji, no external asset).
function BrandMark() {
  return (
    <span
      aria-hidden
      className="grid h-8 w-8 flex-none place-items-center rounded-[10px] bg-gradient-to-br from-accent to-accent-dim text-ink shadow-[inset_0_1px_0_rgba(255,255,255,0.28)]"
    >
      <svg
        viewBox="0 0 24 24"
        width={18}
        height={18}
        fill="none"
        stroke="currentColor"
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <circle cx="12" cy="12" r="9" />
        <path d="M12 7.5l3.5 2.6-1.3 4.1h-4.4L8.5 10.1 12 7.5z" />
        <path d="M12 7.5V4M15.5 10.1l3.2-1M14.2 14.2l2 2.8M9.8 14.2l-2 2.8M8.5 10.1l-3.2-1" />
      </svg>
    </span>
  );
}

export default function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState<HealthStatus>("connecting");
  const [typingNote, setTypingNote] = useState<string>();
  const sessionRef = useRef<string | null>(null);
  const noteTimers = useRef<number[]>([]);

  // Health polling with strict cleanup (taste-skill useEffect-cleanup rule).
  useEffect(() => {
    let active = true;
    async function poll() {
      try {
        const h = await getHealth();
        if (!active) return;
        setStatus(
          h.oracle && h.grok_configured ? "live" : h.oracle ? "db-only" : "offline",
        );
      } catch {
        if (active) setStatus("offline");
      }
    }
    poll();
    const id = window.setInterval(poll, 20000);
    return () => {
      active = false;
      window.clearInterval(id);
    };
  }, []);

  const clearNoteTimers = useCallback(() => {
    noteTimers.current.forEach((t) => window.clearTimeout(t));
    noteTimers.current = [];
  }, []);

  // The first prediction (Elo replay) and a live Grok turn can take 10-40s.
  // Escalate the typing note so the wait reads as deliberate, not stuck.
  const startNotes = useCallback(() => {
    setTypingNote("running the model…");
    noteTimers.current = [
      window.setTimeout(
        () => setTypingNote("replaying Elo + assembling features…"),
        6000,
      ),
      window.setTimeout(
        () => setTypingNote("querying Oracle and reasoning with Grok…"),
        14000,
      ),
      window.setTimeout(
        () => setTypingNote("still working — first run warms the Elo cache…"),
        26000,
      ),
    ];
  }, []);

  const handleSend = useCallback(
    async (text: string) => {
      if (busy) return;
      const userMsg: Message = { id: nextId(), role: "user", text };
      setMessages((m) => [...m, userMsg]);
      setBusy(true);
      startNotes();

      try {
        const data = await sendChat(text, sessionRef.current);
        sessionRef.current = data.session_id;
        setMessages((m) => [
          ...m,
          {
            id: nextId(),
            role: "assistant",
            text: data.reply || "(empty reply)",
            trace: data.tool_trace,
          },
        ]);
      } catch (err) {
        const e = err as AgentApiError;
        const detail = e.detail ? `\n\n${e.detail}` : "";
        setMessages((m) => [
          ...m,
          {
            id: nextId(),
            role: "assistant",
            text: `${e.message ?? "Request failed"}${detail}`,
            isError: true,
          },
        ]);
      } finally {
        clearNoteTimers();
        setTypingNote(undefined);
        setBusy(false);
      }
    },
    [busy, startNotes, clearNoteTimers],
  );

  const handleReset = useCallback(async () => {
    if (busy) return;
    const sid = sessionRef.current;
    sessionRef.current = null;
    setMessages([]);
    if (sid) await clearMemory(sid);
  }, [busy]);

  const snapshot = useMemo(() => buildSnapshot(messages), [messages]);

  return (
    <div className="flex min-h-[100dvh] flex-col">
      {/* Header */}
      <header className="sticky top-0 z-20 flex items-center justify-between border-b border-line-soft bg-ink/72 px-4 py-3 backdrop-blur-md sm:px-6">
        <div className="flex items-center gap-3">
          <BrandMark />
          <div className="leading-tight">
            <h1 className="text-[14.5px] font-semibold tracking-tight text-fg">
              Soccer Analytics Agent
            </h1>
            <p className="font-mono text-[10.5px] tracking-wide text-fg-faint">
              oracle ai database · grok 4 · 92-feature xgboost
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2.5">
          <HealthPill status={status} />
          <motion.button
            type="button"
            onClick={handleReset}
            disabled={busy}
            whileTap={{ scale: 0.96 }}
            className="inline-flex items-center gap-1.5 rounded-[10px] border border-line bg-surface-2 px-3 py-1.5 text-[12.5px] text-fg-dim transition-colors hover:border-line-soft hover:text-fg disabled:opacity-45"
          >
            <ArrowsClockwiseIcon size={13} weight="bold" />
            <span className="hidden sm:inline">Reset</span>
          </motion.button>
        </div>
      </header>

      {/* Split layout: conversation + persistent analytics panel.
          Collapses to a single column below lg. */}
      <main className="mx-auto grid w-full max-w-[1400px] flex-1 grid-cols-1 lg:grid-cols-[minmax(0,1fr)_392px] xl:grid-cols-[minmax(0,1fr)_440px]">
        <ChatColumn
          messages={messages}
          busy={busy}
          typingNote={typingNote}
          onSend={handleSend}
        />
        <aside className="hidden border-l border-line-soft bg-surface/30 lg:block">
          <div className="sticky top-[57px] h-[calc(100dvh-57px)] p-5">
            <AnalyticsPanel snapshot={snapshot} />
          </div>
        </aside>
      </main>
    </div>
  );
}
