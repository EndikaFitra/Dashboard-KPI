import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from schemas.chatbot import ChatbotRequest, ChatbotResponse
from services.mcp_tools import MCP_TOOLS
from services.ollama_service import generate_response
from services.context_builder import select_tool, build_prompt, build_context_summary

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("", response_model=ChatbotResponse)
async def chatbot(
    request: ChatbotRequest,
    db: Session = Depends(get_db),
):
    """
    AI Chatbot workflow:
    1. Select MCP tool based on user question
    2. Query Data Warehouse via MCP tool
    3. Build LLM context from tool output
    4. Send to Ollama qwen3:4b-instruct
    5. Return structured response
    """
    logger.info(f"POST /chatbot question='{request.question[:60]}...'")

    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    # Step 1: Select tool
    tool_name, params = select_tool(request.question)
    logger.info(f"Selected tool: {tool_name} params={params}")

    # Step 2: Query warehouse
    tool_fn = MCP_TOOLS.get(tool_name)
    if not tool_fn:
        raise HTTPException(status_code=500, detail=f"Tool '{tool_name}' not found")

    try:
        tool_data = tool_fn(db=db, **params)
    except Exception as e:
        logger.error(f"Tool execution error: {e}", exc_info=True)
        tool_data = {"error": str(e)}

    # Step 3: Build context + prompt
    prompt = build_prompt(request.question, tool_name, tool_data)
    context_summary = build_context_summary(tool_name, tool_data)

    # Step 4: Send to Ollama
    answer = await generate_response(prompt)

    # Step 5: Return response
    return ChatbotResponse(
        question=request.question,
        answer=answer,
        tool_used=tool_name,
        context_summary=context_summary,
    )
