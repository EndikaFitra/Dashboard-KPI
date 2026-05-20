import {
  Wifi, Code, TrendingUp, Users, MessageSquare,
  BarChart2, LineChart as LineChartIcon,
} from "lucide-react";
import { NavLink } from "@/components/NavLink";
import { useLocation, useNavigate } from "react-router-dom";
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

const DIVISIONS = [
  { id: 1, slug: "network",           title: "Network",           icon: Wifi },
  { id: 2, slug: "software-engineer", title: "Software Engineer", icon: Code },
  { id: 3, slug: "sales-executive",   title: "Sales Executive",   icon: TrendingUp },
  { id: 4, slug: "hr-officer",        title: "HR Officer",        icon: Users },
];

function DivisionNavItem({
  div,
  collapsed,
  isActive,
}: {
  div: typeof DIVISIONS[0];
  collapsed: boolean;
  isActive: boolean;
}) {
  const navigate = useNavigate();

  return (
    <SidebarMenuItem>
      <SidebarMenuButton
        isActive={isActive}
        className="cursor-pointer w-full"
        onClick={() => navigate(`/${div.slug}`)}
      >
        <div.icon className="w-4 h-4 shrink-0" />
        {!collapsed && (
          <span className="flex-1 text-left truncate">{div.title}</span>
        )}
      </SidebarMenuButton>
    </SidebarMenuItem>
  );
}

export function AppSidebar() {
  const { state } = useSidebar();
  const collapsed = state === "collapsed";
  const location = useLocation();

  return (
    <Sidebar collapsible="icon" className="border-r-0">
      <SidebarContent className="pt-6">
        {/* Logo */}
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

        {/* Divisions */}
        <SidebarGroup>
          {!collapsed && (
            <SidebarGroupLabel className="text-sidebar-foreground/40 text-[10px] uppercase tracking-widest font-semibold">
              Divisions
            </SidebarGroupLabel>
          )}
          <SidebarGroupContent>
            <SidebarMenu>
              {DIVISIONS.map((div) => (
                <DivisionNavItem
                  key={div.id}
                  div={div}
                  collapsed={collapsed}
                  isActive={location.pathname === `/${div.slug}`}
                />
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        {/* Tools */}
        <SidebarGroup>
          {!collapsed && (
            <SidebarGroupLabel className="text-sidebar-foreground/40 text-[10px] uppercase tracking-widest font-semibold">
              Tools
            </SidebarGroupLabel>
          )}
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton asChild isActive={location.pathname === "/chat"}>
                  <NavLink to="/chat" className="transition-colors" activeClassName="bg-sidebar-accent text-sidebar-accent-foreground font-medium">
                    <MessageSquare className="w-4 h-4 shrink-0" />
                    {!collapsed && <span>AI Analyst</span>}
                  </NavLink>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton asChild isActive={location.pathname === "/forecast"}>
                  <NavLink to="/forecast" className="transition-colors" activeClassName="bg-sidebar-accent text-sidebar-accent-foreground font-medium">
                    <LineChartIcon className="w-4 h-4 shrink-0" />
                    {!collapsed && <span>Statistic Analyst</span>}
                  </NavLink>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
    </Sidebar>
  );
}
