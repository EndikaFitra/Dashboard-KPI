/**
 * Shared types and utility functions used by KPI components.
 * Static mock data has been removed — all data now comes from the REST API.
 */

export interface KPIIndicator {
  id: string;
  name: string;
  target: number;
  targetUnit: string;
  realization: number;
  weight: number;
  score: number;
}

export function formatTarget(value: number, unit: string): string {
  if (unit === "IDR") {
    return new Intl.NumberFormat("id-ID", {
      style: "currency",
      currency: "IDR",
      maximumFractionDigits: 0,
    }).format(value);
  }
  const formatted = Number(value).toFixed(2);
  if (unit === "%") return `${formatted}%`;
  return `${formatted} ${unit}`;
}

export function getStatusColor(score: number): "achieved" | "warning" | "danger" {
  if (score >= 100) return "achieved";
  if (score >= 80) return "warning";
  return "danger";
}
