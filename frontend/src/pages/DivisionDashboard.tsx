import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  AlertCircle, TrendingUp, TrendingDown, Minus,
  ArrowUpRight, ArrowDownRight,
} from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, LineChart, Line, Legend,
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

// ── Semicircle gauge ──────────────────────────────────────────────────────── //
function WeightGauge({ weight, color, name }: { weight: number; color: string; name: string }) {
  const r = 28;
  const cx = 40;   // center-x = SVG width / 2
  const cy = 40;   // baseline di bagian bawah SVG
  const circ = Math.PI * r;
  const filled = (weight / 100) * circ;
  const empty = circ - filled;
  const arc = `M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`;

  return (
    <div className="flex flex-col items-center text-center gap-0.5 min-w-[80px]">
      <svg width={80} height={50} viewBox="0 0 80 50">
        {/* Track */}
        <path d={arc} fill="none" stroke="hsl(220,13%,91%)" strokeWidth={8} strokeLinecap="round" />
        {/* Filled arc */}
        <path
          d={arc} fill="none" stroke={color} strokeWidth={8} strokeLinecap="round"
          strokeDasharray={`${filled} ${empty}`}
          strokeDashoffset={0}
        />
      </svg>
      <span className="text-sm font-bold -mt-2" style={{ color }}>{weight}%</span>
      <p className="text-[10px] text-slate-500 leading-tight max-w-[80px] line-clamp-2">{name}</p>
    </div>
  );
}

