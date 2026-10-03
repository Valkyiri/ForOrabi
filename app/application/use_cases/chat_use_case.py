import logging
from app.domain.entities.chat import ChatResult
from app.domain.exceptions import DomainError
from app.domain.interfaces.assistant import AssistantWorkflow
logger = logging.getLogger(__name__)

class ChatUseCase:

    def __init__(self, assistant: AssistantWorkflow) -> None:
        self._assistant = assistant

    async def execute(self, question: str) -> ChatResult:
        cleaned = question.strip()
        if not cleaned:
            raise DomainError('Question must not be empty.')
        logger.info('Handling question: %s', cleaned[:160])
        return await self._assistant.answer(cleaned)
