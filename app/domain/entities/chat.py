from typing import Literal
from pydantic import BaseModel, Field
from app.domain.entities.chunk import Chunk
from app.domain.entities.verification import VerificationResult
Intent = Literal['documentation_question', 'summary_request']

class RouteDecision(BaseModel):
    intent: Intent

class SourceReference(BaseModel):
    title: str
    url: str
    section: str
    chunk_id: str

class GeneratedAnswer(BaseModel):
    answer: str
    context: str
    chunks: list[Chunk]
    agent_name: str

class ChatResult(BaseModel):
    question: str
    intent: Intent
    answer: str
    agent: str
    sources: list[SourceReference] = Field(default_factory=list)
    chunks: list[Chunk] = Field(default_factory=list)
    verification: VerificationResult
