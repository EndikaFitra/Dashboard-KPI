import { useQuery } from "@tanstack/react-query";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend, ReferenceLine,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  TrendingUp, Activity, BarChart3, AlertCircle,
  Database, Hash, Target,
} from "lucide-react";
import { getMrrForecast } from "@/api/client";
import type { MrrForecastData, ForecastPoint } from "@/api/client";

// ── Chart colors ──────────────────────────────────────────────────────── //
const COLOR_ACTUAL = "hsl(220, 70%, 50%)";   // blue
const COLOR_FITTED = "hsl(30, 90%, 55%)";     // orange
const COLOR_FORECAST = "hsl(152, 60%, 42%)";   // green

// ── Number formatting ─────────────────────────────────────────────────── //
const fmtMRR = (v: number) => {
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`;
  if (v >= 1_000) return `${(v / 1_000).toFixed(0)}K`;
  return v.toLocaleString("id-ID");
};

const fmtMRRFull = (v: number) =>
  `Rp ${v.toLocaleString("id-ID")}`;

// ── Build unified chart data ──────────────────────────────────────────── //
function buildChartData(data: MrrForecastData) {
  const chartData: {
    label: string;
    actual: number | null;
    fitted: number | null;
    forecast: number | null;
  }[] = [];

  // Actual & Fitted (same length, aligned by index)
  data.actual.forEach((a: ForecastPoint, i: number) => {
    chartData.push({
      label: a.label,
      actual: a.value,
      fitted: data.fitted[i]?.value ?? null,
      forecast: null,
    });
  });

  // Bridge: add the last actual point as the first forecast point
  // so the forecast line connects visually with the actual line
  // Bridge ini akan memasukkan nilai aktual terakhir ke kategori forecast
  /* const lastActual = data.actual[data.actual.length - 1];
  if (lastActual) {
    chartData[chartData.length - 1].forecast = lastActual.value;
  }*/

  // Forecast points
  data.forecast.forEach((f: ForecastPoint) => {
    chartData.push({
      label: f.label,
      actual: null,
      fitted: null,
      forecast: f.value,
    });
  });

  return chartData;
}

// ── Custom tooltip ────────────────────────────────────────────────────── //
function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload || payload.length === 0) return null;

  return (
    <div className="bg-white/95 backdrop-blur border border-slate-200 rounded-xl shadow-xl px-4 py-3 text-xs">
      <p className="font-bold text-slate-700 mb-1.5">{label}</p>
      {payload.map((entry: any) => {
        if (entry.value == null) return null;
        return (
          <div key={entry.dataKey} className="flex items-center gap-2 py-0.5">
            <span
              className="w-2.5 h-2.5 rounded-full shrink-0"
              style={{ backgroundColor: entry.color }}
            />
            <span className="text-slate-500 capitalize">{entry.dataKey}:</span>
            <span className="font-bold text-slate-800">{fmtMRRFull(entry.value)}</span>
          </div>
        );
      })}
    </div>
  );
}

// ── Stat card component ───────────────────────────────────────────────── //
function StatCard({
  icon: Icon,
  label,
  value,
  sub,
  accent = false,
}: {
  icon: any;
  label: string;
  value: string;
  sub?: string;
  accent?: boolean;
}) {
  return (
    <Card className={`border shadow-none ${accent ? "border-emerald-200 bg-emerald-50/50" : "border-slate-100"}`}>
      <CardContent className="px-5 py-4 flex items-start gap-3">
        <div className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 ${accent ? "bg-emerald-100" : "bg-slate-100"
          }`}>
          <Icon className={`w-4.5 h-4.5 ${accent ? "text-emerald-600" : "text-slate-500"}`} />
        </div>
        <div className="min-w-0">
          <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-wide">{label}</p>
          {/*<p className={`text-lg font-black leading-tight mt-0.5 ${accent ? "text-emerald-700" : "text-slate-800"}`}>
            {value}
          </p>*/}
          {/* Gunakan text-base agar sedikit lebih kecil dan whitespace-nowrap agar tidak turun ke bawah*/}
          <p className={`text-base font-black leading-tight mt-0.5 whitespace-nowrap ${accent ? "text-emerald-700" : "text-slate-800"}`}>
            {value}
          </p>

          {sub && <p className="text-[11px] text-slate-400 mt-0.5">{sub}</p>}
        </div>
      </CardContent>
    </Card>
  );
}

