"""
Seed script v2 — Database baru dengan schema per-indikator.

Perbedaan dari seed.py lama:
  - DimKpi sekarang punya kolom evaluation_period sendiri (M/Q/H)
  - Data fakta (fact_kpi_performance) diinput sesuai evaluation_period masing-masing KPI:
      * Network KPI (H) → input per H1/H2 (period_id 17, 18)
      * Software Engineer KPI (Q) → input per Q1/Q2/Q3/Q4 (period_id 13-16)
      * Sales Executive KPI (Q) → input per Q1/Q2/Q3/Q4 (period_id 13-16)
      * HR Officer KPI (M) → input per Jan–Dec (period_id 1-12)
  - Tabel fact_kpi_quarterly TIDAK di-seed (tidak digunakan lagi)

Run: python scripts/seed_v2.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, engine, Base
import models  # noqa

Base.metadata.create_all(bind=engine)

from models.division import DimDivision
from models.kpi import DimKpi
from models.period import DimPeriod
from models.fact_raw import FactKpiPerformance


def seed():
    db = SessionLocal()
    try:
        # ─────────────────────────────────────────────────────────────────── #
        # 1. DIVISIONS                                                         #
        # ─────────────────────────────────────────────────────────────────── #
        if db.query(DimDivision).count() == 0:
            db.add_all([
                DimDivision(division_id=1, division_name="Network",          evaluation_period="H"),
                DimDivision(division_id=2, division_name="Software Engineer", evaluation_period="Q"),
                DimDivision(division_id=3, division_name="Sales Executive",  evaluation_period="Q"),
                DimDivision(division_id=4, division_name="HR Officer",       evaluation_period="M"),
            ])
            db.commit()
            print("✓ Seeded dim_division (4 rows)")

        # ─────────────────────────────────────────────────────────────────── #
        # 2. KPIs — dengan evaluation_period per KPI                          #
        # ─────────────────────────────────────────────────────────────────── #
        if db.query(DimKpi).count() == 0:
            db.add_all([
                # ── Network (div 1) — KPI 1&2: Half Year (H), KPI 3: Quarterly (Q) ── #
                DimKpi(kpi_id=1,  division_id=1, evaluation_period="H",
                       kpi_name="Melaksanakan delivery inovasi",
                       unit="unit", visualization_type="card",
                       default_target=1.0, weight=5.0),
                DimKpi(kpi_id=2,  division_id=1, evaluation_period="H",
                       kpi_name="Melakukan incident prevention",
                       unit="%", visualization_type="bar",
                       default_target=100.0, weight=35.0),
                DimKpi(kpi_id=3,  division_id=1, evaluation_period="Q",
                       kpi_name="SLA compliance",
                       unit="%", visualization_type="bar",
                       default_target=98.0, weight=60.0),

                # ── Software Engineer (div 2) — KPI 4/5/6: Monthly (M), KPI 7: Quarterly (Q) ── #
                DimKpi(kpi_id=4,  division_id=2, evaluation_period="M",
                       kpi_name="Productivity",
                       unit="%", visualization_type="bar",
                       default_target=100.0, weight=25.0),
                DimKpi(kpi_id=5,  division_id=2, evaluation_period="M",
                       kpi_name="Reduce bug rate in production environment",
                       unit="%", visualization_type="bar",
                       default_target=95.0, weight=25.0),
                DimKpi(kpi_id=6,  division_id=2, evaluation_period="M",
                       kpi_name="Team collaboration",
                       unit="%", visualization_type="bar",
                       default_target=100.0, weight=20.0),
                DimKpi(kpi_id=7,  division_id=2, evaluation_period="Q",
                       kpi_name="Create innovation or optimization",
                       unit="unit", visualization_type="card",
                       default_target=1.0, weight=30.0),

                # ── Sales Executive (div 3) — evaluasi Quarterly (Q) ───── #
                DimKpi(kpi_id=8,  division_id=3, evaluation_period="Q",
                       kpi_name="Meningkatkan MRR perusahaan sesuai target",
                       unit="IDR", visualization_type="card",
                       default_target=30_000_000.0, weight=60.0),
                DimKpi(kpi_id=9,  division_id=3, evaluation_period="Q",
                       kpi_name="Menambah jumlah customer baru",
                       unit="customer", visualization_type="bar",
                       default_target=9.0, weight=30.0),
                DimKpi(kpi_id=10, division_id=3, evaluation_period="Q",
                       kpi_name="Target quotation terkirim untuk hot prospek",
                       unit="quotation", visualization_type="bar",
                       default_target=30.0, weight=10.0),

                # ── HR Officer (div 4) — evaluasi Monthly (M) ─────────── #
                DimKpi(kpi_id=11, division_id=4, evaluation_period="M",
                       kpi_name="Melengkapi administrasi personalia",
                       unit="%", visualization_type="bar",
                       default_target=100.0, weight=20.0),
                DimKpi(kpi_id=12, division_id=4, evaluation_period="M",
                       kpi_name="Melengkapi administrasi rekrutmen dan seleksi",
                       unit="%", visualization_type="bar",
                       default_target=100.0, weight=20.0),
                DimKpi(kpi_id=13, division_id=4, evaluation_period="M",
                       kpi_name="Melengkapi administrasi payroll",
                       unit="%", visualization_type="bar",
                       default_target=100.0, weight=20.0),
                DimKpi(kpi_id=14, division_id=4, evaluation_period="M",
                       kpi_name="Melengkapi administrasi kompetensi",
                       unit="%", visualization_type="bar",
                       default_target=100.0, weight=20.0),
                DimKpi(kpi_id=15, division_id=4, evaluation_period="M",
                       kpi_name="Follow up kegiatan HRGA",
                       unit="%", visualization_type="bar",
                       default_target=100.0, weight=20.0),
            ])
            db.commit()
            print("✓ Seeded dim_kpi (15 rows, dengan evaluation_period per KPI)")

        # ─────────────────────────────────────────────────────────────────── #
        # 3. PERIODS                                                           #
        # ─────────────────────────────────────────────────────────────────── #
        if db.query(DimPeriod).count() == 0:
            db.add_all([
                # Monthly (M)
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
                # Quarterly (Q)
                DimPeriod(period_id=13, period_name="Q1", period_type="Q", period_order=1),
                DimPeriod(period_id=14, period_name="Q2", period_type="Q", period_order=2),
                DimPeriod(period_id=15, period_name="Q3", period_type="Q", period_order=3),
                DimPeriod(period_id=16, period_name="Q4", period_type="Q", period_order=4),
                # Half Year (H)
                DimPeriod(period_id=17, period_name="H1", period_type="H", period_order=1),
                DimPeriod(period_id=18, period_name="H2", period_type="H", period_order=2),
            ])
            db.commit()
            print("✓ Seeded dim_period (18 rows)")

        # ─────────────────────────────────────────────────────────────────── #
        # 4. FACT DATA — 2024 & 2025                                          #
        # Input WAJIB sesuai evaluation_period masing-masing KPI:             #
        #   KPI 1 (inovasi)      : H  → period_id 17 (H1), 18 (H2)           #
        #   KPI 2 (prevention)   : H  → period_id 17 (H1), 18 (H2)           #
        #   KPI 3 (SLA)          : Q  → period_id 13-16 (Q1-Q4)              #
        #   KPI 4 (productivity) : M  → period_id 1-12 (Jan-Dec)             #
        #   KPI 5 (bug rate)     : M  → period_id 1-12 (Jan-Dec)             #
        #   KPI 6 (collab)       : M  → period_id 1-12 (Jan-Dec)             #
        #   KPI 7 (innovation SE): Q  → period_id 13-16 (Q1-Q4)             #
        #   KPI 8-10 (Sales)     : Q  → period_id 13-16 (Q1-Q4)             #
        #   KPI 11-15 (HR)       : M  → period_id 1-12 (Jan-Dec)            #
        # ─────────────────────────────────────────────────────────────────── #
        if db.query(FactKpiPerformance).count() == 0:
            facts = []

            def f(div, kpi, period_id, year, target, realization):
                facts.append(FactKpiPerformance(
                    division_id=div, kpi_id=kpi, period_id=period_id,
                    year=year, target=target, realization=realization,
                ))

            # ═══════════════════════════════════════════════════════════════ #
            # NETWORK (div=1, eval=H) — input per H1 / H2                    #
            # ═══════════════════════════════════════════════════════════════ #
            # KPI 1: delivery inovasi (target 1 unit per semester)
            # H1 = semester Jan-Jun, H2 = semester Jul-Des
            for yr, data in {
                2024: [(17, 1.0, 0.8), (18, 1.0, 1.0)],   # H1: 80%, H2: 100%
                2025: [(17, 1.0, 1.0), (18, 1.0, 1.0)],   # H1: 100%, H2: 100%
            }.items():
                for (pid, tgt, real) in data:
                    f(1, 1, pid, yr, tgt, real)

            # KPI 2: incident prevention (%)
            for yr, data in {
                2024: [(17, 100, 91), (18, 100, 93)],      # H1: 91%, H2: 93%
                2025: [(17, 100, 94), (18, 100, 95)],      # H1: 94%, H2: 95%
            }.items():
                for (pid, tgt, real) in data:
                    f(1, 2, pid, yr, tgt, real)

            # KPI 3: SLA compliance (%) — eval=Q → per Q1/Q2/Q3/Q4
            for yr, data in {
                2024: [(13, 98, 95.5), (14, 98, 96.5), (15, 98, 97.0), (16, 98, 97.5)],
                2025: [(13, 98, 97.0), (14, 98, 97.5), (15, 98, 98.0), (16, 98, 98.5)],
            }.items():
                for (pid, tgt, real) in data:
                    f(1, 3, pid, yr, tgt, real)

            # ═══════════════════════════════════════════════════════════════ #
            # SOFTWARE ENGINEER (div=2)                                       #
            #   KPI 4/5/6 → Monthly (M), KPI 7 → Quarterly (Q)              #
            # ═══════════════════════════════════════════════════════════════ #
            # KPI 4: Productivity (%) — eval=M → per Jan-Dec
            for yr, data in {
                2024: [(1,100,88),(2,100,89),(3,100,90),(4,100,91),(5,100,92),(6,100,91),
                       (7,100,92),(8,100,93),(9,100,93),(10,100,94),(11,100,95),(12,100,94)],
                2025: [(1,100,92),(2,100,93),(3,100,94),(4,100,95),(5,100,95),(6,100,96),
                       (7,100,94),(8,100,95),(9,100,96),(10,100,97),(11,100,97),(12,100,98)],
            }.items():
                for (pid, tgt, real) in data:
                    f(2, 4, pid, yr, tgt, real)

            # KPI 5: Reduce bug rate (%) — eval=M → per Jan-Dec
            for yr, data in {
                2024: [(1,95,82),(2,95,84),(3,95,85),(4,95,86),(5,95,87),(6,95,87),
                       (7,95,88),(8,95,89),(9,95,89),(10,95,90),(11,95,90),(12,95,91)],
                2025: [(1,95,86),(2,95,87),(3,95,88),(4,95,89),(5,95,90),(6,95,90),
                       (7,95,89),(8,95,90),(9,95,91),(10,95,92),(11,95,92),(12,95,93)],
            }.items():
                for (pid, tgt, real) in data:
                    f(2, 5, pid, yr, tgt, real)

            # KPI 6: Team collaboration (%) — eval=M → per Jan-Dec
            for yr, data in {
                2024: [(1,100,93),(2,100,94),(3,100,95),(4,100,96),(5,100,96),(6,100,97),
                       (7,100,95),(8,100,96),(9,100,97),(10,100,97),(11,100,98),(12,100,98)],
                2025: [(1,100,96),(2,100,97),(3,100,97),(4,100,98),(5,100,98),(6,100,99),
                       (7,100,97),(8,100,98),(9,100,99),(10,100,99),(11,100,100),(12,100,100)],
            }.items():
                for (pid, tgt, real) in data:
                    f(2, 6, pid, yr, tgt, real)

            # KPI 7: Innovation (unit) — eval=Q → per Q1/Q2/Q3/Q4
            for yr, data in {
                2024: [(13, 1, 1), (14, 1, 1), (15, 1, 1), (16, 1, 1)],
                2025: [(13, 1, 1), (14, 1, 1), (15, 1, 1), (16, 1, 1)],
            }.items():
                for (pid, tgt, real) in data:
                    f(2, 7, pid, yr, tgt, real)

            # ═══════════════════════════════════════════════════════════════ #
            # SALES EXECUTIVE (div=3, eval=Q) — input per Q1/Q2/Q3/Q4       #
            # ═══════════════════════════════════════════════════════════════ #
            # KPI 8: MRR (IDR)
            for yr, data in {
                2024: [(13, 30e6, 22e6), (14, 30e6, 25e6), (15, 30e6, 25e6), (16, 30e6, 26e6)],
                2025: [(13, 30e6, 24e6), (14, 30e6, 27e6), (15, 30e6, 26e6), (16, 30e6, 28e6)],
            }.items():
                for (pid, tgt, real) in data:
                    f(3, 8, pid, yr, tgt, real)

            # KPI 9: New customers
            for yr, data in {
                2024: [(13, 9, 7), (14, 9, 8), (15, 9, 8), (16, 9, 9)],
                2025: [(13, 9, 7), (14, 9, 8), (15, 9, 9), (16, 9, 9)],
            }.items():
                for (pid, tgt, real) in data:
                    f(3, 9, pid, yr, tgt, real)

            # KPI 10: Quotations sent
            for yr, data in {
                2024: [(13, 30, 27), (14, 30, 28), (15, 30, 28), (16, 30, 29)],
                2025: [(13, 30, 27), (14, 30, 29), (15, 30, 29), (16, 30, 30)],
            }.items():
                for (pid, tgt, real) in data:
                    f(3, 10, pid, yr, tgt, real)

            # ═══════════════════════════════════════════════════════════════ #
            # HR OFFICER (div=4, eval=M) — input per Jan-Dec                 #
            # ═══════════════════════════════════════════════════════════════ #
            # KPI 11: Admin personalia
            for yr, data in {
                2024: [(1,100,98),(2,100,99),(3,100,100),(4,100,99),(5,100,100),(6,100,100),
                       (7,100,99),(8,100,100),(9,100,100),(10,100,100),(11,100,100),(12,100,100)],
                2025: [(1,100,100),(2,100,100),(3,100,100),(4,100,100),(5,100,100),(6,100,100),
                       (7,100,100),(8,100,100),(9,100,100),(10,100,100),(11,100,100),(12,100,100)],
            }.items():
                for (pid, tgt, real) in data:
                    f(4, 11, pid, yr, tgt, real)

            # KPI 12: Rekrutmen
            for yr, data in {
                2024: [(1,100,90),(2,100,92),(3,100,93),(4,100,94),(5,100,95),(6,100,95),
                       (7,100,93),(8,100,94),(9,100,95),(10,100,95),(11,100,96),(12,100,97)],
                2025: [(1,100,93),(2,100,94),(3,100,95),(4,100,95),(5,100,96),(6,100,96),
                       (7,100,94),(8,100,95),(9,100,96),(10,100,96),(11,100,97),(12,100,97)],
            }.items():
                for (pid, tgt, real) in data:
                    f(4, 12, pid, yr, tgt, real)

            # KPI 13: Payroll
            for yr, data in {
                2024: [(1,100,98),(2,100,99),(3,100,100),(4,100,100),(5,100,100),(6,100,100),
                       (7,100,99),(8,100,100),(9,100,100),(10,100,100),(11,100,100),(12,100,100)],
                2025: [(1,100,100),(2,100,100),(3,100,100),(4,100,100),(5,100,100),(6,100,100),
                       (7,100,100),(8,100,100),(9,100,100),(10,100,100),(11,100,100),(12,100,100)],
            }.items():
                for (pid, tgt, real) in data:
                    f(4, 13, pid, yr, tgt, real)

            # KPI 14: Kompetensi
            for yr, data in {
                2024: [(1,100,82),(2,100,84),(3,100,85),(4,100,86),(5,100,87),(6,100,88),
                       (7,100,86),(8,100,87),(9,100,88),(10,100,87),(11,100,88),(12,100,89)],
                2025: [(1,100,85),(2,100,86),(3,100,87),(4,100,88),(5,100,89),(6,100,90),
                       (7,100,87),(8,100,88),(9,100,89),(10,100,89),(11,100,90),(12,100,91)],
            }.items():
                for (pid, tgt, real) in data:
                    f(4, 14, pid, yr, tgt, real)

            # KPI 15: Follow up HRGA
            for yr, data in {
                2024: [(1,100,88),(2,100,89),(3,100,90),(4,100,91),(5,100,92),(6,100,92),
                       (7,100,90),(8,100,91),(9,100,92),(10,100,92),(11,100,93),(12,100,94)],
                2025: [(1,100,90),(2,100,91),(3,100,92),(4,100,92),(5,100,93),(6,100,94),
                       (7,100,91),(8,100,92),(9,100,93),(10,100,93),(11,100,94),(12,100,95)],
            }.items():
                for (pid, tgt, real) in data:
                    f(4, 15, pid, yr, tgt, real)

            db.add_all(facts)
            db.commit()
            print(f"✓ Seeded fact_kpi_performance ({len(facts)} records)")
            print("  → KPI 1,2 (Network): per H1/H2")
            print("  → KPI 3 (SLA): per Q1/Q2/Q3/Q4")
            print("  → KPI 4,5,6 (SE Productivity/BugRate/Collab): per Jan-Dec")
            print("  → KPI 7 (SE Innovation): per Q1/Q2/Q3/Q4")
            print("  → KPI 8,9,10 (Sales): per Q1/Q2/Q3/Q4")
            print("  → KPI 11-15 (HR): per Jan-Dec")

        print("\n✅ Database v2 seeding complete!")
        print("   Dashboard sudah siap — tidak perlu run ETL.")

    except Exception as e:
        db.rollback()
        print(f"\n❌ Seeding failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
