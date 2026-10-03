from pydantic import BaseModel, Field

class VerificationResult(BaseModel):
    supported: bool
    explanation: str
    unsupported_claims: list[str] = Field(default_factory=list)
