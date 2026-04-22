import { useState } from "react";
import { useParams } from "react-router-dom";
import { KPIScoreCard } from "@/components/KPIScoreCard";
import { TargetVsRealizationChart } from "@/components/TargetVsRealizationChart";
import { PerformanceTrendChart } from "@/components/PerformanceTrendChart";
import { WeightedContributionChart } from "@/components/WeightedContributionChart";
import { KPIListTable } from "@/components/KPIListTable";
import { KPIDetailCard } from "@/components/KPIDetailCard";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { AlertCircle } from "lucide-react";
import { useDivision, useTrend, useAvailableYears } from "@/hooks/useKpiData";
import type { KPIIndicator } from "@/data/kpiData";
import type { KpiItem } from "@/api/client";

// Map API KpiItem → legacy KPIIndicator shape expected by existing components
function toKpiIndicator(item: KpiItem): KPIIndicator {
  return {
    id: `kpi-${item.kpi_id}-${item.quarter}`,
    name: item.kpi_name,
    target: item.target,
    targetUnit: item.unit,
    realization: item.realization,
    weight: item.weight,
    score: item.achievement,
  };
}

// Deduplicate by kpi_id — use the latest quarter's values
function deduplicateKpis(kpis: KpiItem[]): KpiItem[] {
  const map = new Map<number, KpiItem>();
  for (const k of kpis) {
    const existing = map.get(k.kpi_id);
    if (!existing || k.quarter > existing.quarter) {
      map.set(k.kpi_id, k);
    }
  }
  return Array.from(map.values());
}

const EVAL_LABEL: Record<string, string> = { H: "Half Year", Q: "Quarter", M: "Monthly" };

// KPI IDs that should use the detail card view (non-% units)
const CARD_UNITS = new Set(["unit", "IDR", "customer", "quotation"]);

export default function DivisionDashboard() {
  const { divisionId } = useParams<{ divisionId: string }>();
  const [year, setYear] = useState(new Date().getFullYear());
  const { data: years = [new Date().getFullYear()] } = useAvailableYears();

  // Division ID is stored as number 1-4; map slug → id
  const SLUG_TO_ID: Record<string, number> = {
    "network": 1,
    "software-engineer": 2,
    "sales-executive": 3,
    "hr-officer": 4,
  };
  const divId = SLUG_TO_ID[divisionId ?? ""] ?? 1;

  const { data: division, isLoading: divLoading, error: divError } = useDivision(divId, year);
  const { data: trend, isLoading: trendLoading } = useTrend(divId, year);

  if (divLoading || trendLoading) {
    return (
      <div className="space-y-6 max-w-7xl">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-28 rounded-xl" />
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <Skeleton className="h-72 rounded-xl" />
          <Skeleton className="h-72 rounded-xl" />
        </div>
      </div>
    );
  }

  if (divError || !division) {
    return (
      <div className="flex items-center gap-3 text-destructive p-6">
        <AlertCircle className="w-5 h-5" />
        <span>Division not found or backend unavailable.</span>
      </div>
    );
  }

  // Deduplicate and convert
  const uniqueKpis = deduplicateKpis(division.kpis);
  const legacyKpis: KPIIndicator[] = uniqueKpis.map(toKpiIndicator);

  // Split: detail cards (non-% units) vs bar chart kpis
  const cardKpis = legacyKpis.filter((k) => CARD_UNITS.has(k.targetUnit));
  const barKpis = legacyKpis.filter((k) => !CARD_UNITS.has(k.targetUnit));

  // Trend data
  const currentTrend = (trend?.current_trend ?? []).map((t) => ({ period: t.period, score: t.achievement }));
  const prevTrend = (trend?.previous_trend ?? []).map((t) => ({ period: t.period, score: t.achievement }));
  const evalLabel = EVAL_LABEL[division.evaluation_period] ?? division.evaluation_period;
  const trendChartType = divId === 1 ? "bar" : "line"; // Network → bar chart

  // Overall score = avg achievement
  const score = division.avg_achievement;
  const totalKPI = uniqueKpis.length;

  return (
    <div className="space-y-6 max-w-7xl">
      {/* Header — wraps to two lines on small screens */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h1 className="text-xl md:text-2xl font-bold tracking-tight">{division.division_name} Division</h1>
          <div className="flex items-center gap-2 mt-1 flex-wrap">
            <Badge variant="secondary" className="text-xs">{evalLabel}</Badge>
            <span className="text-sm text-muted-foreground">Performance Dashboard</span>
          </div>
        </div>
        <Select value={String(year)} onValueChange={(v) => setYear(Number(v))}>
          <SelectTrigger className="w-28 bg-card shrink-0">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {years.map((y) => (
              <SelectItem key={y} value={String(y)}>{y}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <KPIScoreCard score={score} totalKPI={totalKPI} />

      {cardKpis.length > 0 ? (
        <>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {cardKpis.map((kpi) => (
              <KPIDetailCard key={kpi.id} kpi={kpi} />
            ))}
            {barKpis.length > 0 && <TargetVsRealizationChart kpis={barKpis} />}
          </div>
          <PerformanceTrendChart data={currentTrend} prevYearData={prevTrend} periodLabel={evalLabel} chartType={trendChartType} />
        </>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <TargetVsRealizationChart kpis={legacyKpis} />
          <PerformanceTrendChart data={currentTrend} prevYearData={prevTrend} periodLabel={evalLabel} chartType={trendChartType} />
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <WeightedContributionChart kpis={legacyKpis} />
        <KPIListTable kpis={legacyKpis} />
      </div>
    </div>
  );
}
