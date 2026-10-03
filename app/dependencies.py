from functools import lru_cache
from app.application.services.chunking_service import ChunkingService
from app.application.services.ingestion_service import IngestionService
from app.application.services.retrieval_service import RetrievalService
from app.application.use_cases.chat_use_case import ChatUseCase
from app.application.use_cases.ingest_documents_use_case import IngestDocumentsUseCase
from app.config import Settings, get_settings
from app.infrastructure.agents.graph import DocumentationAssistantGraph
from app.infrastructure.ingestion.fastapi_loader import FastAPIDocumentationLoader
from app.infrastructure.llm.factory import build_chat_provider, build_embedding_provider
from app.infrastructure.vector_store.chroma_store import ChromaVectorStore

def build_chat_use_case(settings: Settings | None=None) -> ChatUseCase:
    settings = settings or get_settings()
    llm = build_chat_provider(settings)
    embeddings = build_embedding_provider(settings)
    store = ChromaVectorStore(settings.chroma_dir, settings.chroma_collection)
    retrieval = RetrievalService(embeddings, store, top_k=settings.retrieval_top_k)
    assistant = DocumentationAssistantGraph(llm, retrieval)
    return ChatUseCase(assistant)

def build_ingest_use_case(settings: Settings | None=None) -> IngestDocumentsUseCase:
    settings = settings or get_settings()
    embeddings = build_embedding_provider(settings)
    loader = FastAPIDocumentationLoader(settings.raw_dir)
    chunker = ChunkingService(max_chars=settings.chunk_max_chars, overlap_chars=settings.chunk_overlap_chars)
    store = ChromaVectorStore(settings.chroma_dir, settings.chroma_collection)
    service = IngestionService(loader=loader, chunker=chunker, embeddings=embeddings, store=store, processed_dir=settings.processed_dir)
    return IngestDocumentsUseCase(service)

@lru_cache
def get_chat_use_case() -> ChatUseCase:
    return build_chat_use_case()

@lru_cache
def get_ingest_use_case() -> IngestDocumentsUseCase:
    return build_ingest_use_case()
