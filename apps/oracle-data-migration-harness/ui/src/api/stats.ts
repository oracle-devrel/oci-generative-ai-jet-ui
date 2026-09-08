import type { Side } from "../types";

export type Stats =
  | { migrated: false }
  | {
      products: number;
      reviews: number;
      categories: number;
      duality_views?: number;
      vector_dim?: number;
      vectors?: number;
      memory_messages?: number;
    };

export async function fetchStats(side: Side): Promise<Stats> {
  const r = await fetch(`/stats/${side}`);
  return r.json();
}
