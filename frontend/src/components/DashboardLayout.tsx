import { SidebarProvider, SidebarTrigger, SidebarInset } from "@/components/ui/sidebar";
import { AppSidebar } from "@/components/AppSidebar";
import { Outlet, useNavigate } from "react-router-dom";
import { getUsername, getRole, isAdmin, logout } from "@/lib/auth";
import { LogOut, ShieldAlert } from "lucide-react";

export function DashboardLayout() {
  const navigate = useNavigate();
  const username = getUsername() ?? "User";
  const role = getRole() ?? "user";
  const adminUser = isAdmin();

  function handleLogout() {
    logout();
    navigate("/login", { replace: true });
  }

  return (
    <SidebarProvider>
      <AppSidebar />

      {/*
        SidebarInset renders as <main> with flex-1 + auto left-margin transition.
        Do NOT nest another <main> inside — use <div> for the inner wrapper.
      */}
      <SidebarInset>
        {/* Top header bar */}
        <header className="h-14 flex items-center border-b bg-card px-4 shrink-0 justify-between">
          <SidebarTrigger className="mr-4" />

          <div className="flex items-center gap-3">
            {adminUser && (
              <button
                onClick={() => navigate("/admin")}
                className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-primary bg-primary/10 hover:bg-primary/20 rounded-lg transition"
              >
                <ShieldAlert className="w-3.5 h-3.5" />
                Admin Panel
              </button>
            )}

            <div className="flex items-center gap-2 pl-3 border-l border-border">
              <div className={`w-8 h-8 rounded-full bg-primary flex items-center justify-center text-xs font-bold text-primary-foreground uppercase shadow-sm`}>
                {username.charAt(0)}
              </div>
              <div className="hidden sm:block">
                <p className="text-xs font-medium text-foreground leading-tight">{username}</p>
                <p className="text-[10px] text-muted-foreground capitalize">{role}</p>
              </div>
              <button
                onClick={handleLogout}
                title="Logout"
                className="p-1.5 text-muted-foreground hover:text-foreground hover:bg-muted rounded-lg transition"
              >
                <LogOut className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </header>

        {/* Page content */}
        <div className="flex-1 overflow-auto p-4 md:p-6">
          <Outlet />
        </div>
      </SidebarInset>
    </SidebarProvider>
  );
}
