import { memo } from "react";
import { StatusDot } from "./StatusDot";
import type { HealthStatus } from "../lib/types";

const MAP: Record<HealthStatus, { label: string; color: string }> = {
  connecting: { label: "connecting", color: "var(--color-fg-faint)" },
  live: { label: "live", color: "var(--color-accent)" },
  "db-only": { label: "db only", color: "var(--color-amber)" },
  offline: { label: "offline", color: "var(--color-rose)" },
};

/** Live status pill driven by /health. */
function HealthPillBase({ status }: { status: HealthStatus }) {
  const { label, color } = MAP[status];
  return (
    <span className="inline-flex items-center gap-2 rounded-full border border-line bg-surface/60 px-3 py-1.5 backdrop-blur-sm">
      <StatusDot color={color} />
      <span className="font-mono text-[11.5px] text-fg-dim">{label}</span>
    </span>
  );
}

export const HealthPill = memo(HealthPillBase);
