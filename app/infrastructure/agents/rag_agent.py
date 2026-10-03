import logging
from app.application.services.retrieval_service import RetrievalService
from app.domain.entities.chat import GeneratedAnswer
from app.domain.entities.chunk import Chunk
from app.domain.interfaces.llm_provider import LLMProvider
from app.domain.messages import INSUFFICIENT_DOCUMENTATION
from app.infrastructure.agents.prompts import RAG_SYSTEM_PROMPT
logger = logging.getLogger(__name__)

class DocumentationRAGAgent:
    name = 'documentation_rag'

    def __init__(self, llm: LLMProvider, retrieval: RetrievalService) -> None:
        self._llm = llm
        self._retrieval = retrieval

    async def answer(self, question: str) -> GeneratedAnswer:
        chunks = await self._retrieval.retrieve(question)
        return await self._generate(question, chunks)

    async def _generate(self, question: str, chunks: list[Chunk]) -> GeneratedAnswer:
        if not chunks:
            logger.info('Documentation RAG agent has no retrieved chunks')
            return GeneratedAnswer(answer=INSUFFICIENT_DOCUMENTATION, context='', chunks=[], agent_name=self.name)
        context = self._retrieval.build_context(chunks)
        logger.info('Documentation RAG agent answering from %s chunks', len(chunks))
        answer = await self._llm.complete(system_prompt=RAG_SYSTEM_PROMPT, user_prompt=f'Question:\n{question}\n\nDocumentation context:\n{context}')
        return GeneratedAnswer(answer=answer, context=context, chunks=chunks, agent_name=self.name)
