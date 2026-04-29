import sys, os
sys.path.insert(0, 'd:/projek_kp_2/backend')
os.chdir('d:/projek_kp_2/backend')
from dotenv import load_dotenv; load_dotenv()

print('Testing imports...')
from models.kpi import DimKpi; print('  [OK] models.kpi')
from schemas.admin import KpiCreate, KpiUpdate, KpiResponse; print('  [OK] schemas.admin')
from services.aggregation_service import calculate_kpi_annual, calculate_division_report; print('  [OK] services.aggregation_service')
from services.mcp_tools import get_overview_kpi, get_division_kpi; print('  [OK] services.mcp_tools')
from services.etl_service import run_etl; print('  [OK] services.etl_service')
from routers.admin import router as admin_router; print('  [OK] routers.admin')
from routers.dashboard import router as dash_router; print('  [OK] routers.dashboard')

print('\nTesting calculation...')
from app.database import SessionLocal
db = SessionLocal()

result = calculate_division_report(db, 1, 2025)
print(f'  Division 1 (Network) report: {result.get("division_report", "N/A")}%')
print(f'  KPIs computed: {len(result.get("kpis", []))}')
for k in result.get('kpis', []):
    print(f'    - {k["kpi_name"][:35]:35s} | eval={k["evaluation_period"]} | annual={k["annual_report"]:6.2f}% | weight={k["weight"]}%')

print('\n  All Divisions:')
overview = get_overview_kpi(db, 2025)
for d in overview.get('divisions', []):
    print(f'    {d["division_name"]:25s} Division Report: {d["division_report"]:6.2f}%  status={d["status"]}')
print(f'\n  Company Avg: {overview.get("company_avg", 0):.2f}%')

db.close()
print('\nAll OK!')
