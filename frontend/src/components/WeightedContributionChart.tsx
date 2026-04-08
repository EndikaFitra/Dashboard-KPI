import { Card } from "@/components/ui/card";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from "recharts";
import type { KPIIndicator } from "@/data/kpiData";

const COLORS = [
  "hsl(220 70% 45%)",
  "hsl(152 60% 42%)",
  "hsl(38 92% 50%)",
  "hsl(0 72% 51%)",
  "hsl(280 60% 55%)",
];

interface Props {
  kpis: KPIIndicator[];
}

export function WeightedContributionChart({ kpis }: Props) {
  const data = kpis.map((k) => ({
    name: k.name.length > 30 ? k.name.slice(0, 30) + "…" : k.name,
    value: k.weight,
  }));

  return (
    <Card className="p-5 shadow-sm border-0 shadow-foreground/5">
      <h3 className="text-sm font-semibold mb-4">Weighted KPI Contribution</h3>
      <ResponsiveContainer width="100%" height={280}>
        <PieChart>
          <Pie data={data} dataKey="value" nameKey="name" cx="50%" cy="50%" innerRadius={60} outerRadius={100} paddingAngle={2}>
            {data.map((_, i) => (
              <Cell key={i} fill={COLORS[i % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip contentStyle={{ borderRadius: "8px", border: "none", boxShadow: "0 4px 12px rgba(0,0,0,0.1)" }} />
          <Legend iconType="circle" wrapperStyle={{ fontSize: 11 }} />
        </PieChart>
      </ResponsiveContainer>
    </Card>
  );
}
