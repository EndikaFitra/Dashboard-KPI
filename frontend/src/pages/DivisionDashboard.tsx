import { useState } from "react";
import { useParams } from "react-router-dom";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { AlertCircle, TrendingUp, TrendingDown, Minus, Target, CheckCircle2 } from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, LineChart, Line, Legend,
} from "recharts";
import { useDivision, useTrend, useAvailableYears } from "@/hooks/useKpiData";
import type { KpiItem, PeriodDetail } from "@/api/client";

const EVAL_LABEL: Record<string, string> = { H: "Half Year", Q: "Quarterly", M: "Monthly" };
const PERIOD_COLOR = ["hsl(220 70% 50%)", "hsl(152 60% 42%)", "hsl(38 92% 50%)", "hsl(0 72% 51%)",
  "hsl(280 60% 55%)", "hsl(190 70% 45%)", "hsl(45 80% 50%)", "hsl(340 65% 50%)",
  "hsl(100 55% 40%)", "hsl(200 65% 48%)", "hsl(15 70% 52%)", "hsl(250 60% 55%)"];

const STATUS_COLOR: Record<string, string> = {
  green:  "text-emerald-600 bg-emerald-50 border-emerald-200",
  yellow: "text-amber-600 bg-amber-50 border-amber-200",
  red:    "text-red-600 bg-red-50 border-red-200",
};
const STATUS_ICON = {
  green:  <TrendingUp className="w-4 h-4 text-emerald-500" />,
  yellow: <Minus className="w-4 h-4 text-amber-500" />,
  red:    <TrendingDown className="w-4 h-4 text-red-500" />,
};

const SLUG_TO_ID: Record<string, number> = {
  "network": 1, "software-engineer": 2, "sales-executive": 3, "hr-officer": 4,
};

