import logging
from app.domain.entities.chat import SourceReference
from app.domain.entities.chunk import Chunk
from app.domain.exceptions import EmptyCorpusError
from app.domain.interfaces.embedding_provider import EmbeddingProvider
from app.domain.interfaces.vector_store import VectorStore
logger = logging.getLogger(__name__)

class RetrievalService:

    def __init__(self, embeddings: EmbeddingProvider, store: VectorStore, top_k: int=4) -> None:
        if top_k < 1:
            raise ValueError('top_k must be at least 1.')
        self._embeddings = embeddings
        self._store = store
        self._top_k = top_k

    async def retrieve(self, question: str) -> list[Chunk]:
        total = await self._store.count()
        if total == 0:
            raise EmptyCorpusError('No FastAPI documentation is indexed. Run ingestion before asking questions.')
        logger.info('Embedding question for retrieval')
        vector = await self._embeddings.embed_query(question)
        chunks = await self._store.similarity_search(vector, self._top_k)
        logger.info('Retrieved %s chunks', len(chunks))
        return chunks

    @staticmethod
    def build_context(chunks: list[Chunk]) -> str:
        if not chunks:
            return ''
        parts: list[str] = []
        for index, chunk in enumerate(chunks, start=1):
            parts.append('\n'.join([f'[{index}] Title: {chunk.title}', f'Section: {chunk.section}', f'URL: {chunk.url}', chunk.text]))
        return '\n\n---\n\n'.join(parts)

    @staticmethod
    def collect_sources(chunks: list[Chunk]) -> list[SourceReference]:
        sources: list[SourceReference] = []
        seen: set[tuple[str, str]] = set()
        for chunk in chunks:
            key = (chunk.url, chunk.section)
            if key in seen:
                continue
            seen.add(key)
            sources.append(SourceReference(title=chunk.title, url=chunk.url, section=chunk.section, chunk_id=chunk.chunk_id))
        return sources
