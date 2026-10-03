import json
import logging
from pathlib import Path
from app.application.services.chunking_service import ChunkingService
from app.domain.entities.chunk import Chunk
from app.domain.entities.document import Document, IngestionReport
from app.domain.exceptions import IngestionError
from app.domain.interfaces.document_loader import DocumentLoader
from app.domain.interfaces.embedding_provider import EmbeddingProvider
from app.domain.interfaces.vector_store import VectorStore
logger = logging.getLogger(__name__)

class IngestionService:

    def __init__(self, loader: DocumentLoader, chunker: ChunkingService, embeddings: EmbeddingProvider, store: VectorStore, processed_dir: Path) -> None:
        self._loader = loader
        self._chunker = chunker
        self._embeddings = embeddings
        self._store = store
        self._processed_dir = processed_dir

    async def ingest(self) -> IngestionReport:
        documents = await self._loader.load()
        if not documents:
            raise IngestionError('The documentation loader returned no pages.')
        grouped = [(document, self._chunker.chunk_document(document)) for document in documents]
        chunks = [chunk for _, document_chunks in grouped for chunk in document_chunks]
        if not chunks:
            raise IngestionError('Ingestion produced no documentation chunks.')
        self._write_processed(grouped)
        logger.info('Embedding %s chunks', len(chunks))
        vectors = await self._embeddings.embed_documents([chunk.text for chunk in chunks])
        if len(vectors) != len(chunks):
            raise IngestionError('The embedding provider returned an unexpected number of vectors.')
        await self._store.upsert(chunks, vectors)
        sources = [document.url for document, _ in grouped]
        logger.info('Indexed %s chunks from %s documents', len(chunks), len(documents))
        return IngestionReport(documents=len(documents), chunks=len(chunks), sources=sources)

    def _write_processed(self, grouped: list[tuple[Document, list[Chunk]]]) -> None:
        self._processed_dir.mkdir(parents=True, exist_ok=True)
        expected = {document.source for document, _ in grouped}
        for path in self._processed_dir.glob('*.json'):
            if path.stem not in expected:
                path.unlink()
                logger.info('Removed stale processed file %s', path.name)
        for document, chunks in grouped:
            payload = {'source': document.source, 'url': document.url, 'title': document.title, 'chunks': [chunk.model_dump() for chunk in chunks]}
            destination = self._processed_dir / f'{document.source}.json'
            destination.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')