// ── Sub-component: KPI Detail Card ───────────────────────────────────────── //
function KpiCard({ kpi }: { kpi: KpiItem }) {
  const status = kpi.status ?? "red";
  const evalLabel = kpi.evaluation_label ?? EVAL_LABEL[kpi.evaluation_period] ?? kpi.evaluation_period;

  // Build chart data dari periods
  const chartData = (kpi.periods ?? []).map((p: PeriodDetail) => ({
    name: p.period_name,
    Achievement: p.achievement,
    Target: 100,
  }));

  return (
    <Card className="p-4 shadow-sm border-0 shadow-foreground/5 space-y-3">
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <h3 className="font-semibold text-sm text-slate-800 leading-snug">{kpi.kpi_name}</h3>
          <div className="flex items-center gap-1.5 mt-1 flex-wrap">
            <Badge variant="secondary" className="text-[10px] py-0">{evalLabel}</Badge>
            <span className="text-[10px] text-muted-foreground">Bobot: {kpi.weight}%</span>
          </div>
        </div>
        <div className={`flex items-center gap-1 px-2.5 py-1 rounded-full border text-xs font-bold shrink-0 ${STATUS_COLOR[status]}`}>
          {STATUS_ICON[status as keyof typeof STATUS_ICON]}
          {kpi.annual_report.toFixed(1)}%
        </div>
      </div>

      {/* Kontribusi ke Division Report */}
      <div className="text-[11px] text-slate-500">
        Kontribusi Division Report:{" "}
        <span className="font-semibold text-slate-700">
          {((kpi.annual_report * kpi.weight) / 100).toFixed(2)}%
        </span>
        {" "}({kpi.annual_report.toFixed(1)} × {kpi.weight}% ÷ 100)
      </div>

      {/* Bar chart per periode */}
      {chartData.length > 0 && (
        <ResponsiveContainer width="100%" height={130}>
          <BarChart data={chartData} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(220 13% 91%)" />
            <XAxis dataKey="name" tick={{ fontSize: 10 }} />
            <YAxis domain={[0, 130]} tick={{ fontSize: 9 }} />
            <Tooltip
              contentStyle={{ borderRadius: "8px", border: "none", boxShadow: "0 4px 12px rgba(0,0,0,0.1)", fontSize: 11 }}
              formatter={(v: number) => [v.toFixed(1) + "%", ""]}
            />
            <Bar dataKey="Achievement" fill="hsl(220 70% 50%)" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      )}

      {/* Periode detail table */}
      {(kpi.periods ?? []).length > 0 && (
        <table className="w-full text-[11px]">
          <thead>
            <tr className="text-slate-400 border-b border-slate-100">
              <th className="text-left py-1">Periode</th>
              <th className="text-right py-1">Target</th>
              <th className="text-right py-1">Realisasi</th>
              <th className="text-right py-1">Achievement</th>
            </tr>
          </thead>
          <tbody>
            {(kpi.periods ?? []).map((p: PeriodDetail) => (
              <tr key={p.period_id} className="border-b border-slate-50">
                <td className="py-1 text-slate-600">{p.period_name}</td>
                <td className="py-1 text-right text-slate-500">{p.target.toLocaleString("id-ID")}</td>
                <td className="py-1 text-right text-slate-500">{p.realization.toLocaleString("id-ID")}</td>
                <td className={`py-1 text-right font-semibold ${
                  p.achievement >= 100 ? "text-emerald-600" :
                  p.achievement >= 80  ? "text-amber-600" : "text-red-500"
                }`}>{p.achievement.toFixed(1)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Card>
  );
}

// ── Main Component ───────────────────────────────────────────────────────── //
export default function DivisionDashboard() {
  const { divisionId } = useParams<{ divisionId: string }>();
  const [year, setYear] = useState(new Date().getFullYear());
  const { data: years = [new Date().getFullYear()] } = useAvailableYears();

  const divId = SLUG_TO_ID[divisionId ?? ""] ?? 1;

  const { data: division, isLoading: divLoading, error: divError } = useDivision(divId, year);
  const { data: trend, isLoading: trendLoading } = useTrend(divId, year);

  if (divLoading || trendLoading) {
    return (
      <div className="space-y-6 max-w-7xl">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-24 rounded-xl" />
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

  const kpis = division.kpis ?? [];
  const divisionReport = division.division_report ?? division.avg_achievement ?? 0;
  const divStatus = divisionReport >= 100 ? "green" : divisionReport >= 80 ? "yellow" : "red";

  // Bar chart: Annual Report per KPI
  const kpiBarData = kpis.map((k) => ({
    name: k.kpi_name.split(" ").slice(0, 3).join(" "),
    "Annual Report": k.annual_report,
    Bobot: k.weight,
  }));

  // Trend chart data
  const currentTrend = (trend?.current_trend ?? []).map((t) => ({ period: t.period, score: t.achievement }));
  const prevTrend    = (trend?.previous_trend ?? []).map((t) => ({ period: t.period, score: t.achievement }));

  return (
    <div className="space-y-6 max-w-7xl">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h1 className="text-xl md:text-2xl font-bold tracking-tight">{division.division_name} Division</h1>
          <p className="text-sm text-muted-foreground mt-1">Performance Dashboard · {year}</p>
        </div>
        <Select value={String(year)} onValueChange={(v) => setYear(Number(v))}>
          <SelectTrigger className="w-28 bg-card shrink-0">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {years.map((y) => <SelectItem key={y} value={String(y)}>{y}</SelectItem>)}
          </SelectContent>
        </Select>
      </div>

      {/* Division Report Summary */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Card className={`p-4 col-span-2 flex items-center gap-4 border shadow-sm ${STATUS_COLOR[divStatus]}`}>
          <div className="w-12 h-12 rounded-xl bg-white/60 flex items-center justify-center shrink-0">
            <Target className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs font-medium opacity-70">Division Report</p>
            <p className="text-3xl font-extrabold tracking-tight">{divisionReport.toFixed(2)}%</p>
            <p className="text-xs opacity-60 mt-0.5">Σ (Annual × Bobot) / 100</p>
          </div>
        </Card>

        <Card className="p-4 flex items-center gap-3 shadow-sm border-0 shadow-foreground/5">
          <div className="w-10 h-10 rounded-lg bg-accent flex items-center justify-center shrink-0">
            <CheckCircle2 className="w-5 h-5 text-primary" />
          </div>
          <div>
            <p className="text-[11px] text-muted-foreground font-medium">On Target</p>
            <p className="text-xl font-bold">{division.on_target ?? 0}/{kpis.length}</p>
          </div>
        </Card>

        <Card className="p-4 flex items-center gap-3 shadow-sm border-0 shadow-foreground/5">
          <div className="w-10 h-10 rounded-lg bg-accent flex items-center justify-center shrink-0">
            <TrendingUp className="w-5 h-5 text-primary" />
          </div>
          <div>
            <p className="text-[11px] text-muted-foreground font-medium">Total KPI</p>
            <p className="text-xl font-bold">{kpis.length}</p>
          </div>
        </Card>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Annual Report per KPI */}
        <Card className="p-4 md:p-5 shadow-sm border-0 shadow-foreground/5">
          <h3 className="text-sm font-semibold mb-4">Annual Report per KPI</h3>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={kpiBarData} layout="vertical" margin={{ left: 12, right: 16 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(220 13% 91%)" horizontal={false} />
              <XAxis type="number" domain={[0, 130]} tick={{ fontSize: 10 }} unit="%" />
              <YAxis type="category" dataKey="name" tick={{ fontSize: 10 }} width={100} />
              <Tooltip
                contentStyle={{ borderRadius: "8px", border: "none", boxShadow: "0 4px 12px rgba(0,0,0,0.1)", fontSize: 11 }}
                formatter={(v: number) => [v.toFixed(2) + "%", "Annual Report"]}
              />
              <Bar dataKey="Annual Report" radius={[0, 4, 4, 0]}>
                {kpiBarData.map((_, i) => (
                  <rect key={i} fill={PERIOD_COLOR[i % PERIOD_COLOR.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Card>

        {/* Trend chart */}
        <Card className="p-4 md:p-5 shadow-sm border-0 shadow-foreground/5">
          <h3 className="text-sm font-semibold mb-4">Division Report Trend</h3>
          {currentTrend.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <LineChart margin={{ top: 4, right: 16, bottom: 0, left: -20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(220 13% 91%)" />
                <XAxis dataKey="period" tick={{ fontSize: 10 }} allowDuplicatedCategory={false} />
                <YAxis domain={[0, 130]} tick={{ fontSize: 10 }} unit="%" />
                <Tooltip
                  contentStyle={{ borderRadius: "8px", border: "none", boxShadow: "0 4px 12px rgba(0,0,0,0.1)", fontSize: 11 }}
                  formatter={(v: number) => [v.toFixed(2) + "%", ""]}
                />
                <Legend iconType="circle" />
                {currentTrend.length > 0 && (
                  <Line
                    data={currentTrend.map((t) => ({ period: t.period, score: t.score }))}
                    dataKey="score" name={String(year)} stroke="hsl(220 70% 50%)"
                    strokeWidth={2} dot={{ r: 4 }}
                  />
                )}
                {prevTrend.length > 0 && (
                  <Line
                    data={prevTrend.map((t) => ({ period: t.period, score: t.score }))}
                    dataKey="score" name={String(year - 1)} stroke="hsl(220 13% 70%)"
                    strokeWidth={1.5} strokeDasharray="4 3" dot={{ r: 3 }}
                  />
                )}
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[220px] flex items-center justify-center text-slate-400 text-sm">
              Tidak ada data trend untuk tahun ini.
            </div>
          )}
        </Card>
      </div>

      {/* Per-KPI Cards */}
      <div>
        <h2 className="text-sm font-semibold mb-3 text-slate-700">Detail per KPI</h2>
        <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
          {kpis.map((kpi) => (
            <KpiCard key={kpi.kpi_id} kpi={kpi} />
          ))}
        </div>
      </div>

      {/* Division Report Formula Card */}
      <Card className="p-4 md:p-5 shadow-sm border-0 shadow-foreground/5">
        <h3 className="text-sm font-semibold mb-3">Perhitungan Division Report</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 text-xs text-slate-400 uppercase">
                <th className="text-left py-2">KPI</th>
                <th className="text-center py-2">Periode</th>
                <th className="text-right py-2">Annual Report</th>
                <th className="text-right py-2">Bobot</th>
                <th className="text-right py-2">Kontribusi</th>
              </tr>
            </thead>
            <tbody>
              {kpis.map((k) => (
                <tr key={k.kpi_id} className="border-b border-slate-50 hover:bg-slate-50">
                  <td className="py-2 font-medium text-slate-800">{k.kpi_name}</td>
                  <td className="py-2 text-center">
                    <span className="px-1.5 py-0.5 bg-blue-50 text-blue-700 rounded text-[10px] font-medium">
                      {EVAL_LABEL[k.evaluation_period] ?? k.evaluation_period}
                    </span>
                  </td>
                  <td className={`py-2 text-right font-semibold ${
                    k.annual_report >= 100 ? "text-emerald-600" :
                    k.annual_report >= 80  ? "text-amber-600" : "text-red-500"
                  }`}>{k.annual_report.toFixed(2)}%</td>
                  <td className="py-2 text-right text-slate-500">{k.weight}%</td>
                  <td className="py-2 text-right font-semibold text-slate-700">
                    {((k.annual_report * k.weight) / 100).toFixed(2)}%
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr className={`border-t-2 border-slate-200 font-bold ${STATUS_COLOR[divStatus]}`}>
                <td className="py-2" colSpan={4}>Division Report = Σ Kontribusi</td>
                <td className="py-2 text-right text-base">{divisionReport.toFixed(2)}%</td>
              </tr>
            </tfoot>
          </table>
        </div>
      </Card>
    </div>
  );
}
