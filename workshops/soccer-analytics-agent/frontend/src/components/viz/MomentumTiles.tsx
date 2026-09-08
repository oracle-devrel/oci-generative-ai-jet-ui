import { memo } from "react";
import { StatTiles, type Tile } from "./StatTiles";
import { pctRound } from "../../lib/format";
import type { MomentumResult } from "../../lib/types";

/** Psychological / momentum signals over the last n matches. */
function MomentumTilesBase({ data }: { data: MomentumResult }) {
  const tiles: Tile[] = [
    {
      label: "win streak",
      value: String(data.current_streak),
      accent: data.current_streak >= 2,
      sub: "consecutive",
    },
    {
      label: "unbeaten",
      value: String(data.unbeaten_streak),
      accent: data.unbeaten_streak >= 3,
      sub: "non-losses",
    },
    {
      label: "clean sheets",
      value: pctRound(data.clean_sheet_pct),
      accent: data.clean_sheet_pct >= 0.4,
    },
    { label: "comeback rate", value: pctRound(data.comeback_rate) },
    { label: "draw tendency", value: pctRound(data.draw_tendency) },
    {
      label: "blowout wins",
      value: pctRound(data.blowout_win_pct),
      accent: data.blowout_win_pct >= 0.3,
    },
    { label: "blowout losses", value: pctRound(data.blowout_loss_pct) },
    { label: "shutout losses", value: pctRound(data.shutout_loss_pct) },
  ];
  return (
    <StatTiles
      title={`${data.team} — momentum`}
      caption={`last ${data.n}`}
      tiles={tiles}
      cols={4}
    />
  );
}

export const MomentumTiles = memo(MomentumTilesBase);
