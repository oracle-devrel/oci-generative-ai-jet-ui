import { Hash } from "lucide-react";

interface Props {
  threadId: string | null;
}

/** Single-thread sidebar (one WebSocket session = one thread, today). */
export function ThreadList({ threadId }: Props) {
  return (
    <aside className="pane w-56 shrink-0">
      <div className="pane-header">
        <div className="pane-title">Threads</div>
      </div>
      <div className="flex-1 overflow-y-auto py-2 px-2 space-y-1">
        {threadId ? (
          <div className="px-2 py-2 rounded bg-overlay-medium border border-border-subtle">
            <div className="flex items-center gap-1.5 text-[11px] font-mono text-text-primary">
              <Hash size={11} className="text-accent-memory" />
              <span className="truncate">{threadId}</span>
            </div>
            <div className="text-[10px] text-text-muted mt-1">active</div>
          </div>
        ) : (
          <div className="px-2 py-2 text-[11px] text-text-muted">no session yet…</div>
        )}
      </div>
      <div className="border-t border-border-subtle px-3 py-2 text-[10px] text-text-muted">
        each browser tab opens its own thread
      </div>
    </aside>
  );
}
