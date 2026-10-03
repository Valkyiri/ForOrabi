import pytest
from app.application.services.retrieval_service import RetrievalService
from app.domain.entities.chunk import Chunk
from app.domain.exceptions import EmptyCorpusError

def _chunk() -> Chunk:
    return Chunk(chunk_id='chunk-1', text='Depends declares a dependency.', source='tutorial_dependencies', url='https://fastapi.tiangolo.com/tutorial/dependencies/', title='Dependencies', section='Dependencies > Use Depends', document_type='fastapi_documentation')

def test_context_includes_section_and_url() -> None:
    chunk = _chunk()
    context = RetrievalService.build_context([chunk])
    assert chunk.url in context
    assert chunk.section in context
    assert chunk.text in context
    assert RetrievalService.build_context([]) == ''

def test_sources_are_deduplicated_by_section() -> None:
    chunk = _chunk()
    duplicate = chunk.model_copy(update={'chunk_id': 'chunk-2'})
    sources = RetrievalService.collect_sources([chunk, duplicate])
    assert len(sources) == 1
    assert sources[0].section == chunk.section
    assert sources[0].chunk_id == chunk.chunk_id

class _EmptyStore:

    async def count(self) -> int:
        return 0

    async def similarity_search(self, embedding: list[float], top_k: int) -> list[Chunk]:
        return []

    async def upsert(self, chunks: list[Chunk], embeddings: list[list[float]]) -> None:
        return None

class _Embeddings:

    async def embed_query(self, text: str) -> list[float]:
        return [0.1, 0.2]

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[0.1, 0.2] for _ in texts]

async def test_empty_corpus_raises() -> None:
    service = RetrievalService(_Embeddings(), _EmptyStore(), top_k=4)
    with pytest.raises(EmptyCorpusError):
        await service.retrieve('How does Depends work?')
