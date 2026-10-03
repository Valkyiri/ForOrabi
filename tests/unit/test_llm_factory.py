import pytest
from app.config import Settings
from app.domain.exceptions import ConfigurationError
from app.infrastructure.llm.factory import require_llm_provider

def test_auto_selects_gemini_when_that_key_is_set() -> None:
    settings = Settings(llm_provider='', gemini_api_key='gemini-test-key', openai_api_key='')
    assert require_llm_provider(settings) == 'gemini'

def test_auto_selects_openai_when_only_that_key_is_set() -> None:
    settings = Settings(llm_provider='', gemini_api_key='', openai_api_key='openai-test-key')
    assert require_llm_provider(settings) == 'openai'

def test_explicit_openai_requires_openai_key() -> None:
    settings = Settings(llm_provider='openai', gemini_api_key='gemini-test-key', openai_api_key='')
    with pytest.raises(ConfigurationError, match='OPENAI_API_KEY'):
        require_llm_provider(settings)

def test_missing_keys_raise_configuration_error() -> None:
    settings = Settings(llm_provider='', gemini_api_key='', openai_api_key='')
    with pytest.raises(ConfigurationError, match='GEMINI_API_KEY or OPENAI_API_KEY'):
        require_llm_provider(settings)
