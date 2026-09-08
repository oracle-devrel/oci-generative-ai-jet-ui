import { memo } from "react";
import { motion } from "framer-motion";
import { StatTiles, type Tile } from "./StatTiles";
import { num2, pctRound, signed } from "../../lib/format";
import { spring } from "../../lib/motion";
import type { PoissonResult } from "../../lib/types";

// Lambda display ceiling for the dual xG meter.
const LAMBDA_MAX = 3.5;
const lf = (v: number) => Math.max(0, Math.min(1, v / LAMBDA_MAX));

/** Poisson expected-goals: dual lambda meter + outcome / variance tiles. */
function PoissonTilesBase({ data }: { data: PoissonResult }) {
  const tiles: Tile[] = [
    { label: "P(home win)", value: pctRound(data.home_poisson_win), accent: data.home_poisson_win >= 0.45 },
    { label: "P(draw)", value: pctRound(data.home_poisson_draw) },
    { label: "home var", value: num2(data.home_scoring_variance), sub: "scoring" },
    { label: "away var", value: num2(data.away_scoring_variance), sub: "scoring" },
    {
      label: "home over/under",
      value: signed(data.home_overperformance, 2),
      accent: data.home_overperformance > 0,
      sub: "vs model",
    },
    {
      label: "away over/under",
      value: signed(data.away_overperformance, 2),
      accent: data.away_overperformance > 0,
      sub: "vs model",
    },
  ];

  return (
    <div>
      <div className="mb-3 flex items-baseline justify-between">
        <h4 className="text-[15px] font-semibold tracking-tight text-fg">
          Poisson xG
        </h4>
        <span className="font-mono text-[10.5px] text-fg-faint">
          {data.home_team} vs {data.away_team}
        </span>
      </div>

      {/* Expected goals (lambda) — two opposed meters */}
      <div className="mb-3 grid gap-2.5 rounded-[14px] border border-line-soft bg-surface-2 p-3.5">
        {[
          { team: data.home_team, lam: data.home_lambda, color: "var(--color-accent)" },
          { team: data.away_team, lam: data.away_lambda, color: "var(--color-rose)" },
        ].map((row, i) => (
          <div key={row.team} className="grid grid-cols-[1fr_2fr_auto] items-center gap-3">
            <span className="truncate text-[11.5px] text-fg-dim">{row.team}</span>
            <div className="h-2 overflow-hidden rounded-full bg-surface-3">
              <motion.div
                className="h-full rounded-full"
                style={{ background: row.color }}
                initial={{ width: 0 }}
                animate={{ width: `${lf(row.lam) * 100}%` }}
                transition={{ ...spring, delay: 0.05 + i * 0.08 }}
              />
            </div>
            <span className="font-mono text-[12px] tabular-nums text-fg">
              {num2(row.lam)} <span className="text-fg-faint">xG</span>
            </span>
          </div>
        ))}
      </div>

      <StatTiles tiles={tiles} cols={3} />
    </div>
  );
}

export const PoissonTiles = memo(PoissonTilesBase);
