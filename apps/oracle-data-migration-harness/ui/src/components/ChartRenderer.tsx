import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { ChartPayload } from "../types";

export function ChartRenderer({ chart }: { chart: ChartPayload }) {
  return (
    <div className="mt-3 h-48 bg-oracle-cream rounded">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chart.data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1A1A1A20" />
          <XAxis dataKey={chart.x} stroke="#1A1A1A" fontSize={11} />
          <YAxis stroke="#1A1A1A" fontSize={11} />
          <Tooltip />
          <Bar dataKey={chart.y} fill="#C74634" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
