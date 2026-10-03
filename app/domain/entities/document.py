from typing import Literal
from pydantic import BaseModel, Field

class ContentBlock(BaseModel):
    kind: Literal['paragraph', 'code', 'list']
    text: str

class Section(BaseModel):
    heading: str
    level: int
    blocks: list[ContentBlock] = Field(default_factory=list)

class Document(BaseModel):
    source: str
    url: str
    title: str
    sections: list[Section]

class IngestionReport(BaseModel):
    documents: int
    chunks: int
    sources: list[str]
