import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { CaretRightIcon } from "@phosphor-icons/react";

/** Collapsible raw-JSON disclosure — default collapsed; for the technical
 *  audience that wants to verify the exact tool payload. */
export function RawJson({
  data,
  label = "raw json",
}: {
  data: unknown;
  label?: string;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div className="mt-2">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1.5 font-mono text-[10.5px] text-fg-faint transition-colors hover:text-fg-dim active:scale-[0.98]"
        aria-expanded={open}
      >
        <motion.span animate={{ rotate: open ? 90 : 0 }} transition={{ duration: 0.18 }}>
          <CaretRightIcon size={11} weight="bold" />
        </motion.span>
        {label}
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.pre
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="mt-2 max-h-72 overflow-auto rounded-lg border border-line-soft bg-ink p-3 font-mono text-[11px] leading-relaxed text-fg-dim"
          >
            {JSON.stringify(data, null, 2)}
          </motion.pre>
        )}
      </AnimatePresence>
    </div>
  );
}
