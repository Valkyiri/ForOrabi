from typing import Protocol
from app.domain.entities.document import Document

class DocumentLoader(Protocol):

    async def load(self) -> list[Document]:
        pass
