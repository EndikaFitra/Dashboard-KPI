"""
MCP Tools v2 — Production-grade domain analytics interface for KPI LLM chatbot.

Layers:
  GUARDRAILS  → validate_query_intent, check_division_access
  SEMANTIC    → explain_kpi_definition
  ANALYTICAL  → analyze_kpi_drop, get_kpi_contribution, detect_kpi_anomaly
  CORE DATA   → get_overview_kpi, get_division_kpi, get_kpi_trend,
                 get_underperforming_kpi, compare_divisions

Rules:
  - NO raw SQL exposed to LLM
  - NO generic query interface
  - ALL outputs are deterministic, structured, LLM-friendly JSON
  - Invalid queries return structured refusal, never hallucination
"""
import re
import logging
import statistics
from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

from services.aggregation_service import (
    calculate_division_report,
    calculate_kpi_annual,
    _achievement_status,
)

logger = logging.getLogger(__name__)
CURRENT_YEAR = datetime.now().year

# ── Domain registries ────────────────────────────────────────────────────── #

DIVISION_REGISTRY: Dict[int, Dict] = {
    1: {"name": "Network",           "sensitive": False},
    2: {"name": "Software Engineer", "sensitive": False},
    3: {"name": "Sales Executive",   "sensitive": False},
    4: {"name": "HR Officer",        "sensitive": True},
}

KPI_DEFINITIONS: Dict[str, Dict] = {
    "sla compliance": {
        "full_name": "SLA Compliance", "division": "Network",
        "definition": "Persentase layanan jaringan yang memenuhi Service Level Agreement. Mengukur keandalan dan ketersediaan infrastruktur.",
        "unit": "%", "weight": 60, "evaluation_period": "Half Year",
        "higher_is_better": True, "benchmark": "≥99% untuk layanan kritis",
    },
    "incident prevention": {
        "full_name": "Incident Prevention", "division": "Network",
        "definition": "Kemampuan tim mencegah insiden jaringan tidak terencana. Diukur dari rasio pencegahan terhadap potensi insiden teridentifikasi.",
        "unit": "%", "weight": 35, "evaluation_period": "Half Year", "higher_is_better": True,
    },
    "delivery inovasi": {
        "full_name": "Delivery Inovasi", "division": "Network",
        "definition": "Persentase inisiatif inovasi infrastruktur yang berhasil di-deliver sesuai jadwal.",
        "unit": "%", "weight": 5, "evaluation_period": "Half Year", "higher_is_better": True,
    },
    "inovasi": {
        "full_name": "Inovasi & Optimasi", "division": "Software Engineer",
        "definition": "Output inovasi teknis — fitur baru, optimasi performa sistem, atau adopsi teknologi baru yang memberikan dampak nyata.",
        "unit": "%", "weight": 30, "evaluation_period": "Quarterly", "higher_is_better": True,
    },
    "productivity": {
        "full_name": "Productivity", "division": "Software Engineer",
        "definition": "Persentase deliverable yang diselesaikan dari target sprint. Mencerminkan efisiensi throughput tim engineering.",
        "unit": "%", "weight": 25, "evaluation_period": "Quarterly", "higher_is_better": True,
    },
    "bug rate": {
        "full_name": "Bug Rate", "division": "Software Engineer",
        "definition": "Rasio bug terhadap jumlah fitur yang dirilis. Achievement dihitung terbalik: bug rate rendah = achievement tinggi.",
        "unit": "%", "weight": 25, "evaluation_period": "Quarterly",
        "higher_is_better": False, "note": "Lower = better",
    },
    "kolaborasi": {
        "full_name": "Kolaborasi", "division": "Software Engineer",
        "definition": "Skor kolaborasi lintas tim — code review, dokumentasi, kontribusi pada proyek divisi lain.",
        "unit": "%", "weight": 20, "evaluation_period": "Quarterly", "higher_is_better": True,
    },
    "mrr": {
        "full_name": "Monthly Recurring Revenue (MRR)", "division": "Sales Executive",
        "definition": "Total pendapatan berulang yang dikontrak per bulan. KPI utama kesehatan pipeline revenue jangka panjang.",
        "unit": "IDR", "weight": 60, "evaluation_period": "Quarterly", "higher_is_better": True,
    },
    "customer baru": {
        "full_name": "Akuisisi Customer Baru", "division": "Sales Executive",
        "definition": "Jumlah customer baru yang berhasil di-onboard dibanding target. Mengukur efektivitas prospecting dan closing.",
        "unit": "customer", "weight": 30, "evaluation_period": "Quarterly", "higher_is_better": True,
    },
    "quotation": {
        "full_name": "Quotation Conversion Rate", "division": "Sales Executive",
        "definition": "Persentase quotation yang berhasil dikonversi menjadi kontrak. Mencerminkan kualitas proposal dan kemampuan negosiasi.",
        "unit": "%", "weight": 10, "evaluation_period": "Quarterly", "higher_is_better": True,
    },
}

