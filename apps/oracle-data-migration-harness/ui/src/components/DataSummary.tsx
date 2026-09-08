import { useEffect, useState } from "react";
import { fetchStats, type Stats } from "../api/stats";
import type { Side } from "../types";

export function DataSummary({
  side,
  locked,
  refreshKey,
}: {
  side: Side;
  locked?: boolean;
  refreshKey?: number | string;
}) {
  const [stats, setStats] = useState<Stats | null>(null);

  useEffect(() => {
    if (locked) {
      setStats(null);
      return;
    }
    fetchStats(side)
      .then(setStats)
      .catch(() => setStats(null));
  }, [side, locked, refreshKey]);

  if (locked) return <Badge text="Not migrated yet" muted />;
  if (!stats) return <Badge text="Loading..." muted />;
  if (!("products" in stats)) return <Badge text="Not migrated yet" muted />;

  const text =
    side === "mongo"
      ? `MongoDB · ${stats.products} products · ${stats.reviews.toLocaleString()} reviews · ${stats.vectors ?? 0} vectors · ${stats.memory_messages ?? 0} memory messages`
      : `Oracle 26ai · ${stats.products} products · ${stats.reviews.toLocaleString()} reviews · ${stats.duality_views ?? 1} duality view · ${stats.vectors ?? 0} vectors · ${stats.memory_messages ?? 0} memory messages`;

  return <Badge text={text} />;
}

function Badge({ text, muted }: { text: string; muted?: boolean }) {
  return (
    <div
      className={`text-xs px-3 py-1.5 rounded-full inline-block mb-3 ${
        muted
          ? "bg-oracle-ink/5 text-oracle-ink/50"
          : "bg-oracle-cream border border-oracle-ink/10 text-oracle-ink/80"
      }`}
    >
      {text}
    </div>
  );
}
