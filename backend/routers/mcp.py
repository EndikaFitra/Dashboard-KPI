import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from schemas.mcp import McpToolRequest, McpToolResponse
from services.mcp_tools import MCP_TOOLS

logger = logging.getLogger(__name__)
router = APIRouter()

AVAILABLE_TOOLS = list(MCP_TOOLS.keys())


@router.get("/tools")
def list_tools():
    """List all available MCP tools."""
    return {
        "tools": [
            {"name": "get_overview_kpi",       "description": "Company-wide KPI overview", "params": ["year"]},
            {"name": "get_division_kpi",        "description": "Single division KPI detail", "params": ["division_id", "year"]},
            {"name": "get_kpi_trend",           "description": "Year-over-year KPI trend for a division", "params": ["division_id", "year"]},
            {"name": "get_underperforming_kpi", "description": "KPIs with achievement < 80%", "params": ["year"]},
            {"name": "compare_divisions",       "description": "Side-by-side division ranking", "params": ["year"]},
        ]
    }


@router.post("/tools", response_model=McpToolResponse)
def call_tool(
    request: McpToolRequest,
    db: Session = Depends(get_db),
):
    """Dispatch an MCP tool call and return structured data."""
    logger.info(f"POST /mcp/tools tool={request.tool} params={request.params}")

    if request.tool not in MCP_TOOLS:
        return McpToolResponse(
            tool=request.tool,
            success=False,
            data=None,
            error=f"Unknown tool '{request.tool}'. Available: {AVAILABLE_TOOLS}",
        )

    tool_fn = MCP_TOOLS[request.tool]
    params = request.params or {}

    try:
        result = tool_fn(db=db, **params)
        return McpToolResponse(tool=request.tool, success=True, data=result)
    except TypeError as e:
        logger.error(f"MCP tool param error: {e}")
        return McpToolResponse(
            tool=request.tool,
            success=False,
            data=None,
            error=f"Invalid parameters: {str(e)}",
        )
    except Exception as e:
        logger.error(f"MCP tool error: {e}", exc_info=True)
        return McpToolResponse(
            tool=request.tool,
            success=False,
            data=None,
            error=str(e),
        )
