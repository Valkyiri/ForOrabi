import logging
from app.application.services.ingestion_service import IngestionService
from app.domain.entities.document import IngestionReport
logger = logging.getLogger(__name__)

class IngestDocumentsUseCase:

    def __init__(self, ingestion: IngestionService) -> None:
        self._ingestion = ingestion

    async def execute(self) -> IngestionReport:
        logger.info('Starting FastAPI documentation ingestion')
        report = await self._ingestion.ingest()
        logger.info('Ingestion finished: %s documents, %s chunks', report.documents, report.chunks)
        return report
