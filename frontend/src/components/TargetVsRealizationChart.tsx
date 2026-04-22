import { Card } from "@/components/ui/card";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";
import type { KPIIndicator } from "@/data/kpiData";

interface Props {
  kpis: KPIIndicator[];
}

export function TargetVsRealizationChart({ kpis }: Props) {
  const data = kpis.map((k) => ({
    name: k.name.length > 25 ? k.name.slice(0, 25) + "…" : k.name,
    Target: k.target,
    Realization: k.realization,
  }));

  return (
    <Card className="p-5 shadow-sm border-0 shadow-foreground/5">
      <h3 className="text-sm font-semibold mb-4">Target vs Realization</h3>
      <ResponsiveContainer width="100%" height={280}>
        <BarChart data={data} barGap={4}>
          <CartesianGrid strokeDasharray="3 3" stroke="hsl(220 13% 91%)" />
          <XAxis dataKey="name" tick={{ fontSize: 11 }} interval={0} angle={-15} textAnchor="end" height={60} />
          <YAxis tick={{ fontSize: 11 }} />
          <Tooltip
            contentStyle={{ borderRadius: "8px", border: "none", boxShadow: "0 4px 12px rgba(0,0,0,0.1)" }}
            formatter={(value: number) => [Number(value).toFixed(2), ""]}
          />
          <Legend />
          <Bar dataKey="Target" fill="hsl(220 70% 45%)" radius={[4, 4, 0, 0]} />
          <Bar dataKey="Realization" fill="hsl(152 60% 42%)" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </Card>
  );
}
