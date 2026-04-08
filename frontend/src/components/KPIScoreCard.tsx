import { Card } from "@/components/ui/card";
import { TrendingUp, Target } from "lucide-react";

interface KPIScoreCardProps {
  score: number;
  totalKPI: number;
}

export function KPIScoreCard({ score, totalKPI }: KPIScoreCardProps) {
  const cards = [
    {
      label: "KPI Score",
      value: score.toFixed(1),
      icon: TrendingUp,
      accent: "text-primary bg-accent",
    },
    {
      label: "Total KPI",
      value: totalKPI,
      icon: Target,
      accent: "text-primary bg-accent",
    },
  ];

  return (
    <div className="grid grid-cols-2 gap-4">
      {cards.map((c) => (
        <Card key={c.label} className="p-4 flex items-center gap-3 shadow-sm border-0 shadow-foreground/5">
          <div className={`w-10 h-10 rounded-lg flex items-center justify-center shrink-0 ${c.accent}`}>
            <c.icon className="w-5 h-5" />
          </div>
          <div>
            <p className="text-xs text-muted-foreground font-medium">{c.label}</p>
            <p className="text-xl font-bold tracking-tight">{c.value}</p>
          </div>
        </Card>
      ))}
    </div>
  );
}
