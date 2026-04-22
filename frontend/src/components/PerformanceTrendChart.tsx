import { Card } from "@/components/ui/card";
import {
  LineChart, Line,
  BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell,
} from "recharts";

interface Props {
  data: { period: string; score: number }[];
  prevYearData: { period: string; score: number }[];
  periodLabel: string;
  chartType?: "line" | "bar";
}

export function PerformanceTrendChart({ data, prevYearData, periodLabel, chartType = "line" }: Props) {
  // Merge current and previous year data by index for comparison
  const mergedData = data.map((item, i) => ({
    period: item.period,
    "Current Year": item.score,
    "Previous Year": prevYearData[i]?.score ?? null,
  }));

  const tooltipStyle = {
    borderRadius: "8px",
    border: "none",
    boxShadow: "0 4px 12px rgba(0,0,0,0.1)",
  };

  return (
    <Card className="p-5 shadow-sm border-0 shadow-foreground/5">
      <h3 className="text-sm font-semibold mb-1">Performance Trend</h3>
      <p className="text-xs text-muted-foreground mb-4">Evaluation: {periodLabel}</p>

      <ResponsiveContainer width="100%" height={280}>
        {chartType === "bar" ? (
          <BarChart data={mergedData} barCategoryGap="30%" barGap={4}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(220 13% 91%)" />
            <XAxis dataKey="period" tick={{ fontSize: 11 }} />
            <YAxis domain={[0, 120]} tick={{ fontSize: 11 }} />
            <Tooltip
            contentStyle={tooltipStyle}
            formatter={(value: number) => [Number(value).toFixed(2) + "%", ""]}
          />
            <Legend />
            <Bar dataKey="Current Year" radius={[4, 4, 0, 0]} fill="hsl(220 70% 45%)" />
            <Bar dataKey="Previous Year" radius={[4, 4, 0, 0]} fill="hsl(220 13% 69%)" />
          </BarChart>
        ) : (
          <LineChart data={mergedData}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(220 13% 91%)" />
            <XAxis dataKey="period" tick={{ fontSize: 11 }} />
            <YAxis domain={[60, 100]} tick={{ fontSize: 11 }} />
            <Tooltip
            contentStyle={tooltipStyle}
            formatter={(value: number) => [Number(value).toFixed(2) + "%", ""]}
          />
            <Legend />
            <Line type="monotone" dataKey="Current Year" stroke="hsl(220 70% 45%)" strokeWidth={2.5} dot={{ r: 5, fill: "hsl(220 70% 45%)" }} />
            <Line type="monotone" dataKey="Previous Year" stroke="hsl(220 13% 69%)" strokeWidth={2} strokeDasharray="5 5" dot={{ r: 4, fill: "hsl(220 13% 69%)" }} />
          </LineChart>
        )}
      </ResponsiveContainer>
    </Card>
  );
}
