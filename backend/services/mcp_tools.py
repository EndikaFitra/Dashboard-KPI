"""
MCP Tools — each function queries fact_kpi_quarterly and returns structured data.
Achievement calculation uses weighted average from dim_kpi.weight.
"""
import logging
from collections import defaultdict
from typing import Any, Dict
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)

PERIOD_LABEL = {"H": "Half Year", "Q": "Quarter", "M": "Monthly"}


def _achievement_status(achievement: float) -> str:
    if achievement >= 100:
        return "green"
    if achievement >= 80:
        return "yellow"
    return "red"


def _weighted_avg(achievements: list[float], weights: list[float]) -> float:
    """Compute weighted average. Both lists must be same length."""
    total_w = sum(weights)
    if total_w == 0:
        return 0.0
    return sum(a * w for a, w in zip(achievements, weights)) / total_w


# ─────────────────────────────────────────────────────────────────────────── #
# TOOL 1: Overview — all divisions, weighted avg per division                 #
# ─────────────────────────────────────────────────────────────────────────── #
def get_overview_kpi(db: Session, year: int) -> Dict[str, Any]:
    sql = text("""
        SELECT
            d.division_id,
            d.division_name,
            d.evaluation_period,
            COUNT(DISTINCT k.kpi_id)                                            AS total_kpis,
            SUM(kpi_agg.avg_achievement * k.weight) / NULLIF(SUM(k.weight), 0) AS avg_achievement,
            SUM(CASE WHEN kpi_agg.avg_achievement >= 100 THEN 1 ELSE 0 END)    AS achieved_kpis,
            SUM(CASE WHEN kpi_agg.avg_achievement >= 80
                      AND kpi_agg.avg_achievement < 100 THEN 1 ELSE 0 END)     AS warning_kpis,
            SUM(CASE WHEN kpi_agg.avg_achievement < 80 THEN 1 ELSE 0 END)      AS danger_kpis
        FROM dim_division d
        JOIN dim_kpi k ON d.division_id = k.division_id
        LEFT JOIN (
            SELECT kpi_id, division_id, AVG(achievement) AS avg_achievement
            FROM fact_kpi_quarterly
            WHERE year = :year
            GROUP BY kpi_id, division_id
        ) kpi_agg ON k.kpi_id = kpi_agg.kpi_id AND k.division_id = kpi_agg.division_id
        GROUP BY d.division_id, d.division_name, d.evaluation_period
        ORDER BY avg_achievement DESC NULLS LAST
    """)
    rows = db.execute(sql, {"year": year}).fetchall()

    divisions = []
    for r in rows:
        avg = round(r.avg_achievement or 0, 2)
        divisions.append({
            "division_id":      r.division_id,
            "division_name":    r.division_name,
            "evaluation_period": r.evaluation_period,
            "evaluation_label": PERIOD_LABEL.get(r.evaluation_period, r.evaluation_period),
            "avg_achievement":  avg,
            "status":           _achievement_status(avg),
            "total_kpis":       r.total_kpis or 0,
            "achieved_kpis":    r.achieved_kpis or 0,
            "warning_kpis":     r.warning_kpis or 0,
            "danger_kpis":      r.danger_kpis or 0,
        })

    total_kpis  = sum(d["total_kpis"]   for d in divisions)
    achieved    = sum(d["achieved_kpis"] for d in divisions)
    warning     = sum(d["warning_kpis"]  for d in divisions)
    danger      = sum(d["danger_kpis"]   for d in divisions)
    company_avg = round(
        sum(d["avg_achievement"] for d in divisions) / len(divisions), 2
    ) if divisions else 0

    return {
        "year": year,
        "company_avg":   company_avg,
        "total_kpis":    total_kpis,
        "achieved_kpis": achieved,
        "warning_kpis":  warning,
        "danger_kpis":   danger,
        "divisions":     divisions,
    }


