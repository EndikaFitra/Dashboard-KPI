import { Card } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend } from "recharts";
import { TrendingUp, Target, CheckCircle2, Award, AlertCircle } from "lucide-react";
import { useOverview } from "@/hooks/useKpiData";

const COLORS = ["hsl(220 70% 45%)", "hsl(152 60% 42%)", "hsl(38 92% 50%)", "hsl(0 72% 51%)"];

const STATUS_BADGE: Record<string, string> = {
  green:  "bg-kpi-achieved-bg text-kpi-achieved border-0",
  yellow: "bg-kpi-warning-bg text-kpi-warning border-0",
  red:    "bg-kpi-danger-bg text-kpi-danger border-0",
};
const STATUS_LABEL: Record<string, string> = {
  green:  "On Target",
  yellow: "Near Target",
  red:    "Below Target",
};

function LoadingSkeleton() {
  return (
    <div className="space-y-6 max-w-7xl">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-20 rounded-xl" />)}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Skeleton className="h-72 rounded-xl" />
        <Skeleton className="h-72 rounded-xl" />
      </div>
      <Skeleton className="h-48 rounded-xl" />
    </div>
  );
}

export default function Overview() {
  const { data, isLoading, error } = useOverview(2025);

  if (isLoading) return <LoadingSkeleton />;

  if (error || !data) {
    return (
      <div className="flex items-center gap-3 text-destructive p-6">
        <AlertCircle className="w-5 h-5" />
        <span>Failed to load overview data. Make sure the backend is running on port 8000.</span>
      </div>
    );
  }

  const barData = data.divisions.map((d) => ({ name: d.division_name.split(" ")[0], Score: d.avg_achievement }));
  const donutData = [
    { name: "On Target",   value: data.achieved_kpis },
    { name: "Near Target", value: data.warning_kpis },
    { name: "Below Target",value: data.danger_kpis },
  ];

  const summaryCards = [
    { label: "Company Average", value: `${data.company_avg.toFixed(1)}%`, icon: TrendingUp, accent: "text-primary bg-accent" },
    { label: "Total KPIs",      value: data.total_kpis,                   icon: Target,     accent: "text-primary bg-accent" },
    { label: "On Target",       value: data.achieved_kpis,                icon: CheckCircle2,accent: "text-kpi-achieved bg-kpi-achieved-bg" },
    { label: "Divisions",       value: data.divisions.length,             icon: Award,      accent: "text-primary bg-accent" },
  ];

  const sorted = [...data.divisions].sort((a, b) => b.avg_achievement - a.avg_achievement);

  return (
    <div className="space-y-6 max-w-7xl">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Overview Dashboard</h1>
        <p className="text-sm text-muted-foreground mt-1">Company-wide KPI performance monitoring · {data.year}</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {summaryCards.map((c) => (
          <Card key={c.label} className="p-4 flex items-center gap-3 shadow-sm border-0 shadow-foreground/5">
            <div className={`w-10 h-10 rounded-lg flex items-center justify-center shrink-0 ${c.accent}`}>
              <c.icon className="w-5 h-5" />
            </div>
            <div>
              <p className="text-xs text-muted-foreground font-medium">{c.label}</p>
              <p className="text-xl font-bold tracking-tight">{c.value}</p>
            </div>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card className="p-5 shadow-sm border-0 shadow-foreground/5">
          <h3 className="text-sm font-semibold mb-4">Division Performance Comparison</h3>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={barData}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(220 13% 91%)" />
              <XAxis dataKey="name" tick={{ fontSize: 12 }} />
              <YAxis domain={[0, 120]} tick={{ fontSize: 11 }} />
              <Tooltip contentStyle={{ borderRadius: "8px", border: "none", boxShadow: "0 4px 12px rgba(0,0,0,0.1)" }} />
              <Bar dataKey="Score" radius={[6, 6, 0, 0]}>
                {barData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Card>

        <Card className="p-5 shadow-sm border-0 shadow-foreground/5">
          <h3 className="text-sm font-semibold mb-4">KPI Achievement Distribution</h3>
          <ResponsiveContainer width="100%" height={280}>
            <PieChart>
              <Pie data={donutData} dataKey="value" nameKey="name" cx="50%" cy="50%" innerRadius={70} outerRadius={110} paddingAngle={3}>
                <Cell fill="hsl(152 60% 42%)" />
                <Cell fill="hsl(38 92% 50%)" />
                <Cell fill="hsl(0 72% 51%)" />
              </Pie>
              <Tooltip contentStyle={{ borderRadius: "8px", border: "none", boxShadow: "0 4px 12px rgba(0,0,0,0.1)" }} />
              <Legend iconType="circle" />
            </PieChart>
          </ResponsiveContainer>
        </Card>
      </div>

      <Card className="p-5 shadow-sm border-0 shadow-foreground/5">
        <h3 className="text-sm font-semibold mb-4">Division Rankings</h3>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="text-xs w-12">#</TableHead>
              <TableHead className="text-xs">Division</TableHead>
              <TableHead className="text-xs">Period</TableHead>
              <TableHead className="text-xs">Avg Achievement</TableHead>
              <TableHead className="text-xs">KPIs</TableHead>
              <TableHead className="text-xs">Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sorted.map((d, i) => (
              <TableRow key={d.division_id}>
                <TableCell className="font-semibold text-muted-foreground">{i + 1}</TableCell>
                <TableCell className="font-medium">{d.division_name}</TableCell>
                <TableCell className="text-muted-foreground text-sm">{d.evaluation_label}</TableCell>
                <TableCell className="font-bold">{d.avg_achievement.toFixed(1)}%</TableCell>
                <TableCell>{d.achieved_kpis}/{d.total_kpis}</TableCell>
                <TableCell>
                  <Badge className={STATUS_BADGE[d.status] ?? ""}>{STATUS_LABEL[d.status] ?? d.status}</Badge>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>
    </div>
  );
}
