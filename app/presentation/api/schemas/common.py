from pydantic import BaseModel, Field

class HealthResponse(BaseModel):
    status: str
    service: str

class ErrorResponse(BaseModel):
    detail: str

class IngestionResponse(BaseModel):
    documents: int
    chunks: int
    sources: list[str] = Field(default_factory=list)