# ─────────────────────────────────────────────────────────────────────────── #
# TOOL 2: Division detail — per-KPI breakdown with weight                     #
# ─────────────────────────────────────────────────────────────────────────── #
def get_division_kpi(db: Session, division_id: int, year: int) -> Dict[str, Any]:
    div_sql = text("SELECT * FROM dim_division WHERE division_id = :did")
    div = db.execute(div_sql, {"did": division_id}).fetchone()
    if not div:
        return {"error": f"Division {division_id} not found"}

    sql = text("""
        SELECT
            fq.kpi_id,
            k.kpi_name,
            k.unit,
            k.visualization_type,
            k.weight,
            fq.quarter,
            fq.year,
            fq.target,
            fq.realization,
            fq.achievement
        FROM fact_kpi_quarterly fq
        JOIN dim_kpi k ON fq.kpi_id = k.kpi_id
        WHERE fq.division_id = :did AND fq.year = :year
        ORDER BY k.kpi_id, fq.quarter
    """)
    rows = db.execute(sql, {"did": division_id, "year": year}).fetchall()

    # Build KPI list
    kpis = []
    for r in rows:
        kpis.append({
            "kpi_id":           r.kpi_id,
            "kpi_name":         r.kpi_name,
            "unit":             r.unit,
            "visualization_type": r.visualization_type,
            "weight":           r.weight,
            "quarter":          r.quarter,
            "year":             r.year,
            "target":           r.target,
            "realization":      r.realization,
            "achievement":      round(r.achievement, 2),
            "status":           _achievement_status(r.achievement),
        })

    # Weighted avg: first get per-KPI avg across quarters, then weight
    kpi_quarters: dict = defaultdict(list)
    kpi_weight: dict = {}
    for r in rows:
        kpi_quarters[r.kpi_id].append(r.achievement)
        kpi_weight[r.kpi_id] = r.weight

    kpi_avgs   = [sum(v) / len(v) for v in kpi_quarters.values()]
    kpi_weights = [kpi_weight[k] for k in kpi_quarters.keys()]
    avg = round(_weighted_avg(kpi_avgs, kpi_weights), 2)

    return {
        "division_id":       div.division_id,
        "division_name":     div.division_name,
        "evaluation_period": div.evaluation_period,
        "evaluation_label":  PERIOD_LABEL.get(div.evaluation_period, div.evaluation_period),
        "year":              year,
        "avg_achievement":   avg,
        "status":            _achievement_status(avg),
        "kpis":              kpis,
    }


# ─────────────────────────────────────────────────────────────────────────── #
# TOOL 3: Trend — weighted avg per quarter, current vs previous year          #
# ─────────────────────────────────────────────────────────────────────────── #
def get_kpi_trend(db: Session, division_id: int, year: int) -> Dict[str, Any]:
    div_sql = text("SELECT division_name FROM dim_division WHERE division_id = :did")
    div = db.execute(div_sql, {"did": division_id}).fetchone()
    if not div:
        return {"error": f"Division {division_id} not found"}

    sql = text("""
        SELECT
            fq.quarter,
            fq.year,
            fq.achievement,
            k.weight
        FROM fact_kpi_quarterly fq
        JOIN dim_kpi k ON fq.kpi_id = k.kpi_id
        WHERE fq.division_id = :did AND fq.year IN (:year, :prev_year)
        ORDER BY fq.year, fq.quarter
    """)
    rows = db.execute(sql, {
        "did": division_id, "year": year, "prev_year": year - 1
    }).fetchall()

    # Group: (year, quarter) → list of (achievement, weight)
    groups: dict = defaultdict(list)
    for r in rows:
        groups[(r.year, r.quarter)].append((r.achievement, r.weight))

    current, previous = [], []
    for (yr, quarter), vals in sorted(groups.items()):
        achievements = [v[0] for v in vals]
        weights      = [v[1] for v in vals]
        avg = round(_weighted_avg(achievements, weights), 2)
        point = {"period": quarter, "achievement": avg, "year": yr}
        if yr == year:
            current.append(point)
        else:
            previous.append(point)

    return {
        "division_id":   division_id,
        "division_name": div.division_name,
        "current_year":  year,
        "current_trend":  current,
        "previous_trend": previous,
    }


