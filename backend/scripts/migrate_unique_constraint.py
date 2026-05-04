"""
Migration Script — Tambah UNIQUE Constraint ke fact_kpi_performance
=====================================================================
Jalankan script ini SEKALI sebelum menjalankan ETL pertama kali
jika database sudah terisi data sebelumnya (fresh install tidak perlu ini,
karena etl_csv.py menambahkan constraint secara otomatis).

Cara pakai:
  python scripts/migrate_unique_constraint.py

Script ini IDEMPOTEN: aman dijalankan berkali-kali.
"""

import sys
import os
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import text
from app.database import SessionLocal

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
)
logger = logging.getLogger(__name__)


def migrate():
    db = SessionLocal()
    try:
        # 1. Cek apakah constraint sudah ada
        check = text("""
            SELECT COUNT(*) FROM information_schema.table_constraints
            WHERE table_name = 'fact_kpi_performance'
              AND constraint_name = 'uq_kpi_period_year'
        """)
        exists = db.execute(check).scalar()

        if exists:
            logger.info("✓ Constraint 'uq_kpi_period_year' sudah ada — skip.")
            return

        # 2. Cek apakah ada data duplikat yang akan menghalangi penambahan constraint
        dup_check = text("""
            SELECT kpi_id, period_id, year, COUNT(*) as cnt
            FROM fact_kpi_performance
            GROUP BY kpi_id, period_id, year
            HAVING COUNT(*) > 1
        """)
        duplicates = db.execute(dup_check).fetchall()

        if duplicates:
            logger.warning("⚠ Ditemukan data duplikat — constraint tidak dapat ditambahkan sebelum duplikat dibersihkan:")
            for d in duplicates:
                logger.warning(f"  kpi_id={d.kpi_id}, period_id={d.period_id}, year={d.year} → {d.cnt} baris")
            logger.info("")
            logger.info("Jalankan query berikut di DBeaver untuk membersihkan duplikat:")
            logger.info("""
  DELETE FROM fact_kpi_performance
  WHERE fact_id NOT IN (
      SELECT MIN(fact_id)
      FROM fact_kpi_performance
      GROUP BY kpi_id, period_id, year
  );
            """)
            return

        # 3. Tambahkan constraint
        logger.info("Menambahkan UNIQUE constraint (uq_kpi_period_year)...")
        db.execute(text("""
            ALTER TABLE fact_kpi_performance
            ADD CONSTRAINT uq_kpi_period_year UNIQUE (kpi_id, period_id, year)
        """))
        db.commit()
        logger.info("✅ Constraint berhasil ditambahkan!")
        logger.info("   Sekarang ETL dapat dijalankan dengan aman.")

    except Exception as e:
        db.rollback()
        logger.error(f"❌ Migration gagal: {e}", exc_info=True)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    migrate()
