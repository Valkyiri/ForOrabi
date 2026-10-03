from functools import lru_cache
from pathlib import Path
from typing import Literal
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
PROJECT_ROOT = Path(__file__).resolve().parents[1]
LLMProviderName = Literal['gemini', 'openai']

class Settings(BaseSettings):
    llm_provider: str = ''
    gemini_api_key: str = ''
    gemini_model: str = 'gemini-3.5-flash-lite'
    gemini_embedding_model: str = 'models/gemini-embedding-001'
    openai_api_key: str = ''
    openai_model: str = 'gpt-4.1-mini'
    openai_embedding_model: str = 'text-embedding-3-small'
    chroma_path: str = 'data/chroma'
    chroma_collection: str = 'fastapi_docs'
    raw_data_path: str = 'data/raw'
    processed_data_path: str = 'data/processed'
    retrieval_top_k: int = 4
    chunk_max_chars: int = 1400
    chunk_overlap_chars: int = 200
    log_level: str = 'INFO'
    model_config = SettingsConfigDict(env_file=str(PROJECT_ROOT / '.env'), env_file_encoding='utf-8', extra='ignore')

    @model_validator(mode='after')
    def validate_limits(self) -> 'Settings':
        if self.chunk_overlap_chars < 0:
            raise ValueError('chunk_overlap_chars must be zero or greater.')
        if self.chunk_overlap_chars >= self.chunk_max_chars:
            raise ValueError('chunk_overlap_chars must be smaller than chunk_max_chars.')
        if self.retrieval_top_k < 1:
            raise ValueError('retrieval_top_k must be at least 1.')
        if self.llm_provider and self.llm_provider.strip().lower() not in {'gemini', 'openai'}:
            raise ValueError('LLM_PROVIDER must be gemini, openai, or empty for auto-detect.')
        if not self.gemini_model.strip():
            raise ValueError('GEMINI_MODEL must not be empty.')
        if not self.gemini_embedding_model.strip():
            raise ValueError('GEMINI_EMBEDDING_MODEL must not be empty.')
        if not self.openai_model.strip():
            raise ValueError('OPENAI_MODEL must not be empty.')
        if not self.openai_embedding_model.strip():
            raise ValueError('OPENAI_EMBEDDING_MODEL must not be empty.')
        return self

    def resolved_llm_provider(self) -> LLMProviderName:
        explicit = self.llm_provider.strip().lower()
        if explicit == 'gemini':
            return 'gemini'
        if explicit == 'openai':
            return 'openai'
        if self.gemini_api_key.strip():
            return 'gemini'
        if self.openai_api_key.strip():
            return 'openai'
        raise ValueError('No LLM provider can be selected.')

    def path_for(self, value: str) -> Path:
        path = Path(value)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        return path

    @property
    def chroma_dir(self) -> Path:
        return self.path_for(self.chroma_path)

    @property
    def raw_dir(self) -> Path:
        return self.path_for(self.raw_data_path)

    @property
    def processed_dir(self) -> Path:
        return self.path_for(self.processed_data_path)

@lru_cache
def get_settings() -> Settings:
    return Settings()
