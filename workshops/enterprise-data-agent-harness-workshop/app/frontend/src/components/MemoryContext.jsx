import { useState } from "react";
import {
  ChevronDown, Brain, Wrench, BookOpen, MessageSquare, FileCode,
  ScrollText, FileText, History, Gauge,
} from "lucide-react";

const SECTION_META = {
  system_prompt: { label: "SYS", icon: ScrollText, color: "text-text-secondary" },
  messages: { label: "MSG", icon: MessageSquare, color: "text-accent-skill" },
  memories: { label: "MEM", icon: Brain, color: "text-accent-memory" },
  episodic: { label: "EPISODIC", icon: History, color: "text-accent-memory" },
  tool_outputs: { label: "TOOL", icon: FileCode, color: "text-accent-tool" },
  scratchpad: { label: "SCRATCH", icon: FileText, color: "text-accent-tool" },
  skill_manifest: { label: "SKILL", icon: BookOpen, color: "text-accent-skill" },
  tool_manifest: { label: "REG", icon: Wrench, color: "text-accent-tool" },
};

function Section({ section }) {
  const [open, setOpen] = useState(true);
  const meta = SECTION_META[section.key] || { label: "?", icon: Brain, color: "text-text-secondary" };
  const Icon = meta.icon;
  return (
    <div className="border border-white/5 rounded bg-bg-elev overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-3 py-2 hover:bg-white/[0.02]"
      >
        <div className="flex items-center gap-2">
          <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded bg-white/5 ${meta.color}`}>
            {meta.label}
          </span>
          <Icon size={12} className={meta.color} />
          <span className="text-xs text-text-accent">{section.name}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-text-muted">{section.items?.length || 0}</span>
          <ChevronDown
            size={12}
            className={`text-text-muted transition-transform ${open ? "" : "-rotate-90"}`}
          />
        </div>
      </button>
      {open && (
        <div className="border-t border-white/5 px-3 py-2 space-y-1.5">
          {(section.items || []).length === 0 ? (
            <div className="text-[10px] text-text-muted italic">empty</div>
          ) : (
            section.items.map((it, i) => <Item key={i} it={it} sectionKey={section.key} />)
          )}
        </div>
      )}
    </div>
  );
}

function Item({ it, sectionKey }) {
  if (sectionKey === "messages") {
    return (
      <div className="text-[10px]">
        <span className="font-mono text-text-muted">[{it.role}]</span>{" "}
        <span className="text-text-secondary">{it.content}</span>
      </div>
    );
  }
  if (sectionKey === "memories") {
    const scopeChipCls =
      it.scope === "this_thread"
        ? "bg-accent-memory/20 text-accent-memory"
        : it.scope === "other_thread"
          ? "bg-accent-tool/20 text-accent-tool"
          : "bg-text-secondary/15 text-text-secondary";
    const scopeLabel =
      it.scope === "this_thread" ? "this thread"
        : it.scope === "other_thread" ? `from ${(it.origin_thread_id || "").slice(0, 8)}…`
        : "global";
    return (
      <div className="text-[10px]">
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className="font-mono text-accent-memory">[{it.kind}]</span>
          <span className="text-text-accent">{it.subject}</span>
          <span className={`text-[9px] px-1 rounded font-mono ${scopeChipCls}`}>
            {scopeLabel}
          </span>
        </div>
        <div className="text-text-muted mt-0.5">{it.body}</div>
      </div>
    );
  }
  if (sectionKey === "tool_outputs") {
    return (
      <div className="text-[10px]">
        <span className="font-mono text-accent-tool">[{it.tool_name}]</span>{" "}
        <span className="text-text-muted">{it.args}</span>
        <pre className="text-text-muted/70 mt-0.5 whitespace-pre-wrap font-mono">{it.preview}</pre>
      </div>
    );
  }
  if (sectionKey === "skill_manifest") {
    return (
      <div className="text-[10px]">
        <span className="font-mono text-accent-skill">{it.name}</span>
        <div className="text-text-muted mt-0.5">{it.description}</div>
      </div>
    );
  }
  if (sectionKey === "tool_manifest") {
    return (
      <div className="text-[10px]">
        <span className="font-mono text-accent-tool">{it.name}</span>
        <div className="text-text-muted mt-0.5">{it.description}</div>
      </div>
    );
  }
  if (sectionKey === "system_prompt") {
    return (
      <div className="text-[10px]">
        <div className="font-mono text-text-secondary uppercase tracking-wider mb-0.5">{it.label}</div>
        <pre className="text-text-muted/80 whitespace-pre-wrap font-mono leading-relaxed">{it.content}</pre>
      </div>
    );
  }
  if (sectionKey === "scratchpad") {
    return (
      <div className="text-[10px]">
        <span className="font-mono text-accent-tool">{it.path}</span>
        <span className="text-text-muted ml-2">[{it.bytes}b]</span>
        {it.thread_id && it.thread_id !== "shared" && (
          <span className="text-[9px] px-1 ml-2 rounded font-mono bg-accent-memory/15 text-accent-memory"
                title={`physical path: ${it.full_path || it.path}`}>
            scoped: {it.thread_id.slice(0, 8)}…
          </span>
        )}
        {it.thread_id === "shared" && (
          <span className="text-[9px] px-1 ml-2 rounded font-mono bg-text-secondary/15 text-text-secondary">
            shared (no thread)
          </span>
        )}
        <pre className="text-text-muted/80 mt-0.5 whitespace-pre-wrap font-mono">{it.preview}</pre>
      </div>
    );
  }
  if (sectionKey === "episodic") {
    return (
      <div className="text-[10px]">
        <span className="font-mono text-accent-memory">thread {it.thread_id}</span>
        {it.user_query && (
          <span className="text-text-muted ml-2 italic">→ {it.user_query}</span>
        )}
        <pre className="text-text-muted/80 mt-0.5 whitespace-pre-wrap font-mono">{it.body}</pre>
      </div>
    );
  }
  return <pre className="text-[10px] text-text-muted">{JSON.stringify(it, null, 2)}</pre>;
}

function TokenMeter({ usage }) {
  const lt = usage?.lastTurn;
  const cum = usage?.cumulative || { prompt: 0, completion: 0, total: 0 };
  const max = usage?.modelMax || 200_000;
  // The "live" reading the bar tracks is the last turn's prompt_tokens — the
  // size of the context the model just saw. Cumulative is shown alongside it.
  const liveUsed = lt?.prompt || 0;
  const pct = Math.min(100, Math.round((liveUsed / max) * 100));
  const free = Math.max(0, max - liveUsed);

  // Colour-band the bar so the user can read fullness at a glance.
  const barColor =
    pct < 50 ? "bg-accent-memory" :
    pct < 80 ? "bg-accent-tool" :
    "bg-accent-sql";

  return (
    <div className="border border-white/5 rounded bg-bg-elev overflow-hidden">
      <div className="px-3 py-2 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-white/5 text-accent-tool">
            CTX
          </span>
          <Gauge size={12} className="text-accent-tool" />
          <span className="text-xs text-text-accent">Token usage</span>
        </div>
        <div className="text-[10px] text-text-muted font-mono">
          {usage?.model || "—"}
        </div>
      </div>

      <div className="border-t border-white/5 px-3 py-2 space-y-2">
        {/* Bar — live usage vs model max */}
        <div>
          <div className="flex items-baseline justify-between mb-1">
            <span className="text-[10px] text-text-muted">last turn prompt</span>
            <span className="text-[11px] font-mono text-text-accent">
              {liveUsed.toLocaleString()} / {max.toLocaleString()}
              <span className="text-text-muted ml-1">({pct}%)</span>
            </span>
          </div>
          <div className="h-1.5 bg-white/[0.05] rounded overflow-hidden">
            <div className={`h-full ${barColor} transition-all duration-300`} style={{ width: `${pct}%` }} />
          </div>
          <div className="flex justify-between text-[9px] text-text-muted mt-0.5">
            <span>0</span>
            <span className="text-accent-memory">free: {free.toLocaleString()}</span>
            <span>{max.toLocaleString()}</span>
          </div>
        </div>

        {/* Per-turn breakdown */}
        <div className="grid grid-cols-3 gap-2 text-[10px] font-mono">
          <Stat label="prompt"     value={lt?.prompt}     color="text-accent-skill" />
          <Stat label="completion" value={lt?.completion} color="text-accent-memory" />
          <Stat label="turn total" value={lt?.total}      color="text-text-accent" />
        </div>

        {/* Cumulative across thread */}
        <div className="grid grid-cols-3 gap-2 text-[10px] font-mono pt-1 border-t border-white/[0.04]">
          <Stat label="∑ prompt"     value={cum.prompt}     color="text-text-muted" />
          <Stat label="∑ completion" value={cum.completion} color="text-text-muted" />
          <Stat label="∑ total"      value={cum.total}      color="text-text-secondary" />
        </div>
      </div>
    </div>
  );
}

function Stat({ label, value, color }) {
  return (
    <div className="flex flex-col">
      <span className="text-[9px] uppercase tracking-wider text-text-muted">{label}</span>
      <span className={color}>{value != null ? value.toLocaleString() : "—"}</span>
    </div>
  );
}

export default function MemoryContext({ contextWindow, tokenUsage }) {
  const sections = contextWindow?.sections || [];
  return (
    <aside className="w-96 border-l border-white/5 bg-bg-panel overflow-y-auto py-3 px-3 space-y-2">
      <div className="px-1 py-1 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="text-[10px] uppercase tracking-wider text-text-muted">Memory Context</div>
          {contextWindow?.thread_id && (
            <span className="text-[9px] px-1.5 py-0.5 rounded font-mono bg-accent-skill/15 text-accent-skill"
                  title="all thread-scoped sections (messages, tool outputs, scratchpad, episodic) are filtered to this thread">
              thread: {String(contextWindow.thread_id).slice(0, 8)}…
            </span>
          )}
        </div>
        {contextWindow?.query && (
          <div className="text-[9px] text-text-muted/70 font-mono truncate max-w-[10rem]">
            ↳ {contextWindow.query}
          </div>
        )}
      </div>

      <TokenMeter usage={tokenUsage} />

      {sections.length === 0 ? (
        <div className="text-xs text-text-muted px-2 py-3 italic">
          send a message to populate the context window
        </div>
      ) : (
        sections.map((s) => <Section key={s.key} section={s} />)
      )}
    </aside>
  );
}
