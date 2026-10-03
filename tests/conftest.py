import os
import pytest
os.environ.setdefault('ANONYMIZED_TELEMETRY', 'False')

@pytest.fixture(autouse=True)
def clear_cached_settings():
    from app.config import get_settings
    from app.dependencies import get_chat_use_case, get_ingest_use_case
    get_settings.cache_clear()
    get_chat_use_case.cache_clear()
    get_ingest_use_case.cache_clear()
    yield
    get_settings.cache_clear()
    get_chat_use_case.cache_clear()
    get_ingest_use_case.cache_clear()
