"""
Aggregation Service — Month → Quarter aggregation logic.

Rules:
  realization = AVG(monthly realizations within quarter)
  target      = AVG(monthly targets within quarter)
  achievement = (realization / target) * 100
"""
import logging
from collections import defaultdict
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)

# Static month→quarter mapping (fallback if dim_period_mapping is empty)
MONTH_TO_QUARTER = {
    1: "Q1", 2: "Q1", 3: "Q1",
    4: "Q2", 5: "Q2", 6: "Q2",
    7: "Q3", 8: "Q3", 9: "Q3",
    10: "Q4", 11: "Q4", 12: "Q4",
}

MONTH_ORDER_TO_QUARTER_MAP = MONTH_TO_QUARTER  # alias


def _quarter_from_period_order(period_order: int, period_type: str) -> str | None:
    """Map period_order to Q1-Q4 string based on type."""
    if period_type == "M":
        return MONTH_TO_QUARTER.get(period_order)
    if period_type == "Q":
        return f"Q{period_order}"
    return None


def aggregate_monthly_to_quarterly(db: Session, year: int) -> dict:
    """
    Read raw monthly fact records for `year`, apply dim_period_mapping,
    compute AVG target/realization per (division, kpi, quarter), then
    upsert into fact_kpi_quarterly.
    Returns a summary dict.
    """
    # 1. Pull all monthly raw data for the year with period info
    raw_sql = text("""
        SELECT
            f.fact_id,
            f.division_id,
            f.kpi_id,
            f.year,
            f.target,
            f.realization,
            p.period_id,
            p.period_type,
            p.period_order,
            p.period_name
        FROM fact_kpi_performance f
        JOIN dim_period p ON f.period_id = p.period_id
        WHERE f.year = :year
        ORDER BY f.division_id, f.kpi_id, p.period_order
    """)
    raw_rows = db.execute(raw_sql, {"year": year}).fetchall()

    if not raw_rows:
        logger.warning(f"No raw data found for year {year}")
        return {"year": year, "processed": 0, "upserted": 0}

    # 2. Build quarter groups: key=(division_id, kpi_id, year, quarter)
    groups: dict = defaultdict(lambda: {"targets": [], "realizations": []})

    for row in raw_rows:
        quarter = _quarter_from_period_order(row.period_order, row.period_type)
        if quarter is None:
            logger.debug(f"Skipping period {row.period_name} (type={row.period_type})")
            continue
        key = (row.division_id, row.kpi_id, row.year, quarter)
        groups[key]["targets"].append(row.target)
        groups[key]["realizations"].append(row.realization)

    if not groups:
        logger.warning(f"No monthly data to aggregate for year {year}")
        return {"year": year, "processed": len(raw_rows), "upserted": 0}

    # 3. Upsert into fact_kpi_quarterly
    upserted = 0
    for (division_id, kpi_id, yr, quarter), vals in groups.items():
        targets = vals["targets"]
        realizations = vals["realizations"]

        avg_target = sum(targets) / len(targets)
        avg_realization = sum(realizations) / len(realizations)
        achievement = (avg_realization / avg_target * 100) if avg_target > 0 else 0.0

        # Check if row already exists
        check_sql = text("""
            SELECT id FROM fact_kpi_quarterly
            WHERE division_id = :did AND kpi_id = :kid
              AND quarter = :quarter AND year = :year
        """)
        existing = db.execute(check_sql, {
            "did": division_id, "kid": kpi_id,
            "quarter": quarter, "year": yr
        }).fetchone()

        if existing:
            update_sql = text("""
                UPDATE fact_kpi_quarterly
                SET target = :target, realization = :realization, achievement = :achievement
                WHERE id = :id
            """)
            db.execute(update_sql, {
                "target": avg_target,
                "realization": avg_realization,
                "achievement": achievement,
                "id": existing.id,
            })
        else:
            insert_sql = text("""
                INSERT INTO fact_kpi_quarterly
                    (division_id, kpi_id, quarter, year, target, realization, achievement)
                VALUES
                    (:did, :kid, :quarter, :year, :target, :realization, :achievement)
            """)
            db.execute(insert_sql, {
                "did": division_id, "kid": kpi_id,
                "quarter": quarter, "year": yr,
                "target": avg_target,
                "realization": avg_realization,
                "achievement": achievement,
            })
        upserted += 1

    db.commit()
    logger.info(f"ETL year={year}: processed={len(raw_rows)} rows, upserted={upserted} quarterly records")
    return {"year": year, "processed": len(raw_rows), "upserted": upserted}