// ── Per-KPI Section ────────────────────────────────────────────────────────── //
function KpiSection({
  kpi, prevKpi, idx, year,
}: {
  kpi: KpiItem;
  prevKpi?: KpiItem;
  idx: number;
  year: number;
}) {
  const color = CHART_COLORS[idx % CHART_COLORS.length];
  const periods: PeriodDetail[] = (kpi.periods ?? []) as PeriodDetail[];
  const prevPeriods: PeriodDetail[] = (prevKpi?.periods ?? []) as PeriodDetail[];
  const evalLabel = EVAL_LABEL[kpi.evaluation_period] ?? kpi.evaluation_period;
  const status = kpi.status ?? "red";

  // Current = last period with data
  const lastPeriod = periods[periods.length - 1] as PeriodDetail | undefined;

  // Delta vs same period name in previous year
  const samePrevPeriod = lastPeriod
    ? prevPeriods.find((p) => p.period_name === lastPeriod.period_name)
    : undefined;
  const delta = lastPeriod && samePrevPeriod
    ? lastPeriod.achievement - samePrevPeriod.achievement
    : null;

  // ── Comparison bar: grouped per period name — this year vs prev year ──────
  const compMap = new Map<string, { curr?: number; prev?: number }>();
  periods.forEach((p) => compMap.set(p.period_name, { curr: p.achievement }));
  prevPeriods.forEach((p) => {
    const e = compMap.get(p.period_name) ?? {};
    compMap.set(p.period_name, { ...e, prev: p.achievement });
  });
  const orderedNames: string[] = [];
  periods.forEach((p) => { if (!orderedNames.includes(p.period_name)) orderedNames.push(p.period_name); });
  prevPeriods.forEach((p) => { if (!orderedNames.includes(p.period_name)) orderedNames.push(p.period_name); });
  const compData = orderedNames.map((name) => {
    const e = compMap.get(name) ?? {};
    return { period: name, [String(year)]: e.curr ?? null, [String(year - 1)]: e.prev ?? null };
  });

  // ── Trend: prev year periods + current year periods as one timeline ────────
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

  return (
    <section id={`kpi-${kpi.kpi_id}`} className="scroll-mt-6 space-y-3">
      {/* ── KPI header row ── */}
      <div className="flex flex-wrap items-center gap-2 pt-2 pb-1 border-b border-slate-100">
        <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: color }} />
        <h2 className="text-sm font-bold text-slate-800 flex-1 min-w-0 truncate">{kpi.kpi_name}</h2>
        <Badge variant="outline" className="text-[10px] shrink-0">{evalLabel}</Badge>
        <span className="text-xs text-slate-400 shrink-0">Bobot {kpi.weight}%</span>
        <span className={`flex items-center gap-1 px-2 py-0.5 rounded-full border text-[11px] font-semibold shrink-0 ${STATUS_COLOR[status]}`}>
          {STATUS_ICON[status as keyof typeof STATUS_ICON]}
          {status === "green" ? "On Target" : status === "yellow" ? "Near Target" : "Below Target"}
        </span>
      </div>

      {/* ── Row 1: Current (narrow) + Annual Report (wide) ── */}
      <div className="grid grid-cols-[1fr_2fr] gap-3 items-stretch">

        {/* Current KPI card */}
        <Card className="border border-slate-100 shadow-none flex flex-col">
          <CardHeader className="pb-0 pt-4 px-5">
            <CardTitle className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide">
              Current — {lastPeriod?.period_name ?? "–"}
            </CardTitle>
          </CardHeader>
          <CardContent className="px-5 pb-5 flex flex-col justify-between flex-1 gap-4 pt-3">
            {lastPeriod ? (
              <>
                {/* Realization — large */}
                <div>
                  <div className="flex items-end gap-2">
                    <span className="text-6xl font-black leading-none" style={{ color }}>
                      {lastPeriod.realization.toLocaleString("id-ID")}
                    </span>
                    <span className="text-base text-slate-400 mb-1">{kpi.unit}</span>
                  </div>
                  <div className="mt-2 flex items-center justify-between text-sm text-slate-500">
                    <span>Target: <strong>{lastPeriod.target.toLocaleString("id-ID")}</strong></span>
                    <span>Achievement: <span className={`text-lg font-black ${lastPeriod.achievement >= 100 ? "text-emerald-600" :
                      lastPeriod.achievement >= 80 ? "text-amber-600" : "text-red-500"}`}>
                      {lastPeriod.achievement.toFixed(1)}%
                    </span>
                    </span>
                  </div>
                </div>

                {/* Delta vs prev year */}
                {delta !== null && (
                  <div className={`flex items-center gap-1.5 text-sm font-semibold pt-3 border-t border-slate-100 ${delta >= 0 ? "text-emerald-600" : "text-red-500"}`}>
                    {delta >= 0 ? <ArrowUpRight className="w-4 h-4" /> : <ArrowDownRight className="w-4 h-4" />}
                    {Math.abs(delta).toFixed(1)}% vs {lastPeriod.period_name} {year - 1}
                  </div>
                )}
              </>
            ) : (
              <p className="text-sm text-slate-400">Belum ada data</p>
            )}
          </CardContent>
        </Card>

        {/* Annual Report card */}
        <Card className={`border shadow-none flex flex-col ${STATUS_COLOR[status]}`}>
          <CardHeader className="pb-0 pt-4 px-5">
            <CardTitle className="text-[11px] font-semibold uppercase tracking-wide opacity-70">
              Annual Report
            </CardTitle>
          </CardHeader>
          <CardContent className="px-5 pb-5 flex flex-col justify-between flex-1 gap-4 pt-3">
            {/* Score + keterangan */}
            <div>
              <p className="text-6xl font-black leading-none">{kpi.annual_report.toFixed(2)}%</p>
              <p className="text-sm opacity-60 mt-2">
                Rata-rata {evalLabel.toLowerCase()} · Kontribusi:{" "}
                <strong>{((kpi.annual_report * kpi.weight) / 100).toFixed(2)}%</strong>
              </p>
            </div>

            {/* Mini period table */}
            {periods.length > 0 && (
              <div className="overflow-x-auto border-t border-current/10 pt-3">
                <table className="w-full text-xs text-right whitespace-nowrap">
                  <thead>
                    <tr className="opacity-60">
                      <th className="pr-3 font-normal text-left pb-1">Periode</th>
                      <th className="pr-3 font-normal pb-1">Realisasi</th>
                      <th className="pr-3 font-normal pb-1">Target</th>
                      <th className="font-normal pb-1">Ach%</th>
                    </tr>
                  </thead>
                  <tbody>
                    {periods.map((p) => (
                      <tr key={p.period_id} className="border-t border-current/10">
                        <td className="pr-3 py-1 text-left font-medium">{p.period_name}</td>
                        <td className="pr-3 py-1">{p.realization.toLocaleString("id-ID")}</td>
                        <td className="pr-3 py-1">{p.target.toLocaleString("id-ID")}</td>
                        <td className={`py-1 font-bold ${p.achievement >= 100 ? "text-emerald-700" :
                          p.achievement >= 80 ? "text-amber-700" : "text-red-700"}`}>
                          {p.achievement.toFixed(1)}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* ── Row 2: Perbandingan tahun (full width bar chart) ── */}
      <Card className="border border-slate-100 shadow-none">
        <CardHeader className="pb-1 pt-3 px-4">
          <CardTitle className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide">
            Perbandingan {year} vs {year - 1}
          </CardTitle>
        </CardHeader>
        <CardContent className="px-0 pb-3">
          {compData.length > 0 ? (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={compData} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(220,13%,93%)" vertical={false} />
                <XAxis dataKey="period" tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis domain={[0, 130]} ticks={[0, 25, 50, 75, 100, 130]} tick={{ fontSize: 10 }} axisLine={false} tickLine={false} width={36} />
                <Tooltip
                  contentStyle={{ borderRadius: 8, border: "1px solid hsl(220,13%,91%)", boxShadow: "0 4px 16px rgba(0,0,0,.08)", fontSize: 12 }}
                  formatter={(v: unknown, name: string) => [v != null ? (v as number).toFixed(1) + "%" : "–", name]}
                />
                <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 11, paddingTop: 4 }} />
                <Bar dataKey={String(year)} fill={color} radius={[4, 4, 0, 0]} maxBarSize={40} />
                <Bar dataKey={String(year - 1)} fill="hsl(220,13%,80%)" radius={[4, 4, 0, 0]} maxBarSize={40} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[160px] flex items-center justify-center text-slate-400 text-xs">
              Belum ada data tahun {year - 1}
            </div>
          )}
        </CardContent>
      </Card>

      {/* ── Row 3: Trend (full width line chart) ── */}
      <Card className="border border-slate-100 shadow-none">
        <CardHeader className="pb-1 pt-3 px-4">
          <CardTitle className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide">
            Trend {year - 1}–{year} ({evalLabel})
          </CardTitle>
        </CardHeader>
        <CardContent className="px-0 pb-3">
          {trendData.length > 0 ? (
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={trendData} margin={{ top: 4, right: 16, left: 0, bottom: 28 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(220,13%,93%)" vertical={false} />
                <XAxis
                  dataKey="label" tick={{ fontSize: 9 }}
                  angle={-25} textAnchor="end" height={36}
                  axisLine={false} tickLine={false}
                />
                <YAxis domain={[0, 130]} ticks={[0, 25, 50, 75, 100, 130]} tick={{ fontSize: 10 }} axisLine={false} tickLine={false} width={36} />
                <Tooltip
                  contentStyle={{ borderRadius: 8, border: "1px solid hsl(220,13%,91%)", boxShadow: "0 4px 16px rgba(0,0,0,.08)", fontSize: 12 }}
                  formatter={(v: unknown, name: string) => [v != null ? (v as number).toFixed(1) + "%" : "–", name]}
                />
                <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 11 }} />
                <Line
                  dataKey={String(year)} stroke={color} strokeWidth={2.5}
                  dot={{ r: 4, fill: color, strokeWidth: 0 }} activeDot={{ r: 6 }}
                  connectNulls={false}
                />
                <Line
                  dataKey={String(year - 1)} stroke="hsl(220,13%,70%)" strokeWidth={1.5}
                  strokeDasharray="5 4"
                  dot={{ r: 3, fill: "hsl(220,13%,70%)", strokeWidth: 0 }} activeDot={{ r: 5 }}
                  connectNulls={false}
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[170px] flex items-center justify-center text-slate-400 text-xs">
              Belum ada data
            </div>
          )}
        </CardContent>
      </Card>
    </section>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────── //
export default function DivisionDashboard() {
  const { divisionId } = useParams<{ divisionId: string }>();
  const [selectedYear, setSelectedYear] = useState<number | null>(null);
  const { data: years } = useAvailableYears();

  // Set default year to the latest available year from DB on load
  useEffect(() => {
    if (years && years.length > 0 && selectedYear === null) {
      setSelectedYear(years[0]);
    }
  }, [years, selectedYear]);

  const year = selectedYear ?? 2025; // fallback to 2025 while loading


  const divId = SLUG_TO_ID[divisionId ?? ""] ?? 1;
  const { data: division, isLoading, error } = useDivision(divId, year);
  const { data: prevDivision } = useDivision(divId, year - 1);

  const prevKpiMap = new Map<number, KpiItem>();
  (prevDivision?.kpis ?? []).forEach((k: KpiItem) => prevKpiMap.set(k.kpi_id, k));

  // Scroll to anchor on load/navigation
  useEffect(() => {
    const hash = window.location.hash;
    if (hash) {
      setTimeout(() => {
        document.querySelector(hash)?.scrollIntoView({ behavior: "smooth", block: "start" });
      }, 400);
    }
  }, [divisionId]);

  if (isLoading) return (
    <div className="space-y-4 max-w-4xl">
      <Skeleton className="h-8 w-56" />
      <div className="grid grid-cols-2 gap-4">
        <Skeleton className="h-32 rounded-xl" />
        <Skeleton className="h-32 rounded-xl" />
      </div>
      <Skeleton className="h-40 rounded-xl" />
      {[...Array(3)].map((_, i) => <Skeleton key={i} className="h-64 rounded-xl" />)}
    </div>
  );

  if (error || !division) return (
    <div className="flex items-center gap-3 text-destructive p-6">
      <AlertCircle className="w-5 h-5" />
      <span>Divisi tidak ditemukan atau backend tidak aktif.</span>
    </div>
  );

  const kpis: KpiItem[] = division.kpis ?? [];
  const divReport: number = division.division_report ?? division.avg_achievement ?? 0;
  const divStatus = divReport >= 100 ? "green" : divReport >= 80 ? "yellow" : "red";

  return (
    <div className="space-y-5">

      {/* ══════════════════════════════════════════════════════════════════
          HEADLINE
      ══════════════════════════════════════════════════════════════════ */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold tracking-tight">{division.division_name}</h1>
          <p className="text-xs text-muted-foreground mt-0.5">KPI Dashboard · {year}</p>
        </div>
        <Select value={String(year)} onValueChange={(v) => setSelectedYear(Number(v))}>
          <SelectTrigger className="w-28 h-8 text-sm bg-background shrink-0">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {(years ?? [year]).map((y) => <SelectItem key={y} value={String(y)}>{y}</SelectItem>)}
          </SelectContent>
        </Select>
      </div>

      {/* ══════════════════════════════════════════════════════════════════
          ROW: Division Report (left) | Weight gauges (right)
      ══════════════════════════════════════════════════════════════════ */}
      <div className="grid grid-cols-2 gap-4">

        {/* Division Report card */}
        <Card className={`border-2 shadow-none ${STATUS_COLOR[divStatus]}`}>
          <CardHeader className="pb-1 pt-4 px-5">
            <CardTitle className="text-[11px] font-semibold uppercase tracking-wide opacity-70">
              Division Report
            </CardTitle>
          </CardHeader>
          <CardContent className="px-5 pb-4 space-y-2">
            <p className="text-4xl font-black">{divReport.toFixed(2)}%</p>
            <p className="text-[11px] opacity-60">Σ (Annual Report × Bobot) / 100</p>
            <div className="flex gap-4 pt-1 border-t border-current/10">
              <div className="text-center">
                <p className="text-lg font-bold">{division.on_target ?? 0}</p>
                <p className="text-[10px] opacity-60">On Target</p>
              </div>
              <div className="text-center">
                <p className="text-lg font-bold">{division.on_progress ?? 0}</p>
                <p className="text-[10px] opacity-60">Near Target</p>
              </div>
              <div className="text-center">
                <p className="text-lg font-bold">{kpis.length}</p>
                <p className="text-[10px] opacity-60">Total KPI</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Weight gauges */}
        <Card className="border border-slate-100 shadow-none">
          <CardHeader className="pb-1 pt-4 px-5">
            <CardTitle className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide">
              Distribusi Bobot
            </CardTitle>
          </CardHeader>
          <CardContent className="px-4 pt-4 pb-4">
            <div className="flex flex-wrap gap-3 justify-around items-start">
              {kpis.map((kpi, idx) => (
                <WeightGauge
                  key={kpi.kpi_id}
                  weight={kpi.weight}
                  color={CHART_COLORS[idx % CHART_COLORS.length]}
                  name={kpi.kpi_name}
                />
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* ══════════════════════════════════════════════════════════════════
          DAFTAR KPI — full width table
      ══════════════════════════════════════════════════════════════════ */}
      <Card className="border border-slate-100 shadow-none overflow-hidden">
        <CardHeader className="pb-2 pt-4 px-5">
          <CardTitle className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide">
            Daftar KPI
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-y border-slate-100 bg-slate-50/70 text-[11px] text-slate-400 uppercase">
                  <th className="px-5 py-2.5 text-left">Indikator</th>
                  <th className="px-4 py-2.5 text-center">Periode</th>
                  <th className="px-4 py-2.5 text-right">Bobot</th>
                  <th className="px-4 py-2.5 text-right">Annual Report</th>
                  <th className="px-4 py-2.5 text-right">Kontribusi</th>
                  <th className="px-4 py-2.5 text-center">Status</th>
                  <th className="px-4 py-2.5 text-center">↓</th>
                </tr>
              </thead>
              <tbody>
                {kpis.map((kpi, idx) => {
                  const c = CHART_COLORS[idx % CHART_COLORS.length];
                  const st = kpi.status ?? "red";
                  return (
                    <tr key={kpi.kpi_id}
                      className="border-b border-slate-50 hover:bg-slate-50/60 transition-colors">
                      <td className="px-5 py-2.5">
                        <div className="flex items-center gap-2">
                          <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: c }} />
                          <span className="font-medium text-slate-800 text-xs">{kpi.kpi_name}</span>
                        </div>
                      </td>
                      <td className="px-4 py-2.5 text-center">
                        <span className="text-[10px] px-1.5 py-0.5 bg-blue-50 text-blue-700 rounded font-medium">
                          {EVAL_LABEL[kpi.evaluation_period] ?? kpi.evaluation_period}
                        </span>
                      </td>
                      <td className="px-4 py-2.5 text-right text-xs text-slate-500">{kpi.weight}%</td>
                      <td className={`px-4 py-2.5 text-right text-xs font-bold ${kpi.annual_report >= 100 ? "text-emerald-600" :
                        kpi.annual_report >= 80 ? "text-amber-600" : "text-red-500"}`}>
                        {kpi.annual_report.toFixed(2)}%
                      </td>
                      <td className="px-4 py-2.5 text-right text-xs font-semibold text-slate-700">
                        {((kpi.annual_report * kpi.weight) / 100).toFixed(2)}%
                      </td>
                      <td className="px-4 py-2.5 text-center">
                        <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full border text-[10px] font-semibold ${STATUS_COLOR[st]}`}>
                          {STATUS_ICON[st as keyof typeof STATUS_ICON]}
                          {st === "green" ? "On Target" : st === "yellow" ? "Near Target" : "Below Target"}
                        </span>
                      </td>
                      <td className="px-4 py-2.5 text-center">
                        <button
                          onClick={() => document.getElementById(`kpi-${kpi.kpi_id}`)
                            ?.scrollIntoView({ behavior: "smooth", block: "start" })}
                          className="text-[11px] text-blue-600 hover:text-blue-800 font-medium hover:underline"
                        >
                          ↓ Detail
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
              <tfoot>
                <tr className={`border-t-2 border-slate-200 font-bold text-sm ${STATUS_COLOR[divStatus]}`}>
                  <td className="px-5 py-2.5 text-xs" colSpan={4}>Division Report = Σ Kontribusi</td>
                  <td className="px-4 py-2.5 text-right">{divReport.toFixed(2)}%</td>
                  <td colSpan={2} />
                </tr>
              </tfoot>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* ══════════════════════════════════════════════════════════════════
          PER-KPI SECTIONS
      ══════════════════════════════════════════════════════════════════ */}
      <div className="space-y-8 pb-8">
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
