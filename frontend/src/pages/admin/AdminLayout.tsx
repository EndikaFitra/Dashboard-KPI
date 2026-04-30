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
      <aside className="w-60 flex flex-col bg-sidebar text-sidebar-foreground shrink-0 border-r border-sidebar-border">
        {/* Brand */}
        <div className="px-5 py-5 border-b border-sidebar-border">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center shadow-sm">
              <BarChart3 className="w-4 h-4 text-primary-foreground" />
            </div>
            <div>
              <p className="text-sm font-bold leading-tight text-sidebar-foreground">KPI Analytics</p>
              <p className="text-[10px] text-sidebar-muted uppercase tracking-widest">Admin Panel</p>
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
                    ? "bg-sidebar-primary text-sidebar-primary-foreground font-medium shadow-sm"
                    : "text-sidebar-foreground/80 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                }`
              }
            >
              <Icon className="w-4 h-4 shrink-0" />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* Footer */}
        <div className="px-3 pb-5 space-y-0.5 border-t border-sidebar-border pt-4">
          <button
            onClick={() => navigate("/")}
            className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-sidebar-foreground/80 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground transition w-full"
          >
            <ArrowLeft className="w-4 h-4" />
            Kembali ke Dashboard
          </button>
          <button
            onClick={handleLogout}
            className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-red-400 hover:bg-red-500/10 hover:text-red-400 transition w-full"
          >
            <LogOut className="w-4 h-4" />
            Logout
          </button>
          <div className="px-3 pt-3 flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-xs font-bold text-primary-foreground uppercase shadow-sm">
              {username.charAt(0)}
            </div>
            <div>
              <p className="text-xs font-medium text-sidebar-foreground">{username}</p>
              <p className="text-[10px] text-sidebar-muted">Administrator</p>
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
