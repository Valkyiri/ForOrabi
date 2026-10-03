import logging
from app.application.services.retrieval_service import RetrievalService
from app.domain.entities.chat import GeneratedAnswer
from app.domain.entities.chunk import Chunk
from app.domain.interfaces.llm_provider import LLMProvider
from app.domain.messages import INSUFFICIENT_DOCUMENTATION
from app.infrastructure.agents.prompts import SUMMARY_SYSTEM_PROMPT
logger = logging.getLogger(__name__)

class SummaryAgent:
    name = 'summary'

    def __init__(self, llm: LLMProvider, retrieval: RetrievalService) -> None:
        self._llm = llm
        self._retrieval = retrieval

    async def summarize(self, question: str) -> GeneratedAnswer:
        chunks = await self._retrieval.retrieve(question)
        if not chunks:
            logger.info('Summary agent has no retrieved chunks')
            return GeneratedAnswer(answer=INSUFFICIENT_DOCUMENTATION, context='', chunks=[], agent_name=self.name)
        context = self._retrieval.build_context(chunks)
        logger.info('Summary agent summarizing %s chunks', len(chunks))
        answer = await self._llm.complete(system_prompt=SUMMARY_SYSTEM_PROMPT, user_prompt=f'Summary request:\n{question}\n\nDocumentation context:\n{context}')
        return GeneratedAnswer(answer=answer, context=context, chunks=chunks, agent_name=self.name)
