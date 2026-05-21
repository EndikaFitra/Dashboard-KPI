import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import {
  Target,
  BarChart3,
  Activity,
  TrendingUp,
  RefreshCw,
  Info
} from "lucide-react";
import Plot from "react-plotly.js";

import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { getClusterResults, postRecomputeCluster, ClusterResultData } from "@/api/client";

// Template deskripsi (konstanta frontend)
const CLUSTER_DESCRIPTIONS: Record<string, string> = {
  "Peak Revenue & Premium Efficiency": `
 Basis pelanggan baru sedang-rendah, dokumen penawaran (quotation) paling sedikit, tetapi pendapatan bulanan berulang (MRR) mencapai puncak absolutnya (0.8488).
  `.trim(),

  "Core Growth & Stable Acquisition": `
Fase ini menggambarkan kondisi "normal baru" atau kondisi operasional inti yang paling sehat. Proses penawaran berjalan efisien dan terarah, sehingga setiap proposal yang keluar memiliki peluang konversi tinggi menjadi pelanggan baru yang langsung berkontribusi pada pendapatan jangka menengah.
  `.trim(),

  "Stagnant Acquisition & Slow Down": `
Kuartal-kuartal ini mencerminkan periode slowdown (perlambatan ekonomi atau kejenuhan produk). Tim sales tetap mengeluarkan tenaga untuk mengirimkan penawaran, namun pasar merespons dengan sangat pasif, menyebabkan konversi ke pelanggan baru mandek. Periode ini biasanya digunakan internal untuk evaluasi produk atau perubahan strategi.
  `.trim(),

  "Low-Yield Operational": `
Fase ini adalah potret nyata dari pasar yang sangat kompetitif (red ocean market). Tim sales harus bekerja ekstra keras mengikuti banyak proses bidding atau tender formal (menguras banyak resource menerbitkan quotation), namun imbal hasil keuangannya relatif rendah karena marjin yang tertekan oleh perang harga atau banyak memenangkan akun berskala kecil.
  `.trim(),

  "Hyper-Acquisition & Market Penetration": `
Kuartal-kuartal ini mencerminkan strategi growth hacking atau penetrasi pasar agresif (misal: peluncuran produk baru, promo diskon besar-besaran, atau skema gratis biaya awal). Secara kuantitas transaksi dan volume pelanggan baru, penjualan meledak luar biasa, meskipun efek monetisasinya (MRR) baru akan dipanen secara bertahap di masa depan.
  `.trim(),
};

const getBadgeColor = (name: string) => {
  if (name.includes("Peak")) return "bg-amber-100 text-amber-700 border-amber-200";
  if (name.includes("Core")) return "bg-blue-100 text-blue-700 border-blue-200";
  if (name.includes("Stagnant")) return "bg-slate-100 text-slate-700 border-slate-200";
  if (name.includes("Low-Yield")) return "bg-red-100 text-red-700 border-red-200";
  if (name.includes("Hyper")) return "bg-emerald-100 text-emerald-700 border-emerald-200";
  return "bg-gray-100 text-gray-700 border-gray-200";
};

const getPlotlyColor = (name: string) => {
  if (name.includes("Peak")) return "rgb(245, 158, 11)"; // amber-500
  if (name.includes("Core")) return "rgb(59, 130, 246)"; // blue-500
  if (name.includes("Stagnant")) return "rgb(100, 116, 139)"; // slate-500
  if (name.includes("Low-Yield")) return "rgb(239, 68, 68)"; // red-500
  if (name.includes("Hyper")) return "rgb(16, 185, 129)"; // emerald-500
  return "rgb(156, 163, 175)"; // gray-400
};

