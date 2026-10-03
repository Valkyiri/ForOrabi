import hashlib
from app.application.services.retrieval_service import RetrievalService
from app.domain.entities.chunk import Chunk

class FakeEmbeddings:

    def __init__(self, dimensions: int=32) -> None:
        self._dimensions = dimensions

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    async def embed_query(self, text: str) -> list[float]:
        return self._embed(text)

    def _embed(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode()).digest()
        values: list[float] = []
        while len(values) < self._dimensions:
            digest = hashlib.sha256(digest).digest()
            values.extend((byte / 255 for byte in digest))
        return values[:self._dimensions]

class FakeRetrieval:

    def __init__(self, chunks: list[Chunk]) -> None:
        self._chunks = chunks

    async def retrieve(self, question: str) -> list[Chunk]:
        return list(self._chunks)

    def build_context(self, chunks: list[Chunk]) -> str:
        return RetrievalService.build_context(chunks)

class FakeLLM:

    def __init__(self, *, unsupported: bool=False) -> None:
        self.unsupported = unsupported
        self.completions: list[str] = []

    async def complete(self, *, system_prompt: str, user_prompt: str) -> str:
        self.completions.append(system_prompt)
        if self.unsupported and 'Documentation RAG Agent' in system_prompt:
            return 'FastAPI supports the imaginary decorator @app.magic().'
        if 'Summary Agent' in system_prompt:
            return 'Middleware runs for every request.'
        return 'Depends declares a dependency for a path operation.'

    async def complete_structured(self, *, system_prompt: str, user_prompt: str, response_model: type):
        if response_model.__name__ == 'RouteDecision':
            intent = 'summary_request' if 'summarize' in user_prompt.lower() else 'documentation_question'
            return response_model(intent=intent)
        if response_model.__name__ == 'VerificationResult':
            if 'imaginary' in user_prompt:
                return response_model(supported=False, explanation='The decorator is not in the retrieved documentation.', unsupported_claims=['@app.magic() exists'])
            return response_model(supported=True, explanation='The answer is supported by the retrieved documentation.', unsupported_claims=[])
        raise AssertionError(f'Unexpected response model {response_model.__name__}')
