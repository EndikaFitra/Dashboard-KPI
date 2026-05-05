import {
  Wifi, Code, TrendingUp, Users, MessageSquare,
  BarChart2, ChevronDown, ChevronRight, Hash, LineChart as LineChartIcon,
} from "lucide-react";
import { NavLink } from "@/components/NavLink";
import { useLocation, useNavigate } from "react-router-dom";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { adminGetKpi } from "@/api/client";
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

const EVAL_BADGE: Record<string, string> = { M: "M", Q: "Q", H: "H" };

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
  const [open, setOpen] = useState(isActive);

  const { data: kpis = [] } = useQuery({
    queryKey: ["sidebar-kpis", div.id],
    queryFn: () => adminGetKpi(div.id),
    staleTime: 5 * 60_000,
    enabled: open || isActive,
  });

  return (
    <SidebarMenuItem>
      <SidebarMenuButton
        isActive={isActive}
        className="cursor-pointer w-full group"
        onClick={() => { navigate(`/${div.slug}`); setOpen(true); }}
      >
        <div.icon className="w-4 h-4 shrink-0" />
        {!collapsed && (
          <>
            <span className="flex-1 text-left truncate">{div.title}</span>
            <span
              role="button"
              onClick={(e) => { e.stopPropagation(); setOpen((v) => !v); }}
              className="ml-auto p-0.5 rounded hover:bg-sidebar-accent/40 transition-colors opacity-0 group-hover:opacity-100"
            >
              {open
                ? <ChevronDown className="w-3.5 h-3.5 opacity-60" />
                : <ChevronRight className="w-3.5 h-3.5 opacity-60" />}
            </span>
          </>
        )}
      </SidebarMenuButton>

      {/* KPI sub-items */}
      {open && !collapsed && kpis.length > 0 && (
        <ul className="mt-0.5 ml-4 border-l border-sidebar-border pl-2 space-y-0.5">
          {kpis.map((kpi: any) => (
            <li key={kpi.kpi_id}>
              <button
                onClick={() => {
                  const el = document.getElementById(`kpi-${kpi.kpi_id}`);
                  if (el) {
                    el.scrollIntoView({ behavior: "smooth", block: "start" });
                  } else {
                    // navigate first, then scroll
                    navigate(`/${div.slug}`);
                    setTimeout(() => {
                      document.getElementById(`kpi-${kpi.kpi_id}`)?.scrollIntoView({ behavior: "smooth", block: "start" });
                    }, 400);
                  }
                }}
                className="w-full flex items-start gap-1.5 px-2 py-1 rounded-md text-left text-[11px] text-sidebar-foreground/70 hover:text-sidebar-foreground hover:bg-sidebar-accent/50 transition-colors"
              >
                <Hash className="w-3 h-3 mt-0.5 shrink-0 opacity-40" />
                <span className="flex-1 truncate leading-tight">{kpi.kpi_name}</span>
                <span className="shrink-0 text-[9px] font-bold bg-sidebar-accent/60 rounded px-1 py-0.5">
                  {EVAL_BADGE[kpi.evaluation_period] ?? kpi.evaluation_period}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
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