_REFUSE_PATTERNS = [
    (r"\b(delete|drop|truncate|alter|insert|update)\b", "Permintaan modifikasi data tidak didukung."),
    (r"password|credential|token|secret",               "Permintaan terkait keamanan sistem tidak diproses."),
    (r"gaji.+individu|slip.+gaji|kompensasi.+personal", "Data kompensasi individu bersifat rahasia."),
    (r"data.+pribadi|nama.+karyawan",                   "Data personal karyawan tidak tersedia di sini."),
]


def _meta() -> Dict:
    return {"generated_at": datetime.now().isoformat(), "data_source": "fact_kpi_performance"}


# ═══════════════════════════════════════════════════════════════════════════ #
#  GUARDRAILS                                                                 #
# ═══════════════════════════════════════════════════════════════════════════ #

def validate_query_intent(question: str) -> Dict[str, Any]:
    """Periksa apakah pertanyaan valid dan aman sebelum memanggil tools."""
    q = question.lower()
    for pattern, reason in _REFUSE_PATTERNS:
        if re.search(pattern, q):
            return {"valid": False, "action": "REFUSE", "reason": reason}
    return {"valid": True, "action": "PROCEED"}


def check_division_access(division_id: int, user_role: str = "viewer") -> Dict[str, Any]:
    """Periksa apakah user_role diizinkan mengakses data divisi tertentu."""
    div = DIVISION_REGISTRY.get(division_id)
    if not div:
        return {"allowed": False, "reason": f"Division ID {division_id} tidak dikenal."}
    if div["sensitive"] and user_role not in ("admin", "hr_manager"):
        return {
            "allowed": False,
            "reason": f"Akses ke data {div['name']} memerlukan role 'admin' atau 'hr_manager'. Role saat ini: '{user_role}'.",
        }
    return {"allowed": True, "division_name": div["name"]}


# ═══════════════════════════════════════════════════════════════════════════ #
#  SEMANTIC LAYER                                                             #
# ═══════════════════════════════════════════════════════════════════════════ #

def explain_kpi_definition(db: Session, kpi_name: str = "", kpi_id: int = 0) -> Dict[str, Any]:
    """
    Kembalikan definisi, konteks bisnis, dan metadata KPI.
    Lookup berdasarkan kpi_id (dari DB) atau kpi_name (dari registry).
    """
    # Jika kpi_id diberikan, ambil nama dari DB
    if kpi_id:
        row = db.execute(
            text("SELECT kpi_name, unit, weight, evaluation_period FROM dim_kpi WHERE kpi_id = :id"),
            {"id": kpi_id}
        ).fetchone()
        if not row:
            return {"error": f"KPI ID {kpi_id} tidak ditemukan.", "action": "REFUSE"}
        kpi_name = row.kpi_name

    # Fuzzy match ke registry
    normalized = kpi_name.strip().lower()
    definition = None
    for key, val in KPI_DEFINITIONS.items():
        if key in normalized or normalized in key:
            definition = val
            break

    if definition:
        return {
            "kpi_name":          kpi_name,
            "full_name":         definition["full_name"],
            "division":          definition["division"],
            "definition":        definition["definition"],
            "unit":              definition["unit"],
            "weight_pct":        definition.get("weight"),
            "evaluation_period": definition["evaluation_period"],
            "higher_is_better":  definition["higher_is_better"],
            "benchmark":         definition.get("benchmark"),
            "note":              definition.get("note"),
            "metadata":          _meta(),
        }

    # Fallback: kembalikan info dari DB tanpa definisi naratif
    if kpi_id:
        return {
            "kpi_name":    kpi_name,
            "kpi_id":      kpi_id,
            "unit":        row.unit,
            "weight_pct":  row.weight,
            "evaluation_period": row.evaluation_period,
            "definition":  "Definisi belum tersedia dalam registry.",
            "metadata":    _meta(),
        }

    return {"error": f"KPI '{kpi_name}' tidak ditemukan.", "action": "REFUSE"}


