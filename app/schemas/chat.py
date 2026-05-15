from typing import Literal

from pydantic import BaseModel, field_validator


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]

    @field_validator("messages")
    @classmethod
    def validate_messages(cls, value):
        if not value:
            raise ValueError("messages must not be empty")
        if value[-1].role != "user":
            raise ValueError("last message must be from the user")
        return value


class Recommendation(BaseModel):
    name: str
    url: str
    test_type: str


class ChatResponse(BaseModel):
    reply: str
    recommendations: list[Recommendation] = []
    end_of_conversation: bool = False
