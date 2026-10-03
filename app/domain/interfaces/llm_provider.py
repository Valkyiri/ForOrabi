from typing import Protocol, TypeVar
from pydantic import BaseModel
T = TypeVar('T', bound=BaseModel)

class LLMProvider(Protocol):

    async def complete(self, *, system_prompt: str, user_prompt: str) -> str:
        pass

    async def complete_structured(self, *, system_prompt: str, user_prompt: str, response_model: type[T]) -> T:
        pass
