"""
Context Builder — transforms MCP tool output into an LLM prompt.
"""
import json
from typing import Any, Dict

SYSTEM_PROMPT = """You are an expert KPI Data Analyst assistant for a company's performance monitoring system.
You analyze KPI (Key Performance Indicator) data from multiple divisions:
- Network Division (Half-Year evaluation)
- Software Engineer Division (Quarterly evaluation)
- Sales Executive Division (Quarterly evaluation)
- HR Officer Division (Monthly evaluation)

Achievement thresholds:
- Green (On Target): >= 100%
- Yellow (Near Target): 80% - 99%
- Red (Below Target): < 80%

Always be concise, professional, and data-driven. Refer to specific numbers when available.
Answer in the same language as the user's question (Indonesian or English).
"""


def select_tool(question: str) -> tuple[str, dict]:
    """
    Simple keyword-based tool selection.
    Returns (tool_name, params).
    """
    q = question.lower()

    # Extract year if mentioned
    import re
    year_match = re.search(r"\b(202[0-9])\b", q)
    year = int(year_match.group(1)) if year_match else 2025

    # Extract division ID hints
    division_hints = {
        "network": 1,
        "software": 2,
        "engineer": 2,
        "sales": 3,
        "hr": 4,
        "human resource": 4,
        "officer": 4,
    }

    division_id = None
    for keyword, did in division_hints.items():
        if keyword in q:
            division_id = did
            break

    # Tool selection by keywords
    if any(w in q for w in ["underperform", "below target", "danger", "red", "poor", "rendah", "kurang"]):
        return "get_underperforming_kpi", {"year": year}

    if any(w in q for w in ["trend", "compare year", "last year", "previous year", "history", "tren", "tahun lalu"]):
        did = division_id or 1
        return "get_kpi_trend", {"division_id": did, "year": year}

    if any(w in q for w in ["compare division", "ranking", "best", "worst", "bandingkan", "peringkat"]):
        return "compare_divisions", {"year": year}

    if division_id and any(w in q for w in ["kpi", "performance", "achievement", "detail", "capaian"]):
        return "get_division_kpi", {"division_id": division_id, "year": year}

    if division_id:
        return "get_division_kpi", {"division_id": division_id, "year": year}

    # Default: overview
    return "get_overview_kpi", {"year": year}


def build_prompt(question: str, tool_name: str, tool_data: Dict[str, Any]) -> str:
    """Build the full LLM prompt from question + tool data."""
    context = json.dumps(tool_data, indent=2, ensure_ascii=False)

    prompt = f"""{SYSTEM_PROMPT}

--- KPI DATA CONTEXT ---
Tool used: {tool_name}
Data:
{context}
--- END CONTEXT ---

User Question: {question}

Please provide a clear, concise answer based on the KPI data above."""
    return prompt


def build_context_summary(tool_name: str, tool_data: Dict[str, Any]) -> str:
    """Build a short human-readable context summary."""
    if tool_name == "get_overview_kpi":
        year = tool_data.get("year", "?")
        total = tool_data.get("total_kpis", 0)
        avg = tool_data.get("company_avg", 0)
        return f"Overview {year}: {total} KPIs, company avg {avg:.1f}%"

    if tool_name == "get_division_kpi":
        name = tool_data.get("division_name", "?")
        avg = tool_data.get("avg_achievement", 0)
        return f"{name} division: avg achievement {avg:.1f}%"

    if tool_name == "get_kpi_trend":
        name = tool_data.get("division_name", "?")
        year = tool_data.get("current_year", "?")
        return f"Trend for {name} in {year} vs {year - 1 if isinstance(year, int) else '?'}"

    if tool_name == "get_underperforming_kpi":
        count = tool_data.get("count", 0)
        return f"{count} underperforming KPI(s) found (achievement < 80%)"

    if tool_name == "compare_divisions":
        n = len(tool_data.get("ranking", []))
        return f"Compared {n} divisions by achievement"

    return f"Tool: {tool_name}"
