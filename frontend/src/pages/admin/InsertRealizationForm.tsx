import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  adminGetDivisions, adminGetKpi, adminGetPeriods, adminGetRealizations,
  adminPostRealization, adminPutRealization,
  DivisionMeta, PeriodMeta, RealizationRecord, RealizationPayload,
} from "@/api/client";
import {
  ClipboardList, Save, CheckCircle2, AlertCircle, Loader2,
  Pencil, X, PlusCircle, TrendingUp, TrendingDown, Minus,
} from "lucide-react";

const EMPTY: RealizationPayload = {
  division_id: 0, kpi_id: 0, period_id: 0,
  year: new Date().getFullYear(), target: 0, realization: 0,
};

export default function InsertRealizationForm() {
  const qc = useQueryClient();
  const [form, setForm]           = useState<RealizationPayload>(EMPTY);
  const [editId, setEditId]       = useState<number | null>(null);
  const [feedback, setFeedback]   = useState<{ ok: boolean; text: string } | null>(null);
  const [filterYear, setFilterYear] = useState(new Date().getFullYear());

  // ── Reference data from API ──────────────────────────────────────────── //
  const { data: divisions = [] } = useQuery<DivisionMeta[]>({
    queryKey: ["admin-meta-divisions"],
    queryFn: adminGetDivisions,
  });

  const selectedDiv = divisions.find((d) => d.id === form.division_id) as DivisionMeta | undefined
    ?? divisions.find((d) => d.division_id === form.division_id);

  const { data: kpis = [] } = useQuery({
    queryKey: ["admin-kpi", form.division_id],
    queryFn: () => adminGetKpi(form.division_id),
    enabled: form.division_id > 0,
  });

  const { data: periods = [] } = useQuery<PeriodMeta[]>({
    queryKey: ["admin-meta-periods", selectedDiv?.evaluation_period],
    queryFn: () => adminGetPeriods(selectedDiv?.evaluation_period),
    enabled: !!selectedDiv,
  });

  // ── Existing data table ──────────────────────────────────────────────── //
  const { data: realizations = [], isLoading: loadingTable } = useQuery<RealizationRecord[]>({
    queryKey: ["admin-realizations", form.division_id, filterYear],
    queryFn: () => adminGetRealizations({
      division_id: form.division_id || undefined,
      year: filterYear,
    }),
    enabled: form.division_id > 0,
  });

  // Auto-select first division on load
  useEffect(() => {
    if (divisions.length > 0 && form.division_id === 0) {
      setForm((f) => ({ ...f, division_id: divisions[0].division_id }));
    }
  }, [divisions]);

  // ── Mutations ──────────────────────────────────────────────────────────── //
  const createMut = useMutation({
    mutationFn: adminPostRealization,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-realizations"] });
      setFeedback({ ok: true, text: "Data realisasi berhasil disimpan!" });
      setForm((f) => ({ ...f, kpi_id: 0, period_id: 0, target: 0, realization: 0 }));
    },
    onError: (e: any) =>
      setFeedback({ ok: false, text: e?.response?.data?.detail || "Gagal menyimpan data" }),
  });

  const updateMut = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: { target?: number; realization?: number } }) =>
      adminPutRealization(id, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-realizations"] });
      setFeedback({ ok: true, text: "Data realisasi berhasil diperbarui!" });
      setEditId(null);
    },
    onError: (e: any) =>
      setFeedback({ ok: false, text: e?.response?.data?.detail || "Gagal memperbarui data" }),
  });

  function handleDivisionChange(divId: number) {
    setForm({ ...EMPTY, division_id: divId, year: filterYear });
    setEditId(null);
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setFeedback(null);
    if (!form.kpi_id || !form.period_id) {
      setFeedback({ ok: false, text: "Pilih KPI dan Periode terlebih dahulu" });
      return;
    }
    if (editId !== null) {
      updateMut.mutate({ id: editId, payload: { target: form.target, realization: form.realization } });
    } else {
      createMut.mutate(form);
    }
  }

  function startEdit(row: RealizationRecord) {
    setEditId(row.fact_id);
    setForm({
      division_id: row.division_id,
      kpi_id: row.kpi_id,
      period_id: row.period_id,
      year: row.year,
      target: row.target,
      realization: row.realization,
    });
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function cancelEdit() {
    setEditId(null);
    setForm((f) => ({ ...EMPTY, division_id: f.division_id, year: filterYear }));
  }

  const achievement = form.target > 0
    ? ((form.realization / form.target) * 100)
    : null;

  const isBusy = createMut.isPending || updateMut.isPending;

  const inputCls = "w-full px-3 py-2 rounded-lg border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300 transition bg-white";

  return (
    <div className="p-8 max-w-6xl space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Input & Update Realisasi KPI</h1>
        <p className="text-slate-500 text-sm mt-1">
          Masukkan target dan realisasi KPI per periode, kemudian Run ETL agar dashboard terupdate.
        </p>
      </div>

      {/* Workflow info */}
      <div className="bg-blue-50 border border-blue-200 rounded-xl px-5 py-4 text-blue-800 text-sm">
        <p className="font-semibold mb-1">📋 Alur Menambah/Update Data Indikator:</p>
        <ol className="list-decimal list-inside space-y-1 text-blue-700">
          <li>Pilih <strong>Divisi</strong> → pilih <strong>KPI</strong> → pilih <strong>Periode</strong></li>
          <li>Masukkan <strong>Target</strong> dan <strong>Realisasi</strong> → klik <strong>Simpan</strong></li>
          <li>Untuk <em>update</em> data yang ada: klik ✏️ di tabel bawah</li>
          <li>Setelah selesai input: buka <strong>Admin Dashboard</strong> → <strong>Run ETL</strong></li>
        </ol>
      </div>

      {/* Form Card */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-6">
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center gap-3">
            <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${editId ? "bg-amber-100" : "bg-indigo-100"}`}>
              {editId ? <Pencil className="w-5 h-5 text-amber-600" /> : <PlusCircle className="w-5 h-5 text-indigo-600" />}
            </div>
            <div>
              <h2 className="font-semibold text-slate-700">
                {editId ? `Edit Record #${editId}` : "Tambah Data Baru"}
              </h2>
              <p className="text-xs text-slate-400">{editId ? "Ubah target atau realisasi" : "Isi semua field lalu simpan"}</p>
            </div>
          </div>
          {editId && (
            <button onClick={cancelEdit} className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-lg transition">
              <X className="w-3.5 h-3.5" /> Batal Edit
            </button>
          )}
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {/* Division */}
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1.5">Divisi</label>
              <select
                value={form.division_id}
                onChange={(e) => handleDivisionChange(+e.target.value)}
                className={inputCls}
                disabled={!!editId}
              >
                <option value={0}>-- Pilih Divisi --</option>
                {divisions.map((d) => (
                  <option key={d.division_id} value={d.division_id}>{d.division_name}</option>
                ))}
              </select>
            </div>

            {/* KPI */}
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1.5">KPI</label>
              <select
                value={form.kpi_id}
                onChange={(e) => setForm({ ...form, kpi_id: +e.target.value })}
                className={inputCls}
                required
                disabled={!!editId || form.division_id === 0}
              >
                <option value={0}>-- Pilih KPI --</option>
                {kpis.map((k: any) => (
                  <option key={k.kpi_id} value={k.kpi_id}>{k.kpi_name} ({k.unit})</option>
                ))}
              </select>
            </div>

            {/* Year */}
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1.5">Tahun</label>
              <input
                type="number"
                value={form.year}
                onChange={(e) => setForm({ ...form, year: +e.target.value })}
                className={inputCls}
                required
                disabled={!!editId}
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {/* Period */}
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1.5">
                Periode
                {selectedDiv && (
                  <span className="ml-1.5 text-blue-500 font-normal">
                    ({selectedDiv.evaluation_period === "M" ? "Bulanan" : selectedDiv.evaluation_period === "Q" ? "Kuartalan" : "Semester"})
                  </span>
                )}
              </label>
              <select
                value={form.period_id}
                onChange={(e) => setForm({ ...form, period_id: +e.target.value })}
                className={inputCls}
                required
                disabled={!!editId || !selectedDiv}
              >
                <option value={0}>-- Pilih Periode --</option>
                {periods.map((p) => (
                  <option key={p.period_id} value={p.period_id}>{p.period_name}</option>
                ))}
              </select>
            </div>

            {/* Target */}
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1.5">Target</label>
              <input
                type="number" step="0.01" required
                value={form.target || ""}
                onChange={(e) => setForm({ ...form, target: +e.target.value })}
                placeholder="0"
                className={inputCls}
              />
            </div>

            {/* Realization */}
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1.5">Realisasi</label>
              <input
                type="number" step="0.01" required
                value={form.realization || ""}
                onChange={(e) => setForm({ ...form, realization: +e.target.value })}
                placeholder="0"
                className={inputCls}
              />
            </div>
          </div>

          {/* Achievement Preview */}
          {achievement !== null && (
            <div className={`flex items-center justify-between px-4 py-3 rounded-lg border ${
              achievement >= 100 ? "bg-emerald-50 border-emerald-200" :
              achievement >= 80  ? "bg-amber-50 border-amber-200" : "bg-red-50 border-red-200"
            }`}>
              <span className="text-xs text-slate-500 flex items-center gap-1.5">
                {achievement >= 100 ? <TrendingUp className="w-4 h-4 text-emerald-500" /> :
                 achievement >= 80  ? <Minus className="w-4 h-4 text-amber-500" /> :
                 <TrendingDown className="w-4 h-4 text-red-500" />}
                Preview Achievement
              </span>
              <span className={`font-bold text-sm ${
                achievement >= 100 ? "text-emerald-700" :
                achievement >= 80  ? "text-amber-700" : "text-red-700"
              }`}>
                {achievement.toFixed(1)}%
              </span>
            </div>
          )}

          {/* Feedback */}
          {feedback && (
            <div className={`px-4 py-3 rounded-lg text-sm flex items-center gap-2 ${
              feedback.ok ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                          : "bg-red-50 text-red-700 border border-red-200"
            }`}>
              {feedback.ok ? <CheckCircle2 className="w-4 h-4 shrink-0" /> : <AlertCircle className="w-4 h-4 shrink-0" />}
              {feedback.text}
            </div>
          )}

          <button
            type="submit"
            disabled={isBusy || form.division_id === 0}
            className={`px-6 py-2.5 text-white text-sm font-medium rounded-lg transition flex items-center gap-2 disabled:opacity-60 ${
              editId ? "bg-amber-600 hover:bg-amber-700" : "bg-indigo-600 hover:bg-indigo-700"
            }`}
          >
            {isBusy
              ? <><Loader2 className="w-4 h-4 animate-spin" /> Menyimpan...</>
              : <><Save className="w-4 h-4" /> {editId ? "Simpan Perubahan" : "Simpan Data"}</>}
          </button>
        </form>
      </div>

      {/* Existing Data Table */}
      {form.division_id > 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-slate-100 overflow-hidden">
          <div className="p-4 border-b border-slate-100 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <ClipboardList className="w-4 h-4 text-slate-500" />
              <h2 className="font-semibold text-slate-700">
                Data Realisasi — {divisions.find((d) => d.division_id === form.division_id)?.division_name}
              </h2>
            </div>
            <div className="flex items-center gap-2">
              <label className="text-xs text-slate-500">Tahun:</label>
              <input
                type="number"
                value={filterYear}
                onChange={(e) => setFilterYear(+e.target.value)}
                className="w-24 px-2 py-1.5 border border-slate-200 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-blue-300"
              />
            </div>
          </div>

          {loadingTable ? (
            <div className="p-8 text-center text-slate-400"><Loader2 className="w-5 h-5 animate-spin inline" /></div>
          ) : realizations.length === 0 ? (
            <div className="p-8 text-center text-slate-400 text-sm">
              Belum ada data realisasi untuk divisi dan tahun ini.
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-100 text-slate-500 text-xs uppercase tracking-wide">
                  <th className="px-4 py-3 text-left">KPI</th>
                  <th className="px-4 py-3 text-center">Periode</th>
                  <th className="px-4 py-3 text-center">Tahun</th>
                  <th className="px-4 py-3 text-right">Target</th>
                  <th className="px-4 py-3 text-right">Realisasi</th>
                  <th className="px-4 py-3 text-right">Achievement</th>
                  <th className="px-4 py-3 text-center">Edit</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {realizations.map((row) => (
                  <tr key={row.fact_id} className={`hover:bg-slate-50 transition ${editId === row.fact_id ? "bg-amber-50" : ""}`}>
                    <td className="px-4 py-3 font-medium text-slate-800 max-w-[180px] truncate">{row.kpi_name}</td>
                    <td className="px-4 py-3 text-center">
                      <span className="px-2 py-0.5 bg-slate-100 rounded text-xs text-slate-600">{row.period_name}</span>
                    </td>
                    <td className="px-4 py-3 text-center text-slate-600">{row.year}</td>
                    <td className="px-4 py-3 text-right text-slate-600">{row.target.toLocaleString("id-ID")}</td>
                    <td className="px-4 py-3 text-right text-slate-600">{row.realization.toLocaleString("id-ID")}</td>
                    <td className="px-4 py-3 text-right">
                      <span className={`font-semibold ${
                        row.achievement >= 100 ? "text-emerald-600" :
                        row.achievement >= 80  ? "text-amber-600" : "text-red-500"
                      }`}>
                        {row.achievement}%
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <button
                        onClick={() => startEdit(row)}
                        className="p-1.5 text-amber-500 hover:bg-amber-50 rounded-lg transition"
                        title="Edit record ini"
                      >
                        <Pencil className="w-3.5 h-3.5" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}
