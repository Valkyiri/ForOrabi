from typing import Protocol
from app.domain.entities.chat import ChatResult

class AssistantWorkflow(Protocol):

    async def answer(self, question: str) -> ChatResult:
        pass
