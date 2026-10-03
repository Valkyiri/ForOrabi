import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.domain.exceptions import ConfigurationError, DomainError, EmptyCorpusError, ExternalServiceError, IngestionError
logger = logging.getLogger(__name__)

def status_code_for(exc: DomainError) -> int:
    if isinstance(exc, ConfigurationError):
        return 503
    if isinstance(exc, EmptyCorpusError):
        return 409
    if isinstance(exc, (ExternalServiceError, IngestionError)):
        return 502
    return 400

def register_exception_handlers(app: FastAPI) -> None:

    @app.exception_handler(DomainError)
    async def handle_domain_error(request: Request, exc: DomainError) -> JSONResponse:
        logger.warning('Request failed: %s', exc)
        return JSONResponse(status_code=status_code_for(exc), content={'detail': str(exc)})

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception('Unhandled error on %s', request.url.path)
        return JSONResponse(status_code=500, content={'detail': 'An unexpected error occurred.'})
