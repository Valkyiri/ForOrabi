import logging
import uvicorn
from fastapi import FastAPI
from app.config import get_settings
from app.logging_config import configure_logging
from app.presentation.api.exception_handlers import register_exception_handlers
from app.presentation.api.routes import chat, health, ingestion, ui
logger = logging.getLogger(__name__)

def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    app = FastAPI(title='Multi-Agent FastAPI Documentation RAG Assistant', version='1.0.0', description='Answers questions about the official FastAPI documentation with a LangGraph workflow: router, documentation RAG, summary, and verification.')
    register_exception_handlers(app)
    app.include_router(ui.router)
    app.include_router(health.router)
    app.include_router(chat.router)
    app.include_router(ingestion.router)
    logger.info('Application ready')
    return app
app = create_app()
if __name__ == '__main__':
    uvicorn.run(app, host='127.0.0.1', port=8000, reload=False)
