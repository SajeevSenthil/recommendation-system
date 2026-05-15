from fastapi import APIRouter, Request

from app.schemas.chat import ChatRequest, ChatResponse
from app.services.agent import run_turn


router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok"}


@router.post("/chat", response_model=ChatResponse)
def chat(chat_request: ChatRequest, request: Request):
    try:
        result = run_turn(
            [message.model_dump() for message in chat_request.messages],
            request.app.state.index,
            request.app.state.meta,
        )
        return ChatResponse(**result)
    except Exception:
        return ChatResponse(
            reply="I encountered an issue. Please rephrase your request.",
            recommendations=[],
            end_of_conversation=False,
        )
