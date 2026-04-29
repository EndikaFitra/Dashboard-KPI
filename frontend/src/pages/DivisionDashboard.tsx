import { useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { AlertCircle, TrendingUp, TrendingDown, Minus, Target, ArrowUpRight, ArrowDownRight } from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, LineChart, Line, Legend,
  RadialBarChart, RadialBar, Cell,
} from "recharts";
import { useDivision, useAvailableYears } from "@/hooks/useKpiData";
import type { KpiItem, PeriodDetail } from "@/api/client";

// ── Constants ─────────────────────────────────────────────────────────────── //
const SLUG_TO_ID: Record<string, number> = {
  network: 1, "software-engineer": 2, "sales-executive": 3, "hr-officer": 4,
};
const EVAL_LABEL: Record<string, string> = { H: "Half Year", Q: "Quarterly", M: "Monthly" };
const STATUS_COLOR: Record<string, string> = {
  green: "text-emerald-600 bg-emerald-50 border-emerald-200",
  yellow: "text-amber-600 bg-amber-50 border-amber-200",
  red: "text-red-600 bg-red-50 border-red-200",
};
const STATUS_ICON = {
  green: <TrendingUp className="w-3.5 h-3.5" />,
  yellow: <Minus className="w-3.5 h-3.5" />,
  red: <TrendingDown className="w-3.5 h-3.5" />,
};
const CHART_COLORS = [
  "hsl(220,70%,50%)", "hsl(152,60%,42%)", "hsl(38,92%,50%)", "hsl(0,72%,51%)",
  "hsl(280,60%,55%)", "hsl(190,70%,45%)", "hsl(15,70%,52%)", "hsl(250,60%,55%)",
  "hsl(100,55%,40%)", "hsl(45,80%,50%)", "hsl(340,65%,50%)", "hsl(200,65%,48%)",
];

// ── Gauge for weight ───────────────────────────────────────────────────────── //
function WeightGauge({ weight, color }: { weight: number; color: string }) {
  const data = [{ value: weight }, { value: 100 - weight }];
  return (
    <div className="flex flex-col items-center gap-1">
      <RadialBarChart width={80} height={50} cx={40} cy={46} innerRadius={28} outerRadius={42}
        startAngle={180} endAngle={0} data={data}>
        <RadialBar dataKey="value" cornerRadius={4}>
          <Cell fill={color} />
          <Cell fill="hsl(220,13%,91%)" />
        </RadialBar>
      </RadialBarChart>
      <span className="text-sm font-bold -mt-1" style={{ color }}>{weight}%</span>
    </div>
  );
}

