"""
ETL Runner — CLI entry point for the KPI aggregation pipeline.

Usage:
  python etl_runner.py               # Run ETL for current year (2025)
  python etl_runner.py --year 2024   # Run ETL for specific year
  python etl_runner.py --all         # Run ETL for all years in raw data
"""
import sys
import os
import argparse
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

from app.database import SessionLocal, engine, Base
import models  # noqa — register all ORM models

# Ensure tables exist
Base.metadata.create_all(bind=engine)

from services.etl_service import run_etl, run_etl_all_years


def main():
    parser = argparse.ArgumentParser(description="KPI ETL Aggregation Pipeline")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--year", type=int, help="Run ETL for a specific year (e.g. 2025)")
    group.add_argument("--all", action="store_true", help="Run ETL for all years in raw data")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        if args.all:
            logger.info("Running ETL for ALL years...")
            results = run_etl_all_years(db)
            for r in results:
                status = "✓" if r["status"] == "success" else "✗"
                print(f"  {status} Year {r['year']}: processed={r.get('processed',0)} rows, upserted={r.get('upserted',0)} quarterly records")
        else:
            import datetime
            year = args.year or datetime.date.today().year
            logger.info(f"Running ETL for year={year}...")
            result = run_etl(db, year)
            if result["status"] == "success":
                print(f"\n✅ ETL Success — year={result['year']}")
                print(f"   Raw rows processed : {result.get('processed', 0)}")
                print(f"   Quarterly upserted : {result.get('upserted', 0)}")
            else:
                print(f"\n❌ ETL Failed — year={result['year']}")
                print(f"   Error: {result.get('error', 'unknown')}")
                sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
