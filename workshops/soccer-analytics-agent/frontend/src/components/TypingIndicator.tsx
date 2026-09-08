import { memo } from "react";
import { motion } from "framer-motion";

const DOTS = [0, 1, 2];

// Isolated perpetual-motion leaf: typing indicator shown while the agent
// thinks. The first prediction (Elo replay) and a live Grok turn can take
// 10-40s, so this state must read as deliberate, not stuck.
function TypingIndicatorBase({ note }: { note?: string }) {
  return (
    <div className="inline-flex items-center gap-3 rounded-[var(--radius-card)] rounded-bl-[5px] border border-line-soft bg-surface px-4 py-3 shadow-[var(--shadow-tint-sm)]">
      <span className="flex items-center gap-1.5">
        {DOTS.map((d) => (
          <motion.span
            key={d}
            className="h-1.5 w-1.5 rounded-full bg-accent"
            animate={{ y: [0, -4, 0], opacity: [0.4, 1, 0.4] }}
            transition={{
              duration: 1.1,
              repeat: Infinity,
              ease: "easeInOut",
              delay: d * 0.16,
            }}
          />
        ))}
      </span>
      <span className="font-mono text-[11.5px] text-fg-faint">
        {note ?? "running the model…"}
      </span>
    </div>
  );
}

export const TypingIndicator = memo(TypingIndicatorBase);
