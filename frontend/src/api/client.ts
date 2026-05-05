import axios from "axios";
import { getToken, logout } from "@/lib/auth";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";
const MCP_BASE = import.meta.env.VITE_MCP_URL || "http://localhost:8001";

const api = axios.create({
  baseURL: API_BASE,
  headers: { "Content-Type": "application/json" },
  timeout: 30000,
});

// MCP Server client — chatbot calls FastMCP directly
const mcp = axios.create({
  baseURL: MCP_BASE,
  headers: { "Content-Type": "application/json" },
  timeout: 120000,
});

// ── Auto-attach JWT token to every request ─────────────────────────────── //
api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ── Auto-logout on 401 ─────────────────────────────────────────────────── //
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      logout();
      // Hanya redirect jika tidak sedang berada di halaman login
      // untuk mencegah refresh saat login gagal
      if (window.location.pathname !== "/login") {
        window.location.href = "/login";
      }
    }
    return Promise.reject(err);
  }
);

// ── Dashboard ──────────────────────────────────────────────────────────── //

export interface PeriodDetail {
  period_id: number;
  period_name: string;
  period_order: number;
  target: number;
  realization: number;
  achievement: number;
  status: "green" | "yellow" | "red";
}

export interface KpiItem {
  kpi_id: number;
  kpi_name: string;
  unit: string;
  weight: number;
  evaluation_period: string;   // M | Q | H
  evaluation_label?: string;
  annual_report: number;       // rata-rata achievement seluruh periode
  status: "green" | "yellow" | "red";
  periods: PeriodDetail[];     // breakdown per periode
  // legacy fields untuk backward compat
  quarter: string;
  year: number;
  target: number;
  realization: number;
  achievement: number;
}

export interface DivisionOverview {
  division_id: number;
  division_name: string;
  division_report: number;     // Σ(annual × weight)/100
  status: "green" | "yellow" | "red";
  total_kpis: number;
  on_target: number;
  on_progress: number;
  // legacy
  avg_achievement: number;
  achieved_kpis: number;
  warning_kpis: number;
  danger_kpis: number;
}

export interface OverviewData {
  year: number;
  company_avg: number;
  total_kpis: number;
  on_target: number;
  on_progress: number;
  // legacy
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
  division_report: number;     // skor akhir divisi
  avg_achievement: number;     // alias division_report (legacy)
  status: string;
  total_kpis: number;
  on_target: number;
  on_progress: number;
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
  evaluation_period: string;
  year: number;
  annual_report: number;
  status: string;
  // legacy
  quarter: string;
  achievement: number;
}

export interface UnderperformData {
  year: number;
  count: number;
  items: UnderperformItem[];
}

export const getAvailableYears = () =>
  api.get<number[]>("/dashboard/years").then((r) => r.data);

export const getOverview = (year = 2025) =>
  api.get<OverviewData>(`/dashboard/overview?year=${year}`).then((r) => r.data);

export const getDivision = (divisionId: number, year = 2025) =>
  api.get<DivisionDetailData>(`/dashboard/division/${divisionId}?year=${year}`).then((r) => r.data);

export const getTrend = (divisionId: number, year = 2025) =>
  api.get<TrendData>(`/dashboard/trend/${divisionId}?year=${year}`).then((r) => r.data);

export const getUnderperform = (year = 2025) =>
  api.get<UnderperformData>(`/dashboard/underperform?year=${year}`).then((r) => r.data);

// ── FastMCP Chat (port 8001) ───────────────────────────────────────────── //

export interface McpChatResponse {
  response: string;
  model: string;
}

export const postMcpChat = (message: string, year = 2025) =>
  mcp.post<McpChatResponse>("/chat", { message, year }).then((r) => r.data);

export const getMcpHealth = () => mcp.get("/").then((r) => r.data);
export const getMcpTools = () => mcp.get("/tools").then((r) => r.data);

// ── Auth ───────────────────────────────────────────────────────────────── //

export interface LoginPayload { username: string; password: string }
export interface TokenResponse {
  access_token: string;
  token_type: string;
  role: string;
  username: string;
}
export interface UserResponse {
  user_id: number;
  username: string;
  email: string;
  role: string;
  is_active: boolean;
  created_at: string;
}
export interface UserCreatePayload {
  username: string;
  email: string;
  password: string;
  role: string;
}

