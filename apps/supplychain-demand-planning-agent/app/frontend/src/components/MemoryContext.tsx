import { useState } from "react";
import { Check, ChevronDown, ChevronRight, Loader2, Wrench } from "lucide-react";
import type { AgentName, AgentTrace, ToolCall } from "../types";

interface Props {
  agents: Record<AgentName, AgentTrace>;
}

const ORDER: AgentName[] = ["supervisor", "policy_agent", "demand_analyst"];

const COLOR: Record<AgentName, { dot: string; chip: string; label: string }> = {
  supervisor: {
    dot: "bg-accent-oracle",
    chip: "bg-accent-oracle/15 text-accent-oracle",
    label: "supervisor",
  },
  policy_agent: {
    dot: "bg-accent-skill",
    chip: "bg-accent-skill/15  text-accent-skill",
    label: "policy_agent",
  },
  demand_analyst: {
    dot: "bg-accent-memory",
    chip: "bg-accent-memory/15 text-accent-memory",
    label: "demand_analyst",
  },
};

export function MemoryContext({ agents }: Props) {
  const [active, setActive] = useState<AgentName>("supervisor");
  const trace = agents[active];
  const status: "idle" | "running" | "done" = trace.finished
    ? "done"
    : trace.started
      ? "running"
      : "idle";

  return (
    <aside className="pane w-[24rem] shrink-0">
      <div className="pane-header">
        <div className="pane-title">Agent context</div>
        <div className="text-[10px] text-text-muted">live per-agent trace</div>
      </div>

      <div className="grid grid-cols-3 gap-1 p-2 border-b border-border-subtle">
        {ORDER.map((a) => {
          const c = COLOR[a];
          const s = agents[a].finished ? "done" : agents[a].started ? "running" : "idle";
          const calls = agents[a].toolCalls.length;
          return (
            <button
              key={a}
              onClick={() => setActive(a)}
              className={`text-left px-2 py-1.5 rounded border text-[11px] font-mono transition-colors ${
                a === active
                  ? `border-border-medium bg-overlay-medium ${c.chip}`
                  : "border-border-subtle bg-bg-elev text-text-secondary hover:bg-overlay-soft"
              }`}
            >
              <div className="flex items-center gap-1.5">
                <span
                  className={`w-1.5 h-1.5 rounded-full ${c.dot} ${s === "running" ? "animate-pulse" : ""}`}
                />
                <span className="truncate font-semibold">{c.label}</span>
              </div>
              <div className="text-[9px] text-text-muted mt-0.5">
                {s} · {calls} tool{calls === 1 ? "" : "s"}
              </div>
            </button>
          );
        })}
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        <Section title="Status">
          <div className="text-[11px] font-mono space-y-1">
            <KV
              k="state"
              v={status}
              accentClass={
                status === "running"
                  ? "text-accent-tool"
                  : status === "done"
                    ? "text-accent-memory"
                    : "text-text-muted"
              }
            />
            <KV
              k="started"
              v={trace.started ? new Date(trace.started).toLocaleTimeString() : "—"}
            />
            <KV
              k="finished"
              v={trace.finished ? new Date(trace.finished).toLocaleTimeString() : "—"}
            />
          </div>
        </Section>

        <Section title={`Tool calls (${trace.toolCalls.length})`}>
          {trace.toolCalls.length === 0 ? (
            <div className="text-[11px] text-text-muted">no tools called yet</div>
          ) : (
            <div className="space-y-1.5">
              {trace.toolCalls.map((tc) => (
                <ToolCallRow key={tc.id} tc={tc} />
              ))}
            </div>
          )}
        </Section>

        <Section title="Streaming output">
          {trace.tokens ? (
            <pre className="text-[11px] font-mono whitespace-pre-wrap bg-bg-elev border border-border-subtle rounded p-2 max-h-60 overflow-auto leading-relaxed text-text-accent">
              {trace.tokens}
            </pre>
          ) : (
            <div className="text-[11px] text-text-muted">no tokens streamed yet</div>
          )}
        </Section>

        {trace.summary && (
          <Section title="Final summary">
            <pre className="text-[11px] font-mono whitespace-pre-wrap bg-bg-elev border border-border-subtle rounded p-2 max-h-40 overflow-auto leading-relaxed text-text-accent">
              {trace.summary}
            </pre>
          </Section>
        )}
      </div>
    </aside>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  const [open, setOpen] = useState(true);
  return (
    <div className="rounded border border-border-subtle bg-bg-elev">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full px-2.5 py-1.5 flex items-center justify-between text-[10px] uppercase tracking-wider text-text-secondary hover:text-text-primary"
      >
        <span>{title}</span>
        {open ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
      </button>
      {open && <div className="px-2.5 pb-2.5">{children}</div>}
    </div>
  );
}

function KV({ k, v, accentClass }: { k: string; v: string; accentClass?: string }) {
  return (
    <div className="flex justify-between">
      <span className="text-text-muted">{k}</span>
      <span className={accentClass || "text-text-accent"}>{v}</span>
    </div>
  );
}

function ToolCallRow({ tc }: { tc: ToolCall }) {
  const [open, setOpen] = useState(false);
  const argsPreview = Object.entries(tc.args)
    .map(([k, v]) => `${k}=${JSON.stringify(v).slice(0, 24)}`)
    .join(", ");
  return (
    <div className="border border-border-subtle rounded bg-bg-panel text-[11px]">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full px-2 py-1.5 flex items-center gap-2 text-left"
      >
        <span className={`chip ${tc.finishedAt ? "badge-done" : "badge-running"}`}>
          {tc.finishedAt ? <Check size={9} /> : <Loader2 size={9} className="animate-spin" />}
          {tc.finishedAt ? "done" : "running"}
        </span>
        <span className="font-mono text-accent-tool truncate flex items-center gap-1">
          <Wrench size={10} className="text-text-muted" />
          {tc.tool}
        </span>
        {argsPreview && <span className="text-text-muted truncate flex-1">({argsPreview})</span>}
        {open ? (
          <ChevronDown size={12} className="text-text-muted shrink-0" />
        ) : (
          <ChevronRight size={12} className="text-text-muted shrink-0" />
        )}
      </button>
      {open && tc.result && (
        <pre className="px-2 pb-2 text-[10px] font-mono whitespace-pre-wrap text-text-accent border-t border-border-subtle pt-2 max-h-48 overflow-auto leading-relaxed">
          {tc.result.slice(0, 4000)}
        </pre>
      )}
    </div>
  );
}
