import { memo } from "react";
import { motion } from "framer-motion";
import { signed } from "../../lib/format";
import { spring } from "../../lib/motion";
import type { EloResult } from "../../lib/types";

interface Props {
  data: EloResult;
}

// Elo display window. ~1200 (weak) to ~2100 (elite) covers the dataset's
// range comfortably; we clamp the fill so it reads as a tier gauge.
const LO = 1200;
const HI = 2100;
const frac = (v: number) => Math.max(0, Math.min(1, (v - LO) / (HI - LO)));

const TIERS = [
  { key: "world_cup_elo", label: "World Cup" },
  { key: "continental_elo", label: "Continental" },
  { key: "qualifier_elo", label: "Qualifier" },
  { key: "friendly_elo", label: "Friendly" },
] as const;

/** Per-tier Elo gauges with spring-filled bars, headed by the global rating. */
function EloGaugesBase({ data }: Props) {
  return (
    <div>
      <div className="flex items-baseline justify-between">
        <div>
          <p className="font-mono text-[10.5px] uppercase tracking-[0.14em] text-fg-faint">
            elo rating
          </p>
          <h4 className="mt-1 text-[15px] font-semibold tracking-tight text-fg">
            {data.team}
          </h4>
        </div>
        <div className="text-right">
          <div className="font-mono text-[22px] font-medium leading-none tabular-nums text-fg">
            {Math.round(data.elo)}
          </div>
          <div
            className="mt-1 font-mono text-[11px] tabular-nums"
            style={{ color: data.vs_average >= 0 ? "var(--color-accent)" : "var(--color-rose)" }}
          >
            {signed(data.vs_average, 0)} vs avg
          </div>
        </div>
      </div>

      <div className="mt-4 grid gap-2.5">
        {TIERS.map((t, i) => {
          const v = data[t.key] as number;
          return (
            <div key={t.key} className="grid grid-cols-[78px_1fr_46px] items-center gap-3">
              <span className="text-[11.5px] text-fg-dim">{t.label}</span>
              <div className="h-1.5 overflow-hidden rounded-full bg-surface-3">
                <motion.div
                  className="h-full rounded-full"
                  style={{
                    background:
                      "linear-gradient(90deg, var(--color-accent-dim), var(--color-accent))",
                  }}
                  initial={{ width: 0 }}
                  animate={{ width: `${frac(v) * 100}%` }}
                  transition={{ ...spring, delay: 0.05 + i * 0.06 }}
                />
              </div>
              <span className="text-right font-mono text-[11.5px] tabular-nums text-fg-dim">
                {Math.round(v)}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export const EloGauges = memo(EloGaugesBase);