# ═══════════════════════════════════════════════════════════════════════════ #
#  ANALYTICAL TOOLS                                                           #
# ═══════════════════════════════════════════════════════════════════════════ #

def analyze_kpi_drop(
    db: Session, division_id: Optional[int], year: int, compare_year: Optional[int] = None
) -> Dict[str, Any]:
    """
    Jelaskan mengapa performa naik/turun antara dua tahun.
    - division_id=None atau 0 → analisis company-wide (semua divisi)
    - division_id=1..4       → analisis satu divisi spesifik
    """
    compare_year = compare_year or (year - 1)

    # ── Company-wide mode ───────────────────────────────────────────────── #
    if not division_id:
        div_rows = db.execute(
            text("SELECT division_id FROM dim_division ORDER BY division_id")
        ).fetchall()

        division_deltas: List[Dict] = []
        curr_totals, prev_totals = [], []

        for dr in div_rows:
            curr = calculate_division_report(db, dr.division_id, year)
            prev = calculate_division_report(db, dr.division_id, compare_year)
            if "error" in curr or "error" in prev:
                continue
            c_val = curr["division_report"]
            p_val = prev["division_report"]
            delta = round(c_val - p_val, 2)
            curr_totals.append(c_val)
            prev_totals.append(p_val)
            division_deltas.append({
                "division_id":              curr["division_id"],
                "division_name":            curr["division_name"],
                "division_report_current":  c_val,
                "division_report_previous": p_val,
                "delta":                    delta,
                "direction": "improvement" if delta > 0 else "drop" if delta < 0 else "stable",
            })

        if not division_deltas:
            return {"error": f"Data tidak tersedia untuk perbandingan tahun {compare_year} → {year}."}

        company_curr = round(sum(curr_totals) / len(curr_totals), 2)
        company_prev = round(sum(prev_totals) / len(prev_totals), 2)
        company_delta = round(company_curr - company_prev, 2)
        division_deltas.sort(key=lambda x: x["delta"])

        return {
            "scope":                    "company_wide",
            "year":                     year,
            "compare_year":             compare_year,
            "company_avg_current":      company_curr,
            "company_avg_previous":     company_prev,
            "company_avg_delta":        company_delta,
            "overall_direction":        "improvement" if company_delta > 0 else "drop" if company_delta < 0 else "stable",
            "division_comparison":      division_deltas,
            "most_improved":            max(division_deltas, key=lambda x: x["delta"])["division_name"],
            "most_declined":            min(division_deltas, key=lambda x: x["delta"])["division_name"],
            "metadata":                 _meta(),
        }

    # ── Single division mode ─────────────────────────────────────────────── #
    current  = calculate_division_report(db, division_id, year)
    previous = calculate_division_report(db, division_id, compare_year)

    if "error" in current:
        return {"error": f"Data divisi {division_id} tahun {year} tidak tersedia: {current['error']}"}
    if "error" in previous:
        return {"error": f"Data divisi {division_id} tahun {compare_year} tidak tersedia: {previous['error']}"}

    prev_map = {k["kpi_id"]: k for k in previous["kpis"]}
    kpi_analysis: List[Dict] = []

    for k in current["kpis"]:
        prev_k = prev_map.get(k["kpi_id"])
        curr_annual = k["annual_report"]
        prev_annual = prev_k["annual_report"] if prev_k else None
        delta = round(curr_annual - prev_annual, 2) if prev_annual is not None else None
        contribution_delta = round(delta * k["weight"] / 100, 2) if delta is not None else None

        kpi_analysis.append({
            "kpi_id":                 k["kpi_id"],
            "kpi_name":               k["kpi_name"],
            "weight":                 k["weight"],
            "annual_report_current":  curr_annual,
            "annual_report_previous": prev_annual,
            "delta":                  delta,
            "direction": (
                "improvement" if (delta or 0) > 0
                else "drop"   if (delta or 0) < 0
                else "stable"
            ),
            "contribution_delta": contribution_delta,
        })

    kpi_analysis.sort(key=lambda x: (x["delta"] or 0))
    div_report_delta = round(current["division_report"] - previous["division_report"], 2)
    drops = [k for k in kpi_analysis if (k["delta"] or 0) < 0]

    return {
        "scope":                    "single_division",
        "division_id":              division_id,
        "division_name":            current["division_name"],
        "year":                     year,
        "compare_year":             compare_year,
        "division_report_current":  current["division_report"],
        "division_report_previous": previous["division_report"],
        "division_report_delta":    div_report_delta,
        "overall_direction":        "improvement" if div_report_delta > 0 else "drop" if div_report_delta < 0 else "stable",
        "primary_cause":            drops[0]["kpi_name"] if drops else "Tidak ada penurunan signifikan",
        "kpi_drops":                [k for k in kpi_analysis if k["direction"] == "drop"],
        "kpi_improvements":         [k for k in kpi_analysis if k["direction"] == "improvement"],
        "kpi_stable":               [k for k in kpi_analysis if k["direction"] == "stable"],
        "metadata":                 _meta(),
    }


