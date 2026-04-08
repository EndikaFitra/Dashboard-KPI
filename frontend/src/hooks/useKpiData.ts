import { useQuery } from "@tanstack/react-query";
import {
  getOverview,
  getDivision,
  getTrend,
  getUnderperform,
} from "@/api/client";

// ── Overview ───────────────────────────────────────────────────────────── //
export function useOverview(year = 2025) {
  return useQuery({
    queryKey: ["overview", year],
    queryFn: () => getOverview(year),
    staleTime: 60_000,
    retry: 2,
  });
}

// ── Division detail ────────────────────────────────────────────────────── //
export function useDivision(divisionId: number | undefined, year = 2025) {
  return useQuery({
    queryKey: ["division", divisionId, year],
    queryFn: () => getDivision(divisionId!, year),
    enabled: !!divisionId,
    staleTime: 60_000,
    retry: 2,
  });
}

// ── Trend ──────────────────────────────────────────────────────────────── //
export function useTrend(divisionId: number | undefined, year = 2025) {
  return useQuery({
    queryKey: ["trend", divisionId, year],
    queryFn: () => getTrend(divisionId!, year),
    enabled: !!divisionId,
    staleTime: 60_000,
    retry: 2,
  });
}

// ── Underperforming KPIs ───────────────────────────────────────────────── //
export function useUnderperform(year = 2025) {
  return useQuery({
    queryKey: ["underperform", year],
    queryFn: () => getUnderperform(year),
    staleTime: 60_000,
    retry: 2,
  });
}
