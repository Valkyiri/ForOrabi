import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar
from langchain_core.embeddings import Embeddings
from app.domain.exceptions import ExternalServiceError
logger = logging.getLogger(__name__)
T = TypeVar('T')
_BATCH_SIZE = 20
_MAX_RETRIES = 6
_RETRY_SECONDS = 25

class LangChainEmbeddingProvider:

    def __init__(self, embeddings: Embeddings) -> None:
        self._embeddings = embeddings

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors: list[list[float]] = []
        for start in range(0, len(texts), _BATCH_SIZE):
            batch = texts[start:start + _BATCH_SIZE]
            vectors.extend(await self._with_retry(lambda b=batch: self._embeddings.aembed_documents(b)))
        if len(vectors) != len(texts):
            raise ExternalServiceError('The embedding provider returned an unexpected number of vectors.')
        return vectors

    async def embed_query(self, text: str) -> list[float]:
        return await self._with_retry(lambda: self._embeddings.aembed_query(text))

    async def _with_retry(self, operation: Callable[[], Awaitable[T]]) -> T:
        last_error: Exception | None = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                return await operation()
            except Exception as exc:
                last_error = exc
                if not _is_rate_limit(exc) or attempt == _MAX_RETRIES:
                    logger.exception('LangChain embedding request failed')
                    raise ExternalServiceError('The embedding request failed.') from exc
                logger.warning('Embedding rate limit hit; retrying in %s seconds (attempt %s/%s)', _RETRY_SECONDS, attempt, _MAX_RETRIES)
                await asyncio.sleep(_RETRY_SECONDS)
        raise ExternalServiceError('The embedding request failed.') from last_error

def _is_rate_limit(exc: Exception) -> bool:
    text = str(exc).upper()
    return 'RESOURCE_EXHAUSTED' in text or '429' in text