def get_kpi_contribution(db: Session, division_id: int, year: int) -> Dict[str, Any]:
    """
    Hitung kontribusi nyata setiap KPI terhadap Division Report.
    Identifikasi KPI pendorong utama dan KPI dengan potensi peningkatan terbesar.
    """
    result = calculate_division_report(db, division_id, year)
    if "error" in result:
        return {"error": result["error"]}

    division_report = result["division_report"]
    contributions: List[Dict] = []

    for k in result["kpis"]:
        annual  = k["annual_report"]
        weight  = k["weight"]
        contrib = round(annual * weight / 100, 2)
        contrib_pct = round(contrib / division_report * 100, 1) if division_report > 0 else 0
        potential   = round((100 - annual) * weight / 100, 2) if annual < 100 else 0.0

        contributions.append({
            "kpi_id":              k["kpi_id"],
            "kpi_name":            k["kpi_name"],
            "weight":              weight,
            "annual_report":       annual,
            "status":              k["status"],
            "contribution_points": contrib,
            "contribution_pct":    contrib_pct,
            "potential_gain":      potential,
        })

    contributions.sort(key=lambda x: x["contribution_points"], reverse=True)

    return {
        "division_id":      division_id,
        "division_name":    result["division_name"],
        "year":             year,
        "division_report":  division_report,
        "kpi_contributions": contributions,
        "top_contributor":  contributions[0]["kpi_name"] if contributions else None,
        "highest_potential": max(contributions, key=lambda x: x["potential_gain"])["kpi_name"] if contributions else None,
        "metadata":         _meta(),
    }


def detect_kpi_anomaly(db: Session, division_id: int, year: int) -> Dict[str, Any]:
    """
    Deteksi periode dengan performa tidak biasa (outlier statistik).
    Menggunakan z-score per KPI untuk menemukan spike atau drop yang signifikan.
    """
    result = calculate_division_report(db, division_id, year)
    if "error" in result:
        return {"error": result["error"]}

    anomalies: List[Dict] = []

    for k in result["kpis"]:
        periods = k.get("periods", [])
        if len(periods) < 2:
            continue

        achievements = [p["achievement"] for p in periods]
        mean  = statistics.mean(achievements)
        stdev = statistics.stdev(achievements) if len(achievements) >= 2 else 0

        if stdev == 0:
            continue

        for p in periods:
            ach = p["achievement"]
            z   = abs(ach - mean) / stdev
            if z >= 1.5:
                anomalies.append({
                    "kpi_id":    k["kpi_id"],
                    "kpi_name":  k["kpi_name"],
                    "period":    p["period_name"],
                    "achievement": ach,
                    "kpi_mean":  round(mean, 2),
                    "deviation": round(ach - mean, 2),
                    "z_score":   round(z, 2),
                    "type":      "spike" if ach > mean else "drop",
                })

    anomalies.sort(key=lambda x: x["z_score"], reverse=True)

    return {
        "division_id":    division_id,
        "division_name":  result["division_name"],
        "year":           year,
        "anomaly_count":  len(anomalies),
        "anomalies":      anomalies,
        "interpretation": (
            f"Ditemukan {len(anomalies)} periode dengan performa tidak biasa."
            if anomalies
            else "Tidak ditemukan anomali — performa konsisten sepanjang tahun."
        ),
        "metadata":       _meta(),
    }


