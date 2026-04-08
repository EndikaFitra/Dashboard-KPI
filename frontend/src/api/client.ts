import axios from "axios";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

const api = axios.create({
  baseURL: API_BASE,
  headers: { "Content-Type": "application/json" },
  timeout: 30000,
});

// ── Dashboard ──────────────────────────────────────────────────────────── //

export interface KpiItem {
  kpi_id: number;
  kpi_name: string;
  unit: string;
  visualization_type: string;
  weight: number;
  quarter: string;
  year: number;
  target: number;
  realization: number;
  achievement: number;
  status: "green" | "yellow" | "red";
}

export interface DivisionOverview {
  division_id: number;
  division_name: string;
  evaluation_period: string;
  evaluation_label: string;
  avg_achievement: number;
  status: "green" | "yellow" | "red";
  total_kpis: number;
  achieved_kpis: number;
  warning_kpis: number;
  danger_kpis: number;
}

export interface OverviewData {
  year: number;
  company_avg: number;
  total_kpis: number;
  achieved_kpis: number;
  warning_kpis: number;
  danger_kpis: number;
  divisions: DivisionOverview[];
}

export interface DivisionDetailData {
  division_id: number;
  division_name: string;
  evaluation_period: string;
  evaluation_label: string;
  year: number;
  avg_achievement: number;
  status: string;
  kpis: KpiItem[];
}

export interface TrendPoint {
  period: string;
  achievement: number;
  year: number;
}

export interface TrendData {
  division_id: number;
  division_name: string;
  current_year: number;
  current_trend: TrendPoint[];
  previous_trend: TrendPoint[];
}

export interface UnderperformItem {
  division_id: number;
  division_name: string;
  kpi_id: number;
  kpi_name: string;
  unit: string;
  quarter: string;
  year: number;
  target: number;
  realization: number;
  achievement: number;
  gap: number;
}

export interface UnderperformData {
  year: number;
  count: number;
  items: UnderperformItem[];
}

export const getOverview = (year = 2025) =>
  api.get<OverviewData>(`/dashboard/overview?year=${year}`).then((r) => r.data);

export const getDivision = (divisionId: number, year = 2025) =>
  api.get<DivisionDetailData>(`/dashboard/division/${divisionId}?year=${year}`).then((r) => r.data);

export const getTrend = (divisionId: number, year = 2025) =>
  api.get<TrendData>(`/dashboard/trend/${divisionId}?year=${year}`).then((r) => r.data);

export const getUnderperform = (year = 2025) =>
  api.get<UnderperformData>(`/dashboard/underperform?year=${year}`).then((r) => r.data);

// ── Chatbot ────────────────────────────────────────────────────────────── //

export interface ChatbotResponse {
  question: string;
  answer: string;
  tool_used: string;
  context_summary: string;
}

export const postChatbot = (question: string) =>
  api.post<ChatbotResponse>("/chatbot", { question }).then((r) => r.data);

// ── MCP ───────────────────────────────────────────────────────────────── //

export const callMcpTool = (tool: string, params: Record<string, unknown> = {}) =>
  api.post("/mcp/tools", { tool, params }).then((r) => r.data);

// ── KPI Realization ────────────────────────────────────────────────────── //

export interface RealizationPayload {
  division_id: number;
  kpi_id: number;
  period_id: number;
  year: number;
  target: number;
  realization: number;
}

export const postRealization = (payload: RealizationPayload) =>
  api.post("/kpi/realization", payload).then((r) => r.data);

export const putRealization = (id: number, payload: Partial<RealizationPayload>) =>
  api.put(`/kpi/realization/${id}`, payload).then((r) => r.data);
