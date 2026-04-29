"""
MCP Tools — query dan kalkulasi KPI menggunakan model per-indikator.

Semua perhitungan menggunakan calculate_division_report / calculate_kpi_annual
dari aggregation_service, bukan lagi fact_kpi_quarterly.
"""
import logging
from typing import Any, Dict
from sqlalchemy.orm import Session
from sqlalchemy import text

from services.aggregation_service import (
    calculate_division_report,
    calculate_kpi_annual,
    _achievement_status,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────── #
# TOOL 1: Overview — semua divisi, Division Report masing-masing              #
# ─────────────────────────────────────────────────────────────────────────── #
def get_overview_kpi(db: Session, year: int) -> Dict[str, Any]:
    """Company-wide KPI overview: Division Report tiap divisi."""
    div_sql = text("SELECT division_id FROM dim_division ORDER BY division_id")
    div_rows = db.execute(div_sql).fetchall()

    divisions = []
    for dr in div_rows:
        result = calculate_division_report(db, dr.division_id, year)
        if "error" not in result:
            divisions.append({
                "division_id":     result["division_id"],
                "division_name":   result["division_name"],
                "division_report": result["division_report"],
                "status":          result["status"],
                "total_kpis":      result["total_kpis"],
                "on_target":       result["on_target"],
                "on_progress":     result["on_progress"],
            })

    # Company average = rata-rata Division Report semua divisi
    company_avg = round(
        sum(d["division_report"] for d in divisions) / len(divisions), 2
    ) if divisions else 0.0

    total_kpis   = sum(d["total_kpis"]   for d in divisions)
    on_target    = sum(d["on_target"]    for d in divisions)
    on_progress  = sum(d["on_progress"]  for d in divisions)

    # Sort by Division Report descending
    divisions.sort(key=lambda d: d["division_report"], reverse=True)

    return {
        "year":         year,
        "company_avg":  company_avg,
        "total_kpis":   total_kpis,
        "on_target":    on_target,
        "on_progress":  on_progress,
        # Legacy field names for frontend compatibility
        "achieved_kpis": on_target,
        "warning_kpis":  0,
        "danger_kpis":   on_progress,
        "divisions":    divisions,
    }


# ─────────────────────────────────────────────────────────────────────────── #
# TOOL 2: Division detail — per-KPI Annual Report + Division Report           #
# ─────────────────────────────────────────────────────────────────────────── #
def get_division_kpi(db: Session, division_id: int, year: int) -> Dict[str, Any]:
    """Breakdown detail KPI + Annual Report + Division Report satu divisi."""
    result = calculate_division_report(db, division_id, year)
    if "error" in result:
        return result

    # Buat flat list KPI items untuk frontend
    kpi_items = []
    for k in result["kpis"]:
        # Satu entry per KPI (annual level) + breakdown periodik
        kpi_items.append({
            "kpi_id":            k["kpi_id"],
            "kpi_name":          k["kpi_name"],
            "unit":              k["unit"],
            "weight":            k["weight"],
            "evaluation_period": k["evaluation_period"],
            "evaluation_label":  k.get("evaluation_label", k["evaluation_period"]),
            "visualization_type": k["visualization_type"],
            "annual_report":     k["annual_report"],
            "status":            k["status"],
            "periods":           k["periods"],
            # Legacy fields for frontend compatibility
            "quarter":       "annual",
            "year":          year,
            "target":        k["default_target"],
            "realization":   round(k["annual_report"] * k["default_target"] / 100, 2) if k["default_target"] else 0,
            "achievement":   k["annual_report"],
        })

    return {
        "division_id":      result["division_id"],
        "division_name":    result["division_name"],
        "evaluation_period": "mixed",   # tiap KPI bisa beda
        "evaluation_label":  "Per Indikator",
        "year":              year,
        "avg_achievement":   result["division_report"],  # legacy field
        "division_report":   result["division_report"],
        "status":            result["status"],
        "total_kpis":        result["total_kpis"],
        "on_target":         result["on_target"],
        "on_progress":       result["on_progress"],
        "kpis":              kpi_items,
    }


# ─────────────────────────────────────────────────────────────────────────── #
# TOOL 3: Trend — Division Report per tahun (current vs previous)             #
# ─────────────────────────────────────────────────────────────────────────── #
def get_kpi_trend(db: Session, division_id: int, year: int) -> Dict[str, Any]:
    """
    Tren Division Report year-over-year.
    Current year: breakdown per-periode tiap KPI digabung jadi trend.
    Previous year: Division Report satu nilai.
    """
    div_sql = text("SELECT division_name FROM dim_division WHERE division_id = :did")
    div = db.execute(div_sql, {"did": division_id}).fetchone()
    if not div:
        return {"error": f"Division {division_id} not found"}

    # Ambil semua KPI divisi
    kpi_sql = text("SELECT kpi_id, evaluation_period FROM dim_kpi WHERE division_id = :did ORDER BY kpi_id")
    kpis = db.execute(kpi_sql, {"did": division_id}).fetchall()

    # Current year: kumpulkan achievement per periode dari semua KPI,
    # lalu hitung weighted average per titik waktu
    # Karena tiap KPI bisa punya periode beda, trend yang ditampilkan
    # adalah Division Report per-periode yang paling dominan.
    # Untuk simplisitas: ambil per-KPI trend, grouped by period_name.
    from collections import defaultdict

    period_contributions: dict = defaultdict(lambda: {"weighted_sum": 0.0, "weight_sum": 0.0})

    for kpi_row in kpis:
        kpi_data = calculate_kpi_annual(db, kpi_row.kpi_id, year)
        if not kpi_data or not kpi_data.get("periods"):
            continue
        w = kpi_data["weight"]
        for p in kpi_data["periods"]:
            key = (p["period_order"], p["period_name"])
            period_contributions[key]["weighted_sum"] += p["achievement"] * w
            period_contributions[key]["weight_sum"] += w

    current_trend = []
    for (order, name), vals in sorted(period_contributions.items()):
        avg = round(vals["weighted_sum"] / vals["weight_sum"], 2) if vals["weight_sum"] > 0 else 0.0
        current_trend.append({"period": name, "achievement": avg, "year": year})

    # Previous year: satu nilai Division Report
    prev_result = calculate_division_report(db, division_id, year - 1)
    prev_div_report = prev_result.get("division_report", 0.0) if "error" not in prev_result else 0.0
    previous_trend = [{"period": str(year - 1), "achievement": prev_div_report, "year": year - 1}]

    return {
        "division_id":    division_id,
        "division_name":  div.division_name,
        "current_year":   year,
        "current_trend":  current_trend,
        "previous_trend": previous_trend,
    }


# ─────────────────────────────────────────────────────────────────────────── #
# TOOL 4: Underperforming — Annual Report KPI < 80                            #
# ─────────────────────────────────────────────────────────────────────────── #
def get_underperforming_kpi(db: Session, year: int) -> Dict[str, Any]:
    """KPI dengan Annual Report < 80%."""
    div_sql = text("SELECT division_id FROM dim_division ORDER BY division_id")
    div_rows = db.execute(div_sql).fetchall()

    kpi_sql = text("SELECT kpi_id, division_id FROM dim_kpi ORDER BY division_id, kpi_id")
    kpi_rows = db.execute(kpi_sql).fetchall()

    items = []
    for kpi_row in kpi_rows:
        kpi_data = calculate_kpi_annual(db, kpi_row.kpi_id, year)
        if not kpi_data or kpi_data.get("annual_report", 100) >= 80:
            continue

        # Ambil nama divisi
        div_name_sql = text("SELECT division_name FROM dim_division WHERE division_id = :did")
        div_name = db.execute(div_name_sql, {"did": kpi_row.division_id}).fetchone()

        items.append({
            "division_id":    kpi_row.division_id,
            "division_name":  div_name.division_name if div_name else "Unknown",
            "kpi_id":         kpi_data["kpi_id"],
            "kpi_name":       kpi_data["kpi_name"],
            "unit":           kpi_data["unit"],
            "weight":         kpi_data["weight"],
            "evaluation_period": kpi_data["evaluation_period"],
            "year":           year,
            "annual_report":  kpi_data["annual_report"],
            "status":         kpi_data["status"],
            # legacy
            "quarter":        "annual",
            "achievement":    kpi_data["annual_report"],
        })

    # Sort by annual_report ascending (terburuk di atas)
    items.sort(key=lambda x: x["annual_report"])

    return {"year": year, "count": len(items), "items": items}


# ─────────────────────────────────────────────────────────────────────────── #
# TOOL 5: Compare divisions — ranking berdasarkan Division Report              #
# ─────────────────────────────────────────────────────────────────────────── #
def compare_divisions(db: Session, year: int) -> Dict[str, Any]:
    """Ranking divisi berdasarkan Division Report."""
    div_sql = text("SELECT division_id FROM dim_division ORDER BY division_id")
    div_rows = db.execute(div_sql).fetchall()

    ranking = []
    for i, dr in enumerate(div_rows):
        result = calculate_division_report(db, dr.division_id, year)
        if "error" not in result:
            kpi_annuals = [k["annual_report"] for k in result["kpis"] if k.get("periods")]
            ranking.append({
                "rank":            0,  # akan di-set setelah sort
                "division_id":     result["division_id"],
                "division_name":   result["division_name"],
                "division_report": result["division_report"],
                "avg_achievement": result["division_report"],  # legacy
                "min_achievement": round(min(kpi_annuals), 2) if kpi_annuals else 0.0,
                "max_achievement": round(max(kpi_annuals), 2) if kpi_annuals else 0.0,
                "total_kpis":      result["total_kpis"],
                "status":          result["status"],
            })

    ranking.sort(key=lambda x: x["division_report"], reverse=True)
    for i, r in enumerate(ranking):
        r["rank"] = i + 1

    return {"year": year, "ranking": ranking}


# ─────────────────────────────────────────────────────────────────────────── #
# Registry
# ─────────────────────────────────────────────────────────────────────────── #
MCP_TOOLS = {
    "get_overview_kpi":        get_overview_kpi,
    "get_division_kpi":        get_division_kpi,
    "get_kpi_trend":           get_kpi_trend,
    "get_underperforming_kpi": get_underperforming_kpi,
    "compare_divisions":       compare_divisions,
}