# ═══════════════════════════════════════════════════════════════════════════ #
#  CORE DATA TOOLS (improved)                                                 #
# ═══════════════════════════════════════════════════════════════════════════ #

def get_overview_kpi(db: Session, year: int) -> Dict[str, Any]:
    """Company-wide KPI overview: Division Report dan status tiap divisi."""
    div_rows = db.execute(
        text("SELECT division_id FROM dim_division ORDER BY division_id")
    ).fetchall()

    divisions = []
    for dr in div_rows:
        result = calculate_division_report(db, dr.division_id, year)
        if "error" not in result:
            near  = result.get("on_progress", 0)
            below = result["total_kpis"] - result["on_target"] - near
            divisions.append({
                "division_id":     result["division_id"],
                "division_name":   result["division_name"],
                "division_report": result["division_report"],
                "status":          result["status"],
                "total_kpis":      result["total_kpis"],
                "on_target":       result["on_target"],
                "near_target":     near,
                "below_target":    below,
            })

    if not divisions:
        return {"error": f"Tidak ada data KPI untuk tahun {year}."}

    company_avg  = round(sum(d["division_report"] for d in divisions) / len(divisions), 2)
    total_kpis   = sum(d["total_kpis"]   for d in divisions)
    on_target    = sum(d["on_target"]    for d in divisions)
    near_target  = sum(d["near_target"]  for d in divisions)
    below_target = sum(d["below_target"] for d in divisions)
    divisions.sort(key=lambda d: d["division_report"], reverse=True)

    return {
        "year":          year,
        "company_avg":   company_avg,
        "total_kpis":    total_kpis,
        "on_target":     on_target,
        "near_target":   near_target,
        "below_target":  below_target,
        "divisions":     divisions,
        "metadata":      _meta(),
    }


def get_division_kpi(db: Session, division_id: int, year: int) -> Dict[str, Any]:
    """Detail KPI per divisi: Annual Report tiap indikator + Division Report."""
    result = calculate_division_report(db, division_id, year)
    if "error" in result:
        return {"error": result["error"]}

    kpi_items = []
    for k in result["kpis"]:
        kpi_items.append({
            "kpi_id":            k["kpi_id"],
            "kpi_name":          k["kpi_name"],
            "unit":              k["unit"],
            "weight":            k["weight"],
            "evaluation_period": k["evaluation_period"],
            "evaluation_label":  k.get("evaluation_label", k["evaluation_period"]),
            "annual_report":     k["annual_report"],
            "status":            k["status"],
            "periods":           k["periods"],
        })

    near  = result.get("on_progress", 0)
    below = result["total_kpis"] - result["on_target"] - near

    return {
        "division_id":     result["division_id"],
        "division_name":   result["division_name"],
        "year":            year,
        "division_report": result["division_report"],
        "status":          result["status"],
        "total_kpis":      result["total_kpis"],
        "on_target":       result["on_target"],
        "near_target":     near,
        "below_target":    below,
        "kpis":            kpi_items,
        "metadata":        _meta(),
    }


def get_kpi_trend(db: Session, division_id: int, year: int) -> Dict[str, Any]:
    """Tren Division Report year-over-year untuk satu divisi."""
    from collections import defaultdict

    div = db.execute(
        text("SELECT division_name FROM dim_division WHERE division_id = :did"),
        {"did": division_id}
    ).fetchone()
    if not div:
        return {"error": f"Division {division_id} tidak ditemukan."}

    kpi_rows = db.execute(
        text("SELECT kpi_id, evaluation_period FROM dim_kpi WHERE division_id = :did ORDER BY kpi_id"),
        {"did": division_id}
    ).fetchall()

    period_contributions: dict = defaultdict(lambda: {"weighted_sum": 0.0, "weight_sum": 0.0})
    for row in kpi_rows:
        kpi_data = calculate_kpi_annual(db, row.kpi_id, year)
        if not kpi_data or not kpi_data.get("periods"):
            continue
        w = kpi_data["weight"]
        for p in kpi_data["periods"]:
            key = (p["period_order"], p["period_name"])
            period_contributions[key]["weighted_sum"] += p["achievement"] * w
            period_contributions[key]["weight_sum"]   += w

    current_trend = [
        {
            "period":      name,
            "achievement": round(vals["weighted_sum"] / vals["weight_sum"], 2) if vals["weight_sum"] > 0 else 0.0,
            "year":        year,
        }
        for (order, name), vals in sorted(period_contributions.items())
    ]

    prev_result      = calculate_division_report(db, division_id, year - 1)
    prev_div_report  = prev_result.get("division_report", 0.0) if "error" not in prev_result else 0.0

    return {
        "division_id":    division_id,
        "division_name":  div.division_name,
        "current_year":   year,
        "current_trend":  current_trend,
        "previous_year":  year - 1,
        "previous_division_report": prev_div_report,
        "metadata":       _meta(),
    }


