import { memo } from "react";
import { StatTiles, type Tile } from "./StatTiles";
import { num2, pctRound, signed } from "../../lib/format";
import type { FormResult } from "../../lib/types";

/** Rolling form + goal averages over the last n matches. */
function FormTilesBase({ data }: { data: FormResult }) {
  const tiles: Tile[] = [
    { label: "form", value: pctRound(data.form), accent: data.form >= 0.6, sub: "pts / max" },
    { label: "weighted", value: pctRound(data.weighted_form), sub: "decay-weighted" },
    { label: "goals for", value: num2(data.avg_goals_scored), sub: "per match" },
    { label: "goals against", value: num2(data.avg_goals_conceded), sub: "per match" },
    {
      label: "goal diff",
      value: signed(data.goal_diff_avg, 2),
      accent: data.goal_diff_avg > 0,
      sub: "per match",
    },
    { label: "matches", value: String(data.total_matches), sub: "tracked" },
  ];
  return (
    <StatTiles
      title={`${data.team} — recent form`}
      caption={`last ${data.n}`}
      tiles={tiles}
      cols={3}
    />
  );
}

export const FormTiles = memo(FormTilesBase);
