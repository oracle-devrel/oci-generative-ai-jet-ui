import { memo } from "react";
import { motion } from "framer-motion";
import { spring } from "../lib/motion";
import { ToolTrace } from "./ToolTrace";
import type { Message } from "../lib/types";

/** A single conversation turn — user (right) or agent (left), with an
 *  optional visual tool trace below assistant replies. */
function MessageBubbleBase({ message }: { message: Message }) {
  const isUser = message.role === "user";
  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={spring}
      className={`flex flex-col ${isUser ? "items-end" : "items-start"}`}
    >
      <span className="mb-1.5 px-1 font-mono text-[10px] uppercase tracking-[0.12em] text-fg-faint">
        {isUser ? "you" : "agent"}
      </span>
      <div
        className={
          isUser
            ? "max-w-[88%] rounded-[var(--radius-card)] rounded-br-[5px] border border-line bg-surface-2 px-4 py-3 text-[14.5px] leading-relaxed text-fg"
            : message.isError
              ? "max-w-[92%] whitespace-pre-wrap break-words rounded-[var(--radius-card)] rounded-bl-[5px] border border-rose/45 bg-rose/10 px-4 py-3 text-[14.5px] leading-relaxed text-rose"
              : "max-w-[92%] whitespace-pre-wrap break-words rounded-[var(--radius-card)] rounded-bl-[5px] border border-line-soft bg-surface px-4 py-3 text-[14.5px] leading-relaxed text-fg shadow-[var(--shadow-tint-sm)]"
        }
      >
        {message.text}
      </div>
      {!isUser && message.trace && message.trace.length > 0 && (
        <div className="w-full max-w-[92%]">
          <ToolTrace trace={message.trace} />
        </div>
      )}
    </motion.div>
  );
}

export const MessageBubble = memo(MessageBubbleBase);
