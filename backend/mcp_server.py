"""
FastMCP Server — KPI Analytics Chatbot

Menjalankan MCP tool server + HTTP /chat endpoint untuk chatbot.
Frontend memanggil langsung ke port 8001, tidak melalui FastAPI.

Run:
    cd backend
    python mcp_server.py

Endpoints:
    GET  http://localhost:8001/       -> health check
    POST http://localhost:8001/chat  -> chatbot (frontend memanggil ini)
    GET  http://localhost:8001/tools -> daftar MCP tools
"""

import os
import re
import sys
import json
import logging
from datetime import datetime

CURRENT_YEAR = datetime.now().year

import httpx
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Agar import relative backend bisa jalan
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from app.database import SessionLocal
from services.mcp_tools import (
    get_overview_kpi        as _overview,
    get_division_kpi        as _division,
    get_kpi_trend           as _trend,
    get_underperforming_kpi as _underperform,
    compare_divisions       as _compare,
    analyze_kpi_drop        as _drop_analysis,
    get_kpi_contribution    as _contribution,
    detect_kpi_anomaly      as _anomaly,
    explain_kpi_definition  as _explain,
    get_cluster_analysis    as _cluster_analysis,
    explain_cluster_method  as _cluster_explain,
    validate_query_intent,
)

# Import fungsi utama dari forecasting_service yang kita buat sebelumnya.
# Fungsi ini berisi seluruh logika ARIMA: query data dari DB, fitting model,
# menghitung forecast 4 quarter ke depan, dan menghitung MAPE.
from services.forecasting_service import get_mrr_forecast as _get_mrr_forecast

# --------------------------------------------------------------------------- #
# Config
# --------------------------------------------------------------------------- #
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s -- %(message)s",
)
logger = logging.getLogger(__name__)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL   = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
GROQ_URL     = "https://api.groq.com/openai/v1/chat/completions"
MCP_PORT     = int(os.getenv("MCP_PORT", "8001"))


# --------------------------------------------------------------------------- #
# Helper
# --------------------------------------------------------------------------- #
def _db_call(fn, *args, **kwargs):
    """Buka sesi DB, jalankan fungsi, tutup sesi."""
    db = SessionLocal()
    try:
        return fn(db, *args, **kwargs)
    finally:
        db.close()


def _extract_years_from_text(text: str, fallback: int) -> list:
    """
    Scan teks untuk semua angka tahun 4 digit (2020-2099).
    Kembalikan list tahun unik sesuai urutan kemunculan.
    Jika tidak ada, kembalikan [fallback].
    """
    matches = re.findall(r'\b(20[2-9]\d)\b', text)
    if matches:
        seen = []
        for m in matches:
            y = int(m)
            if y not in seen:
                seen.append(y)
        return seen
    return [fallback]


# --------------------------------------------------------------------------- #
# Raw Python functions (callable, dipakai oleh TOOL_REGISTRY dan FastMCP)
# --------------------------------------------------------------------------- #
def fn_get_overview_kpi(year: int = 2025) -> dict:
    """Company-wide KPI overview: skor semua divisi, jumlah KPI, status achievement."""
    return _db_call(_overview, year)


def fn_get_division_kpi(division_id: int, year: int = 2025) -> dict:
    """Breakdown KPI untuk satu divisi.
    division_id: 1=Network, 2=SoftwareEngineer, 3=SalesExecutive, 4=HROfficer"""
    return _db_call(_division, division_id, year)


def fn_get_kpi_trend(division_id: int, year: int = 2025) -> dict:
    """Tren Division Report year-over-year untuk satu divisi.
    Periode breakdown mengikuti evaluasi masing-masing KPI (M/Q/H).
    division_id: 1=Network, 2=SoftwareEngineer, 3=SalesExecutive, 4=HROfficer"""
    return _db_call(_trend, division_id, year)


def fn_get_underperforming_kpi(year: int = 2025) -> dict:
    """KPI dengan achievement di bawah 80% -- indikator yang perlu perhatian."""
    return _db_call(_underperform, year)


