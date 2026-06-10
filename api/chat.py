from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.gemini_service import GeminiService

router = APIRouter(prefix="/api/chat", tags=["Chat"])


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    model: str = "gemini-1.0"


class ChatResponse(BaseModel):
    model: str
    output: str
    note: Optional[str] = None


@router.post("/", response_model=ChatResponse)
def chat(req: ChatRequest):
    try:
        svc = GeminiService(model=req.model)
        response = svc.chat([message.dict() for message in req.messages])
        return response
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
