import logging
from fastapi import APIRouter, Depends
from app.application.use_cases.ingest_documents_use_case import IngestDocumentsUseCase
from app.dependencies import get_ingest_use_case
from app.presentation.api.schemas.common import ErrorResponse, IngestionResponse
logger = logging.getLogger(__name__)
router = APIRouter(tags=['ingestion'])

@router.post('/ingest', response_model=IngestionResponse, responses={502: {'model': ErrorResponse}, 503: {'model': ErrorResponse}})
async def ingest(use_case: IngestDocumentsUseCase=Depends(get_ingest_use_case)) -> IngestionResponse:
    logger.info('Ingestion request received')
    report = await use_case.execute()
    return IngestionResponse(documents=report.documents, chunks=report.chunks, sources=report.sources)
