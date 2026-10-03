import logging
import re
from app.domain.entities.chat import RouteDecision
from app.domain.interfaces.llm_provider import LLMProvider
logger = logging.getLogger(__name__)
_SUMMARY_PATTERN = re.compile('\\b(summarize|summarise|summary|recap|overview|give me an overview)\\b', re.IGNORECASE)

class RouterAgent:

    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    async def route(self, question: str) -> RouteDecision:
        logger.info('Routing question')
        if _SUMMARY_PATTERN.search(question):
            decision = RouteDecision(intent='summary_request')
        else:
            decision = RouteDecision(intent='documentation_question')
        logger.info('Router selected intent %s', decision.intent)
        return decision
