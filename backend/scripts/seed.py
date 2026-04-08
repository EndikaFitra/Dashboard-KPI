"""
Seed script — populates all dimension tables and raw fact data.
Run from backend/ directory: python scripts/seed.py

Divisions:
  1 = Network        (H)
  2 = Software Eng   (Q)
  3 = Sales Exec     (Q)
  4 = HR Officer     (M)
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, engine, Base
import models  # noqa — registers all ORM models

# Create tables
Base.metadata.create_all(bind=engine)

from models.division import DimDivision
from models.kpi import DimKpi
from models.period import DimPeriod
from models.mapping import DimPeriodMapping
from models.fact_raw import FactKpiPerformance


def seed():
    db = SessionLocal()
    try:
        # ------------------------------------------------------------------ #
        # 1. DIVISIONS                                                         #
        # ------------------------------------------------------------------ #
        if db.query(DimDivision).count() == 0:
            divisions = [
                DimDivision(division_id=1, division_name="Network",          evaluation_period="H"),
                DimDivision(division_id=2, division_name="Software Engineer", evaluation_period="Q"),
                DimDivision(division_id=3, division_name="Sales Executive",  evaluation_period="Q"),
                DimDivision(division_id=4, division_name="HR Officer",       evaluation_period="M"),
            ]
            db.add_all(divisions)
            db.commit()
            print("✓ Seeded dim_division")

        # ------------------------------------------------------------------ #
        # 2. KPIs                                                              #
        # ------------------------------------------------------------------ #
        if db.query(DimKpi).count() == 0:
            kpis = [
                # Network (div 1) — total weight = 100%
                DimKpi(kpi_id=1, division_id=1, kpi_name="Melaksanakan delivery inovasi",     unit="unit", visualization_type="card",  default_target=1.0,       weight=5.0),
                DimKpi(kpi_id=2, division_id=1, kpi_name="Melakukan incident prevention",      unit="%",    visualization_type="bar",   default_target=100.0,     weight=35.0),
                DimKpi(kpi_id=3, division_id=1, kpi_name="SLA compliance",                     unit="%",    visualization_type="bar",   default_target=98.0,      weight=60.0),
                # Software Engineer (div 2) — total weight = 100%
                DimKpi(kpi_id=4, division_id=2, kpi_name="Productivity",                                unit="%",    visualization_type="bar",   default_target=100.0,  weight=25.0),
                DimKpi(kpi_id=5, division_id=2, kpi_name="Reduce bug rate in production environment",  unit="%",    visualization_type="bar",   default_target=95.0,   weight=25.0),
                DimKpi(kpi_id=6, division_id=2, kpi_name="Team collaboration",                         unit="%",    visualization_type="bar",   default_target=100.0,  weight=20.0),
                DimKpi(kpi_id=7, division_id=2, kpi_name="Create innovation or optimization",          unit="unit", visualization_type="card",  default_target=1.0,    weight=30.0),
                # Sales Executive (div 3) — total weight = 100%
                DimKpi(kpi_id=8,  division_id=3, kpi_name="Meningkatkan MRR perusahaan sesuai target",  unit="IDR",       visualization_type="card", default_target=30000000.0, weight=60.0),
                DimKpi(kpi_id=9,  division_id=3, kpi_name="Menambah jumlah customer baru",               unit="customer",  visualization_type="bar",  default_target=9.0,        weight=30.0),
                DimKpi(kpi_id=10, division_id=3, kpi_name="Target quotation terkirim untuk hot prospek", unit="quotation", visualization_type="bar",  default_target=30.0,       weight=10.0),
                # HR Officer (div 4) — total weight = 100%
                DimKpi(kpi_id=11, division_id=4, kpi_name="Melengkapi administrasi personalia",                  unit="%", visualization_type="bar", default_target=100.0, weight=20.0),
                DimKpi(kpi_id=12, division_id=4, kpi_name="Melengkapi administrasi rekrutmen dan seleksi",       unit="%", visualization_type="bar", default_target=100.0, weight=20.0),
                DimKpi(kpi_id=13, division_id=4, kpi_name="Melengkapi administrasi payroll",                     unit="%", visualization_type="bar", default_target=100.0, weight=20.0),
                DimKpi(kpi_id=14, division_id=4, kpi_name="Melengkapi administrasi kompetensi",                  unit="%", visualization_type="bar", default_target=100.0, weight=20.0),
                DimKpi(kpi_id=15, division_id=4, kpi_name="Follow up kegiatan HRGA",                             unit="%", visualization_type="bar", default_target=100.0, weight=20.0),
            ]
            db.add_all(kpis)
            db.commit()
            print("✓ Seeded dim_kpi")

        # ------------------------------------------------------------------ #
        # 3. PERIODS                                                           #
        # ------------------------------------------------------------------ #
        if db.query(DimPeriod).count() == 0:
            periods = [
                # Monthly (M) — period_order = month number
                DimPeriod(period_id=1,  period_name="Jan", period_type="M", period_order=1),
                DimPeriod(period_id=2,  period_name="Feb", period_type="M", period_order=2),
                DimPeriod(period_id=3,  period_name="Mar", period_type="M", period_order=3),
                DimPeriod(period_id=4,  period_name="Apr", period_type="M", period_order=4),
                DimPeriod(period_id=5,  period_name="May", period_type="M", period_order=5),
                DimPeriod(period_id=6,  period_name="Jun", period_type="M", period_order=6),
                DimPeriod(period_id=7,  period_name="Jul", period_type="M", period_order=7),
                DimPeriod(period_id=8,  period_name="Aug", period_type="M", period_order=8),
                DimPeriod(period_id=9,  period_name="Sep", period_type="M", period_order=9),
                DimPeriod(period_id=10, period_name="Oct", period_type="M", period_order=10),
                DimPeriod(period_id=11, period_name="Nov", period_type="M", period_order=11),
                DimPeriod(period_id=12, period_name="Dec", period_type="M", period_order=12),
                # Quarterly (Q) — period_order = quarter number
                DimPeriod(period_id=13, period_name="Q1", period_type="Q", period_order=1),
                DimPeriod(period_id=14, period_name="Q2", period_type="Q", period_order=2),
                DimPeriod(period_id=15, period_name="Q3", period_type="Q", period_order=3),
                DimPeriod(period_id=16, period_name="Q4", period_type="Q", period_order=4),
                # Half-year (H)
                DimPeriod(period_id=17, period_name="H1", period_type="H", period_order=1),
                DimPeriod(period_id=18, period_name="H2", period_type="H", period_order=2),
            ]
            db.add_all(periods)
            db.commit()
            print("✓ Seeded dim_period")

        # ------------------------------------------------------------------ #
        # 4. PERIOD MAPPINGS (Month → Quarter)                                #
        # ------------------------------------------------------------------ #
        if db.query(DimPeriodMapping).count() == 0:
            mappings = [
                # Q1: Jan(1), Feb(2), Mar(3) → Q1(13)
                DimPeriodMapping(source_period_id=1,  target_period_id=13, target_type="Q"),
                DimPeriodMapping(source_period_id=2,  target_period_id=13, target_type="Q"),
                DimPeriodMapping(source_period_id=3,  target_period_id=13, target_type="Q"),
                # Q2: Apr(4), May(5), Jun(6) → Q2(14)
                DimPeriodMapping(source_period_id=4,  target_period_id=14, target_type="Q"),
                DimPeriodMapping(source_period_id=5,  target_period_id=14, target_type="Q"),
                DimPeriodMapping(source_period_id=6,  target_period_id=14, target_type="Q"),
                # Q3: Jul(7), Aug(8), Sep(9) → Q3(15)
                DimPeriodMapping(source_period_id=7,  target_period_id=15, target_type="Q"),
                DimPeriodMapping(source_period_id=8,  target_period_id=15, target_type="Q"),
                DimPeriodMapping(source_period_id=9,  target_period_id=15, target_type="Q"),
                # Q4: Oct(10), Nov(11), Dec(12) → Q4(16)
                DimPeriodMapping(source_period_id=10, target_period_id=16, target_type="Q"),
                DimPeriodMapping(source_period_id=11, target_period_id=16, target_type="Q"),
                DimPeriodMapping(source_period_id=12, target_period_id=16, target_type="Q"),
            ]
            db.add_all(mappings)
            db.commit()
            print("✓ Seeded dim_period_mapping")

        # ------------------------------------------------------------------ #
        # 5. RAW FACT DATA — 2024 & 2025                                      #
        # ------------------------------------------------------------------ #
        if db.query(FactKpiPerformance).count() == 0:
            facts = []

            # Helper to add a monthly record
            def m(div, kpi, month, year, target, realization):
                facts.append(FactKpiPerformance(
                    division_id=div, kpi_id=kpi, period_id=month,
                    year=year, target=target, realization=realization,
                ))

            # ---- NETWORK (div=1): Half-year evaluation
            # For ETL purposes we store monthly data; H is derived from quarters
            # KPI 1: delivery inovasi (unit)
            for yr, vals in {
                2024: [(1,1.0,0.7),(2,1.0,0.8),(3,1.0,0.9),(4,1.0,0.8),(5,1.0,0.9),(6,1.0,1.0),
                        (7,1.0,0.8),(8,1.0,0.9),(9,1.0,1.0),(10,1.0,0.9),(11,1.0,1.0),(12,1.0,1.0)],
                2025: [(1,1.0,0.7),(2,1.0,0.8),(3,1.0,0.9),(4,1.0,1.0),(5,1.0,1.0),(6,1.0,1.0),
                        (7,1.0,0.8),(8,1.0,0.9),(9,1.0,1.0),(10,1.0,1.0),(11,1.0,1.0),(12,1.0,1.0)],
            }.items():
                for (mon, tgt, real) in vals:
                    m(1, 1, mon, yr, tgt, real)

            # KPI 2: incident prevention (%)
            for yr, vals in {
                2024: [(1,100,88),(2,100,90),(3,100,91),(4,100,89),(5,100,92),(6,100,93),
                        (7,100,90),(8,100,91),(9,100,93),(10,100,92),(11,100,94),(12,100,95)],
                2025: [(1,100,90),(2,100,91),(3,100,92),(4,100,93),(5,100,94),(6,100,95),
                        (7,100,92),(8,100,93),(9,100,94),(10,100,95),(11,100,96),(12,100,97)],
            }.items():
                for (mon, tgt, real) in vals:
                    m(1, 2, mon, yr, tgt, real)

            # KPI 3: SLA compliance (%)
            for yr, vals in {
                2024: [(1,98,95),(2,98,96),(3,98,97),(4,98,96),(5,98,97),(6,98,98),
                        (7,98,96),(8,98,97),(9,98,98),(10,98,97),(11,98,98),(12,98,99)],
                2025: [(1,98,96),(2,98,97),(3,98,97),(4,98,98),(5,98,98),(6,98,99),
                        (7,98,97),(8,98,98),(9,98,99),(10,98,98),(11,98,99),(12,98,99)],
            }.items():
                for (mon, tgt, real) in vals:
                    m(1, 3, mon, yr, tgt, real)

            # ---- SOFTWARE ENGINEER (div=2): Quarterly evaluation
            # KPI 4: Productivity (%)
            for yr, vals in {
                2024: [(1,100,88),(2,100,89),(3,100,90),(4,100,91),(5,100,92),(6,100,91),
                        (7,100,92),(8,100,93),(9,100,93),(10,100,94),(11,100,95),(12,100,94)],
                2025: [(1,100,92),(2,100,93),(3,100,94),(4,100,95),(5,100,95),(6,100,96),
                        (7,100,94),(8,100,95),(9,100,96),(10,100,97),(11,100,97),(12,100,98)],
            }.items():
                for (mon, tgt, real) in vals:
                    m(2, 4, mon, yr, tgt, real)

            # KPI 5: Reduce bug rate (%)
            for yr, vals in {
                2024: [(1,95,82),(2,95,84),(3,95,85),(4,95,86),(5,95,87),(6,95,87),
                        (7,95,88),(8,95,89),(9,95,89),(10,95,90),(11,95,90),(12,95,91)],
                2025: [(1,95,86),(2,95,87),(3,95,88),(4,95,89),(5,95,90),(6,95,90),
                        (7,95,89),(8,95,90),(9,95,91),(10,95,92),(11,95,92),(12,95,93)],
            }.items():
                for (mon, tgt, real) in vals:
                    m(2, 5, mon, yr, tgt, real)

            # KPI 6: Team collaboration (%)
            for yr, vals in {
                2024: [(1,100,93),(2,100,94),(3,100,95),(4,100,96),(5,100,96),(6,100,97),
                        (7,100,95),(8,100,96),(9,100,97),(10,100,97),(11,100,98),(12,100,98)],
                2025: [(1,100,96),(2,100,97),(3,100,97),(4,100,98),(5,100,98),(6,100,99),
                        (7,100,97),(8,100,98),(9,100,99),(10,100,99),(11,100,100),(12,100,100)],
            }.items():
                for (mon, tgt, real) in vals:
                    m(2, 6, mon, yr, tgt, real)

            # KPI 7: Innovation (unit)
            for yr, vals in {
                2024: [(1,1,1),(2,1,1),(3,1,1),(4,1,1),(5,1,1),(6,1,1),
                        (7,1,1),(8,1,1),(9,1,1),(10,1,1),(11,1,1),(12,1,1)],
                2025: [(1,1,1),(2,1,1),(3,1,1),(4,1,1),(5,1,1),(6,1,1),
                        (7,1,1),(8,1,1),(9,1,1),(10,1,1),(11,1,1),(12,1,1)],
            }.items():
                for (mon, tgt, real) in vals:
                    m(2, 7, mon, yr, tgt, real)

            # ---- SALES EXECUTIVE (div=3): Quarterly
            # KPI 8: MRR (IDR)
            for yr, vals in {
                2024: [(1,30e6,20e6),(2,30e6,22e6),(3,30e6,23e6),(4,30e6,24e6),(5,30e6,25e6),(6,30e6,26e6),
                        (7,30e6,24e6),(8,30e6,25e6),(9,30e6,26e6),(10,30e6,25e6),(11,30e6,26e6),(12,30e6,27e6)],
                2025: [(1,30e6,22e6),(2,30e6,24e6),(3,30e6,25e6),(4,30e6,26e6),(5,30e6,27e6),(6,30e6,28e6),
                        (7,30e6,25e6),(8,30e6,26e6),(9,30e6,27e6),(10,30e6,26e6),(11,30e6,27e6),(12,30e6,28e6)],
            }.items():
                for (mon, tgt, real) in vals:
                    m(3, 8, mon, yr, tgt, real)

            # KPI 9: New customers
            for yr, vals in {
                2024: [(1,9,6),(2,9,7),(3,9,7),(4,9,7),(5,9,8),(6,9,8),
                        (7,9,7),(8,9,7),(9,9,8),(10,9,8),(11,9,9),(12,9,9)],
                2025: [(1,9,6),(2,9,7),(3,9,7),(4,9,8),(5,9,8),(6,9,9),
                        (7,9,7),(8,9,8),(9,9,9),(10,9,8),(11,9,9),(12,9,9)],
            }.items():
                for (mon, tgt, real) in vals:
                    m(3, 9, mon, yr, tgt, real)

            # KPI 10: Quotations sent
            for yr, vals in {
                2024: [(1,30,25),(2,30,27),(3,30,28),(4,30,27),(5,30,28),(6,30,29),
                        (7,30,27),(8,30,28),(9,30,29),(10,30,28),(11,30,29),(12,30,30)],
                2025: [(1,30,26),(2,30,27),(3,30,28),(4,30,28),(5,30,29),(6,30,30),
                        (7,30,27),(8,30,28),(9,30,29),(10,30,29),(11,30,30),(12,30,30)],
            }.items():
                for (mon, tgt, real) in vals:
                    m(3, 10, mon, yr, tgt, real)

            # ---- HR OFFICER (div=4): Monthly
            # KPI 11: Admin personalia
            for yr, vals in {
                2024: [(1,100,98),(2,100,99),(3,100,100),(4,100,99),(5,100,100),(6,100,100),
                        (7,100,99),(8,100,100),(9,100,100),(10,100,100),(11,100,100),(12,100,100)],
                2025: [(1,100,100),(2,100,100),(3,100,100),(4,100,100),(5,100,100),(6,100,100),
                        (7,100,100),(8,100,100),(9,100,100),(10,100,100),(11,100,100),(12,100,100)],
            }.items():
                for (mon, tgt, real) in vals:
                    m(4, 11, mon, yr, tgt, real)

            # KPI 12: Rekrutmen
            for yr, vals in {
                2024: [(1,100,90),(2,100,92),(3,100,93),(4,100,94),(5,100,95),(6,100,95),
                        (7,100,93),(8,100,94),(9,100,95),(10,100,95),(11,100,96),(12,100,97)],
                2025: [(1,100,93),(2,100,94),(3,100,95),(4,100,95),(5,100,96),(6,100,96),
                        (7,100,94),(8,100,95),(9,100,96),(10,100,96),(11,100,97),(12,100,97)],
            }.items():
                for (mon, tgt, real) in vals:
                    m(4, 12, mon, yr, tgt, real)

            # KPI 13: Payroll
            for yr, vals in {
                2024: [(1,100,98),(2,100,99),(3,100,100),(4,100,100),(5,100,100),(6,100,100),
                        (7,100,99),(8,100,100),(9,100,100),(10,100,100),(11,100,100),(12,100,100)],
                2025: [(1,100,100),(2,100,100),(3,100,100),(4,100,100),(5,100,100),(6,100,100),
                        (7,100,100),(8,100,100),(9,100,100),(10,100,100),(11,100,100),(12,100,100)],
            }.items():
                for (mon, tgt, real) in vals:
                    m(4, 13, mon, yr, tgt, real)

            # KPI 14: Kompetensi
            for yr, vals in {
                2024: [(1,100,82),(2,100,84),(3,100,85),(4,100,86),(5,100,87),(6,100,88),
                        (7,100,86),(8,100,87),(9,100,88),(10,100,87),(11,100,88),(12,100,89)],
                2025: [(1,100,85),(2,100,86),(3,100,87),(4,100,88),(5,100,89),(6,100,90),
                        (7,100,87),(8,100,88),(9,100,89),(10,100,89),(11,100,90),(12,100,91)],
            }.items():
                for (mon, tgt, real) in vals:
                    m(4, 14, mon, yr, tgt, real)

            # KPI 15: Follow up HRGA (%)
            for yr, vals in {
                2024: [(1,100,88),(2,100,89),(3,100,90),(4,100,91),(5,100,92),(6,100,92),
                        (7,100,90),(8,100,91),(9,100,92),(10,100,92),(11,100,93),(12,100,94)],
                2025: [(1,100,90),(2,100,91),(3,100,92),(4,100,92),(5,100,93),(6,100,94),
                        (7,100,91),(8,100,92),(9,100,93),(10,100,93),(11,100,94),(12,100,95)],
            }.items():
                for (mon, tgt, real) in vals:
                    m(4, 15, mon, yr, tgt, real)

            db.add_all(facts)
            db.commit()
            print(f"✓ Seeded fact_kpi_performance ({len(facts)} records)")

        print("\n✅ Database seeding complete!")
        print("   Run ETL next:  python etl_runner.py")

    except Exception as e:
        db.rollback()
        print(f"\n❌ Seeding failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
