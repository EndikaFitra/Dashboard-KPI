import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { adminGetKpi, adminPostKpi, adminPutKpi, adminDeleteKpi, KpiPayload } from "@/api/client";
import {
  PlusCircle, Pencil, Trash2, Loader2, CheckCircle2,
  AlertCircle, X, Save,
} from "lucide-react";

const DIVISIONS = [
  { id: 1, name: "Network" },
  { id: 2, name: "Software Engineer" },
  { id: 3, name: "Sales Executive" },
  { id: 4, name: "HR Officer" },
];

const EVAL_PERIODS = [
  { value: "Q", label: "Quarterly (per Kuartal)" },
  { value: "M", label: "Monthly (per Bulan)" },
  { value: "H", label: "Half Year (per Semester)" },
];
const EVAL_PERIOD_LABEL: Record<string, string> = { Q: "Quarterly", M: "Monthly", H: "Half Year" };

const EMPTY: KpiPayload = {
  division_id: 1, kpi_name: "", unit: "",
  default_target: 100, weight: 0,
  evaluation_period: "Q",
};

export default function InsertKpiForm() {
  const qc = useQueryClient();
  const [form, setForm] = useState<KpiPayload>(EMPTY);
  const [editId, setEditId] = useState<number | null>(null);
  const [filterDiv, setFilterDiv] = useState(0);
  const [feedback, setFeedback] = useState<{ ok: boolean; text: string } | null>(null);

  const { data: kpis = [], isLoading } = useQuery({
    queryKey: ["admin-kpi", filterDiv],
    queryFn: () => adminGetKpi(filterDiv || undefined),
  });

  const createMut = useMutation({
    mutationFn: adminPostKpi,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["admin-kpi"] }); setForm(EMPTY); setFeedback({ ok: true, text: "KPI berhasil ditambahkan!" }); },
    onError: (e: any) => setFeedback({ ok: false, text: e?.response?.data?.detail || "Gagal menambahkan KPI" }),
  });

  const updateMut = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: Partial<KpiPayload> }) => adminPutKpi(id, payload),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["admin-kpi"] }); setEditId(null); setFeedback({ ok: true, text: "KPI berhasil diperbarui!" }); },
    onError: (e: any) => setFeedback({ ok: false, text: e?.response?.data?.detail || "Gagal memperbarui KPI" }),
  });

  const deleteMut = useMutation({
    mutationFn: adminDeleteKpi,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["admin-kpi"] }); setFeedback({ ok: true, text: "KPI berhasil dihapus!" }); },
    onError: (e: any) => setFeedback({ ok: false, text: e?.response?.data?.detail || "Gagal menghapus KPI" }),
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setFeedback(null);
    if (editId !== null) {
      updateMut.mutate({ id: editId, payload: form });
    } else {
      createMut.mutate(form);
    }
  }

  function startEdit(kpi: any) {
    setEditId(kpi.kpi_id);
    setForm({
      division_id: kpi.division_id, kpi_name: kpi.kpi_name, unit: kpi.unit,
      default_target: kpi.default_target,
      weight: kpi.weight, evaluation_period: kpi.evaluation_period ?? "Q",
    });
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  const isBusy = createMut.isPending || updateMut.isPending;

  return (
    <div className="p-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-800">Kelola KPI</h1>
        <p className="text-slate-500 text-sm mt-1">Tambah, edit, atau hapus indikator KPI</p>
      </div>

      {/* Form */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-6 mb-6">
        <h2 className="font-semibold text-slate-700 mb-4 flex items-center gap-2">
          {editId ? <Pencil className="w-4 h-4" /> : <PlusCircle className="w-4 h-4" />}
          {editId ? "Edit KPI" : "Tambah KPI Baru"}
        </h2>

        <form onSubmit={handleSubmit} className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {/* Division */}
          <div>
            <label className="label-sm">Divisi</label>
            <select value={form.division_id} onChange={(e) => setForm({ ...form, division_id: +e.target.value })} className="input-field">
              {DIVISIONS.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
            </select>
          </div>

          {/* KPI Name */}
          <div>
            <label className="label-sm">Nama KPI</label>
            <input required value={form.kpi_name} onChange={(e) => setForm({ ...form, kpi_name: e.target.value })} placeholder="e.g. SLA Compliance" className="input-field" />
          </div>

          {/* Unit */}
          <div>
            <label className="label-sm">Unit</label>
            <input required value={form.unit} onChange={(e) => setForm({ ...form, unit: e.target.value })} placeholder="e.g. %, IDR, ticket" className="input-field" />
          </div>


          {/* Default Target */}
          <div>
            <label className="label-sm">Target Default</label>
            <input type="number" step="0.01" required value={form.default_target} onChange={(e) => setForm({ ...form, default_target: +e.target.value })} className="input-field" />
          </div>

          {/* Evaluation Period */}
          <div>
            <label className="label-sm">Periode Evaluasi</label>
            <select value={form.evaluation_period} onChange={(e) => setForm({ ...form, evaluation_period: e.target.value })} className="input-field">
              {EVAL_PERIODS.map((ep) => <option key={ep.value} value={ep.value}>{ep.label}</option>)}
            </select>
          </div>

          {/* Weight */}
          <div>
            <label className="label-sm">Bobot (%) <span className="text-slate-400 font-normal">0–100</span></label>
            <input type="number" step="0.1" min="0" max="100" required value={form.weight} onChange={(e) => setForm({ ...form, weight: +e.target.value })} className="input-field" />
          </div>

          {/* Feedback */}
          {feedback && (
            <div className={`col-span-full px-4 py-3 rounded-lg text-sm flex items-center gap-2 ${feedback.ok ? "bg-emerald-50 text-emerald-700 border border-emerald-200" : "bg-red-50 text-red-700 border border-red-200"}`}>
              {feedback.ok ? <CheckCircle2 className="w-4 h-4 shrink-0" /> : <AlertCircle className="w-4 h-4 shrink-0" />}
              {feedback.text}
            </div>
          )}

          {/* Buttons */}
          <div className="col-span-full flex gap-3">
            <button type="submit" disabled={isBusy} className="btn-primary flex items-center gap-2">
              {isBusy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
              {editId ? "Simpan Perubahan" : "Tambah KPI"}
            </button>
            {editId && (
              <button type="button" onClick={() => { setEditId(null); setForm(EMPTY); }} className="btn-secondary flex items-center gap-2">
                <X className="w-4 h-4" /> Batal
              </button>
            )}
          </div>
        </form>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-100 overflow-hidden">
        <div className="p-4 flex items-center justify-between border-b border-slate-100">
          <h2 className="font-semibold text-slate-700">Daftar KPI</h2>
          <select value={filterDiv} onChange={(e) => setFilterDiv(+e.target.value)} className="input-field w-40 text-xs">
            <option value={0}>Semua Divisi</option>
            {DIVISIONS.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
          </select>
        </div>

        {isLoading ? (
          <div className="p-8 text-center text-slate-400"><Loader2 className="w-5 h-5 animate-spin inline" /></div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-100 text-slate-500 text-xs uppercase tracking-wide">
                <th className="px-4 py-3 text-left">Divisi</th>
                <th className="px-4 py-3 text-left">KPI</th>
                <th className="px-4 py-3 text-left">Unit</th>
                <th className="px-4 py-3 text-center">Periode</th>
                <th className="px-4 py-3 text-right">Target</th>
                <th className="px-4 py-3 text-right">Bobot</th>
                <th className="px-4 py-3 text-center">Aksi</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {kpis.map((kpi: any) => (
                <tr key={kpi.kpi_id} className="hover:bg-slate-50 transition">
                  <td className="px-4 py-3 text-slate-500 text-xs">{DIVISIONS.find((d) => d.id === kpi.division_id)?.name}</td>
                  <td className="px-4 py-3 font-medium text-slate-800">{kpi.kpi_name}</td>
                  <td className="px-4 py-3 text-slate-500">{kpi.unit}</td>
                  <td className="px-4 py-3 text-center">
                    <span className="px-2 py-0.5 bg-blue-50 text-blue-700 rounded text-xs font-medium">
                      {EVAL_PERIOD_LABEL[kpi.evaluation_period] ?? kpi.evaluation_period}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right text-slate-600">{kpi.default_target}</td>
                  <td className="px-4 py-3 text-right text-slate-600">{kpi.weight}%</td>
                  <td className="px-4 py-3 text-center">
                    <div className="flex items-center justify-center gap-2">
                      <button onClick={() => startEdit(kpi)} className="p-1.5 text-blue-500 hover:bg-blue-50 rounded-lg transition"><Pencil className="w-3.5 h-3.5" /></button>
                      <button onClick={() => { if (confirm("Hapus KPI ini?")) deleteMut.mutate(kpi.kpi_id); }} className="p-1.5 text-red-400 hover:bg-red-50 rounded-lg transition"><Trash2 className="w-3.5 h-3.5" /></button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Inline styles helper */}
      <style>{`
        .label-sm { @apply block text-xs font-medium text-slate-600 mb-1.5; }
        .input-field { @apply w-full px-3 py-2 rounded-lg border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300 transition; }
        .btn-primary { @apply px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition disabled:opacity-60; }
        .btn-secondary { @apply px-5 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-sm font-medium rounded-lg transition; }
      `}</style>
    </div>
  );
}
