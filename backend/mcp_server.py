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
    get_overview_kpi      as _overview,
    get_division_kpi      as _division,
    get_kpi_trend         as _trend,
    get_underperforming_kpi as _underperform,
    compare_divisions     as _compare,
)

# --------------------------------------------------------------------------- #
# Config
# --------------------------------------------------------------------------- #
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s -- %(message)s",
)
logger = logging.getLogger(__name__)

GROQ_API_URL = os.getenv("GROQ_API_URL", "https://api.groq.com/openai/v1")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL   = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
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


def _extract_year_from_text(text: str, fallback: int) -> int:
    """
    Scan teks untuk angka tahun 4 digit (2020-2099).
    Jika ditemukan, gunakan tahun yang disebutkan user.
    Jika tidak ada, kembalikan fallback.
    """
    matches = re.findall(r'\b(20[2-9]\d)\b', text)
    if matches:
        return int(matches[-1])  # gunakan tahun terakhir yang disebutkan
    return fallback


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
    """Tren KPI year-over-year (per kuartal) untuk satu divisi.
    division_id: 1=Network, 2=SoftwareEngineer, 3=SalesExecutive, 4=HROfficer"""
    return _db_call(_trend, division_id, year)


def fn_get_underperforming_kpi(year: int = 2025) -> dict:
    """KPI dengan achievement di bawah 80% -- indikator yang perlu perhatian."""
    return _db_call(_underperform, year)


def fn_compare_divisions(year: int = 2025) -> dict:
    """Ranking semua divisi berdasarkan weighted KPI achievement score."""
    return _db_call(_compare, year)


# --------------------------------------------------------------------------- #
# TOOL_REGISTRY -- pakai fungsi Python asli (fn_*), bukan FunctionTool wrapper
# --------------------------------------------------------------------------- #
TOOL_REGISTRY: dict = {
    "get_overview_kpi":        fn_get_overview_kpi,
    "get_division_kpi":        fn_get_division_kpi,
    "get_kpi_trend":           fn_get_kpi_trend,
    "get_underperforming_kpi": fn_get_underperforming_kpi,
    "compare_divisions":       fn_compare_divisions,
}


# --------------------------------------------------------------------------- #
# Tool schemas untuk Groq API
# --------------------------------------------------------------------------- #
GROQ_TOOLS = [
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
]

SYSTEM_PROMPT = """/no_think
Kamu adalah analis KPI perusahaan. Kamu memiliki akses ke tools untuk mengambil data KPI real-time dari database.

Divisi perusahaan:
- Network (ID=1): evaluasi Half Year, bobot KPI: SLA 60%, Incident Prevention 35%, Inovasi 5%
- Software Engineer (ID=2): evaluasi Quarter, bobot: Inovasi/Optimasi 30%, Productivity 25%, Bug Rate 25%, Kolaborasi 20%
- Sales Executive (ID=3): evaluasi Quarter, bobot: MRR 60%, Customer Baru 30%, Quotation 10%
- HR Officer (ID=4): evaluasi Monthly, semua KPI bobot 20% masing-masing

ATURAN PENTING:
- SELALU panggil tool terlebih dahulu sebelum menjawab
- Jika user menyebutkan tahun tertentu (misal 2026, 2024), GUNAKAN tahun tersebut sebagai parameter `year` saat memanggil tool. JANGAN gunakan tahun lain.
- Jika user tidak menyebutkan tahun, gunakan tahun yang tercantum di konteks pesan (tahun: XXXX)
- Gunakan Bahasa Indonesia yang ringkas dan profesional
- Achievement >=100% = On Progress
- Format angka dengan jelas (persentase, IDR, unit, dll)
- Fokus pada insight yang actionable
"""


# --------------------------------------------------------------------------- #
# Groq Tool Calling Loop
# --------------------------------------------------------------------------- #
async def run_chat_loop(question: str, year: int) -> str:
    """
    Kirim pertanyaan ke Groq dengan tool definitions.
    Jika Groq memanggil tool, eksekusi fungsi Python asli dan feed hasilnya kembali.
    Ulangi hingga Groq menghasilkan jawaban final (tanpa tool_calls).
    """
    # Prioritaskan tahun yang disebutkan user dalam teks pertanyaan
    year = _extract_year_from_text(question, year)
    logger.info(f"Effective year for this chat: {year}")

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": f"{question} (gunakan data tahun: {year})"},
    ]

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        for iteration in range(5):
            logger.info(f"Groq iteration {iteration + 1}, messages={len(messages)}")

            resp = await client.post(
                f"{GROQ_API_URL}/chat/completions",
                headers=headers,
                json={
                    "model":    GROQ_MODEL,
                    "messages": messages,
                    "tools":    GROQ_TOOLS,
                    "tool_choice": "auto",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            
            usage = data.get("usage", {})
            prompt_count = usage.get("prompt_tokens", 0)
            eval_count = usage.get("completion_tokens", 0)
            duration_ms = usage.get("total_time", 0) * 1000 if "total_time" in usage else 0
            
            if eval_count > 0 or prompt_count > 0:
                logger.info(f"  [Metrics] Tokens: {prompt_count} prompt + {eval_count} eval | Model Time: {duration_ms:.2f} ms")

            choices = data.get("choices", [])
            if not choices:
                return "Tidak ada respons dari model."

            msg = choices[0].get("message", {})
            tool_calls = msg.get("tool_calls") or []

            if not tool_calls:
                # Tidak ada tool_calls -> jawaban final
                return msg.get("content") or "Tidak ada respons dari model."

            # Simpan giliran asisten + tool_calls ke history
            messages.append(msg)

            # Eksekusi setiap tool call
            for tc in tool_calls:
                fn_name = tc.get("function", {}).get("name", "")
                fn_args_str = tc.get("function", {}).get("arguments", "{}")

                try:
                    fn_args = json.loads(fn_args_str)
                except Exception:
                    fn_args = {}

                # Isi year default jika tidak ada
                if "year" not in fn_args:
                    fn_args["year"] = year

                logger.info(f"  Tool call: {fn_name}({fn_args})")

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
                    "role": "tool",
                    "tool_call_id": tc.get("id"),
                    "name": fn_name,
                    "content": json.dumps(result, ensure_ascii=False, default=str),
                })

    return "Maaf, AI mencapai batas iterasi. Coba pertanyaan yang lebih spesifik."


# --------------------------------------------------------------------------- #
# FastAPI App
# --------------------------------------------------------------------------- #
app = FastAPI(
    title="KPI Analytics MCP Server",
    description="FastMCP + Ollama tool calling server untuk chatbot KPI",
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
            for t in GROQ_TOOLS
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
            f"Tidak dapat terhubung ke Groq API di {GROQ_API_URL}. "
            "Pastikan koneksi internet stabil."
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
    logger.info(f"Groq API: {GROQ_API_URL} | Model: {GROQ_MODEL}")
    uvicorn.run(app, host="0.0.0.0", port=MCP_PORT, log_level="info")
