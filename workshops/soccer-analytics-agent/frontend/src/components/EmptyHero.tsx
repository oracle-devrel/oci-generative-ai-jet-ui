import { motion } from "framer-motion";
import { ArrowUpRightIcon } from "@phosphor-icons/react";
import { stagger, riseItem } from "../lib/motion";

const SUGGESTIONS = [
  {
    k: "01",
    q: "Which teams have the highest Elo ratings going into World Cup 2026?",
    label: "Top Elo ratings going into World Cup 2026",
  },
  {
    k: "02",
    q: "Predict Spain vs Brazil at a neutral venue.",
    label: "Predict Spain vs Brazil at a neutral venue",
  },
  {
    k: "03",
    q: "Compare Argentina and France: their Elo, recent form, and head-to-head.",
    label: "Compare Argentina and France — Elo, form, H2H",
  },
  {
    k: "04",
    q: "Show Brazil's momentum and Poisson xG against Germany.",
    label: "Brazil momentum and Poisson xG vs Germany",
  },
];

interface Props {
  onPick: (q: string) => void;
}

/** Composed empty state: asymmetric left-aligned hero + suggestion chips. */
export function EmptyHero({ onPick }: Props) {
  return (
    <motion.div
      variants={stagger}
      initial="hidden"
      animate="show"
      className="mx-auto max-w-[640px] pt-[clamp(24px,7vh,72px)]"
    >
      <motion.p
        variants={riseItem}
        className="font-mono text-[11px] uppercase tracking-[0.18em] text-accent"
      >
        oracle ai database · grok 4 · 92-feature xgboost
      </motion.p>
      <motion.h2
        variants={riseItem}
        className="mt-3 text-[clamp(28px,4.6vw,42px)] font-semibold leading-[1.04] tracking-tight text-fg"
      >
        Ask about{" "}
        <span className="text-accent">49,287 matches</span>{" "}
        <br className="hidden sm:block" />
        of international football.
      </motion.h2>
      <motion.p
        variants={riseItem}
        className="mt-3.5 max-w-[54ch] text-[14.5px] leading-relaxed text-fg-dim"
      >
        Real Elo ratings, recent form, head-to-head, momentum, and Poisson xG
        feed the model behind every prediction. The analytics panel updates as
        the agent works. Pick a starting point or type your own.
      </motion.p>

      <motion.div
        variants={stagger}
        className="mt-7 grid grid-cols-1 gap-2.5 sm:grid-cols-2"
      >
        {SUGGESTIONS.map((s) => (
          <motion.button
            key={s.k}
            variants={riseItem}
            type="button"
            onClick={() => onPick(s.q)}
            whileTap={{ scale: 0.99 }}
            className="group flex items-start gap-3 rounded-[14px] border border-line-soft bg-surface px-4 py-3.5 text-left transition-[border-color,background,transform] hover:-translate-y-px hover:border-line hover:bg-surface-2"
          >
            <span className="mt-0.5 flex-none font-mono text-[11px] text-accent">
              {s.k}
            </span>
            <span className="flex-1 text-[13.5px] leading-snug text-fg">
              {s.label}
            </span>
            <ArrowUpRightIcon
              size={15}
              weight="bold"
              className="mt-0.5 flex-none text-fg-faint transition-colors group-hover:text-accent"
            />
          </motion.button>
        ))}
      </motion.div>
    </motion.div>
  );
}
