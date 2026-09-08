import { useEffect, useRef } from "react";
import { AnimatePresence } from "framer-motion";
import { MessageBubble } from "./MessageBubble";
import { TypingIndicator } from "./TypingIndicator";
import { EmptyHero } from "./EmptyHero";
import { Composer } from "./Composer";
import type { Message } from "../lib/types";

interface Props {
  messages: Message[];
  busy: boolean;
  typingNote?: string;
  onSend: (message: string) => void;
}

/** The conversation column: scrollable log + pinned composer. */
export function ChatColumn({ messages, busy, typingNote, onSend }: Props) {
  const logRef = useRef<HTMLDivElement>(null);
  const endRef = useRef<HTMLDivElement>(null);

  // Keep the latest turn in view as messages / typing state change.
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length, busy]);

  const empty = messages.length === 0;

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div ref={logRef} className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto w-full max-w-[760px] px-4 py-6 sm:px-6">
          {empty ? (
            <EmptyHero onPick={onSend} />
          ) : (
            <div className="grid gap-6">
              <AnimatePresence initial={false}>
                {messages.map((m) => (
                  <MessageBubble key={m.id} message={m} />
                ))}
              </AnimatePresence>
              {busy && (
                <div className="flex flex-col items-start">
                  <span className="mb-1.5 px-1 font-mono text-[10px] uppercase tracking-[0.12em] text-fg-faint">
                    agent
                  </span>
                  <TypingIndicator note={typingNote} />
                </div>
              )}
            </div>
          )}
          <div ref={endRef} />
        </div>
      </div>

      <div className="border-t border-line-soft bg-ink/70 px-4 py-4 backdrop-blur-md sm:px-6">
        <div className="mx-auto w-full max-w-[760px]">
          <Composer onSend={onSend} busy={busy} />
        </div>
      </div>
    </div>
  );
}
