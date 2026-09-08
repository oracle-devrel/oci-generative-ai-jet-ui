import { Trash2 } from "lucide-react";

export default function ThreadList({ threads, currentThreadId, onSelect, onDelete }) {
  return (
    <aside className="w-56 border-r border-white/5 bg-bg-panel overflow-y-auto py-2">
      <div className="px-3 py-1 text-[10px] uppercase tracking-wider text-text-muted">
        Threads
      </div>
      {threads.length === 0 && (
        <div className="px-3 py-2 text-xs text-text-secondary">
          (no threads yet — your first message will create one)
        </div>
      )}
      {threads.map((t) => {
        const active = t.thread_id === currentThreadId;
        return (
          <div
            key={t.thread_id}
            className={`group flex items-center px-3 py-2 hover:bg-white/[0.03] ${
              active ? "bg-white/[0.05] text-text-primary" : "text-text-secondary"
            }`}
          >
            <button
              onClick={() => onSelect(t.thread_id)}
              className="flex-1 text-left min-w-0"
            >
              <div className="font-mono text-[11px] truncate">{t.thread_id}</div>
              {t.summary && (
                <div className="text-[10px] text-text-muted truncate mt-0.5">{t.summary}</div>
              )}
            </button>
            <button
              onClick={(e) => {
                e.stopPropagation();
                if (
                  window.confirm(
                    `Delete thread ${t.thread_id}? This removes all of its messages and memories.`
                  )
                ) {
                  onDelete?.(t.thread_id);
                }
              }}
              className="ml-2 p-1 rounded text-text-muted opacity-0 group-hover:opacity-100 hover:text-accent-sql hover:bg-accent-sql/10 transition"
              title="delete thread"
            >
              <Trash2 size={11} />
            </button>
          </div>
        );
      })}
    </aside>
  );
}
