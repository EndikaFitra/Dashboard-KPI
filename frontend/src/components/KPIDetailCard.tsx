import { Card } from "@/components/ui/card";
import { TrendingUp, Target } from "lucide-react";
import type { KPIIndicator } from "@/data/kpiData";
import { formatTarget, getStatusColor } from "@/data/kpiData";

interface Props {
  kpi: KPIIndicator;
  title?: string;
}

export function KPIDetailCard({ kpi, title }: Props) {
  const status = getStatusColor(kpi.score);
  const pct = ((kpi.realization / kpi.target) * 100).toFixed(1);

  const statusStyles = {
    achieved: "bg-achieved/10 text-achieved border-achieved/20",
    warning: "bg-warning/10 text-warning border-warning/20",
    danger: "bg-danger/10 text-danger border-danger/20",
  };

  const statusLabel = {
    achieved: "On Track",
    warning: "Warning",
    danger: "Below Target",
  };

  return (
    <Card className="p-5 shadow-sm border-0 shadow-foreground/5">
      <h3 className="text-sm font-semibold mb-4">{title || `Target vs Realization — ${kpi.name}`}</h3>
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <span className="text-xs text-muted-foreground font-medium">{kpi.name}</span>
          <span className={`text-xs font-semibold px-2 py-0.5 rounded-full border ${statusStyles[status]}`}>
            {statusLabel[status]}
          </span>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="bg-muted/50 rounded-lg p-4 text-center">
            <Target className="w-4 h-4 mx-auto mb-1 text-muted-foreground" />
            <p className="text-[10px] text-muted-foreground uppercase tracking-wide mb-1">Target</p>
            <p className="text-lg font-bold">{formatTarget(kpi.target, kpi.targetUnit)}</p>
          </div>
          <div className="bg-muted/50 rounded-lg p-4 text-center">
            <TrendingUp className="w-4 h-4 mx-auto mb-1 text-muted-foreground" />
            <p className="text-[10px] text-muted-foreground uppercase tracking-wide mb-1">Realization</p>
            <p className="text-lg font-bold">{formatTarget(kpi.realization, kpi.targetUnit)}</p>
          </div>
        </div>

        <div className="space-y-1.5">
          <div className="flex justify-between text-xs">
            <span className="text-muted-foreground">Achievement</span>
            <span className="font-semibold">{pct}%</span>
          </div>
          <div className="h-2 bg-muted rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all ${
                status === "achieved" ? "bg-achieved" : status === "warning" ? "bg-warning" : "bg-danger"
              }`}
              style={{ width: `${Math.min(Number(pct), 100)}%` }}
            />
          </div>
        </div>

        <div className="flex justify-between text-xs text-muted-foreground pt-1 border-t border-border">
          <span>Weight: {kpi.weight}%</span>
          <span>Score: {kpi.score}</span>
        </div>
      </div>
    </Card>
  );
}
