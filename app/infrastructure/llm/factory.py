import logging
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from app.config import Settings
from app.domain.exceptions import ConfigurationError
from app.infrastructure.embeddings.langchain_embeddings import LangChainEmbeddingProvider
from app.infrastructure.llm.langchain_provider import LangChainChatProvider
logger = logging.getLogger(__name__)
_GEMINI_CHAT_FALLBACKS = ('gemini-3.5-flash-lite', 'gemini-flash-lite-latest', 'gemini-3.7-flash', 'gemini-3.5-flash')

def require_llm_provider(settings: Settings) -> str:
    try:
        provider = settings.resolved_llm_provider()
    except ValueError as exc:
        raise ConfigurationError('Set GEMINI_API_KEY or OPENAI_API_KEY in the environment or a .env file.') from exc
    if provider == 'gemini' and (not settings.gemini_api_key.strip()):
        raise ConfigurationError('GEMINI_API_KEY is not set. Add it to the environment or a .env file.')
    if provider == 'openai' and (not settings.openai_api_key.strip()):
        raise ConfigurationError('OPENAI_API_KEY is not set. Add it to the environment or a .env file.')
    return provider

def build_chat_provider(settings: Settings) -> LangChainChatProvider:
    provider = require_llm_provider(settings)
    if provider == 'gemini':
        names = _unique_models(settings.gemini_model, *_GEMINI_CHAT_FALLBACKS)
        logger.info('Using LangChain Gemini chat models %s', ', '.join(names))
        models = [ChatGoogleGenerativeAI(model=name, google_api_key=settings.gemini_api_key, temperature=0, timeout=60) for name in names]
        return LangChainChatProvider(models)
    logger.info('Using LangChain OpenAI chat model %s', settings.openai_model)
    return LangChainChatProvider(ChatOpenAI(model=settings.openai_model, api_key=settings.openai_api_key, temperature=0, timeout=60))

def build_embedding_provider(settings: Settings) -> LangChainEmbeddingProvider:
    provider = require_llm_provider(settings)
    if provider == 'gemini':
        logger.info('Using LangChain Gemini embeddings %s', settings.gemini_embedding_model)
        embeddings = GoogleGenerativeAIEmbeddings(model=settings.gemini_embedding_model, google_api_key=settings.gemini_api_key)
    else:
        logger.info('Using LangChain OpenAI embeddings %s', settings.openai_embedding_model)
        embeddings = OpenAIEmbeddings(model=settings.openai_embedding_model, api_key=settings.openai_api_key, timeout=60)
    return LangChainEmbeddingProvider(embeddings)

def _unique_models(*names: str) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for name in names:
        cleaned = name.strip()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            ordered.append(cleaned)
    return ordered
