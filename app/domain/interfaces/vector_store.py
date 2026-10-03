from typing import Protocol
from app.domain.entities.chunk import Chunk

class VectorStore(Protocol):

    async def upsert(self, chunks: list[Chunk], embeddings: list[list[float]]) -> None:
        pass

    async def similarity_search(self, embedding: list[float], top_k: int) -> list[Chunk]:
        pass

    async def count(self) -> int:
        pass