# ─────────────────────────────────────────────────────────────────────────── #
# TOOL 4: Underperforming — achievement < 80 (individual KPI, not weighted)   #
# ─────────────────────────────────────────────────────────────────────────── #
def get_underperforming_kpi(db: Session, year: int) -> Dict[str, Any]:
    sql = text("""
        SELECT
            d.division_id,
            d.division_name,
            fq.kpi_id,
            k.kpi_name,
            k.unit,
            k.weight,
            fq.quarter,
            fq.year,
            fq.target,
            fq.realization,
            fq.achievement,
            (fq.realization - fq.target) AS gap
        FROM fact_kpi_quarterly fq
        JOIN dim_division d ON fq.division_id = d.division_id
        JOIN dim_kpi k ON fq.kpi_id = k.kpi_id
        WHERE fq.year = :year AND fq.achievement < 80
        ORDER BY fq.achievement ASC
    """)
    rows = db.execute(sql, {"year": year}).fetchall()

    items = []
    for r in rows:
        items.append({
            "division_id":   r.division_id,
            "division_name": r.division_name,
            "kpi_id":        r.kpi_id,
            "kpi_name":      r.kpi_name,
            "unit":          r.unit,
            "weight":        r.weight,
            "quarter":       r.quarter,
            "year":          r.year,
            "target":        r.target,
            "realization":   r.realization,
            "achievement":   round(r.achievement, 2),
            "gap":           round(r.gap, 2),
        })

    return {"year": year, "count": len(items), "items": items}


# ─────────────────────────────────────────────────────────────────────────── #
# TOOL 5: Compare divisions — weighted ranking                                 #
# ─────────────────────────────────────────────────────────────────────────── #
def compare_divisions(db: Session, year: int) -> Dict[str, Any]:
    sql = text("""
        SELECT
            d.division_id,
            d.division_name,
            d.evaluation_period,
            COUNT(DISTINCT k.kpi_id)                                            AS total_kpis,
            SUM(kpi_agg.avg_achievement * k.weight) / NULLIF(SUM(k.weight), 0) AS avg_achievement,
            MIN(kpi_agg.avg_achievement)                                        AS min_achievement,
            MAX(kpi_agg.avg_achievement)                                        AS max_achievement
        FROM dim_division d
        JOIN dim_kpi k ON d.division_id = k.division_id
        LEFT JOIN (
            SELECT kpi_id, division_id, AVG(achievement) AS avg_achievement
            FROM fact_kpi_quarterly
            WHERE year = :year
            GROUP BY kpi_id, division_id
        ) kpi_agg ON k.kpi_id = kpi_agg.kpi_id AND k.division_id = kpi_agg.division_id
        GROUP BY d.division_id, d.division_name, d.evaluation_period
        ORDER BY avg_achievement DESC NULLS LAST
    """)
    rows = db.execute(sql, {"year": year}).fetchall()

    ranking = []
    for i, r in enumerate(rows):
        avg = round(r.avg_achievement or 0, 2)
        ranking.append({
            "rank":             i + 1,
            "division_id":      r.division_id,
            "division_name":    r.division_name,
            "evaluation_period":r.evaluation_period,
            "evaluation_label": PERIOD_LABEL.get(r.evaluation_period, r.evaluation_period),
            "avg_achievement":  avg,
            "min_achievement":  round(r.min_achievement or 0, 2),
            "max_achievement":  round(r.max_achievement or 0, 2),
            "total_kpis":       r.total_kpis or 0,
            "status":           _achievement_status(avg),
        })

    return {"year": year, "ranking": ranking}


# Registry for dispatcher
MCP_TOOLS = {
    "get_overview_kpi":       get_overview_kpi,
    "get_division_kpi":       get_division_kpi,
    "get_kpi_trend":          get_kpi_trend,
    "get_underperforming_kpi":get_underperforming_kpi,
    "compare_divisions":      compare_divisions,
}