export default function ClusterPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data, isLoading, error, isRefetching } = useQuery<ClusterResultData>({
    queryKey: ["cluster-results"],
    queryFn: () => getClusterResults(),
    staleTime: 5 * 60_000,
    retry: 2,
  });

  const recompute = useMutation({
    mutationFn: postRecomputeCluster,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cluster-results"] });
    },
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-6 h-6 animate-spin text-primary" />
        <span className="ml-2 text-muted-foreground">Loading clustering data...</span>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-6 bg-red-50 text-red-600 rounded-lg">
        Terjadi kesalahan saat memuat data clustering. Pastikan data Sales (MRR, Customer Baru, Quotation) tersedia.
      </div>
    );
  }

  // Siapkan data plot 3D per cluster
  const clusterNames = Array.from(new Set(data.scatter_3d.map(d => d.cluster_name)));

  const plotData = clusterNames.map(name => {
    const points = data.scatter_3d.filter(p => p.cluster_name === name);
    return {
      type: "scatter3d" as const,
      mode: "markers" as const,
      name: name,
      x: points.map(p => p.customer_baru_norm),
      y: points.map(p => p.quotation_norm),
      z: points.map(p => p.mrr_norm),
      marker: {
        size: 6,
        color: getPlotlyColor(name),
        opacity: 0.8,
        line: { width: 1, color: 'white' }
      },
    };
  });

  return (
    <div className="max-w-[1400px] mx-auto space-y-6 pb-12">
      {/* ── Headline & Navigation ── */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center shrink-0">
            <TrendingUp className="w-5 h-5 text-primary" />
          </div>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold tracking-tight">Statistic Analyst</h1>
              <Select
                defaultValue="cluster"
                onValueChange={(v) => {
                  if (v === "forecast") navigate("/forecast");
                }}
              >
                <SelectTrigger className="w-[200px] h-8 text-sm bg-accent/50 border-0 font-medium">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="cluster">Cluster Analysis</SelectItem>
                  <SelectItem value="forecast">MRR Forecast</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <p className="text-sm text-muted-foreground mt-1">
              Segmentasi fase sales menggunakan Agglomerative Hierarchical Clustering
            </p>
          </div>
        </div>

        <Button
          variant="outline"
          size="sm"
          onClick={() => recompute.mutate()}
          disabled={recompute.isPending || isRefetching}
          className="gap-2"
        >
          <RefreshCw className={`w-4 h-4 ${(recompute.isPending || isRefetching) ? "animate-spin" : ""}`} />
          Re-compute Cluster
        </Button>
      </div>

      {/* ── Evaluation Cards ── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="p-5 flex flex-col justify-center border-border/60 shadow-sm">
          <div className="flex items-center justify-between text-muted-foreground mb-3">
            <h3 className="text-sm font-medium">Silhouette Score</h3>
            <Target className="w-4 h-4 text-primary" />
          </div>
          <div className="text-2xl font-bold">{data.evaluation.silhouette_score.toFixed(4)}</div>
          <p className="text-xs text-muted-foreground mt-1">Kualitas pemisahan antar cluster</p>
        </Card>

        <Card className="p-5 flex flex-col justify-center border-border/60 shadow-sm">
          <div className="flex items-center justify-between text-muted-foreground mb-3">
            <h3 className="text-sm font-medium">BSS/TSS Ratio</h3>
            <BarChart3 className="w-4 h-4 text-emerald-500" />
          </div>
          <div className="text-2xl font-bold">{(data.evaluation.bss_tss_ratio * 100).toFixed(2)}%</div>
          <p className="text-xs text-muted-foreground mt-1">Proporsi varians yang dijelaskan</p>
        </Card>

        <Card className="p-5 flex flex-col justify-center border-border/60 shadow-sm">
          <div className="flex items-center justify-between text-muted-foreground mb-3">
            <h3 className="text-sm font-medium">Cophenetic Correlation</h3>
            <Activity className="w-4 h-4 text-amber-500" />
          </div>
          <div className="text-2xl font-bold">{data.evaluation.cophenetic_corr.toFixed(4)}</div>
          <p className="text-xs text-muted-foreground mt-1">Validitas struktur hierarki dendrogram</p>
        </Card>
      </div>

      {/* ── Data Table & 3D Plot ── */}
      <div className="flex flex-col gap-6">

        {/* Table */}
        <Card className="flex flex-col shadow-sm border-border/60 overflow-hidden">
          <div className="p-5 border-b border-border/50 bg-muted/20">
            <h3 className="font-semibold">Clustering Data Result</h3>
            <p className="text-xs text-muted-foreground mt-0.5">
              Tabel data asli sebelum dinormalisasi. Menampilkan {data.data_table.length} baris observasi.
            </p>
          </div>

          <div className="flex-1 overflow-auto max-h-[260px]">
            <table className="w-full text-sm text-left">
              <thead className="text-xs text-muted-foreground uppercase bg-muted/40 sticky top-0 z-10">
                <tr>
                  <th className="px-4 py-3 font-medium">Customer Baru</th>
                  <th className="px-4 py-3 font-medium">Quotation</th>
                  <th className="px-4 py-3 font-medium">MRR</th>
                  <th className="px-4 py-3 font-medium">Cluster</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/50">
                {data.data_table.map((row, idx) => (
                  <tr key={idx} className="hover:bg-muted/20 transition-colors">
                    <td className="px-4 py-3">{row.customer_baru}</td>
                    <td className="px-4 py-3">{row.quotation}</td>
                    <td className="px-4 py-3 font-mono">
                      Rp {row.mrr.toLocaleString('id-ID')}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${getBadgeColor(row.cluster_name)}`}>
                        {row.cluster_name}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>

        {/* 3D Plot */}
        <Card className="flex flex-col shadow-sm border-border/60">
          <div className="p-5 border-b border-border/50 bg-muted/20">
            <h3 className="font-semibold">3D Scatter Visualization</h3>
            <p className="text-xs text-muted-foreground mt-0.5">
              Visualisasi distribusi menggunakan data ternormalisasi (MinMaxScaler). Drag untuk merotasi.
            </p>
          </div>
          <div className="flex-1 p-2 bg-slate-50 dark:bg-slate-900/50 h-[350px]">
            <Plot
              data={plotData}
              layout={{
                autosize: true,
                margin: { l: 0, r: 0, b: 0, t: 0 },
                paper_bgcolor: 'transparent',
                plot_bgcolor: 'transparent',
                scene: {
                  xaxis: { title: 'Cust. Baru', gridcolor: '#e2e8f0', zerolinecolor: '#cbd5e1' },
                  yaxis: { title: 'Quotation', gridcolor: '#e2e8f0', zerolinecolor: '#cbd5e1' },
                  zaxis: { title: 'MRR', gridcolor: '#e2e8f0', zerolinecolor: '#cbd5e1' },
                  camera: { eye: { x: 1.5, y: 1.5, z: 1.2 } }
                },
                showlegend: true,
                legend: { x: 0, y: 1, bgcolor: 'rgba(255,255,255,0.7)' },
              }}
              config={{
                displayModeBar: true,
                scrollZoom: true,
                responsive: true,
              }}
              useResizeHandler={true}
              style={{ width: '100%', height: '100%' }}
            />
          </div>
        </Card>
      </div>

      {/* ── Cluster Descriptions ── */}
      <h3 className="text-lg font-semibold mt-10 mb-4">Interpretasi Cluster</h3>
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
        {Object.keys(CLUSTER_DESCRIPTIONS).map((name) => (
          <Card key={name} className="overflow-hidden shadow-sm border-border/60">
            <div className={`px-5 py-3 border-b ${getBadgeColor(name).replace('text-', 'text-').replace('bg-', 'bg-').split(' ')[0]}`}>
              <div className="flex items-center gap-2">
                <Info className={`w-4 h-4 ${getBadgeColor(name).split(' ')[1]}`} />
                <h4 className={`font-semibold text-sm ${getBadgeColor(name).split(' ')[1]}`}>{name}</h4>
              </div>
            </div>
            <div className="p-5 text-sm text-muted-foreground whitespace-pre-wrap leading-relaxed text-justify">
              {CLUSTER_DESCRIPTIONS[name] || data.cluster_descriptions[name] || "Tidak ada deskripsi."}
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
