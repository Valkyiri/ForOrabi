import asyncio
import logging
import os
from pathlib import Path
os.environ.setdefault('ANONYMIZED_TELEMETRY', 'False')
import chromadb
from app.domain.entities.chunk import DOCUMENT_TYPE, Chunk
from app.domain.exceptions import ExternalServiceError
logger = logging.getLogger(__name__)
_PAGE_SIZE = 500
_UPSERT_BATCH = 100

class ChromaVectorStore:

    def __init__(self, path: Path, collection_name: str) -> None:
        path.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(path))
        self._collection = self._client.get_or_create_collection(name=collection_name, metadata={'hnsw:space': 'cosine'})

    async def upsert(self, chunks: list[Chunk], embeddings: list[list[float]]) -> None:
        if len(chunks) != len(embeddings):
            raise ExternalServiceError('Embedding count does not match chunk count.')
        seen: set[str] = set()
        unique_chunks: list[Chunk] = []
        unique_vectors: list[list[float]] = []
        for chunk, vector in zip(chunks, embeddings, strict=True):
            if chunk.chunk_id in seen:
                continue
            seen.add(chunk.chunk_id)
            unique_chunks.append(chunk)
            unique_vectors.append(vector)
        await asyncio.to_thread(self._upsert_sync, unique_chunks, unique_vectors)

    async def similarity_search(self, embedding: list[float], top_k: int) -> list[Chunk]:
        return await asyncio.to_thread(self._search_sync, embedding, top_k)

    async def count(self) -> int:
        return await asyncio.to_thread(self._collection.count)

    async def fetch_texts(self) -> list[str]:
        return await asyncio.to_thread(self._fetch_texts_sync)

    def close(self) -> None:
        self._collection = None
        self._client = None
        try:
            from chromadb.api.client import SharedSystemClient
            SharedSystemClient.clear_system_cache()
        except Exception:
            logger.debug('Chroma system cache was not cleared', exc_info=True)

    def _upsert_sync(self, chunks: list[Chunk], embeddings: list[list[float]]) -> None:
        try:
            keep_by_url: dict[str, set[str]] = {}
            for chunk in chunks:
                keep_by_url.setdefault(chunk.url, set()).add(chunk.chunk_id)
            for start in range(0, len(chunks), _UPSERT_BATCH):
                batch = chunks[start:start + _UPSERT_BATCH]
                vectors = embeddings[start:start + _UPSERT_BATCH]
                self._collection.upsert(ids=[chunk.chunk_id for chunk in batch], documents=[chunk.text for chunk in batch], embeddings=vectors, metadatas=[chunk.to_metadata() for chunk in batch])
            stale = self._stale_ids(keep_by_url)
            if stale:
                self._collection.delete(ids=stale)
                logger.info('Removed %s stale chunks', len(stale))
        except ExternalServiceError:
            raise
        except Exception as exc:
            self._raise_store_error(exc)

    def _search_sync(self, embedding: list[float], top_k: int) -> list[Chunk]:
        try:
            total = self._collection.count()
            if total == 0:
                return []
            result = self._collection.query(query_embeddings=[embedding], n_results=min(top_k, total), include=['documents', 'metadatas'])
        except Exception as exc:
            self._raise_store_error(exc)
        ids = (result.get('ids') or [[]])[0]
        documents = (result.get('documents') or [[]])[0]
        metadatas = (result.get('metadatas') or [[]])[0]
        chunks: list[Chunk] = []
        for chunk_id, document, metadata in zip(ids, documents, metadatas):
            metadata = metadata or {}
            chunks.append(Chunk(chunk_id=str(metadata.get('chunk_id') or chunk_id), text=document or '', source=str(metadata.get('source') or ''), url=str(metadata.get('url') or ''), title=str(metadata.get('title') or ''), section=str(metadata.get('section') or ''), document_type=str(metadata.get('document_type') or DOCUMENT_TYPE)))
        return chunks

    def _stale_ids(self, keep_by_url: dict[str, set[str]]) -> list[str]:
        stale: list[str] = []
        offset = 0
        while True:
            existing = self._collection.get(include=['metadatas'], limit=_PAGE_SIZE, offset=offset)
            ids = existing.get('ids') or []
            metadatas = existing.get('metadatas') or []
            if not ids:
                break
            for chunk_id, metadata in zip(ids, metadatas):
                metadata = metadata or {}
                url = str(metadata.get('url') or '')
                allowed = keep_by_url.get(url)
                if allowed is None or chunk_id not in allowed:
                    stale.append(chunk_id)
            if len(ids) < _PAGE_SIZE:
                break
            offset += _PAGE_SIZE
        return stale

    def _fetch_texts_sync(self) -> list[str]:
        texts: list[str] = []
        offset = 0
        while True:
            existing = self._collection.get(include=['documents'], limit=_PAGE_SIZE, offset=offset)
            documents = existing.get('documents') or []
            if not documents:
                break
            texts.extend((document or '' for document in documents))
            if len(documents) < _PAGE_SIZE:
                break
            offset += _PAGE_SIZE
        return texts

    @staticmethod
    def _raise_store_error(exc: Exception) -> None:
        message = str(exc).lower()
        if 'dimension' in message:
            raise ExternalServiceError('The stored embeddings do not match the current embedding model. Delete data/chroma and run ingestion again.') from exc
        logger.exception('ChromaDB request failed')
        raise ExternalServiceError('The vector store request failed.') from exc
