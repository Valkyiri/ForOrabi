import logging
from app.domain.entities.verification import VerificationResult
from app.domain.interfaces.llm_provider import LLMProvider
from app.infrastructure.agents.prompts import VERIFICATION_SYSTEM_PROMPT
logger = logging.getLogger(__name__)

class VerificationAgent:

    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    async def verify(self, *, question: str, answer: str, context: str) -> VerificationResult:
        logger.info('Verifying answer')
        result = await self._llm.complete_structured(system_prompt=VERIFICATION_SYSTEM_PROMPT, user_prompt=f"Question:\n{question}\n\nAnswer:\n{answer}\n\nRetrieved documentation context:\n{context or '(no context retrieved)'}", response_model=VerificationResult)
        logger.info('Verification supported=%s', result.supported)
        return result
