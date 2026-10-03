from app.application.services.chunking_service import ChunkingService
from app.application.services.ingestion_service import IngestionService
from app.application.use_cases.ingest_documents_use_case import IngestDocumentsUseCase
from app.domain.entities.document import ContentBlock, Document, Section
from app.infrastructure.vector_store.chroma_store import ChromaVectorStore
from tests.fakes import FakeEmbeddings

class _Loader:

    def __init__(self, documents: list[Document]) -> None:
        self.documents = documents

    async def load(self) -> list[Document]:
        return self.documents

def _document(source: str, sentence: str) -> Document:
    return Document(source=source, url=f'https://fastapi.tiangolo.com/tutorial/{source}/', title=source, sections=[Section(heading=source, level=1, blocks=[ContentBlock(kind='paragraph', text=sentence)])])

async def test_ingestion_updates_chunks_without_duplicating_them(tmp_path) -> None:
    store = ChromaVectorStore(tmp_path / 'chroma', 'fastapi_docs')
    loader = _Loader([_document('path-params', 'Alpha unique sentence about path parameters.'), _document('dependencies', 'Beta unique sentence about dependencies.')])
    service = IngestionService(loader=loader, chunker=ChunkingService(max_chars=400, overlap_chars=50), embeddings=FakeEmbeddings(), store=store, processed_dir=tmp_path / 'processed')
    use_case = IngestDocumentsUseCase(service)
    try:
        first = await use_case.execute()
        second = await use_case.execute()
        assert first.chunks == second.chunks == 2
        assert await store.count() == 2
        assert len(list((tmp_path / 'processed').glob('*.json'))) == 2
        loader.documents = [_document('path-params', 'Alpha revised sentence about query parameters.'), _document('dependencies', 'Beta unique sentence about dependencies.')]
        third = await use_case.execute()
        texts = await store.fetch_texts()
        joined = '\n'.join(texts)
        assert await store.count() == third.chunks == 2
        assert 'Alpha unique sentence' not in joined
        assert 'Alpha revised sentence' in joined
        assert 'Beta unique sentence' in joined
    finally:
        store.close()
