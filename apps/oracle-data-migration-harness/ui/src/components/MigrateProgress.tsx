import { useState } from "react";
import type { StageEvent } from "../api/migrate";

const STAGES = ["plan", "sample", "translate_schema", "dry_run", "transfer", "verify", "reconcile"];

const STAGE_LABELS: Record<string, string> = {
  plan: "plan",
  sample: "sample",
  translate_schema: "translate schema",
  dry_run: "dry run",
  transfer: "transfer",
  verify: "verify",
  reconcile: "reconcile",
};

const STAGE_DESCRIPTIONS: Record<string, string> = {
  plan: "Creates the run manifest for documents, vectors, and memory.",
  sample: "Pulls a small slice from MongoDB so the harness can inspect the document shape.",
  translate_schema: "Reads the Oracle migration playbook and chooses JSON Relational Duality.",
  dry_run: "Rehearses the landing path on a small batch before moving everything.",
  transfer: "Moves documents, vectors, and conversation memory into Oracle.",
  verify: "Checks counts, content samples, and migrated memory after the move.",
  reconcile: "Records gaps, fixes, and the final run state.",
};

export function MigrateProgress({ events }: { events: StageEvent[] }) {
  const [openCode, setOpenCode] = useState<Record<string, boolean>>({});
  const last = events[events.length - 1];
  const latestByStage = new Map<string, StageEvent>();
  for (const event of events) latestByStage.set(event.stage, event);

  return (
    <div className="mt-4 w-full min-h-0 flex flex-col gap-3">
      {last && (
        <div className="rounded-md bg-white/70 border border-oracle-ink/10 px-3 py-2">
          <p className="text-xs italic opacity-80">{last.narration}</p>
          {last.ddl_preview && (
            <p className="mt-1 text-[11px] font-mono opacity-60">{last.ddl_preview}</p>
          )}
        </div>
      )}

      <div className="space-y-3 pb-4">
        {STAGES.map((stage) => {
          const evt = latestByStage.get(stage);
          const status = evt?.status ?? "pending";
          const isActive = status === "started";
          const isComplete = status === "completed";
          const isCodeOpen = Boolean(openCode[stage]);

          return (
            <section
              key={stage}
              className={`rounded-lg border bg-white/75 overflow-hidden ${
                isActive
                  ? "border-yellow-400 shadow-sm"
                  : isComplete
                    ? "border-oracle-red/40"
                    : "border-oracle-ink/10 opacity-65"
              }`}
            >
              <div className="flex items-start gap-2 px-3 py-2 border-b border-oracle-ink/10">
                <span
                  className={`mt-1 w-2 h-2 rounded-full shrink-0 ${
                    isComplete
                      ? "bg-oracle-red"
                      : isActive
                        ? "bg-yellow-400 animate-pulse"
                        : "bg-oracle-ink/15"
                  }`}
                />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between gap-2">
                    <h3 className="text-xs font-mono font-semibold">{STAGE_LABELS[stage]}</h3>
                    <span className="text-[10px] uppercase tracking-wide opacity-50">{status}</span>
                  </div>
                  <p className="mt-1 text-[11px] leading-snug text-oracle-ink/60">
                    {STAGE_DESCRIPTIONS[stage]}
                  </p>
                  {evt?.narration && (
                    <p className="mt-1 text-[11px] italic text-oracle-ink/70">{evt.narration}</p>
                  )}
                  {isComplete && evt?.code && (
                    <button
                      type="button"
                      onClick={() => setOpenCode((prev) => ({ ...prev, [stage]: !prev[stage] }))}
                      className="mt-2 rounded-full border border-oracle-ink/15 bg-white/80 px-2.5 py-1 text-[10px] font-medium text-oracle-ink/65 hover:border-oracle-red hover:text-oracle-red"
                    >
                      {isCodeOpen ? "Hide code details" : "Show code details"}
                    </button>
                  )}
                </div>
              </div>

              {isCodeOpen && isComplete && evt?.code && (
                <div className="bg-oracle-ink text-oracle-cream">
                  <div className="flex items-center justify-between px-3 py-1.5 border-b border-oracle-cream/10 bg-black/20">
                    <span className="text-[9px] font-semibold uppercase tracking-wide text-oracle-cream/60">
                      Code that ran in this stage
                    </span>
                    <span className="text-[9px] text-oracle-cream/50">completed</span>
                  </div>
                  <pre className="max-h-44 overflow-auto p-3 text-[10px] leading-relaxed font-mono whitespace-pre-wrap">
                    <code>{evt.code}</code>
                  </pre>
                </div>
              )}
            </section>
          );
        })}
      </div>
    </div>
  );
}
