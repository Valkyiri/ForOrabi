from pydantic import BaseModel, Field
DOCUMENT_TYPE = 'fastapi_documentation'

class Chunk(BaseModel):
    chunk_id: str
    text: str
    source: str
    url: str
    title: str
    section: str
    document_type: str = Field(default=DOCUMENT_TYPE)

    def to_metadata(self) -> dict[str, str]:
        return {'source': self.source, 'url': self.url, 'title': self.title, 'section': self.section, 'chunk_id': self.chunk_id, 'document_type': self.document_type}
