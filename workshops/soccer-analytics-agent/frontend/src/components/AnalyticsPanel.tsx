import { memo } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ChartLineUpIcon, PulseIcon } from "@phosphor-icons/react";
import type { AnalyticsSnapshot } from "../lib/analytics";
import { hasAnalytics } from "../lib/analytics";
import { stagger, riseItem } from "../lib/motion";
import { ProbabilityBar } from "./viz/ProbabilityBar";
import { EloGauges } from "./viz/EloGauges";
import { FormTiles } from "./viz/FormTiles";
import { MomentumTiles } from "./viz/MomentumTiles";
import { PoissonTiles } from "./viz/PoissonTiles";

function Section({ children }: { children: React.ReactNode }) {
  return (
    <motion.section
      variants={riseItem}
      className="rounded-[var(--radius-card)] border border-line-soft bg-surface/70 p-5 shadow-[var(--shadow-tint)] backdrop-blur-sm"
    >
      {children}
    </motion.section>
  );
}

/** Persistent analytics panel. Renders the most-recent match / team that the
 *  agent has analyzed in this conversation. The "one memorable thing". */
function AnalyticsPanelBase({ snapshot }: { snapshot: AnalyticsSnapshot }) {
  const populated = hasAnalytics(snapshot);

  return (
    <div className="flex h-full flex-col">
      <header className="flex items-center justify-between border-b border-line-soft px-1 pb-4">
        <div className="flex items-center gap-2.5">
          <ChartLineUpIcon size={17} weight="bold" className="text-accent" />
          <h2 className="text-[13px] font-semibold tracking-tight text-fg">
            Analytics
          </h2>
        </div>
        {snapshot.subjectTeams.length > 0 && (
          <span className="truncate font-mono text-[10.5px] text-fg-faint">
            {snapshot.subjectTeams.slice(0, 2).join(" · ")}
          </span>
        )}
      </header>

      <div className="min-h-0 flex-1 overflow-y-auto px-1 pt-4">
        <AnimatePresence mode="wait">
          {!populated ? (
            <motion.div
              key="empty"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="flex h-full flex-col items-center justify-center px-4 text-center"
            >
              <div className="grid h-12 w-12 place-items-center rounded-2xl border border-line-soft bg-surface-2">
                <PulseIcon size={20} weight="bold" className="text-fg-faint" />
              </div>
              <p className="mt-4 text-[13.5px] font-medium text-fg-dim">
                No analysis yet
              </p>
              <p className="mt-1.5 max-w-[34ch] text-[12px] leading-relaxed text-fg-faint">
                Ask for a prediction or a team breakdown — the probability bar,
                Elo gauges, and stat tiles render here as the agent works.
              </p>
            </motion.div>
          ) : (
            <motion.div
              key="filled"
              variants={stagger}
              initial="hidden"
              animate="show"
              className="grid gap-3.5 pb-2"
            >
              {snapshot.prediction && (
                <Section>
                  <ProbabilityBar data={snapshot.prediction} variant="hero" />
                </Section>
              )}
              {snapshot.poisson && (
                <Section>
                  <PoissonTiles data={snapshot.poisson} />
                </Section>
              )}
              {snapshot.elo.map((e) => (
                <Section key={`elo-${e.team}`}>
                  <EloGauges data={e} />
                </Section>
              ))}
              {snapshot.form.map((f) => (
                <Section key={`form-${f.team}`}>
                  <FormTiles data={f} />
                </Section>
              ))}
              {snapshot.momentum && (
                <Section>
                  <MomentumTiles data={snapshot.momentum} />
                </Section>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

export const AnalyticsPanel = memo(AnalyticsPanelBase);
