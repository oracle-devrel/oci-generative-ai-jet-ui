import { useEffect, useState } from "react";
import { streamChat } from "../api/chat";
import { fetchMemory } from "../api/memory";
import type { ChatMsg, ChartPayload, Side } from "../types";
import { ChatMessage } from "./ChatMessage";
import { DemoPills } from "./DemoPills";
import { DataSummary } from "./DataSummary";
import { ChatInput } from "./ChatInput";
import { DataInspector } from "./DataInspector";
import { SourceConnection } from "./SourceConnection";
import mongoLogo from "../assets/mongodb-logo.png";
import oracleLogo from "../assets/oracle-logo.png";

export function ChatPane({
  side,
  locked,
  refreshKey,
  resetKey,
}: {
  side: Side;
  locked?: boolean;
  refreshKey?: number;
  resetKey?: number;
}) {
  const [msgs, setMsgs] = useState<ChatMsg[]>([]);
  const [busy, setBusy] = useState(false);
  const [inspectorOpen, setInspectorOpen] = useState(false);
  const [statsRefresh, setStatsRefresh] = useState(0);

  useEffect(() => {
    setMsgs([]);
    setBusy(false);
    setInspectorOpen(false);
    setStatsRefresh((k) => k + 1);
  }, [resetKey]);

  useEffect(() => {
    if (side !== "oracle" || locked) return;
    fetchMemory("oracle")
      .then((memory) => {
        const imported = memory.messages.filter((m) => m.source_side === "mongo");
        if (!imported.length) return;
        setMsgs(
          imported.map((m) => ({
            role: m.role,
            text: m.content,
          }))
        );
      })
      .catch(() => {});
  }, [side, locked, refreshKey]);

  function updateLast(arr: ChatMsg[], patch: Partial<ChatMsg>): ChatMsg[] {
    const out = [...arr];
    out[out.length - 1] = { ...out[out.length - 1], ...patch };
    return out;
  }

  async function ask(q: string) {
    setBusy(true);
    setMsgs((m) => [
      ...m,
      { role: "user", text: q },
      { role: "assistant", text: "", tool_statuses: [] },
    ]);
    await streamChat(
      side,
      q,
      (tok) => setMsgs((m) => updateLast(m, { text: m[m.length - 1].text + tok })),
      (c: ChartPayload) => setMsgs((m) => updateLast(m, { chart: c })),
      (s: string) =>
        setMsgs((m) =>
          updateLast(m, { tool_statuses: [...(m[m.length - 1].tool_statuses ?? []), s] })
        ),
      () => {
        setBusy(false);
        setStatsRefresh((k) => k + 1);
      }
    );
  }

  return (
    <div className={`flex flex-col h-full ${locked ? "opacity-40 pointer-events-none" : ""}`}>
      <div className="mb-3 flex items-center justify-between gap-3">
        <img
          src={side === "mongo" ? mongoLogo : oracleLogo}
          alt={side === "mongo" ? "MongoDB" : "Oracle"}
          className="h-10 w-36 object-contain object-left"
        />
        <button
          onClick={() => setInspectorOpen(true)}
          disabled={locked}
          className="rounded-full border border-oracle-ink/15 bg-white/70 px-3 py-1 text-xs font-medium text-oracle-ink/70 hover:border-oracle-red hover:text-oracle-red disabled:opacity-40"
        >
          Inspect data
        </button>
      </div>
      {side === "mongo" && <SourceConnection onChange={() => setStatsRefresh((k) => k + 1)} />}
      <DataSummary side={side} locked={locked} refreshKey={`${refreshKey ?? 0}:${statsRefresh}`} />
      <DemoPills onPick={ask} disabled={busy || locked} />
      <div className="flex-1 overflow-y-auto flex flex-col gap-2 min-h-0">
        {msgs.length === 0 && !locked && (
          <div className="text-sm opacity-50">Pick a demo question or type one of your own.</div>
        )}
        {locked && <div className="text-sm opacity-60">Not migrated yet.</div>}
        {msgs.map((m, i) => (
          <ChatMessage key={i} msg={m} />
        ))}
      </div>
      <ChatInput
        onSubmit={ask}
        disabled={busy || locked}
        placeholder={side === "mongo" ? "Ask Mongo anything..." : "Ask Oracle anything..."}
      />
      <DataInspector side={side} open={inspectorOpen} onClose={() => setInspectorOpen(false)} />
    </div>
  );
}
