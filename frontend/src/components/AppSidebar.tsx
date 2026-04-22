import { BarChart2, Wifi, Code, TrendingUp, Users, MessageSquare } from "lucide-react";
import { NavLink } from "@/components/NavLink";
import { useLocation } from "react-router-dom";
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  useSidebar,
} from "@/components/ui/sidebar";

const mainItems = [
  { title: "Overview",   url: "/",     icon: BarChart2 },       // berbeda dari logo
  { title: "AI Analyst", url: "/chat", icon: MessageSquare },
];

const divisionItems = [
  { title: "Network",           url: "/network",          icon: Wifi },
  { title: "Software Engineer", url: "/software-engineer", icon: Code },
  { title: "Sales Executive",   url: "/sales-executive",  icon: TrendingUp },
  { title: "HR Officer",        url: "/hr-officer",       icon: Users },
];

function NavGroup({
  items,
  label,
  collapsed,
  location,
}: {
  items: typeof mainItems;
  label: string;
  collapsed: boolean;
  location: ReturnType<typeof useLocation>;
}) {
  return (
    <SidebarGroup>
      {/* Hilangkan label sepenuhnya saat collapsed agar tidak mengambil ruang */}
      {!collapsed && (
        <SidebarGroupLabel className="text-sidebar-foreground/40 text-[10px] uppercase tracking-widest font-semibold">
          {label}
        </SidebarGroupLabel>
      )}
      <SidebarGroupContent>
        <SidebarMenu>
          {items.map((item) => (
            <SidebarMenuItem key={item.title}>
              <SidebarMenuButton asChild isActive={location.pathname === item.url}>
                <NavLink
                  to={item.url}
                  end
                  className="transition-colors duration-150"
                  activeClassName="bg-sidebar-accent text-sidebar-accent-foreground font-medium"
                >
                  <item.icon className="w-4 h-4 shrink-0" />
                  {!collapsed && <span>{item.title}</span>}
                </NavLink>
              </SidebarMenuButton>
            </SidebarMenuItem>
          ))}
        </SidebarMenu>
      </SidebarGroupContent>
    </SidebarGroup>
  );
}

export function AppSidebar() {
  const { state } = useSidebar();
  const collapsed = state === "collapsed";
  const location = useLocation();

  return (
    <Sidebar collapsible="icon" className="border-r-0">
      <SidebarContent className="pt-6">
        {/* Logo — hanya tampil saat expanded */}
        {!collapsed && (
          <div className="px-4 mb-6">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-sidebar-primary flex items-center justify-center shrink-0">
                <BarChart2 className="w-5 h-5 text-sidebar-primary-foreground" />
              </div>
              <div>
                <h1 className="text-sm font-bold text-sidebar-primary-foreground tracking-tight">KPI Dashboard</h1>
                <p className="text-[11px] text-sidebar-foreground/60">Performance Monitor</p>
              </div>
            </div>
          </div>
        )}

        {/* Main nav */}
        <NavGroup items={mainItems} label="Main" collapsed={collapsed} location={location} />

        {/* Divisions nav */}
        <NavGroup items={divisionItems} label="Divisions" collapsed={collapsed} location={location} />
      </SidebarContent>
    </Sidebar>
  );
}
