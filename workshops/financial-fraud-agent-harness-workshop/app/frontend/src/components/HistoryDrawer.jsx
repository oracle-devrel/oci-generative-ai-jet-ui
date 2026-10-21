import { Plus, X } from "lucide-react";
import ThreadList from "./ThreadList";

/**
 * Slide-over conversation history. Replaces the always-on left thread column:
 * the slim rail's History button toggles this panel over the chat, so past
 * conversations are one click away without permanently spending screen width.
 */
export default function HistoryDrawer({
  open, onClose,
  threads, currentThreadId, onSelect, onDelete, onNewThread,
}) {
  return (
    <>
      {open && (
        <div
          className="absolute inset-0 z-30 bg-black/50 backdrop-blur-[1px]"
          onClick={onClose}
        />
      )}
      <div
        className={`absolute inset-y-0 left-0 z-40 w-80 max-w-[85vw] transition-transform duration-300 ease-out ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
        aria-hidden={!open}
        // Off-screen but still in the DOM: `inert` keeps its buttons out of the
        // tab order and the accessibility tree while closed.
        inert={open ? undefined : ""}
      >
        <div className="h-full bg-bg-panel border-r border-white/10 flex flex-col shadow-[8px_0_40px_-12px_rgba(0,0,0,0.7)]">
          <div className="h-11 shrink-0 flex items-center gap-2 px-3 border-b border-white/5">
            <span className="text-[10px] uppercase tracking-wider text-text-muted">Conversations</span>
            <span className="text-[10px] text-text-muted font-mono">{threads.length}</span>
            <button
              onClick={onNewThread}
              className="ml-auto flex items-center gap-1 text-[10px] px-2 py-1 rounded border border-white/10 text-text-secondary hover:text-text-primary hover:border-accent-skill/40"
            >
              <Plus size={11} /> new
            </button>
            <button
              onClick={onClose}
              className="p-1 rounded text-text-muted hover:text-text-primary hover:bg-white/5"
              title="close"
              aria-label="Close conversations"
            >
              <X size={13} />
            </button>
          </div>
          <div className="flex-1 overflow-y-auto">
            <ThreadList
              threads={threads}
              currentThreadId={currentThreadId}
              onSelect={onSelect}
              onDelete={onDelete}
            />
          </div>
        </div>
      </div>
    </>
  );
}