def get_underperforming_kpi(db: Session, year: int) -> Dict[str, Any]:
    """Daftar KPI dengan Annual Report < 80% — indikator yang perlu perhatian segera."""
    kpi_rows = db.execute(
        text("SELECT kpi_id, division_id FROM dim_kpi ORDER BY division_id, kpi_id")
    ).fetchall()

    div_cache: Dict[int, str] = {}
    items: List[Dict] = []

    for row in kpi_rows:
        kpi_data = calculate_kpi_annual(db, row.kpi_id, year)
        if not kpi_data or kpi_data.get("annual_report", 100) >= 80:
            continue

        if row.division_id not in div_cache:
            d = db.execute(
                text("SELECT division_name FROM dim_division WHERE division_id = :did"),
                {"did": row.division_id}
            ).fetchone()
            div_cache[row.division_id] = d.division_name if d else "Unknown"

        items.append({
            "division_id":       row.division_id,
            "division_name":     div_cache[row.division_id],
            "kpi_id":            kpi_data["kpi_id"],
            "kpi_name":          kpi_data["kpi_name"],
            "unit":              kpi_data["unit"],
            "weight":            kpi_data["weight"],
            "evaluation_period": kpi_data["evaluation_period"],
            "year":              year,
            "annual_report":     kpi_data["annual_report"],
            "status":            kpi_data["status"],
        })

    items.sort(key=lambda x: x["annual_report"])

    return {
        "year":      year,
        "count":     len(items),
        "threshold": "< 80%",
        "items":     items,
        "metadata":  _meta(),
    }


def compare_divisions(db: Session, year: int) -> Dict[str, Any]:
    """Ranking semua divisi berdasarkan Division Report."""
    div_rows = db.execute(
        text("SELECT division_id FROM dim_division ORDER BY division_id")
    ).fetchall()

    ranking: List[Dict] = []
    for dr in div_rows:
        result = calculate_division_report(db, dr.division_id, year)
        if "error" in result:
            continue
        kpi_annuals = [k["annual_report"] for k in result["kpis"] if k.get("periods")]
        near  = result.get("on_progress", 0)
        below = result["total_kpis"] - result["on_target"] - near
        ranking.append({
            "division_id":     result["division_id"],
            "division_name":   result["division_name"],
            "division_report": result["division_report"],
            "status":          result["status"],
            "total_kpis":      result["total_kpis"],
            "on_target":       result["on_target"],
            "near_target":     near,
            "below_target":    below,
            "min_kpi_annual":  round(min(kpi_annuals), 2) if kpi_annuals else 0.0,
            "max_kpi_annual":  round(max(kpi_annuals), 2) if kpi_annuals else 0.0,
        })

    ranking.sort(key=lambda x: x["division_report"], reverse=True)
    for i, r in enumerate(ranking):
        r["rank"] = i + 1

    return {"year": year, "ranking": ranking, "metadata": _meta()}


# ── Tool Registry ────────────────────────────────────────────────────────── #

MCP_TOOLS = {
    # Core data
    "get_overview_kpi":        get_overview_kpi,
    "get_division_kpi":        get_division_kpi,
    "get_kpi_trend":           get_kpi_trend,
    "get_underperforming_kpi": get_underperforming_kpi,
    "compare_divisions":       compare_divisions,
    # Analytical
    "analyze_kpi_drop":        analyze_kpi_drop,
    "get_kpi_contribution":    get_kpi_contribution,
    "detect_kpi_anomaly":      detect_kpi_anomaly,
    # Semantic
    "explain_kpi_definition":  explain_kpi_definition,
}