// ── Forecast table ────────────────────────────────────────────────────── //
function ForecastTable({ data }: { data: MrrForecastData }) {
  return (
    <Card className="border border-slate-100 shadow-none overflow-hidden">
      <CardHeader className="pb-2 pt-4 px-5">
        <CardTitle className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide">
          Forecast Results — {data.forecast.length} Quarter Ahead
        </CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-y border-slate-100 bg-slate-50/70 text-[11px] text-slate-400 uppercase">
                <th className="px-5 py-2.5 text-left">Period</th>
                <th className="px-4 py-2.5 text-right">Forecast MRR</th>
              </tr>
            </thead>
            <tbody>
              {data.forecast.map((f) => (
                <tr key={f.label} className="border-b border-slate-50 hover:bg-emerald-50/40 transition-colors">
                  <td className="px-5 py-2.5">
                    <div className="flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: COLOR_FORECAST }} />
                      <span className="font-medium text-slate-800 text-xs">{f.label}</span>
                    </div>
                  </td>
                  <td className="px-4 py-2.5 text-right font-bold text-emerald-700 text-xs">
                    {f.value != null ? fmtMRRFull(f.value) : "–"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}

// ── Main page ─────────────────────────────────────────────────────────── //
export default function ForecastPage() {
  const { data, isLoading, error } = useQuery<MrrForecastData>({
    queryKey: ["mrr-forecast"],
    queryFn: () => getMrrForecast(2, 0, 3, 4),
    staleTime: 5 * 60_000,
    retry: 2,
  });

  // ── Loading state ────────────────────────────────────────────────────── //
  if (isLoading) {
    return (
      <div className="space-y-5 max-w-5xl">
        <Skeleton className="h-8 w-72" />
        <div className="grid grid-cols-4 gap-3">
          {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-20 rounded-xl" />)}
        </div>
        <Skeleton className="h-[400px] rounded-xl" />
        <Skeleton className="h-40 rounded-xl" />
      </div>
    );
  }

  // ── Error state ──────────────────────────────────────────────────────── //
  if (error || !data) {
    return (
      <div className="flex items-center gap-3 text-destructive p-6">
        <AlertCircle className="w-5 h-5" />
        <span>Gagal memuat data forecast. Pastikan backend aktif dan data MRR tersedia.</span>
      </div>
    );
  }

  // ── Prepare chart ────────────────────────────────────────────────────── //
  const chartData = buildChartData(data);

  // Find boundary label for the reference line (last actual data point)
  const boundaryLabel = data.actual[data.actual.length - 1]?.label ?? "";

  return (
    <div className="space-y-5">

      {/* ══════════════════════════════════════════════════════════════════
          HEADLINE
      ══════════════════════════════════════════════════════════════════ */}
      <div>
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-emerald-100 flex items-center justify-center">
            <TrendingUp className="w-5 h-5 text-emerald-600" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight">Statistic Analyst</h1>
            <p className="text-xs text-muted-foreground">
              MRR Forecasting · ARIMA ({data.arima_order.join(", ")})
            </p>
          </div>
        </div>
      </div>

      {/* ══════════════════════════════════════════════════════════════════
          STAT CARDS
      ══════════════════════════════════════════════════════════════════ */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard
          icon={Activity}
          label="Model"
          value={`ARIMA (${data.arima_order.join(",")})`}
          sub="Auto-Regressive Integrated Moving Average"
        />
        <StatCard
          icon={Database}
          label="Data Points"
          value={String(data.data_points)}
          sub="Quarterly observations"
        />
        <StatCard
          icon={Target}
          label="MAPE"
          value={`${data.mape.toFixed(2)}%`}
          sub="Mean Absolute Percentage Error"
          accent
        />
        {/*<StatCard
          icon={Hash}
          label="AIC"
          value={data.aic.toLocaleString("id-ID")}
          sub="Akaike Information Criterion"
        />*/}
        <StatCard
          icon={Target}              // Gunakan icon yang sama dengan MAPE
          label="MAE"               // Ubah label
          value={fmtMRRFull(data.mae)} // Gunakan format mata uang (Rp)
          sub="Mean Absolute Error" // Keterangan detail
          accent                     // Tambahkan ini agar tampilan sama (hijau muda) seperti MAPE
        />
      </div>

      {/* ══════════════════════════════════════════════════════════════════
          MAIN CHART — Actual + Fitted + Forecast
      ══════════════════════════════════════════════════════════════════ */}
      <Card className="border border-slate-100 shadow-none">
        <CardHeader className="pb-1 pt-4 px-5">
          <CardTitle className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide">
            MRR Trend & Forecast — ARIMA ({data.arima_order.join(", ")})
          </CardTitle>
        </CardHeader>
        <CardContent className="px-2 pb-4">
          <ResponsiveContainer width="100%" height={420}>
            <LineChart data={chartData} margin={{ top: 12, right: 24, left: 8, bottom: 36 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(220,13%,93%)" vertical={false} />
              <XAxis
                dataKey="label"
                tick={{ fontSize: 9 }}
                angle={-35}
                textAnchor="end"
                height={50}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                tick={{ fontSize: 10 }}
                axisLine={false}
                tickLine={false}
                width={52}
                tickFormatter={fmtMRR}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend
                iconType="circle"
                iconSize={8}
                wrapperStyle={{ fontSize: 11, paddingTop: 8 }}
              />

              {/* Reference line: forecast boundary */}
              <ReferenceLine
                x={boundaryLabel}
                stroke="hsl(220,13%,75%)"
                strokeDasharray="6 4"
                label={{
                  value: "Forecast →",
                  position: "top",
                  fill: "hsl(220,13%,55%)",
                  fontSize: 10,
                }}
              />

              {/* Actual / Original Data */}
              <Line
                dataKey="actual"
                name="Original Data"
                stroke={COLOR_ACTUAL}
                strokeWidth={2.5}
                dot={{ r: 3.5, fill: COLOR_ACTUAL, strokeWidth: 0 }}
                activeDot={{ r: 6 }}
                connectNulls={false}
              />

              {/* Fitted Values */}
              <Line
                dataKey="fitted"
                name="Fitted Values"
                stroke={COLOR_FITTED}
                strokeWidth={2}
                dot={{ r: 3, fill: COLOR_FITTED, strokeWidth: 0 }}
                activeDot={{ r: 5 }}
                connectNulls={false}
              />

              {/* Forecast */}
              <Line
                dataKey="forecast"
                name="Forecast"
                stroke={COLOR_FORECAST}
                strokeWidth={2.5}
                strokeDasharray="6 3"
                dot={{ r: 4, fill: COLOR_FORECAST, strokeWidth: 0 }}
                activeDot={{ r: 6 }}
                connectNulls={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* ══════════════════════════════════════════════════════════════════
          MAPE INSIGHT CARD
      ══════════════════════════════════════════════════════════════════ */}
      <Card className="border-2 border-emerald-200 bg-emerald-50/40 shadow-none">
        <CardContent className="px-5 py-4">
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 rounded-xl bg-emerald-100 flex items-center justify-center shrink-0">
              <BarChart3 className="w-5 h-5 text-emerald-600" />
            </div>
            <div>
              <p className="text-sm font-bold text-emerald-800">Model Evaluation</p>
              <p className="text-xs text-emerald-700/80 mt-1 leading-relaxed">
                Model ARIMA ({data.arima_order.join(", ")}) menghasilkan <strong>MAPE sebesar {data.mape.toFixed(2)}%</strong>,
                yang menunjukkan bahwa rata-rata error prediksi terhadap data aktual
                {data.mape < 5
                  ? " sangat rendah — model memiliki akurasi yang baik."
                  : data.mape < 10
                    ? " cukup rendah — model memiliki akurasi yang acceptable."
                    : " perlu diperhatikan — pertimbangkan tuning parameter atau model lain."
                }
                {" "}Forecast dilakukan untuk <strong>{data.forecast.length} quarter</strong> ke depan
                berdasarkan <strong>{data.data_points} data points</strong> historis.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* ══════════════════════════════════════════════════════════════════
          FORECAST TABLE
      ══════════════════════════════════════════════════════════════════ */}
      <ForecastTable data={data} />
    </div>
  );
}
