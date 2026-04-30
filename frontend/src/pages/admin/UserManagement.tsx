import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  adminGetUsers, adminPostUser, adminPatchUser, adminDeleteUser,
  UserCreatePayload, UserResponse,
} from "@/api/client";
import {
  Users, UserPlus, CheckCircle2, AlertCircle, Loader2,
  ShieldAlert, Shield, ToggleLeft, ToggleRight, Trash2,
} from "lucide-react";

const EMPTY: UserCreatePayload = { username: "", email: "", password: "", role: "user" };

export default function UserManagement() {
  const qc = useQueryClient();
  const [form, setForm] = useState<UserCreatePayload>(EMPTY);
  const [feedback, setFeedback] = useState<{ ok: boolean; text: string } | null>(null);
  const [showForm, setShowForm] = useState(false);

  const { data: users = [], isLoading } = useQuery<UserResponse[]>({
    queryKey: ["admin-users"],
    queryFn: adminGetUsers,
  });

  const createMut = useMutation({
    mutationFn: adminPostUser,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-users"] });
      setForm(EMPTY);
      setShowForm(false);
      setFeedback({ ok: true, text: "User berhasil ditambahkan!" });
    },
    onError: (e: any) =>
      setFeedback({ ok: false, text: e?.response?.data?.detail || "Gagal menambahkan user" }),
  });

  const patchMut = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: { is_active?: boolean; role?: string } }) =>
      adminPatchUser(id, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-users"] }),
    onError: (e: any) => setFeedback({ ok: false, text: e?.response?.data?.detail || "Gagal memperbarui user" }),
  });

  const deleteMut = useMutation({
    mutationFn: adminDeleteUser,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-users"] }),
    onError: (e: any) => setFeedback({ ok: false, text: e?.response?.data?.detail || "Gagal menghapus user" }),
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setFeedback(null);
    createMut.mutate(form);
  }

  return (
    <div className="p-8">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Manajemen User</h1>
          <p className="text-slate-500 text-sm mt-1">Kelola akun dan hak akses pengguna sistem</p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-2 px-4 py-2 bg-primary hover:bg-primary/90 text-primary-foreground text-sm font-medium rounded-lg transition shadow-sm"
        >
          <UserPlus className="w-4 h-4" />
          Tambah User
        </button>
      </div>

      {/* Feedback */}
      {feedback && (
        <div className={`mb-4 px-4 py-3 rounded-lg text-sm flex items-center gap-2 ${feedback.ok ? "bg-emerald-50 text-emerald-700 border border-emerald-200" : "bg-red-50 text-red-700 border border-red-200"
          }`}>
          {feedback.ok ? <CheckCircle2 className="w-4 h-4 shrink-0" /> : <AlertCircle className="w-4 h-4 shrink-0" />}
          {feedback.text}
          <button onClick={() => setFeedback(null)} className="ml-auto text-current opacity-50 hover:opacity-100">✕</button>
        </div>
      )}

      {/* Add User Form */}
      {showForm && (
        <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-6 mb-6">
          <h2 className="font-semibold text-slate-700 mb-4 flex items-center gap-2">
            <UserPlus className="w-4 h-4" /> Tambah User Baru
          </h2>
          <form onSubmit={handleSubmit} className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1.5">Username</label>
              <input required value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })}
                className="w-full px-3 py-2 rounded-lg border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30" />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1.5">Email</label>
              <input type="email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })}
                className="w-full px-3 py-2 rounded-lg border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30" />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1.5">Password</label>
              <input type="password" required minLength={6} value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })}
                className="w-full px-3 py-2 rounded-lg border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30" />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1.5">Role</label>
              <select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}
                className="w-full px-3 py-2 rounded-lg border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30">
                <option value="user">User — Dashboard only</option>
                <option value="admin">Admin — Full access</option>
              </select>
            </div>
            <div className="col-span-full flex gap-3">
              <button type="submit" disabled={createMut.isPending}
                className="px-5 py-2 bg-primary hover:bg-primary/90 text-primary-foreground text-sm font-medium rounded-lg transition flex items-center gap-2 disabled:opacity-60 shadow-sm">
                {createMut.isPending ? <><Loader2 className="w-4 h-4 animate-spin" /> Menyimpan...</> : "Buat User"}
              </button>
              <button type="button" onClick={() => setShowForm(false)}
                className="px-5 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-sm font-medium rounded-lg transition">
                Batal
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Users Table */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-100 overflow-hidden">
        <div className="p-4 border-b border-slate-100 flex items-center gap-2">
          <Users className="w-4 h-4 text-slate-500" />
          <h2 className="font-semibold text-slate-700">Daftar Pengguna ({users.length})</h2>
        </div>

        {isLoading ? (
          <div className="p-8 text-center text-slate-400"><Loader2 className="w-5 h-5 animate-spin inline" /></div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-100 text-slate-500 text-xs uppercase tracking-wide">
                <th className="px-4 py-3 text-left">User</th>
                <th className="px-4 py-3 text-left">Email</th>
                <th className="px-4 py-3 text-center">Role</th>
                <th className="px-4 py-3 text-center">Status</th>
                <th className="px-4 py-3 text-left">Dibuat</th>
                <th className="px-4 py-3 text-center">Aksi</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {users.map((user) => (
                <tr key={user.user_id} className="hover:bg-slate-50 transition">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2.5">
                      <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold uppercase shadow-sm ${user.role === "admin" ? "bg-primary text-primary-foreground" : "bg-slate-400 text-white"}`}>
                        {user.username.charAt(0)}
                      </div>
                      <span className="font-medium text-slate-800">{user.username}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-slate-500">{user.email}</td>
                  <td className="px-4 py-3 text-center">
                    <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium ${user.role === "admin"
                        ? "bg-primary/10 text-primary"
                        : "bg-slate-100 text-slate-600"
                      }`}>
                      {user.role === "admin" ? <ShieldAlert className="w-3 h-3" /> : <Shield className="w-3 h-3" />}
                      {user.role}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <button
                      onClick={() => patchMut.mutate({ id: user.user_id, payload: { is_active: !user.is_active } })}
                      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium transition ${user.is_active
                          ? "text-emerald-600 hover:bg-emerald-50"
                          : "text-slate-400 hover:bg-slate-100"
                        }`}
                    >
                      {user.is_active
                        ? <><ToggleRight className="w-4 h-4" /> Aktif</>
                        : <><ToggleLeft className="w-4 h-4" /> Nonaktif</>}
                    </button>
                  </td>
                  <td className="px-4 py-3 text-slate-400 text-xs">
                    {new Date(user.created_at).toLocaleDateString("id-ID")}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <button
                      onClick={() => { if (confirm(`Hapus user "${user.username}"?`)) deleteMut.mutate(user.user_id); }}
                      className="p-1.5 text-red-400 hover:bg-red-50 rounded-lg transition"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