def fn_compare_divisions(year: int = 2025) -> dict:
    """Ranking semua divisi berdasarkan weighted KPI achievement score."""
    return _db_call(_compare, year)


def fn_analyze_kpi_drop(division_id: int = 0, year: int = 2025, compare_year: int = 0) -> dict:
    """Analisis penyebab kenaikan/penurunan performa antar dua tahun.
    division_id=0 → analisis seluruh perusahaan.
    division_id: 1=Network, 2=SoftwareEngineer, 3=SalesExecutive, 4=HROfficer"""
    did = division_id if division_id else None
    cy  = compare_year if compare_year else None
    return _db_call(_drop_analysis, did, year, cy)


def fn_get_kpi_contribution(division_id: int, year: int = 2025) -> dict:
    """Kontribusi nyata tiap KPI terhadap Division Report. Identifikasi KPI pendorong & laggard.
    division_id: 1=Network, 2=SoftwareEngineer, 3=SalesExecutive, 4=HROfficer"""
    return _db_call(_contribution, division_id, year)


def fn_detect_kpi_anomaly(division_id: int, year: int = 2025) -> dict:
    """Deteksi periode dengan performa tidak biasa (z-score >= 1.5).
    division_id: 1=Network, 2=SoftwareEngineer, 3=SalesExecutive, 4=HROfficer"""
    return _db_call(_anomaly, division_id, year)


def fn_explain_kpi_definition(kpi_name: str = "", kpi_id: int = 0) -> dict:
    """Definisi, konteks bisnis, dan metadata sebuah KPI."""
    return _db_call(_explain, kpi_name, kpi_id)


def fn_get_mrr_forecast(p: int = 2, d: int = 0, q: int = 3) -> dict:
    """
    Fungsi wrapper untuk memanggil model ARIMA dari forecasting_service.

    Cara kerja:
    1. Membuka sesi koneksi ke database PostgreSQL via _db_call.
    2. Meneruskan panggilan ke fungsi _get_mrr_forecast yang berisi:
       - Query data MRR historis dari tabel fact_kpi_performance.
       - Fitting model ARIMA dengan order (p, d, q).
       - Menghitung forecast untuk 4 quarter ke depan.
       - Menghitung nilai MAPE sebagai ukuran akurasi model.
    3. Mengembalikan hasil dalam bentuk dict yang langsung bisa dibaca AI.

    Parameter:
    - p: order AR (Auto-Regressive) — berapa periode lalu yang mempengaruhi sekarang.
          Ditentukan dari plot PACF pada analisis notebook. Default: 2.
    - d: order differencing — berapa kali data perlu diubah agar stasioner.
          Dari hasil uji ADF, data MRR sudah stasioner, maka d=0.
    - q: order MA (Moving-Average) — seberapa jauh error masa lalu mempengaruhi prediksi.
          Ditentukan dari plot ACF pada analisis notebook. Default: 3.
    """
    return _db_call(_get_mrr_forecast, (p, d, q), 4)


def fn_get_cluster_analysis() -> dict:
    """Ambil hasil clustering Agglomerative Hierarchical untuk indikator Sales."""
    return _db_call(_cluster_analysis)


def fn_explain_cluster_method() -> dict:
    """Penjelasan metode clustering yang digunakan."""
    return _cluster_explain()


# --------------------------------------------------------------------------- #
# TOOL_REGISTRY
# --------------------------------------------------------------------------- #
# TOOL_REGISTRY adalah "daftar menu" yang diberikan kepada AI.
# Setiap kunci (key) adalah nama tool yang bisa dipanggil AI,
# dan nilainya adalah fungsi Python yang akan dieksekusi secara nyata.
# Ketika AI memutuskan untuk memanggil tool, MCP server mencari nama
# tool di dictionary ini lalu mengeksekusi fungsinya.
TOOL_REGISTRY: dict = {
    # Core data — tools untuk membaca data KPI dari database
    "get_overview_kpi":        fn_get_overview_kpi,
    "get_division_kpi":        fn_get_division_kpi,
    "get_kpi_trend":           fn_get_kpi_trend,
    "get_underperforming_kpi": fn_get_underperforming_kpi,
    "compare_divisions":       fn_compare_divisions,
    # Analytical — tools untuk analisis mendalam (perbandingan, kontribusi, anomali)
    "analyze_kpi_drop":        fn_analyze_kpi_drop,
    "get_kpi_contribution":    fn_get_kpi_contribution,
    "detect_kpi_anomaly":      fn_detect_kpi_anomaly,
    # Semantic — tools untuk penjelasan definisi KPI
    "explain_kpi_definition":  fn_explain_kpi_definition,
    # Statistical — tools untuk analisis statistik dan forecasting
    # Mendaftarkan fn_get_mrr_forecast agar AI bisa memanggilnya
    # saat user bertanya tentang prediksi atau proyeksi MRR.
    "get_mrr_forecast":        fn_get_mrr_forecast,
    # Clustering
    "get_cluster_analysis":    fn_get_cluster_analysis,
    "explain_cluster_method":  fn_explain_cluster_method,
}