export const postLogin = (payload: LoginPayload) =>
  api.post<TokenResponse>("/auth/login", payload).then((r) => r.data);

export const getMe = () =>
  api.get<UserResponse>("/auth/me").then((r) => r.data);

// ── Admin ──────────────────────────────────────────────────────────────── //

export interface KpiPayload {
  division_id: number;
  kpi_name: string;
  unit: string;
  default_target: number;
  weight: number;
  evaluation_period: string;  // M | Q | H
}

export interface RealizationPayload {
  division_id: number;
  kpi_id: number;
  period_id: number;
  year: number;
  target: number;
  realization: number;
}

export interface EtlPayload { year: number; all_years: boolean }

export const adminGetKpi = (division_id?: number) =>
  api.get("/admin/kpi", { params: division_id ? { division_id } : {} }).then((r) => r.data);

export const adminGetKpiById = (kpi_id: number) =>
  api.get(`/admin/kpi/${kpi_id}`).then((r) => r.data);

export const adminPostKpi = (payload: KpiPayload) =>
  api.post("/admin/kpi", payload).then((r) => r.data);

export const adminPutKpi = (id: number, payload: Partial<KpiPayload>) =>
  api.put(`/admin/kpi/${id}`, payload).then((r) => r.data);

export const adminDeleteKpi = (id: number) =>
  api.delete(`/admin/kpi/${id}`);

export const adminPostRealization = (payload: RealizationPayload) =>
  api.post("/admin/realization", payload).then((r) => r.data);

export const adminPutRealization = (id: number, payload: Partial<RealizationPayload>) =>
  api.put(`/admin/realization/${id}`, payload).then((r) => r.data);

export const adminDeleteRealization = (id: number) =>
  api.delete(`/admin/realization/${id}`);

export const adminRunEtl = (payload: EtlPayload) =>
  api.post("/admin/run-etl", payload).then((r) => r.data);

export const adminGetUsers = () =>
  api.get<UserResponse[]>("/admin/users").then((r) => r.data);

export const adminPostUser = (payload: UserCreatePayload) =>
  api.post<UserResponse>("/admin/users", payload).then((r) => r.data);

export const adminPatchUser = (id: number, payload: { is_active?: boolean; role?: string }) =>
  api.patch<UserResponse>(`/admin/users/${id}`, payload).then((r) => r.data);

export const adminDeleteUser = (id: number) =>
  api.delete(`/admin/users/${id}`);

// ── Admin Meta (reference data for forms) ─────────────────────────────── //

export interface DivisionMeta {
  division_id: number;
  division_name: string;
  evaluation_period: string; // M | Q | H
}

export interface PeriodMeta {
  period_id: number;
  period_name: string;
  period_type: string;
  period_order: number;
}

export interface RealizationRecord {
  fact_id: number;
  division_id: number;
  kpi_id: number;
  kpi_name: string;
  period_id: number;
  period_name: string;
  year: number;
  target: number;
  realization: number;
  achievement: number;
}

export const adminGetDivisions = () =>
  api.get<DivisionMeta[]>("/admin/meta/divisions").then((r) => r.data);

export const adminGetPeriods = (period_type?: string, kpi_id?: number) =>
  api.get<PeriodMeta[]>("/admin/meta/periods", {
    params: {
      ...(period_type ? { period_type } : {}),
      ...(kpi_id     ? { kpi_id }      : {}),
    },
  }).then((r) => r.data);

export const adminGetRealizations = (params: {
  division_id?: number;
  kpi_id?: number;
  year?: number;
}) => api.get<RealizationRecord[]>("/admin/meta/realizations", { params }).then((r) => r.data);

// ── Forecast ──────────────────────────────────────────────────────────── //

export interface ForecastPoint {
  label: string;       // e.g. "2026-Q2"
  value: number | null;
}

export interface MrrForecastData {
  kpi_name: string;
  arima_order: number[];
  data_points: number;
  mape: number;
  aic: number;
  actual: ForecastPoint[];
  fitted: ForecastPoint[];
  forecast: ForecastPoint[];
}

export const getMrrForecast = (p = 2, d = 0, q = 3, n_forecast = 4) =>
  api.get<MrrForecastData>("/forecast/mrr", {
    params: { p, d, q, n_forecast }
  }).then((r) => r.data);
