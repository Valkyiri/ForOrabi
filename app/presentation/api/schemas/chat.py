from typing import Literal
from pydantic import BaseModel, Field
from app.domain.entities.chat import ChatResult

class ChatRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)

class SourceSchema(BaseModel):
    title: str
    url: str
    section: str
    chunk_id: str

class ChunkSchema(BaseModel):
    chunk_id: str
    text: str
    source: str
    url: str
    title: str
    section: str
    document_type: str

class VerificationSchema(BaseModel):
    supported: bool
    explanation: str
    unsupported_claims: list[str]

class ChatResponse(BaseModel):
    question: str
    intent: Literal['documentation_question', 'summary_request']
    answer: str
    agent: str
    sources: list[SourceSchema]
    chunks: list[ChunkSchema]
    verification: VerificationSchema

    @classmethod
    def from_result(cls, result: ChatResult) -> 'ChatResponse':
        return cls.model_validate(result.model_dump())
