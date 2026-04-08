import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { AppSidebar } from "@/components/AppSidebar";
import { Outlet, useNavigate } from "react-router-dom";
import { ChatbotWidget } from "@/components/ChatbotWidget";
import { getUsername, getRole, isAdmin, logout } from "@/lib/auth";
import { LogOut, ShieldAlert, User } from "lucide-react";

export function DashboardLayout() {
  const navigate   = useNavigate();
  const username   = getUsername() ?? "User";
  const role       = getRole() ?? "user";
  const adminUser  = isAdmin();

  function handleLogout() {
    logout();
    navigate("/login", { replace: true });
  }

  return (
    <SidebarProvider>
      <div className="min-h-screen flex w-full">
        <AppSidebar />
        <div className="flex-1 flex flex-col min-w-0">
          <header className="h-14 flex items-center border-b bg-card px-4 shrink-0 justify-between">
            <SidebarTrigger className="mr-4" />

            {/* User info + actions */}
            <div className="flex items-center gap-3">
              {adminUser && (
                <button
                  onClick={() => navigate("/admin")}
                  className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-blue-600 bg-blue-50 hover:bg-blue-100 rounded-lg transition"
                >
                  <ShieldAlert className="w-3.5 h-3.5" />
                  Admin Panel
                </button>
              )}

              <div className="flex items-center gap-2 pl-3 border-l border-border">
                <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold text-white uppercase ${adminUser ? "bg-blue-600" : "bg-slate-400"}`}>
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

          <main className="flex-1 overflow-auto p-6">
            <Outlet />
          </main>
        </div>
      </div>
      <ChatbotWidget />
    </SidebarProvider>
  );
}
