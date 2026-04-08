from pydantic import BaseModel
from typing import Any, Optional, Dict


class McpToolRequest(BaseModel):
    tool: str
    params: Optional[Dict[str, Any]] = {}


class McpToolResponse(BaseModel):
    tool: str
    success: bool
    data: Any
    error: Optional[str] = None
