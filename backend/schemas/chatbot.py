from pydantic import BaseModel


class ChatbotRequest(BaseModel):
    question: str


class ChatbotResponse(BaseModel):
    question: str
    answer: str
    tool_used: str
    context_summary: str
