import { memo } from "react";
import { motion } from "framer-motion";

// Isolated perpetual-motion leaf: a "breathing" status dot. Memoized so the
// infinite loop never re-renders the parent layout (taste-skill perf rule).
function StatusDotBase({ color }: { color: string }) {
  return (
    <span className="relative flex h-2.5 w-2.5 items-center justify-center">
      <motion.span
        className="absolute inset-0 rounded-full"
        style={{ background: color }}
        animate={{ scale: [1, 2.4], opacity: [0.45, 0] }}
        transition={{ duration: 2.4, repeat: Infinity, ease: "easeOut" }}
      />
      <span
        className="relative h-2 w-2 rounded-full"
        style={{ background: color }}
      />
    </span>
  );
}

export const StatusDot = memo(StatusDotBase);