# --------------------------------------------------------------------------- #
# Tool schemas untuk Ollama API
# --------------------------------------------------------------------------- #
OLLAMA_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_overview_kpi",
            "description": "Ambil overview KPI seluruh perusahaan: skor per divisi, achieved/warning/danger count.",
            "parameters": {
                "type": "object",
                "properties": {
                    "year": {"type": "integer", "description": "Tahun data (default 2025)"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_division_kpi",
            "description": "Breakdown KPI detail untuk satu divisi spesifik.",
            "parameters": {
                "type": "object",
                "properties": {
                    "division_id": {
                        "type": "integer",
                        "description": "ID divisi: 1=Network, 2=SoftwareEngineer, 3=SalesExecutive, 4=HROfficer",
                    },
                    "year": {"type": "integer", "description": "Tahun data (default 2025)"},
                },
                "required": ["division_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_kpi_trend",
            "description": "Tren KPI per kuartal, year-over-year, untuk satu divisi.",
            "parameters": {
                "type": "object",
                "properties": {
                    "division_id": {
                        "type": "integer",
                        "description": "ID divisi: 1=Network, 2=SoftwareEngineer, 3=SalesExecutive, 4=HROfficer",
                    },
                    "year": {"type": "integer", "description": "Tahun data (default 2025)"},
                },
                "required": ["division_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_underperforming_kpi",
            "description": "Daftar semua KPI dengan achievement < 80% -- yang perlu tindakan.",
            "parameters": {
                "type": "object",
                "properties": {
                    "year": {"type": "integer", "description": "Tahun data (default 2025)"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compare_divisions",
            "description": "Bandingkan dan ranking semua divisi berdasarkan weighted KPI score.",
            "parameters": {
                "type": "object",
                "properties": {
                    "year": {"type": "integer", "description": "Tahun data (default 2025)"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_kpi_drop",
            "description": "Analisis mengapa performa naik atau turun antar dua tahun. Jika tidak ada divisi tertentu yang disebutkan user, gunakan division_id=0 untuk analisis seluruh perusahaan.",
            "parameters": {
                "type": "object",
                "properties": {
                    "division_id":  {
                        "type": "integer",
                        "description": "ID divisi: 1=Network, 2=SoftwareEngineer, 3=SalesExecutive, 4=HROfficer. Gunakan 0 jika tidak ada divisi spesifik (analisis seluruh perusahaan).",
                    },
                    "year":         {"type": "integer", "description": "Tahun yang dievaluasi (tahun lebih baru)"},
                    "compare_year": {"type": "integer", "description": "Tahun pembanding (default: year-1). Isi 0 untuk default."},
                },
                "required": ["year"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_kpi_contribution",
            "description": "Hitung kontribusi nyata tiap KPI terhadap Division Report. Gunakan untuk mengetahui KPI pendorong utama dan KPI laggard.",
            "parameters": {
                "type": "object",
                "properties": {
                    "division_id": {"type": "integer", "description": "ID divisi: 1=Network, 2=SoftwareEngineer, 3=SalesExecutive, 4=HROfficer"},
                    "year":        {"type": "integer", "description": "Tahun data"},
                },
                "required": ["division_id", "year"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "detect_kpi_anomaly",
            "description": "Deteksi periode dengan performa tidak biasa secara statistik (z-score ≥ 1.5). Gunakan jika user bertanya tentang lonjakan atau penurunan mendadak.",
            "parameters": {
                "type": "object",
                "properties": {
                    "division_id": {"type": "integer", "description": "ID divisi: 1=Network, 2=SoftwareEngineer, 3=SalesExecutive, 4=HROfficer"},
                    "year":        {"type": "integer", "description": "Tahun data"},
                },
                "required": ["division_id", "year"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "explain_kpi_definition",
            "description": "Kembalikan definisi, konteks bisnis, bobot, dan metadata KPI. Gunakan jika user bertanya 'apa itu KPI X' atau 'jelaskan indikator Y'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "kpi_name": {"type": "string", "description": "Nama KPI (e.g. 'SLA Compliance', 'Bug Rate'). Isi salah satu: kpi_name ATAU kpi_id."},
                    "kpi_id":   {"type": "integer", "description": "ID KPI dari database. Isi 0 jika tidak diketahui."},
                },
                "required": [],
            },
        },
    },
    # ── Tool Statistik: MRR Forecasting ─────────────────────────────────────
    # Schema ini adalah "kartu identitas" tool forecasting yang dibaca oleh AI (Groq).
    # AI menggunakan informasi ini untuk memutuskan KAPAN harus memanggil tool ini.
    # Bagian terpenting adalah "description" — kalimat ini yang AI baca untuk
    # menentukan apakah tool ini relevan dengan pertanyaan user.
    {
        "type": "function",
        "function": {
            "name": "get_mrr_forecast",
            # Deskripsi ini sangat penting: harus mencakup semua kata kunci yang
            # mungkin digunakan user saat bertanya tentang prediksi MRR.
            # AI akan mencocokkan pertanyaan user dengan deskripsi ini.
            "description": (
                "Ambil prediksi (forecast) MRR (Monthly Recurring Revenue) untuk beberapa quarter ke depan "
                "menggunakan model statistik ARIMA yang telah divalidasi. "
                "Gunakan tool ini jika user bertanya tentang: "
                "'forecast MRR', 'prediksi MRR', 'proyeksi pendapatan', "
                "'MRR masa depan', 'MRR quarter berikutnya', atau 'analisis statistik MRR'. "
                "Tool ini mengembalikan nilai forecast yang dihitung secara matematis beserta "
                "nilai MAPE (Mean Absolute Percentage Error) sebagai ukuran akurasi model. "
                "JANGAN gunakan asumsi manual jika tool ini tersedia."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    # Parameter p: menentukan seberapa jauh ke belakang AI melihat pola AR.
                    # Nilai default 2 sudah divalidasi melalui uji ACF/PACF.
                    "p": {
                        "type": "integer",
                        "description": (
                            "Order AR (Auto-Regressive) model ARIMA — "
                            "menentukan pengaruh nilai MRR periode lalu terhadap prediksi. "
                            "Default: 2 (sudah divalidasi via plot PACF)."
                        ),
                    },
                    # Parameter d: berdasarkan uji ADF, data MRR stasioner sehingga d=0.
                    "d": {
                        "type": "integer",
                        "description": (
                            "Order differencing model ARIMA — "
                            "berapa kali data diubah agar menjadi stasioner. "
                            "Default: 0 karena uji ADF membuktikan data MRR sudah stasioner."
                        ),
                    },
                    # Parameter q: menentukan pengaruh error prediksi periode lalu.
                    # Nilai default 3 sudah divalidasi melalui uji ACF/PACF.
                    "q": {
                        "type": "integer",
                        "description": (
                            "Order MA (Moving-Average) model ARIMA — "
                            "menentukan pengaruh error prediksi periode sebelumnya. "
                            "Default: 3 (sudah divalidasi via plot ACF)."
                        ),
                    },
                },
                # Semua parameter bersifat opsional karena sudah ada nilai default
                # yang telah divalidasi secara statistik. AI tidak perlu mengisi
                # parameter ini kecuali user secara eksplisit meminta order berbeda.
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_cluster_analysis",
            "description": (
                "Ambil hasil clustering Agglomerative Hierarchical untuk indikator "
                "divisi Sales (Customer Baru, Quotation, MRR). Gunakan tool ini jika "
                "user bertanya tentang: 'cluster sales', 'segmentasi', 'pengelompokan "
                "data', 'profil cluster', 'berapa cluster', atau nama-nama phase (misal "
                "'Peak Revenue', 'Core Growth', 'Hyper-Acquisition', dsb)."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "explain_cluster_method",
            "description": (
                "Jelaskan metode clustering yang digunakan dalam analisis Sales. "
                "Gunakan jika user bertanya: 'metode apa', 'bagaimana cara clustering', "
                "'apa itu agglomerative', 'apa itu average linkage', 'apa itu silhouette', "
                "'apa itu BSS/TSS', atau 'bagaimana interpretasi cluster'."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
]


SYSTEM_PROMPT = """/no_think
Kamu adalah analis KPI perusahaan. Kamu memiliki akses ke tools untuk mengambil data KPI real-time dari database.

## Divisi perusahaan:
- Network (ID=1): evaluasi Half Year (H), KPI: SLA Compliance 60%, Incident Prevention 35%, Delivery Inovasi 5%
- Software Engineer (ID=2): evaluasi Quarterly (Q), KPI: Inovasi/Optimasi 30%, Productivity 25%, Bug Rate 25%, Kolaborasi 20%
- Sales Executive (ID=3): evaluasi Quarterly (Q), KPI: MRR 60%, Customer Baru 30%, Quotation 10%
- HR Officer (ID=4): evaluasi Monthly (M), semua KPI bobot 20% masing-masing

## Model evaluasi (PENTING — pahami ini):
- **Annual Report** per KPI = rata-rata achievement semua periode dalam satu tahun
- **Division Report** = Σ(Annual Report × Bobot) untuk semua KPI dalam divisi
- Setiap KPI dievaluasi dengan periode yang berbeda (M/Q/H) sesuai jenis indikatornya
- Tidak ada ETL — semua nilai dihitung langsung (on-the-fly) dari data realisasi

## Status KPI:
- **On Target**: Annual Report >= 100%
- **Near Target**: 80% <= Annual Report < 100%
- **Below Target**: Annual Report < 80%

## Field data penting:
- `division_report`: skor gabungan divisi (weighted average annual report)
- `annual_report`: rata-rata achievement KPI sepanjang tahun
- `on_target`: jumlah KPI dengan status On Target
- `near_target`: jumlah KPI dengan status Near Target (mendekati target)
- `below_target`: jumlah KPI dengan status Below Target

## Aturan menjawab:
- SELALU panggil tool terlebih dahulu sebelum menjawab
- Jika user menyebutkan SATU tahun: gunakan tahun tersebut sebagai parameter `year`
- Jika user menyebutkan BEBERAPA tahun (misal "2025 dan 2024"): WAJIB panggil tool TERPISAH untuk SETIAP tahun, lalu bandingkan hasilnya dalam satu jawaban
- Jika user tidak menyebutkan tahun, gunakan tahun yang tercantum di konteks pesan (tahun: XXXX)
- Gunakan Bahasa Indonesia yang ringkas dan profesional
- Format angka dengan jelas (persentase, IDR, unit, dll)
- Fokus pada insight yang actionable

## Panduan pemilihan tool:
| Intent user | Tool yang dipakai |
|---|---|
| "Ringkasan/overview perusahaan" | `get_overview_kpi` |
| "Detail KPI divisi X" | `get_division_kpi` |
| "Ranking divisi" | `compare_divisions` |
| "KPI bermasalah / di bawah target" | `get_underperforming_kpi` |
| "Tren / perkembangan dari waktu ke waktu" | `get_kpi_trend` |
| "Kenapa naik/turun? / Apa penyebabnya?" | `analyze_kpi_drop` |
| "KPI mana yang paling berpengaruh?" | `get_kpi_contribution` |
| "Ada anomali / lonjakan / penurunan mendadak?" | `detect_kpi_anomaly` |
| "Apa itu KPI X? / Jelaskan indikator Y" | `explain_kpi_definition` |
| "Forecast / prediksi / proyeksi MRR" | `get_mrr_forecast` |
| "Cluster / segmentasi data sales" | `get_cluster_analysis` |
| "Metode / algoritma / cara kerja clustering" | `explain_cluster_method` |

## Aturan khusus untuk Forecasting MRR:
- Jika user bertanya tentang PREDIKSI, PROYEKSI, atau FORECAST MRR masa depan,
  WAJIB gunakan tool `get_mrr_forecast`. JANGAN buat estimasi manual.
- Tool ini menggunakan model ARIMA(2,0,3) yang sudah divalidasi secara statistik
  dengan tingkat error (MAPE) sekitar 3%, sehingga jauh lebih akurat daripada
  perkiraan manual berdasarkan tren linear.
- Setelah mendapat hasil dari `get_mrr_forecast`, sampaikan dalam jawaban:
  1. Nilai forecast MRR untuk setiap quarter (format IDR).
  2. Nilai MAPE sebagai indikator akurasi model (contoh: "akurasi model ~96.9%").
  3. Konteks singkat: berapa data historis yang digunakan dan model apa yang dipakai.
- Contoh kalimat pembuka yang baik:
  "Berdasarkan model statistik ARIMA(2,0,3) yang dilatih pada X data poin historis
   dengan tingkat akurasi ~97% (MAPE: 3.11%), berikut proyeksi MRR:"

## Aturan khusus untuk Clustering Sales:
- Jika user bertanya tentang CLUSTER, SEGMENTASI, atau PENGELOMPOKAN data Sales,
  WAJIB gunakan tool `get_cluster_analysis`.
- Jika user bertanya tentang METODE atau CARA KERJA clustering,
  gunakan `explain_cluster_method`.
- Setelah mendapat hasil, sampaikan:
  1. Jumlah cluster dan jumlah observasi
  2. Profil singkat setiap cluster (rata-rata per variabel)
  3. Metrik evaluasi (silhouette, BSS/TSS, cophenetic) dengan interpretasi
"""



# --------------------------------------------------------------------------- #
# Groq Tool Calling Loop
# --------------------------------------------------------------------------- #
async def run_chat_loop(question: str, year: int) -> str:
    """
    Kirim pertanyaan ke Groq dengan tool definitions.
    Guardrail → multi-year detection → Groq tool-calling loop.
    """
    # ── Guardrail pre-check ──────────────────────────────────────────────── #
    safety = validate_query_intent(question)
    if not safety["valid"]:
        logger.warning(f"Query refused: {safety['reason']}")
        return f"Maaf, permintaan tidak dapat diproses. {safety['reason']}"

    # Ekstrak SEMUA tahun yang disebutkan user
    years_found = _extract_years_from_text(question, year)

    if len(years_found) > 1:
        # Multi-year: instruksikan AI untuk memanggil tool per tahun
        year_list = " dan ".join(str(y) for y in years_found)
        user_content = (
            f"{question}\n\n"
            f"[INSTRUKSI SISTEM: User meminta data untuk {len(years_found)} tahun berbeda: {year_list}. "
            f"WAJIB panggil tool TERPISAH untuk setiap tahun ({', '.join(str(y) for y in years_found)}), "
            f"kemudian bandingkan hasilnya dalam satu jawaban.]"
        )
        effective_year = years_found[0]  # default untuk tool yang tidak dapat year
    else:
        effective_year = years_found[0]
        user_content = f"{question} (gunakan data tahun: {effective_year})"

    logger.info(f"Years detected: {years_found} | Effective default year: {effective_year}")

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": user_content},
    ]

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        for iteration in range(5):
            logger.info(f"Groq iteration {iteration + 1}, messages={len(messages)}")

            resp = await client.post(
                GROQ_URL,
                headers=headers,
                json={
                    "model":    GROQ_MODEL,
                    "messages": messages,
                    "tools":    OLLAMA_TOOLS,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            
            # Groq returns usage in 'usage' field
            usage = data.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            
            if prompt_tokens > 0 or completion_tokens > 0:
                logger.info(f"  [Metrics] Tokens: {prompt_tokens} prompt + {completion_tokens} completion")

            msg        = data['choices'][0]['message']
            tool_calls = msg.get("tool_calls") or []

            if not tool_calls:
                # Tidak ada tool_calls -> jawaban final
                return msg.get("content", "Tidak ada respons dari model.")

            # Simpan giliran asisten (termasuk tool_calls) ke history
            messages.append(msg)

            # Eksekusi setiap tool call
            for tc in tool_calls:
                tc_id   = tc.get("id")
                fn_name = tc.get("function", {}).get("name", "")
                fn_args = tc.get("function", {}).get("arguments", {})

                # Groq/OpenAI mengirim arguments sebagai string JSON
                if isinstance(fn_args, str):
                    try:
                        fn_args = json.loads(fn_args)
                    except Exception:
                        fn_args = {}

                # Isi year default jika tidak ada
                if "year" not in fn_args:
                    fn_args["year"] = effective_year

                logger.info(f"  Tool call: {fn_name}({fn_args}) id={tc_id}")

                fn = TOOL_REGISTRY.get(fn_name)
                if fn:
                    try:
                        result = fn(**fn_args)
                    except Exception as exc:
                        result = {"error": str(exc)}
                        logger.error(f"  Tool error: {exc}", exc_info=True)
                else:
                    result = {"error": f"Tool tidak ditemukan: {fn_name}"}

                messages.append({
                    "role":         "tool",
                    "tool_call_id": tc_id,
                    "content":      json.dumps(result, ensure_ascii=False, default=str),
                })

    return "Maaf, AI mencapai batas iterasi. Coba pertanyaan yang lebih spesifik."


# --------------------------------------------------------------------------- #
# FastAPI App
# --------------------------------------------------------------------------- #
app = FastAPI(
    title="KPI Analytics MCP Server",
    description="FastMCP + Groq tool calling server untuk chatbot KPI",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    year: int = CURRENT_YEAR  # default tahun berjalan, bukan hardcode 2025


class ChatResponse(BaseModel):
    response: str
    model: str


@app.get("/", tags=["health"])
def health():
    return {
        "status": "ok",
        "server": "KPI FastMCP Chat Server",
        "model":  GROQ_MODEL,
        "port":   MCP_PORT,
        "tools":  list(TOOL_REGISTRY.keys()),
    }


@app.get("/tools", tags=["mcp"])
def list_tools():
    """Daftar semua MCP tools yang tersedia."""
    return {
        "tools": [
            {
                "name":        t["function"]["name"],
                "description": t["function"]["description"],
                "parameters":  t["function"]["parameters"],
            }
            for t in OLLAMA_TOOLS
        ]
    }


@app.post("/chat", response_model=ChatResponse, tags=["chat"])
async def chat(req: ChatRequest):
    """
    Endpoint utama chatbot.
    Frontend mengirim pertanyaan, server menjalankan Ollama tool-calling loop,
    dan mengembalikan jawaban natural language.
    """
    logger.info(f"Chat: '{req.message}' year={req.year}")
    try:
        answer = await run_chat_loop(req.message, req.year)
        return ChatResponse(response=answer, model=GROQ_MODEL)

    except httpx.ConnectError:
        msg = (
            f"Tidak dapat terhubung ke Groq API di {GROQ_URL}. "
            "Pastikan koneksi internet tersedia dan API Key valid."
        )
        logger.error(msg)
        return ChatResponse(response=msg, model=GROQ_MODEL)

    except httpx.HTTPStatusError as exc:
        msg = f"Groq error {exc.response.status_code}: {exc.response.text[:200]}"
        logger.error(msg)
        return ChatResponse(response=msg, model=GROQ_MODEL)

    except Exception as exc:
        logger.error(f"Chat error: {exc}", exc_info=True)
        return ChatResponse(response=f"Server error: {str(exc)}", model=GROQ_MODEL)


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    logger.info(f"Starting FastMCP Chat Server on port {MCP_PORT}")
    logger.info(f"Groq Model: {GROQ_MODEL}")
    uvicorn.run(app, host="0.0.0.0", port=MCP_PORT, log_level="info")