// ── Per-KPI Section ────────────────────────────────────────────────────────── //
function KpiSection({ kpi, prevKpi, idx, year }: {
  kpi: KpiItem;
  prevKpi?: KpiItem;
  idx: number;
  year: number;
}) {
  const color = CHART_COLORS[idx % CHART_COLORS.length];
  const periods = kpi.periods ?? [];
  const prevPeriods = prevKpi?.periods ?? [];
  const evalLabel = EVAL_LABEL[kpi.evaluation_period] ?? kpi.evaluation_period;
  const status = kpi.status ?? "red";

  // Current = last period with data in this year
  const lastPeriod = periods[periods.length - 1] as PeriodDetail | undefined;

  // Delta: same period name vs previous year
  const samePrevPeriod = lastPeriod
    ? prevPeriods.find((p) => p.period_name === lastPeriod.period_name)
    : undefined;
  const delta = lastPeriod && samePrevPeriod
    ? lastPeriod.achievement - samePrevPeriod.achievement
    : null;

  // ── Comparison grouped bar: per period name, current year vs prev year ──
  const compMap = new Map<string, { curr?: number; prev?: number }>();
  periods.forEach((p) => compMap.set(p.period_name, { curr: p.achievement }));
  prevPeriods.forEach((p) => {
    const e = compMap.get(p.period_name) ?? {};
    compMap.set(p.period_name, { ...e, prev: p.achievement });
  });
  // preserve natural period order
  const orderedNames: string[] = [];
  periods.forEach((p) => { if (!orderedNames.includes(p.period_name)) orderedNames.push(p.period_name); });
  prevPeriods.forEach((p) => { if (!orderedNames.includes(p.period_name)) orderedNames.push(p.period_name); });
  const compData = orderedNames.map((name) => {
    const e = compMap.get(name) ?? {};
    return { period: name, [String(year)]: e.curr ?? null, [String(year - 1)]: e.prev ?? null };
  });

  // ── Trend: combine prev year + current year as sequential x-axis, 2 lines ──
  const prevYear = year - 1;
  const trendData = [
    ...prevPeriods.map((p) => ({
      label: `${prevYear}/${p.period_name}`,
      [String(prevYear)]: p.achievement,
      [String(year)]: null as number | null,
    })),
    ...periods.map((p) => ({
      label: `${year}/${p.period_name}`,
      [String(prevYear)]: null as number | null,
      [String(year)]: p.achievement,
    })),
  ];
  const hasTrend = trendData.length > 0;

  return (
    <section
      id={`kpi-${kpi.kpi_id}`}
      className="scroll-mt-20 space-y-4"
    >
      {/* KPI header */}
      <div className="flex flex-wrap items-center gap-2 border-b border-slate-100 pb-3">
        <div
          className="w-2.5 h-2.5 rounded-full shrink-0"
          style={{ backgroundColor: color }}
        />
        <h2 className="text-base font-bold text-slate-800 flex-1 min-w-0">{kpi.kpi_name}</h2>
        <Badge variant="secondary" className="text-[10px]">{evalLabel}</Badge>
        <span className="text-xs text-slate-400">Bobot: {kpi.weight}%</span>
        <span className={`flex items-center gap-1 px-2 py-0.5 rounded-full border text-xs font-bold ${STATUS_COLOR[status]}`}>
          {STATUS_ICON[status as keyof typeof STATUS_ICON]}
          {status === "green" ? "On Target" : status === "yellow" ? "On Progress" : "Below Target"}
        </span>
      </div>

      {/* 3-column info grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">

        {/* 1. Current KPI Card */}
        <Card className="p-4 flex flex-col gap-3 border-0 shadow-sm shadow-foreground/5">
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
            Current — {lastPeriod?.period_name ?? "-"}
          </p>
          {lastPeriod ? (
            <>
              <div className="flex items-end gap-2">
                <span className="text-3xl font-extrabold" style={{ color }}>
                  {lastPeriod.realization.toLocaleString("id-ID")}
                </span>
                <span className="text-sm text-slate-400 mb-1">{kpi.unit}</span>
              </div>
              <div className="flex items-center justify-between text-xs text-slate-500">
                <span>Target: <strong>{lastPeriod.target.toLocaleString("id-ID")}</strong></span>
                <span className={`flex items-center gap-0.5 font-semibold ${
                  lastPeriod.achievement >= 100 ? "text-emerald-600" :
                  lastPeriod.achievement >= 80 ? "text-amber-600" : "text-red-500"}`}>
                  {lastPeriod.achievement.toFixed(1)}%
                </span>
              </div>
              {delta !== null && (
                <div className={`flex items-center gap-1 text-[11px] font-medium pt-1 border-t border-slate-100 ${delta >= 0 ? "text-emerald-600" : "text-red-500"}`}>
                  {delta >= 0 ? <ArrowUpRight className="w-3.5 h-3.5" /> : <ArrowDownRight className="w-3.5 h-3.5" />}
                  {Math.abs(delta).toFixed(1)}% vs {lastPeriod!.period_name} {year - 1}
                </div>
              )}
            </>
          ) : (
            <p className="text-sm text-slate-400">Belum ada data</p>
          )}
        </Card>

        {/* 2. Perbandingan tahun ini vs tahun lalu — grouped bar per periode */}
        <Card className="p-4 border-0 shadow-sm shadow-foreground/5">
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">
            Perbandingan {year} vs {year - 1}
          </p>
          {compData.length > 0 ? (
            <ResponsiveContainer width="100%" height={120}>
              <BarChart data={compData} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(220,13%,91%)" />
                <XAxis dataKey="period" tick={{ fontSize: 10 }} />
                <YAxis domain={[0, 130]} tick={{ fontSize: 9 }} />
                <Tooltip
                  contentStyle={{ borderRadius: 8, border: "none", boxShadow: "0 4px 12px rgba(0,0,0,.1)", fontSize: 11 }}
                  formatter={(v: unknown, name: string) =>
                    [v != null ? (v as number).toFixed(1) + "%" : "-", name]}
                />
                <Legend iconType="circle" iconSize={7} wrapperStyle={{ fontSize: 10, paddingTop: 2 }} />
                <Bar dataKey={String(year)} fill={color} radius={[3, 3, 0, 0]} maxBarSize={22} />
                <Bar dataKey={String(year - 1)} fill="hsl(220,13%,76%)" radius={[3, 3, 0, 0]} maxBarSize={22} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[120px] flex items-center justify-center text-slate-400 text-xs">
              Belum ada data tahun {year - 1}
            </div>
          )}
        </Card>

        {/* 3. Trend: prev year → current year, 2 lines */}
        <Card className="p-4 border-0 shadow-sm shadow-foreground/5">
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">
            Trend {year - 1}–{year} ({evalLabel})
          </p>
          {hasTrend ? (
            <ResponsiveContainer width="100%" height={120}>
              <LineChart data={trendData} margin={{ top: 4, right: 4, left: -20, bottom: 16 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(220,13%,91%)" />
                <XAxis dataKey="label" tick={{ fontSize: 8 }} angle={-20} textAnchor="end" height={32} />
                <YAxis domain={[0, 130]} tick={{ fontSize: 9 }} />
                <Tooltip
                  contentStyle={{ borderRadius: 8, border: "none", boxShadow: "0 4px 12px rgba(0,0,0,.1)", fontSize: 11 }}
                  formatter={(v: unknown, name: string) =>
                    [v != null ? (v as number).toFixed(1) + "%" : "-", name]}
                />
                <Legend iconType="circle" iconSize={7} wrapperStyle={{ fontSize: 10 }} />
                <Line dataKey={String(year)} stroke={color} strokeWidth={2.5}
                  dot={{ r: 3, fill: color }} activeDot={{ r: 5 }} connectNulls={false} />
                <Line dataKey={String(year - 1)} stroke="hsl(220,13%,65%)" strokeWidth={1.5}
                  strokeDasharray="4 3" dot={{ r: 3 }} activeDot={{ r: 5 }} connectNulls={false} />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[120px] flex items-center justify-center text-slate-400 text-xs">
              Belum ada data
            </div>
          )}
        </Card>
      </div>

      {/* Annual Report — prominent card */}
      <div className={`rounded-xl p-4 flex items-center justify-between gap-4 border ${STATUS_COLOR[status]}`}>
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide opacity-70">Annual Report</p>
          <p className="text-4xl font-black mt-1">{kpi.annual_report.toFixed(2)}%</p>
          <p className="text-[11px] opacity-60 mt-0.5">
            Rata-rata achievement seluruh {evalLabel.toLowerCase()} · Kontribusi:{" "}
            <strong>{((kpi.annual_report * kpi.weight) / 100).toFixed(2)}%</strong>
          </p>
        </div>
        {/* Period breakdown mini table */}
        {periods.length > 0 && (
          <div className="overflow-x-auto shrink-0">
            <table className="text-[11px] text-right">
              <thead>
                <tr className="opacity-60">
                  <th className="pr-3 font-normal text-left pb-1">Periode</th>
                  <th className="pr-3 font-normal pb-1">Target</th>
                  <th className="pr-3 font-normal pb-1">Realisasi</th>
                  <th className="font-normal pb-1">Ach%</th>
                </tr>
              </thead>
              <tbody>
                {periods.map((p) => (
                  <tr key={p.period_id} className="border-t border-current/10">
                    <td className="pr-3 py-0.5 text-left font-medium">{p.period_name}</td>
                    <td className="pr-3 py-0.5">{p.target.toLocaleString("id-ID")}</td>
                    <td className="pr-3 py-0.5">{p.realization.toLocaleString("id-ID")}</td>
                    <td className="py-0.5 font-bold">{p.achievement.toFixed(1)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  );
}

// ── Main page ──────────────────────────────────────────────────────────────── //
export default function DivisionDashboard() {
  const { divisionId } = useParams<{ divisionId: string }>();
  const [year, setYear] = useState(new Date().getFullYear());
  const { data: years = [new Date().getFullYear()] } = useAvailableYears();
  const headerRef = useRef<HTMLDivElement>(null);

  const divId = SLUG_TO_ID[divisionId ?? ""] ?? 1;
  const { data: division, isLoading, error } = useDivision(divId, year);
  // Fetch previous year silently (no loading state — enhancement only)
  const { data: prevDivision } = useDivision(divId, year - 1);
  const prevKpiMap = new Map<number, KpiItem>();
  (prevDivision?.kpis ?? []).forEach((k: KpiItem) => prevKpiMap.set(k.kpi_id, k));

  // Scroll to anchor on mount / navigation
  useEffect(() => {
    const hash = window.location.hash;
    if (hash) {
      setTimeout(() => {
        document.querySelector(hash)?.scrollIntoView({ behavior: "smooth", block: "start" });
      }, 400);
    }
  }, [divisionId]);

  if (isLoading) return (
    <div className="space-y-6 max-w-6xl">
      <Skeleton className="h-10 w-72" />
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[...Array(6)].map((_, i) => <Skeleton key={i} className="h-40 rounded-xl" />)}
      </div>
    </div>
  );

  if (error || !division) return (
    <div className="flex items-center gap-3 text-destructive p-6">
      <AlertCircle className="w-5 h-5" />
      <span>Divisi tidak ditemukan atau backend tidak aktif.</span>
    </div>
  );

  const kpis = division.kpis ?? [];
  const divReport = division.division_report ?? division.avg_achievement ?? 0;
  const divStatus = divReport >= 100 ? "green" : divReport >= 80 ? "yellow" : "red";

  return (
    <div className="space-y-8 max-w-6xl" ref={headerRef}>
      {/* ── Page Header ── */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl md:text-2xl font-bold tracking-tight">{division.division_name}</h1>
          <p className="text-sm text-muted-foreground mt-0.5">KPI Dashboard · Tahun {year}</p>
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

      {/* ── Division Report Card ── */}
      <div className={`rounded-2xl p-5 flex flex-wrap gap-6 items-center border-2 ${STATUS_COLOR[divStatus]}`}>
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide opacity-70">Division Report</p>
          <p className="text-5xl font-black mt-1">{divReport.toFixed(2)}%</p>
          <p className="text-xs opacity-60 mt-1">Σ (Annual Report × Bobot) / 100</p>
        </div>
        <div className="flex gap-6 flex-wrap">
          <div className="text-center">
            <p className="text-2xl font-bold">{division.on_target ?? 0}</p>
            <p className="text-[11px] opacity-70">On Target</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold">{division.on_progress ?? 0}</p>
            <p className="text-[11px] opacity-70">On Progress</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold">{kpis.length}</p>
            <p className="text-[11px] opacity-70">Total KPI</p>
          </div>
        </div>
      </div>

      {/* ── Weight distribution gauges ── */}
      <Card className="p-4 border-0 shadow-sm shadow-foreground/5">
        <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-4">Distribusi Bobot</p>
        <div className="flex flex-wrap gap-6 justify-around">
          {kpis.map((kpi, idx) => (
            <div key={kpi.kpi_id} className="flex flex-col items-center gap-1 text-center max-w-[90px]">
              <WeightGauge weight={kpi.weight} color={CHART_COLORS[idx % CHART_COLORS.length]} />
              <p className="text-[10px] text-slate-500 leading-tight line-clamp-2">{kpi.kpi_name}</p>
            </div>
          ))}
        </div>
      </Card>

      {/* ── KPI List Table ── */}
      <Card className="border-0 shadow-sm shadow-foreground/5 overflow-hidden">
        <div className="px-4 pt-4 pb-2">
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Daftar KPI</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-y border-slate-100 bg-slate-50/60 text-xs text-slate-400 uppercase">
                <th className="px-4 py-2.5 text-left">Indikator</th>
                <th className="px-4 py-2.5 text-center">Periode</th>
                <th className="px-4 py-2.5 text-right">Bobot</th>
                <th className="px-4 py-2.5 text-right">Annual Report</th>
                <th className="px-4 py-2.5 text-right">Kontribusi</th>
                <th className="px-4 py-2.5 text-center">Status</th>
                <th className="px-4 py-2.5 text-center">Detail</th>
              </tr>
            </thead>
            <tbody>
              {kpis.map((kpi, idx) => {
                const color = CHART_COLORS[idx % CHART_COLORS.length];
                return (
                  <tr key={kpi.kpi_id} className="border-b border-slate-50 hover:bg-slate-50/80 transition-colors">
                    <td className="px-4 py-2.5 font-medium text-slate-800 flex items-center gap-2">
                      <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: color }} />
                      {kpi.kpi_name}
                    </td>
                    <td className="px-4 py-2.5 text-center">
                      <span className="px-1.5 py-0.5 bg-blue-50 text-blue-700 rounded text-[10px] font-medium">
                        {EVAL_LABEL[kpi.evaluation_period] ?? kpi.evaluation_period}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-right text-slate-500">{kpi.weight}%</td>
                    <td className={`px-4 py-2.5 text-right font-bold ${
                      kpi.annual_report >= 100 ? "text-emerald-600" :
                      kpi.annual_report >= 80 ? "text-amber-600" : "text-red-500"}`}>
                      {kpi.annual_report.toFixed(2)}%
                    </td>
                    <td className="px-4 py-2.5 text-right font-semibold text-slate-700">
                      {((kpi.annual_report * kpi.weight) / 100).toFixed(2)}%
                    </td>
                    <td className="px-4 py-2.5 text-center">
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full border text-[11px] font-semibold ${STATUS_COLOR[kpi.status ?? "red"]}`}>
                        {STATUS_ICON[(kpi.status ?? "red") as keyof typeof STATUS_ICON]}
                        {kpi.status === "green" ? "On Target" : kpi.status === "yellow" ? "On Progress" : "Below"}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-center">
                      <button
                        onClick={() => document.getElementById(`kpi-${kpi.kpi_id}`)?.scrollIntoView({ behavior: "smooth", block: "start" })}
                        className="text-xs text-blue-600 hover:text-blue-800 hover:underline font-medium"
                      >
                        → Detail
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
            <tfoot>
              <tr className={`font-bold border-t-2 border-slate-200 ${STATUS_COLOR[divStatus]}`}>
                <td className="px-4 py-2.5" colSpan={4}>Division Report = Σ Kontribusi</td>
                <td className="px-4 py-2.5 text-right text-base">{divReport.toFixed(2)}%</td>
                <td colSpan={2} />
              </tr>
            </tfoot>
          </table>
        </div>
      </Card>

      {/* ── Per-KPI Sections ── */}
      <div className="space-y-10">
        {kpis.map((kpi, idx) => (
          <KpiSection
            key={kpi.kpi_id}
            kpi={kpi}
            prevKpi={prevKpiMap.get(kpi.kpi_id)}
            idx={idx}
            year={year}
          />
        ))}
      </div>
    </div>
  );
}
