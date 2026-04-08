import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { adminRunEtl, adminGetUsers } from "@/api/client";
import {
  Users, Database, PlayCircle, CheckCircle2,
  Loader2, AlertCircle, BarChart3, Settings,
} from "lucide-react";

export default function AdminDashboard() {
  const qc = useQueryClient();
  const [etlYear, setEtlYear] = useState(2025);
  const [etlMsg, setEtlMsg]   = useState<{ ok: boolean; text: string } | null>(null);

  const { data: users } = useQuery({
    queryKey: ["admin-users"],
    queryFn: adminGetUsers,
  });

  const etlMutation = useMutation({
    mutationFn: () => adminRunEtl({ year: etlYear, all_years: false }),
    onSuccess: (data) => {
      setEtlMsg({ ok: true, text: `ETL selesai — ${data.processed ?? 0} rows diproses, ${data.upserted ?? 0} records upserted.` });
      qc.invalidateQueries();
    },
    onError: (err: any) => {
      setEtlMsg({ ok: false, text: err?.response?.data?.detail || "ETL gagal. Cek log server." });
    },
  });

  const stats = [
    { label: "Total Users", value: users?.length ?? "—", icon: Users, color: "bg-blue-500" },
    { label: "ETL Last Run", value: "Manual", icon: Database, color: "bg-indigo-500" },
    { label: "System", value: "Online", icon: BarChart3, color: "bg-emerald-500" },
    { label: "Admin Panel", value: "v1.0", icon: Settings, color: "bg-violet-500" },
  ];

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-800">Admin Dashboard</h1>
        <p className="text-slate-500 text-sm mt-1">Kelola data KPI dan sistem analytics</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {stats.map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="bg-white rounded-xl p-5 shadow-sm border border-slate-100">
            <div className={`w-9 h-9 ${color} rounded-lg flex items-center justify-center mb-3`}>
              <Icon className="w-4.5 h-4.5 text-white" />
            </div>
            <p className="text-2xl font-bold text-slate-800">{value}</p>
            <p className="text-xs text-slate-500 mt-0.5">{label}</p>
          </div>
        ))}
      </div>

      {/* ETL Panel */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-6 max-w-lg">
        <div className="flex items-center gap-3 mb-5">
          <div className="w-9 h-9 bg-emerald-100 rounded-lg flex items-center justify-center">
            <PlayCircle className="w-5 h-5 text-emerald-600" />
          </div>
          <div>
            <h2 className="font-semibold text-slate-800">Run ETL</h2>
            <p className="text-xs text-slate-500">Agregasi data raw ke quarterly</p>
          </div>
        </div>

        <div className="flex gap-3 items-end">
          <div className="flex-1">
            <label className="text-xs font-medium text-slate-600 mb-1.5 block">Tahun</label>
            <input
              type="number"
              value={etlYear}
              onChange={(e) => setEtlYear(Number(e.target.value))}
              className="w-full px-3 py-2 rounded-lg border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
            />
          </div>
          <button
            onClick={() => { setEtlMsg(null); etlMutation.mutate(); }}
            disabled={etlMutation.isPending}
            className="px-5 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-medium disabled:opacity-60 transition flex items-center gap-2"
          >
            {etlMutation.isPending ? (
              <><Loader2 className="w-4 h-4 animate-spin" /> Running...</>
            ) : (
              <><PlayCircle className="w-4 h-4" /> Run ETL</>
            )}
          </button>
        </div>

        {etlMsg && (
          <div className={`mt-4 p-3 rounded-lg text-sm flex items-start gap-2 ${
            etlMsg.ok
              ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
              : "bg-red-50 text-red-700 border border-red-200"
          }`}>
            {etlMsg.ok
              ? <CheckCircle2 className="w-4 h-4 mt-0.5 shrink-0" />
              : <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />}
            {etlMsg.text}
          </div>
        )}
      </div>
    </div>
  );
}
