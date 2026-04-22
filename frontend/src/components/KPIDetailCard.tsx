import { Card } from "@/components/ui/card";
import { TrendingUp, Target } from "lucide-react";
import type { KPIIndicator } from "@/data/kpiData";
import { formatTarget } from "@/data/kpiData";

interface Props {
  kpi: KPIIndicator;
  title?: string;
}

export function KPIDetailCard({ kpi, title }: Props) {
  const pct = ((kpi.realization / kpi.target) * 100).toFixed(2);

  return (
    <Card className="p-5 shadow-sm border-0 shadow-foreground/5">
      <h3 className="text-sm font-semibold mb-4">{title || `Target vs Realization — ${kpi.name}`}</h3>
      <div className="space-y-4">
        <p className="text-xs text-muted-foreground font-medium">{kpi.name}</p>

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
            <span className={`font-semibold ${Number(pct) >= 100 ? "text-emerald-600" : "text-blue-600"}`}>
              {pct}%
            </span>
          </div>
          <div className="h-2 bg-muted rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all ${
                Number(pct) >= 100 ? "bg-emerald-500" : "bg-blue-500"
              }`}
              style={{ width: `${Math.min(Number(pct), 100)}%` }}
            />
          </div>
        </div>
      </div>
    </Card>
  );
}
