import { memo } from "react";
import { motion } from "framer-motion";
import { stagger, riseItem } from "../../lib/motion";

export interface Tile {
  label: string;
  value: string;
  /** Optional 0..1 intensity to tint the value (e.g. high streak = accent). */
  accent?: boolean;
  sub?: string;
}

interface Props {
  title?: string;
  caption?: string;
  tiles: Tile[];
  /** Grid columns at >= sm. Mobile is always 2-up. */
  cols?: 2 | 3 | 4;
}

/**
 * Bento stat group. Uses 1px dividers + negative space rather than nested
 * cards (taste-skill anti-card rule). Tiles reveal in a staggered waterfall.
 */
function StatTilesBase({ title, caption, tiles, cols = 4 }: Props) {
  const gridCols =
    cols === 2 ? "sm:grid-cols-2" : cols === 3 ? "sm:grid-cols-3" : "sm:grid-cols-4";
  return (
    <div>
      {title && (
        <div className="mb-3 flex items-baseline justify-between">
          <h4 className="text-[15px] font-semibold tracking-tight text-fg">{title}</h4>
          {caption && (
            <span className="font-mono text-[10.5px] text-fg-faint">{caption}</span>
          )}
        </div>
      )}
      <motion.div
        className={`grid grid-cols-2 ${gridCols} overflow-hidden rounded-[14px] border border-line-soft bg-surface-2`}
        variants={stagger}
        initial="hidden"
        animate="show"
      >
        {tiles.map((t, i) => (
          <motion.div
            key={t.label + i}
            variants={riseItem}
            className="border-line-soft p-3.5 [&:not(:nth-child(2n))]:border-r sm:border-r sm:[&:nth-child(4n)]:border-r-0 [&:nth-child(n+3)]:border-t sm:[&:nth-child(n+3)]:border-t-0"
          >
            <div className="font-mono text-[10px] uppercase tracking-[0.08em] text-fg-faint">
              {t.label}
            </div>
            <div
              className={`mt-1.5 font-mono text-[17px] font-medium tabular-nums ${
                t.accent ? "text-accent" : "text-fg"
              }`}
            >
              {t.value}
            </div>
            {t.sub && (
              <div className="mt-0.5 text-[10.5px] text-fg-dim">{t.sub}</div>
            )}
          </motion.div>
        ))}
      </motion.div>
    </div>
  );
}

export const StatTiles = memo(StatTilesBase);
