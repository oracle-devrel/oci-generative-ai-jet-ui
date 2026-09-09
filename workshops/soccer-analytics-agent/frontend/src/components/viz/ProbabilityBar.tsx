import { memo } from "react";
import { motion } from "framer-motion";
import { pct } from "../../lib/format";
import { spring } from "../../lib/motion";
import type { PredictResult } from "../../lib/types";

interface Props {
  data: PredictResult;
  /** Compact = side-panel hero. Inline = within a chat tool trace. */
  variant?: "hero" | "inline";
}

const SEG = [
  { key: "home", label: "home win", color: "var(--color-accent)" },
  { key: "draw", label: "draw", color: "#5b6675" },
  { key: "away", label: "away win", color: "var(--color-rose)" },
] as const;

/**
 * Animated Win / Draw / Loss probability bar. The three segments always sum
 * to 100%; widths spring-fill from zero on mount. Memoized so it never
 * re-renders from parent state churn.
 */
function ProbabilityBarBase({ data, variant = "hero" }: Props) {
  const total =
    data.prob_home_win + data.prob_draw + data.prob_away_win || 1;
  const vals = {
    home: data.prob_home_win / total,
    draw: data.prob_draw / total,
    away: data.prob_away_win / total,
  };
  const segs = [vals.home, vals.draw, vals.away];

  const leader = vals.home >= vals.away && vals.home >= vals.draw
    ? data.home_team
    : vals.away >= vals.draw
      ? data.away_team
      : "Draw";

  return (
    <div className="w-full">
      <div className="flex items-end justify-between gap-3">
        <div className="min-w-0">
          <p className="font-mono text-[10.5px] uppercase tracking-[0.14em] text-fg-faint">
            prediction
          </p>
          <h3
            className={`mt-1 truncate font-semibold tracking-tight text-fg ${
              variant === "hero" ? "text-[19px]" : "text-[16px]"
            }`}
          >
            {data.home_team}{" "}
            <span className="text-fg-faint">vs</span> {data.away_team}
          </h3>
        </div>
        <span className="flex-none rounded-full border border-line bg-surface-2 px-2.5 py-1 font-mono text-[10.5px] text-accent">
          {data.features_used} features
        </span>
      </div>

      {/* The bar */}
      <div className="mt-4">
        <div
          className="flex h-3.5 w-full gap-[3px] overflow-hidden rounded-full"
          role="img"
          aria-label={`Win ${pct(vals.home)}, draw ${pct(vals.draw)}, away win ${pct(vals.away)}`}
        >
          {SEG.map((s, i) => (
            <motion.span
              key={s.key}
              className="h-full rounded-full"
              style={{ background: s.color }}
              initial={{ width: 0 }}
              animate={{ width: `${segs[i] * 100}%` }}
              transition={{ ...spring, delay: 0.08 + i * 0.07 }}
            />
          ))}
        </div>

        {/* Legend / readouts */}
        <div className="mt-3 grid grid-cols-3 gap-2">
          {SEG.map((s, i) => {
            const teamLabel =
              s.key === "home"
                ? data.home_team
                : s.key === "away"
                  ? data.away_team
                  : "Draw";
            return (
              <div key={s.key} className="min-w-0">
                <div className="flex items-center gap-1.5">
                  <span
                    className="h-2 w-2 flex-none rounded-[3px]"
                    style={{ background: s.color }}
                  />
                  <span className="truncate text-[11.5px] text-fg-dim">
                    {variant === "hero" ? teamLabel : s.label}
                  </span>
                </div>
                <motion.div
                  className="mt-0.5 font-mono text-[17px] font-medium tabular-nums text-fg"
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.2 + i * 0.07 }}
                >
                  {pct(segs[i])}
                </motion.div>
              </div>
            );
          })}
        </div>
      </div>

      <div className="mt-4 flex items-center justify-between border-t border-line-soft pt-3 font-mono text-[10.5px] text-fg-faint">
        <span>
          favored: <span className="text-fg-dim">{leader}</span>
        </span>
        <span>
          {data.model_version} · {data.source}
        </span>
      </div>
    </div>
  );
}

export const ProbabilityBar = memo(ProbabilityBarBase);
