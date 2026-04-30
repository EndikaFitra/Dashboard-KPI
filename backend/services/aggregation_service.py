"""
Aggregation Service — Perhitungan KPI per-indikator (on-the-fly).

Model kalkulasi baru:
  1. Setiap KPI memiliki evaluation_period sendiri (M/Q/H)
  2. Achievement per periode = (realization / target) * 100
  3. Annual Report KPI      = rata-rata achievement seluruh periode dalam setahun
  4. Division Report        = Σ (annual_report_i × weight_i) / 100

Tidak membutuhkan ETL batch — semua dihitung langsung dari fact_kpi_performance.
"""
import logging
from typing import Any, Dict, List
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)

PERIOD_LABEL = {"M": "Monthly", "Q": "Quarterly", "H": "Half Year"}


# ────────────────────────────────────────────────────────────────────────────── #
# Helper
# ────────────────────────────────────────────────────────────────────────────── #
def _achievement_status(value: float) -> str:
    if value >= 100:
        return "green"
    if value >= 80:
        return "yellow"
    return "red"


# ────────────────────────────────────────────────────────────────────────────── #
# Core: hitung Annual Report untuk satu KPI
# ────────────────────────────────────────────────────────────────────────────── #
def calculate_kpi_annual(db: Session, kpi_id: int, year: int) -> Dict[str, Any]:
    """
    Hitung Annual Report satu KPI untuk satu tahun.

    Query fact_kpi_performance JOIN dim_period,
    filter sesuai evaluation_period KPI tersebut,
    kembalikan:
      - periods: list {period_name, period_order, target, realization, achievement}
      - annual_report: rata-rata achievement seluruh periode
    """
    sql = text("""
        SELECT
            k.kpi_id,
            k.kpi_name,
            k.unit,
            k.weight,
            k.evaluation_period,
            k.default_target,
            p.period_id,
            p.period_name,
            p.period_type,
            p.period_order,
            f.year,
            f.target,
            f.realization,
            CASE WHEN f.target > 0
                 THEN (f.realization / f.target) * 100
                 ELSE 0
            END AS achievement
        FROM fact_kpi_performance f
        JOIN dim_kpi    k ON f.kpi_id    = k.kpi_id
        JOIN dim_period p ON f.period_id = p.period_id
        WHERE f.kpi_id = :kpi_id
          AND f.year   = :year
          AND p.period_type = k.evaluation_period
        ORDER BY p.period_order
    """)
    rows = db.execute(sql, {"kpi_id": kpi_id, "year": year}).fetchall()

    if not rows:
        # KPI belum punya data di tahun ini
        kpi_sql = text("SELECT kpi_id, kpi_name, unit, weight, evaluation_period, default_target FROM dim_kpi WHERE kpi_id = :kid")
        kpi_row = db.execute(kpi_sql, {"kid": kpi_id}).fetchone()
        if not kpi_row:
            return {}
        return {
            "kpi_id":             kpi_row.kpi_id,
            "kpi_name":           kpi_row.kpi_name,
            "unit":               kpi_row.unit,
            "weight":             kpi_row.weight,
            "evaluation_period":  kpi_row.evaluation_period,
            "default_target":     kpi_row.default_target,
            "year":               year,
            "annual_report":      0.0,
            "status":             "red",
            "periods":            [],
        }

    periods = []
    achievements = []
    for r in rows:
        ach = round(r.achievement, 2)
        achievements.append(ach)
        periods.append({
            "period_id":    r.period_id,
            "period_name":  r.period_name,
            "period_order": r.period_order,
            "target":       r.target,
            "realization":  r.realization,
            "achievement":  ach,
            "status":       _achievement_status(ach),
        })

    annual_report = round(sum(achievements) / len(achievements), 2) if achievements else 0.0

    return {
        "kpi_id":             rows[0].kpi_id,
        "kpi_name":           rows[0].kpi_name,
        "unit":               rows[0].unit,
        "weight":             rows[0].weight,
        "evaluation_period":  rows[0].evaluation_period,
        "evaluation_label":   PERIOD_LABEL.get(rows[0].evaluation_period, rows[0].evaluation_period),
        "default_target":     rows[0].default_target,
        "year":               year,
        "annual_report":      annual_report,
        "status":             _achievement_status(annual_report),
        "periods":            periods,
    }


# ────────────────────────────────────────────────────────────────────────────── #
# Core: hitung Division Report untuk satu divisi
# ────────────────────────────────────────────────────────────────────────────── #
def calculate_division_report(db: Session, division_id: int, year: int) -> Dict[str, Any]:
    """
    Hitung Division Report untuk satu divisi.

    Division Report = Σ (annual_report_i × weight_i) / 100

    Mengembalikan:
      - division_report: float (%)
      - kpis: list hasil calculate_kpi_annual per KPI
      - total_kpis, on_target, on_progress counts
    """
    # Ambil semua KPI milik divisi ini
    div_sql = text("SELECT * FROM dim_division WHERE division_id = :did")
    div = db.execute(div_sql, {"did": division_id}).fetchone()
    if not div:
        return {"error": f"Division {division_id} not found"}

    kpi_sql = text("SELECT kpi_id FROM dim_kpi WHERE division_id = :did ORDER BY kpi_id")
    kpi_rows = db.execute(kpi_sql, {"did": division_id}).fetchall()

    kpis: List[Dict] = []
    for kpi_row in kpi_rows:
        result = calculate_kpi_annual(db, kpi_row.kpi_id, year)
        if result:
            kpis.append(result)

    # Division Report = Σ(annual_report × weight) / 100
    division_report = round(
        sum(k["annual_report"] * k["weight"] for k in kpis) / 100,
        2
    )

    on_target   = sum(1 for k in kpis if k["annual_report"] >= 100)
    on_progress = sum(1 for k in kpis if k["annual_report"] < 100)

    return {
        "division_id":      div.division_id,
        "division_name":    div.division_name,
        "year":             year,
        "division_report":  division_report,
        "status":           _achievement_status(division_report),
        "total_kpis":       len(kpis),
        "on_target":        on_target,
        "on_progress":      on_progress,
        "kpis":             kpis,
    }
