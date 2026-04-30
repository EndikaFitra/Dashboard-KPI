import { NavLink, Outlet, useNavigate } from "react-router-dom";
import {
  BarChart3, PlusCircle, ClipboardList,
  Users, LogOut, ArrowLeft,
} from "lucide-react";
import { logout, getUsername } from "@/lib/auth";

const NAV = [
  { to: "/admin/kpi",         label: "Kelola KPI",         icon: PlusCircle },
  { to: "/admin/realization", label: "Input Realisasi",    icon: ClipboardList },
  { to: "/admin/users",       label: "Manajemen User",     icon: Users },
];

export default function AdminLayout() {
  const navigate = useNavigate();
  const username = getUsername() ?? "admin";

  function handleLogout() {
    logout();
    navigate("/login", { replace: true });
  }

  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden">
      {/* ─── Sidebar ─────────────────────────────────────────────────── */}
      <aside className="w-60 flex flex-col bg-slate-900 text-white shrink-0">
        {/* Brand */}
        <div className="px-5 py-5 border-b border-white/10">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center">
              <BarChart3 className="w-4 h-4 text-white" />
            </div>
            <div>
              <p className="text-sm font-bold leading-tight">KPI Analytics</p>
              <p className="text-[10px] text-blue-300/70 uppercase tracking-widest">Admin Panel</p>
            </div>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-4 space-y-0.5">
          {NAV.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-150 ${
                  isActive
                    ? "bg-blue-600 text-white font-medium"
                    : "text-slate-300 hover:bg-white/10 hover:text-white"
                }`
              }
            >
              <Icon className="w-4 h-4 shrink-0" />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* Footer */}
        <div className="px-3 pb-5 space-y-0.5 border-t border-white/10 pt-4">
          <button
            onClick={() => navigate("/")}
            className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-slate-300 hover:bg-white/10 hover:text-white transition w-full"
          >
            <ArrowLeft className="w-4 h-4" />
            Kembali ke Dashboard
          </button>
          <button
            onClick={handleLogout}
            className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-red-400 hover:bg-red-500/10 hover:text-red-300 transition w-full"
          >
            <LogOut className="w-4 h-4" />
            Logout
          </button>
          <div className="px-3 pt-3 flex items-center gap-2">
            <div className="w-7 h-7 rounded-full bg-blue-600 flex items-center justify-center text-xs font-bold text-white uppercase">
              {username.charAt(0)}
            </div>
            <div>
              <p className="text-xs font-medium text-white">{username}</p>
              <p className="text-[10px] text-slate-400">Administrator</p>
            </div>
          </div>
        </div>
      </aside>

      {/* ─── Main Content ─────────────────────────────────────────────── */}
      <main className="flex-1 overflow-y-auto">
        <Outlet />
      </main>
    </div>
  );
}
